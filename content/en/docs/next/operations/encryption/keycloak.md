---
title: "Encrypting Keycloak User Data"
linkTitle: "Keycloak"
description: "Encrypt usernames, emails, names and credentials of the platform Keycloak in PostgreSQL with keycloak-kms-proxy and HashiCorp Vault"
weight: 20
---

The platform Keycloak keeps its users in PostgreSQL in plain text: anyone with access to the database, a dump or a backup can read every username, email and name. [keycloak-kms-proxy](https://github.com/cozystack/keycloak-kms-proxy) sits between Keycloak and PostgreSQL and encrypts these columns on the way in and decrypts them on the way out, so the database holds only ciphertext.

The proxy encrypts the columns with data encryption keys (DEKs). The DEKs are stored wrapped by a key in [HashiCorp Vault](https://developer.hashicorp.com/vault/docs/secrets/transit) Transit and are unwrapped in memory when the proxy starts.

The platform Keycloak exists only when OIDC is enabled; see [Enable OIDC](/docs/next/operations/oidc/enable_oidc/).

## What Is Encrypted

| Column | Encryption | Effect |
| --- | --- | --- |
| `USER_ENTITY.USERNAME`, `USER_ENTITY.EMAIL` | Deterministic, lower-cased first | Login by username or email keeps working |
| `USER_ENTITY.FIRST_NAME`, `USER_ENTITY.LAST_NAME` | Randomized | Cannot be searched |
| `USER_ATTRIBUTE.VALUE`, `USER_ATTRIBUTE.LONG_VALUE` of attributes whose name starts with `pii-` | Randomized | Cannot be searched |
| `CREDENTIAL.SECRET_DATA`, `CREDENTIAL.CREDENTIAL_DATA` | Randomized | Adds a layer on top of password hashing |

Everything else is stored as before. In the admin console, a search by username or email works only for an exact value: a substring search does not find encrypted users.

Encrypted values start with the `$KKP$` marker.

{{% alert color="warning" %}}
Always set `encryption.deksetSecretName`. Without it, the proxy generates a new DEK every time it starts and keeps it only in memory, so after a restart of the proxy pod it can no longer decrypt anything it has encrypted before.
{{% /alert %}}

## Prerequisites

- OIDC enabled, so that the `cozystack.keycloak` package is installed.
- A HashiCorp Vault server reachable from the management cluster, and a Vault token that can create a Transit key and use it once to encrypt.
- Go, to run the proxy's backfill tool from source; it is not part of the proxy image.
- `kubectl` and the `flux` CLI. No local `psql` is needed: the check below runs it inside the database pod.
- A maintenance window. Keycloak is stopped while the existing rows are encrypted.

## 1. Prepare Vault

Create a Transit key for Keycloak:

```bash
vault secrets enable transit
vault write -f transit/keys/keycloak
```

The proxy only encrypts and decrypts with this key:

```hcl
# keycloak-kms-proxy.hcl
path "transit/encrypt/keycloak" {
  capabilities = ["update"]
}
path "transit/decrypt/keycloak" {
  capabilities = ["update"]
}
```

```bash
vault policy write keycloak-kms-proxy keycloak-kms-proxy.hcl
```

The recommended way for the proxy to log in is the [Kubernetes auth method](https://developer.hashicorp.com/vault/docs/auth/kubernetes), so that no Vault credential is stored in the cluster. Configure the auth method for the management cluster as described in the Vault documentation, then bind a role to the proxy's ServiceAccount:

```bash
vault write auth/kubernetes/role/keycloak-kms-proxy \
  bound_service_account_names=keycloak-kms-proxy \
  bound_service_account_namespaces=cozy-keycloak \
  policies=keycloak-kms-proxy \
  ttl=1h
```

AppRole and a static token are supported too; see [Other Vault Login Methods](#other-vault-login-methods).

## 2. Create the DEK Set

Generate the DEKs, wrapped by the Transit key, with the backfill tool of the proxy version your Cozystack ships (`0.2.3` in this release):

```bash
git clone --branch v0.2.3 https://github.com/cozystack/keycloak-kms-proxy
cd keycloak-kms-proxy
go run ./cmd/backfill generate-dekset \
  -vault-addr https://vault.example.com:8200 \
  -vault-token "$VAULT_TOKEN" \
  -vault-mount transit \
  -vault-key keycloak \
  -out dekset.json
```

Store the result in a Secret next to Keycloak:

```bash
kubectl --namespace cozy-keycloak create secret generic keycloak-dekset \
  --from-file=dekset.json=dekset.json
```

`dekset.json` is useless without the Vault key, but the Vault key is useless without it too: keep a copy of this file in your backups. Losing either one makes the encrypted data unreadable.

## 3. Encrypt the Existing Rows

Enabling the proxy also switches Keycloak to it, so the rows that are already in the database must be encrypted first. Otherwise logins by username or email stop working.

Take a backup of the `keycloak-db` database, then stop Keycloak. Suspend its HelmRelease first, or Flux scales it back up:

```bash
flux suspend helmrelease keycloak --namespace cozy-keycloak
REPLICAS=$(kubectl --namespace cozy-keycloak get statefulset keycloak --output jsonpath='{.spec.replicas}')
kubectl --namespace cozy-keycloak scale statefulset keycloak --replicas=0
kubectl --namespace cozy-keycloak rollout status statefulset keycloak --timeout=5m
```

Open a connection to the database and run the backfill from the same checkout:

```bash
kubectl --namespace cozy-keycloak port-forward service/keycloak-db-rw 5432:5432 &

DB_USER=$(kubectl --namespace cozy-keycloak get secret keycloak-db-app --output jsonpath='{.data.username}' | base64 -d)
DB_PASS=$(kubectl --namespace cozy-keycloak get secret keycloak-db-app --output jsonpath='{.data.password}' | base64 -d)
DB_NAME=$(kubectl --namespace cozy-keycloak get secret keycloak-db-app --output jsonpath='{.data.dbname}' | base64 -d)

go run ./cmd/backfill encrypt-rows \
  -dekset dekset.json \
  -vault-addr https://vault.example.com:8200 \
  -vault-token "$VAULT_TOKEN" \
  -vault-mount transit \
  -vault-key keycloak \
  -dsn "postgres://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}"
```

The backfill skips values that already carry the `$KKP$` marker, so running it again is safe.

## 4. Enable the Proxy

Set the encryption values on the `cozystack.keycloak` package:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.keycloak
spec:
  variant: default
  components:
    keycloak:
      values:
        encryption:
          enabled: true
          deksetSecretName: keycloak-dekset
          replicas: 2
          kms:
            backend: vault-transit
            vault:
              address: https://vault.example.com:8200
              mount: transit
              keyName: keycloak
              auth: kubernetes
              kubernetes:
                role: keycloak-kms-proxy
```

```bash
kubectl apply --server-side --filename keycloak-package.yaml
flux resume helmrelease keycloak --namespace cozy-keycloak
```

Flux deploys the proxy and updates Keycloak to point at it. If the `keycloak` StatefulSet stays at zero replicas afterwards, scale it back with `kubectl --namespace cozy-keycloak scale statefulset keycloak --replicas="$REPLICAS"`. With a shared DEK set the proxy can run more than one replica; without `deksetSecretName`, `replicas` above 1 is refused.

If Vault uses a private CA, add it as `encryption.kms.vault.caBundle` (PEM), or reference an existing Secret with `encryption.kms.vault.caSecretName` and `caSecretKey`.

## 5. Verify

Check that the proxy and Keycloak are running and that a known user can log in:

```bash
kubectl --namespace cozy-keycloak get pods
```

Then look at the raw data in PostgreSQL. No email must be left without the `$KKP$` marker:

```bash
DB_NAME=$(kubectl --namespace cozy-keycloak get secret keycloak-db-app --output jsonpath='{.data.dbname}' | base64 -d)
kubectl --namespace cozy-keycloak exec -i keycloak-db-1 --container postgres -- \
  psql --dbname "$DB_NAME" --tuples-only <<'SQL'
SELECT count(*) FROM user_entity
WHERE email IS NOT NULL AND email NOT LIKE '$KKP$%';
SQL
```

The proxy exposes Prometheus metrics on port 9090 of the `keycloak-kms-proxy` Service. `kkp_decrypt_failures_total` must stay at zero.

## Other Vault Login Methods

Set `encryption.kms.vault.auth` to one of:

- `kubernetes`: the proxy logs in with its ServiceAccount `keycloak-kms-proxy`. Set `kubernetes.role`, and `kubernetes.mount` if the auth method is not mounted at `kubernetes`.
- `approle`: create a Secret in `cozy-keycloak` with the keys `role-id` and `secret-id`, and set `appRole.secretName` (and `appRole.mount` if it is not `approle`). The proxy logs in again with the same secret ID when its token expires, so the secret ID must not expire or run out of uses.
- `token`: create a Secret in `cozy-keycloak` with the key `token` and set `tokenSecretName`. The proxy never renews this token, so an expired token surfaces on the next proxy restart.

## Key Rotation

Rotating the Transit key needs no change in the cluster: the DEK set stays wrapped with the old key version, which Vault keeps.

```bash
vault write -f transit/keys/keycloak/rotate
```

Rotating the DEKs themselves is not supported by the current proxy tools.

## Limitations

- There is no way back. The tools cannot decrypt the data, and switching `encryption.enabled` off makes Keycloak read ciphertext. To undo the encryption, restore the database backup taken before step 3.
- If Vault is unreachable when the proxy starts, the proxy does not start and Keycloak answers logins with an internal error. A running proxy keeps its DEKs in memory and is not affected by a Vault outage.
- Writes to the database that bypass the proxy, such as manual SQL, are stored in plain text.
