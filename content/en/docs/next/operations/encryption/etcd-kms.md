---
title: "Encrypting etcd with KMS v2"
linkTitle: "etcd with KMS v2"
description: "Encrypt Secrets and application values in the management cluster etcd with a key held in HashiCorp Vault, using KMS v2 on Talos Linux"
weight: 10
---

This guide moves the encryption key of the management cluster etcd out of the cluster. kube-apiserver encrypts each object with a data encryption key (DEK), and the DEK is encrypted by a key encryption key (KEK) that stays in [HashiCorp Vault](https://developer.hashicorp.com/vault/docs/secrets/transit) Transit. [vault-kubernetes-kms](https://github.com/FalcoSuessgott/vault-kubernetes-kms) is the [KMS v2](https://kubernetes.io/docs/tasks/administer-cluster/kms-provider/) plugin that connects kube-apiserver to Vault.

After you finish, an etcd snapshot or a stolen disk no longer exposes Secrets or application values: decrypting them requires a call to Vault from one of the control-plane nodes. See [Encryption at Rest](/docs/next/operations/encryption/) for what is stored where.

## How It Fits Together

On every control-plane node:

1. The KMS plugin runs as a Talos static pod on the host network and listens on a Unix socket in `/var/kms`.
2. kube-apiserver mounts `/var/kms` and reaches the plugin through that socket.
3. Talos renders the kube-apiserver `EncryptionConfiguration` from the `KubeEtcdEncryptionConfig` document in the machine configuration.
4. The plugin authenticates to Vault with AppRole and asks Transit to encrypt and decrypt DEKs with a key that cannot be exported.

The plugin must be a static pod rather than a Deployment: kube-apiserver needs it to read Secrets, so it has to start before the API server does.

## Prerequisites

- Talos Linux v1.14 or later on all control-plane nodes. Talos v1.13 generates the encryption configuration itself and does not allow replacing it; the `KubeEtcdEncryptionConfig` document first appeared in [Talos v1.14](https://docs.siderolabs.com/talos/v1.14/reference/configuration/kubernetes/kubeetcdencryptionconfig). Clusters installed with an earlier Cozystack release may still run Talos v1.13; upgrade them first (see [step 1](#1-upgrade-talos)).
- A Kubernetes version supported by Talos v1.14: 1.33 to 1.37, per the [Talos support matrix](https://docs.siderolabs.com/talos/v1.14/getting-started/support-matrix).
- Talm v0.35.0 or later. Earlier releases cannot render configuration for Talos v1.14 nodes. Keep `talosVersion` in `Chart.yaml` at `v1.13` or lower, as the Talm documentation requires.
- A HashiCorp Vault server reachable from every control-plane node, with permission to enable a secrets engine and an auth method. The examples below use `https://vault.example.com:8200`.
- `talosctl` with the `os:admin` role, and `kubectl` with cluster-admin access to the management cluster.
- For verification: `etcd`, `etcdutl` and `etcdctl` binaries of the same minor version as the cluster etcd (Talos v1.14.1 runs etcd v3.7.1), and `jq`.

{{% alert color="warning" %}}
Vault becomes a dependency of the Kubernetes API. If the Transit key is lost, every Secret encrypted with it is lost as well, and an etcd backup does not help: it holds only ciphertext. Back up Vault, and never delete or trim the Transit key while Secrets encrypted with it may still exist.
{{% /alert %}}

## 1. Upgrade Talos

Skip this step if the control-plane nodes already run Talos v1.14 or later (`talosctl --nodes <cp-ip> version`).

Talos v1.14 no longer loads kernel modules on demand, and DRBD loads its network transport that way. Without the module loaded explicitly, DRBD resources on an upgraded node stay in `Connecting`. The module is already present on Talos v1.13, so add it to the `values.yaml` of your Talm project and apply it to every node before the upgrade:

```yaml
extraKernelModules:
  - name: drbd_transport_tcp
```

Then set the Talos image of this release in `values.yaml` and upgrade the nodes one at a time, waiting for each node to come back and for LINSTOR resources to be in sync before the next one:

```yaml
image: "ghcr.io/cozystack/cozystack/talos:{{< version-pin "talos" >}}"
```

```bash
talm upgrade -f nodes/cp1.yaml
```

## 2. Prepare Vault

Enable the Transit secrets engine and create a key for this cluster. Use a separate key per cluster. By default a Transit key is `aes256-gcm96`, cannot be exported and cannot be deleted.

```bash
vault secrets enable transit
vault write -f transit/keys/mgmt-etcd
```

Create a policy that allows the plugin to use this key and nothing else. The plugin reads the key to report its current version to kube-apiserver, so `read` on the key is required:

```hcl
# mgmt-etcd-kms.hcl
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
path "transit/encrypt/mgmt-etcd" {
  capabilities = ["update"]
}
path "transit/decrypt/mgmt-etcd" {
  capabilities = ["update"]
}
path "transit/keys/mgmt-etcd" {
  capabilities = ["read"]
}
```

```bash
vault policy write mgmt-etcd-kms mgmt-etcd-kms.hcl
```

Enable AppRole and create a role bound to the control-plane node addresses. The binding matters: the plugin credentials end up in the machine configuration, and with `secret_id_bound_cidrs` and `token_bound_cidrs` a credential copied from a stolen disk is useless anywhere but on the control-plane nodes themselves.

```bash
vault auth enable approle
vault write auth/approle/role/mgmt-etcd-kms \
  token_policies=mgmt-etcd-kms \
  secret_id_bound_cidrs=192.168.100.11/32,192.168.100.12/32,192.168.100.13/32 \
  token_bound_cidrs=192.168.100.11/32,192.168.100.12/32,192.168.100.13/32 \
  secret_id_ttl=0 \
  secret_id_num_uses=0 \
  token_ttl=1h \
  token_max_ttl=4h
vault read -field=role_id auth/approle/role/mgmt-etcd-kms/role-id
vault write -f -field=secret_id auth/approle/role/mgmt-etcd-kms/secret-id
```

Replace the addresses with the IPs your control-plane nodes use to reach Vault. The plugin logs in again with the same secret ID whenever its token expires, so the secret ID must not expire or run out of uses (`secret_id_ttl=0`, `secret_id_num_uses=0`). Keep the role ID and secret ID for the next step.

## 3. Add the KMS Plugin to the Control-Plane Nodes

This step starts the plugin and lets kube-apiserver read data encrypted with KMS, but new writes still use the existing `secretbox` key. Nothing changes for the data yet. The switch comes in the next step, once every control-plane node can decrypt with both providers: during a rolling change the API servers must always be able to read what the others have written, as the [Kubernetes documentation](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/#rotating-a-decryption-key) warns.

### Find the Current secretbox Key

Talos names the current key `key2`. Its value is `secrets.secretboxencryptionsecret` in the `secrets.yaml` of your Talm project (decrypt the project first with `talm init --decrypt` if it is encrypted):

```bash
yq '.secrets.secretboxencryptionsecret' secrets.yaml
```

You will copy this value into the encryption configuration below, so that existing Secrets stay readable.

### Choose What to Encrypt

Talos encrypts only `secrets` by default. In Cozystack, the `spec` of every application (Postgres, ClickHouse, Kubernetes and so on) is stored inline in the `spec.values` of a Flux `HelmRelease`, and some applications keep passwords there. Add `helmreleases.helm.toolkit.fluxcd.io` to the encrypted resources to cover them. The examples below encrypt both.

The Helm release history that Flux keeps for every application is stored in Secrets, so `secrets` already covers it.

### Edit the Node Files

Add the following to the body of every control-plane node file (`nodes/<node>.yaml`), below the `# talm:` modeline. Talm applies the body as a patch on top of the rendered configuration, so these fields are sent on every `talm apply`.

```yaml
machine:
  pods:
    - apiVersion: v1
      kind: Pod
      metadata:
        name: vault-kubernetes-kms
        namespace: kube-system
      spec:
        hostNetwork: true
        priorityClassName: system-node-critical
        initContainers:
          # The kubelet creates /var/kms owned by root; hand it to the
          # kube-apiserver user so the plugin can create its socket there.
          - name: socket-dir-owner
            image: docker.io/library/busybox:1.37.0
            command: ["chown", "65534:65534", "/var/kms"]
            securityContext:
              runAsUser: 0
            volumeMounts:
              - name: socket
                mountPath: /var/kms
        containers:
          - name: vault-kubernetes-kms
            image: ghcr.io/falcosuessgott/vault-kubernetes-kms:v1.4.0
            command:
              - /vault-kubernetes-kms
              - -vault-address=https://vault.example.com:8200
              - -auth-method=approle
              - -approle-mount=approle
              - -transit-mount=transit
              - -transit-key=mgmt-etcd
              - -socket=unix:///var/kms/vaultkms.socket
              - -force-socket-overwrite=true
              # Health and metrics endpoint; it listens on all host
              # interfaces (default 8080), so pick a port that is free.
              - -health-port=18080
            env:
              - name: VAULT_KMS_APPROLE_ROLE_ID
                value: "<role-id>"
              - name: VAULT_KMS_APPROLE_SECRET_ID
                value: "<secret-id>"
            securityContext:
              # kube-apiserver runs as 65534 on Talos and can only connect
              # to a socket owned by that user.
              runAsUser: 65534
              runAsGroup: 65534
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop: ["ALL"]
            volumeMounts:
              - name: socket
                mountPath: /var/kms
        volumes:
          - name: socket
            hostPath:
              path: /var/kms
              type: DirectoryOrCreate
cluster:
  # The secretbox key moves into KubeEtcdEncryptionConfig below;
  # Talos rejects a configuration that sets both.
  secretboxEncryptionSecret:
    $patch: delete
  apiServer:
    extraVolumes:
      - hostPath: /var/kms
        mountPath: /var/kms
        readonly: false
---
apiVersion: v1alpha1
kind: KubeEtcdEncryptionConfig
config:
  resources:
    - resources:
        - secrets
        - helmreleases.helm.toolkit.fluxcd.io
      providers:
        - secretbox:
            keys:
              - name: key2
                secret: "<secretbox key from secrets.yaml>"
        - kms:
            apiVersion: v2
            name: vault
            endpoint: unix:///var/kms/vaultkms.socket
            timeout: 3s
        - identity: {}
```

Replace the Vault address, the Transit key name, the role ID, the secret ID and the secretbox key with your values. If the node file already has `cluster.apiServer.extraVolumes` (for example, for OIDC), add the `/var/kms` entry to the existing list.

A few things to know about this configuration:

- `apiVersion: v2` is required. Without it the provider defaults to KMS v1, which is disabled since Kubernetes 1.29, and kube-apiserver refuses the configuration.
- Talos does not validate the body of `KubeEtcdEncryptionConfig` on apply. A typo is only reported later, when Talos renders the file for kube-apiserver. Double-check the field names.
- `machine.pods` and `cluster.apiServer.extraVolumes` are deprecated in Talos v1.14 but still honoured. Talos has no replacement for mounting a host directory into kube-apiserver yet.
- The plugin runs on the host network, because it has to work before the cluster network does: the CNI needs the API server, and the API server needs the plugin.
- Do not add a liveness probe on the plugin's `/live` endpoint. It calls Vault on every check, so a short Vault or network hiccup would make the kubelet restart the plugin.
- If Vault uses a private CA, put the CA certificate on the node and pass it with the `-vault-ca-cert` flag.

{{% alert color="warning" %}}
The node files now contain the AppRole secret ID in plain text. Do not commit them to Git as is. If your Talm project lives in Git, move the pod definition into the project templates and the two IDs into [encrypted user values](/docs/next/install/kubernetes/talm/#24-encrypted-user-values-and-secret-redaction-talm-v032), which Talm decrypts in memory on apply.

Also note that `talm template -I` rewrites node files from the templates and drops everything added by hand. Keep a copy of these blocks outside `nodes/`, and add them again before the next apply if you regenerate a node file. An apply without them would remove the `kms` provider, and kube-apiserver would no longer be able to read Secrets encrypted with KMS.
{{% /alert %}}

### Apply, One Node at a Time

Preview the change first. The dry run also catches the conflict between `secretboxEncryptionSecret` and `KubeEtcdEncryptionConfig`:

```bash
talm apply -f nodes/cp1.yaml --dry-run
```

Then apply it and wait until the node is healthy before moving to the next one:

```bash
talm apply -f nodes/cp1.yaml
kubectl --namespace kube-system get pods --selector k8s-app=kube-apiserver --output wide
kubectl get --raw '/readyz?verbose' | grep kms
```

The last command should print `[+]kms-providers ok`. Repeat for every control-plane node.

## 4. Switch Encryption to KMS

Once all control-plane nodes run the configuration from the previous step, swap the first two providers in every node file, so that KMS encrypts new writes and `secretbox` is kept only to read old data:

```yaml
      providers:
        - kms:
            apiVersion: v2
            name: vault
            endpoint: unix:///var/kms/vaultkms.socket
            timeout: 3s
        - secretbox:
            keys:
              - name: key2
                secret: "<secretbox key from secrets.yaml>"
        - identity: {}
```

Apply the node files one at a time again, checking `[+]kms-providers ok` after each node. The first provider in the list encrypts; all providers are tried in order to decrypt.

## 5. Re-encrypt Existing Data

Objects written before the switch are still stored with the old provider: Secrets with `secretbox`, HelmReleases in plain text. Rewrite all of them so that kube-apiserver stores them again with the new first provider:

```bash
kubectl get secrets --all-namespaces --output json | kubectl replace --filename -
kubectl get helmreleases.helm.toolkit.fluxcd.io --all-namespaces --output json | kubectl replace --filename -
```

Run it when the cluster is quiet. An object that changes while the command runs may fail with a conflict error; running the command again is safe.

## 6. Verify

### Check the Active Configuration

Talos shows the encryption configuration it renders for kube-apiserver. The output contains key material, so reading it requires the `os:admin` role:

```bash
talosctl --nodes <cp-ip> get etcdencryptionconfigs --output yaml
```

The providers must be listed in the order `kms`, `secretbox`, `identity`.

### Check the Data in etcd

On Talos, etcd is a system service rather than a pod, and `talosctl` cannot read individual keys. Take a snapshot, restore it locally and read the Secret from the copy:

```bash
kubectl --namespace default create secret generic kms-check --from-literal=probe=value

talosctl --nodes <cp-ip> etcd snapshot db.snapshot
etcdutl snapshot restore db.snapshot --data-dir ./etcd-restore
etcd --data-dir ./etcd-restore \
  --listen-client-urls http://127.0.0.1:32379 \
  --advertise-client-urls http://127.0.0.1:32379 \
  --listen-peer-urls http://127.0.0.1:32380 &

etcdctl --endpoints http://127.0.0.1:32379 \
  get /registry/secrets/default/kms-check --print-value-only | head -c 64 | hexdump -C
```

The value must start with `k8s:enc:kms:v2:vault:`. A value that starts with `k8s:enc:secretbox:v1:` was not re-encrypted.

To list every Secret and HelmRelease that is not yet encrypted with KMS:

```bash
for prefix in /registry/secrets/ /registry/helm.toolkit.fluxcd.io/helmreleases/; do
  etcdctl --endpoints http://127.0.0.1:32379 \
    get "$prefix" --prefix --write-out json \
    | jq -r '.kvs[]? | select((.value | @base64d | startswith("k8s:enc:kms:v2:")) | not) | .key | @base64d'
done
```

The output must be empty. Then stop the local etcd and delete the copy:

```bash
kill %1
rm -rf ./etcd-restore db.snapshot
kubectl --namespace default delete secret kms-check
```

{{% alert color="warning" %}}
An etcd snapshot contains the whole cluster state, including every resource that is not encrypted. Handle it as sensitive data and delete it right after the check.
{{% /alert %}}

## 7. Remove the Old Key

When the check above shows no Secrets left on `secretbox`, remove the `secretbox` entry from the providers in every node file and apply the node files one at a time:

```yaml
      providers:
        - kms:
            apiVersion: v2
            name: vault
            endpoint: unix:///var/kms/vaultkms.socket
            timeout: 3s
        - identity: {}
```

Until you do this, the old key in the machine configuration can still decrypt any Secret written before the migration.

## Aggregated API Servers

The Cozystack API server (`apps.cozystack.io`, `core.cozystack.io`, `sdn.cozystack.io`) has no storage of its own: everything it serves is stored by the management kube-apiserver, so the configuration above covers it.

An aggregated API server that runs its own etcd, for example one you deploy on top of Cozystack, needs its own encryption configuration. Any API server built on `k8s.io/apiserver` with etcd storage accepts the same `--encryption-provider-config` flag:

- Run the KMS plugin as a sidecar container in the API server pod and share the socket through an `emptyDir` volume.
- Run the plugin with the same UID as the API server, so that the server can connect to the socket the plugin creates.
- Use a separate Transit key for every API server, so that a credential leaked from one of them cannot decrypt the data of the others.
- List the API server's own resources as `<resource>.<group>`, the same way as `helmreleases.helm.toolkit.fluxcd.io` above.
- Do not point a liveness probe with a short timeout at the plugin's `/live` endpoint: it calls Vault on every check. The KMS health check of the API server itself is part of `/readyz`, not `/livez`.

## Tenant Kubernetes Clusters

KMS encryption for tenant Kubernetes clusters is not supported yet: their control planes run as pods managed by Kamaji, and the `kubernetes` application does not let you add a sidecar next to kube-apiserver. By default, Secrets of tenant clusters are stored in their etcd unencrypted.

What works today is encryption with a local key, set through the values of the `Kubernetes` application. The key is stored in a Secret in the tenant namespace of the management cluster. This protects the data in the tenant etcd and in its backups, but anyone who can read Secrets in that namespace can read the key. If the management cluster encrypts `secrets` with KMS, the key itself is encrypted at rest.

Create the Secret in the namespace of the `Kubernetes` application:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mycluster-encryption-config
  namespace: tenant-example
stringData:
  config.yaml: |
    apiVersion: apiserver.config.k8s.io/v1
    kind: EncryptionConfiguration
    resources:
      - resources:
          - secrets
        providers:
          - secretbox:
              keys:
                - name: key1
                  secret: <base64-encoded 32 random bytes>
          - identity: {}
```

Generate the key with `head -c 32 /dev/urandom | base64`. Then add to the values of the `Kubernetes` application:

```yaml
controlPlane:
  apiServer:
    extraArgs:
      - --encryption-provider-config=/etc/kubernetes/encryption/config.yaml
      - --encryption-provider-config-automatic-reload=true
    extraVolumes:
      - name: encryption-config
        secret:
          secretName: mycluster-encryption-config
    extraVolumeMounts:
      - name: encryption-config
        mountPath: /etc/kubernetes/encryption
        readOnly: true
```

Once the control plane has restarted, rewrite the existing Secrets with the kubeconfig of the tenant cluster, using the first command from [step 5](#5-re-encrypt-existing-data). With automatic reload enabled, later changes to the Secret, such as a new key, are picked up without a restart.

## Rotating the Key

The Kubernetes project [recommends](https://kubernetes.io/docs/tasks/administer-cluster/kms-provider/) rotating the key encryption key at least every 90 days. With Vault Transit, a rotation does not require touching the nodes:

```bash
vault write -f transit/keys/mgmt-etcd/rotate
```

The plugin reports the new key version to kube-apiserver, which polls it about once a minute and starts using the new version for new writes without a restart. Existing Secrets stay readable, because Vault keeps the old key versions. To move them to the new version, wait a few minutes after the rotation and run the rewrite from [step 5](#5-re-encrypt-existing-data) again.

Only after that, and after checking that no Secret is still encrypted with an old version, you may raise `min_decryption_version` on the Transit key. Doing it earlier makes the remaining old Secrets unreadable.

## Monitoring and Failure Modes

If the plugin or Vault becomes unavailable, kube-apiserver keeps writing for up to about three minutes and keeps reading from its cache, then Secret reads and writes start to fail. A kube-apiserver that starts while the plugin is down comes up, but reports not ready and cannot serve Secrets.

Watch for it with:

- the `kms-providers` check in `kubectl get --raw '/readyz?verbose'`;
- `apiserver_envelope_encryption_kms_operations_latency_seconds`, labelled with the gRPC status code of each call to the plugin;
- `apiserver_envelope_encryption_invalid_key_id_from_status_total`, which grows when the plugin reports a broken key version;
- `apiserver_storage_transformation_operations_total` with a non-OK `status`, which counts failed encryption and decryption operations.

A ready API server does not always mean Secrets can be read. The most reliable signal is a periodic check that reads a canary Secret.

## Rolling Back

To stop using KMS, put `identity: {}` first while keeping the `kms` provider and the plugin running, apply every node, rewrite all Secrets with the command from [step 5](#5-re-encrypt-existing-data), and only then remove the `kms` provider and the plugin. Removing the plugin before the rewrite makes every KMS-encrypted Secret unreadable.

## Troubleshooting

### `etcd encryption config is already set in v1alpha1 config`

The rendered configuration still carries `cluster.secretboxEncryptionSecret`. Check that the `$patch: delete` directive is in the node file body and is indented under `cluster`. As a fallback, remove the `secretboxencryptionsecret` field from `secrets.yaml`; keep its value, because the `secretbox` provider still needs it.

### `[-]kms-providers failed`

kube-apiserver cannot reach the plugin. Check the plugin logs:

```bash
kubectl --namespace kube-system logs vault-kubernetes-kms-<node-name>
```

Typical causes: the socket is not owned by UID 65534 (the init container did not run, or the plugin runs as another user), the node cannot reach Vault, or the AppRole binding does not include the node address.
