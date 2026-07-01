---
title: "OIDC authentication for kubectl"
linkTitle: "OIDC authentication"
description: "Give tenant users per-identity kubectl access to a Managed Kubernetes cluster with per-cluster audience isolation."
weight: 45
---

Tenant Kubernetes clusters can authenticate `kubectl` users through OIDC instead of the shared static admin kubeconfig. Each user then has their own identity, per-user audit, and RBAC that can be revoked by disabling the account — not by rotating a shared certificate.

The identity model is deliberately **per-cluster** rather than per-tenant: each tenant Kubernetes cluster gets its own OIDC audience, and a token minted for cluster A is rejected by cluster B's apiserver. That gives you cross-cluster isolation without provisioning a Keycloak realm per tenant. The full rationale (why per-cluster audience and not per-tenant realm; how it relates to Keycloak Organizations; what BYO-OIDC looks like) is in the [design proposal](https://github.com/cozystack/community/pull/24).

{{% alert color="info" %}}
The static `kubernetes-<cluster>-admin-kubeconfig` Secret in the tenant namespace stays available as a break-glass path regardless of whether OIDC is enabled.
{{% /alert %}}

## Modes

`spec.oidc.mode` picks the identity source:

- **`None`** — the default. No OIDC; only the static admin kubeconfig works. Existing clusters render identically to before.
- **`System`** — trust the platform `cozy` Keycloak realm via a per-cluster public client and audience binding. Users are the ones a Cozystack platform admin already provisioned in `cozy`; the tenant does not manage a directory of its own.
- **`CustomConfig`** — trust a tenant-supplied issuer directly (BYO IdP: Okta, Auth0, a customer's own Keycloak). `cozy` is not in the path.

## Enable OIDC — `System` mode

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Kubernetes
metadata:
  name: prod
  namespace: tenant-acme
spec:
  oidc:
    mode: System
    users:
      - email: alice@acme.example
        role: admin      # binds to ClusterRole/cluster-admin
      - email: bob@acme.example
        role: view       # binds to ClusterRole/view
  # ...
```

Cozystack provisions:

- A per-cluster `KeycloakClient` in the `cozy` realm, with `clientId` set to `<namespace>-kubernetes-<cluster-name>` (for the CR above: `tenant-acme-kubernetes-prod`). `public: true`, PKCE required, redirect URIs locked to `localhost:8000` and `localhost:18000` (the `kubectl oidc-login` defaults).
- A per-cluster `KeycloakClientScope` whose audience mapper pins the token's `aud` claim to that same `clientId`.
- A structured `AuthenticationConfiguration` (`apiserver.config.k8s.io/v1beta1`) on the tenant kube-apiserver, pointing at the `cozy` issuer and the per-cluster audience.
- One `ClusterRoleBinding` inside the tenant cluster for each `users[]` entry — `admin` → `cluster-admin`, `view` → `view`. The chart uses your `users[].email` value as the `User:` subject and matches it against the token's `email` claim.

Removing a user from `users[]` prunes their `ClusterRoleBinding` on the next reconcile.

### Prerequisite

`System` mode requires the platform-level OIDC feature (`authentication.oidc.enabled` at the Cozystack platform values). If the flag is off, the chart hard-fails the render with a clear message. Ask a Cozystack platform admin to enable it, or use `CustomConfig`.

## Enable OIDC — `CustomConfig` mode

Bring your own issuer. Two supply paths, **mutually exclusive**:

```yaml
spec:
  oidc:
    mode: CustomConfig
    customConfig:
      config: |
        apiVersion: apiserver.config.k8s.io/v1beta1
        kind: AuthenticationConfiguration
        jwt:
        - issuer:
            url: https://idp.acme.example
            certificateAuthority: |
              -----BEGIN CERTIFICATE-----
              ...
              -----END CERTIFICATE-----
            audiences:
            - cozystack-prod
          claimMappings:
            username:
              claim: email
              prefix: ""
            groups:
              claim: groups
              prefix: ""
    users:
      - email: alice@acme.example
        role: admin
```

…or via a pre-existing Secret in the tenant namespace (you create it separately, e.g. under your own GitOps repository, so the AuthenticationConfiguration does not live inside the `Kubernetes` CR):

```yaml
spec:
  oidc:
    mode: CustomConfig
    customConfig:
      secretRef:
        name: acme-byo-authn-config      # Secret with a `config.yaml` key holding the AuthenticationConfiguration
```

Setting both `config` and `secretRef.name` (or neither) fails the render. In `CustomConfig` mode no Keycloak objects are provisioned in `cozy`; the tenant apiserver trusts the operator-supplied issuer directly.

Ensure your BYO issuer emits the `email` claim in the JWT. Every conformant OIDC provider does when the client requests the `email` scope. If you distribute a hand-crafted kubeconfig instead of using the chart-generated one, remember to include `--oidc-extra-scope=email` in the `kubectl oidc-login` exec block.

## Get the kubeconfig

In `System` mode, Cozystack writes a ready-to-use kubeconfig into a `kubernetes-<cluster>-oidc-kubeconfig` Secret in the tenant namespace (the same namespace where the `Kubernetes` resource lives). It's exposed to the dashboard alongside the admin kubeconfig, and you can also fetch it directly:

```shell
kubectl --namespace tenant-acme get secret kubernetes-prod-oidc-kubeconfig \
  --output=jsonpath='{.data.kubeconfig}' | base64 -d > prod.kubeconfig
```

The file contains the tenant CA (extracted from the Kamaji-issued admin kubeconfig at reconcile time), the external apiserver URL, and a `kubectl oidc-login` exec block wired to your per-cluster client.

In `CustomConfig` mode no kubeconfig Secret is generated — you distribute the OIDC kubeconfig out-of-band from your own IdP configuration.

## Sign in

Install the `oidc-login` kubectl plugin once:

```shell
kubectl krew install oidc-login
```

Then use the OIDC kubeconfig — the first request triggers the browser flow:

```shell
kubectl --kubeconfig prod.kubeconfig get pods --all-namespaces
```

`kubectl oidc-login` opens Keycloak's login page on `localhost:8000` (falling back to `localhost:18000`), captures the token, and caches it locally. Subsequent calls are silent until the token expires.

## Toggling OIDC off

Setting `spec.oidc.mode` back to `None` — or deleting the `Kubernetes` resource entirely — reconciles a cleanup pass that removes the tenant apiserver's `--authentication-config` flag, deletes the chart-owned OIDC Secrets, and drops the per-cluster Keycloak client and audience scope. `ClusterRoleBindings` labelled by the release are also removed from the tenant cluster (best-effort during pre-delete, since the tenant apiserver may already be tearing down).

## Prerequisites and gotchas

- **Don't mix with legacy `--oidc-*` flags.** The tenant kube-apiserver refuses to boot if both `--authentication-config` (injected by `spec.oidc`) and any legacy `--oidc-*` flag are set. If you previously wired OIDC by hand through `controlPlane.apiServer.extraArgs`, remove those flags before enabling `spec.oidc`. The chart fails the render with a pointer to this migration.
- **`oidc-login` plugin required.** Without `kubectl krew install oidc-login` the exec block errors out client-side. The plugin is a documented prerequisite.
- **`emailVerified: true` when provisioning Keycloak users.** Phase 1 does not add a `claimValidationRules` entry to the rendered `AuthenticationConfiguration` — so `email_verified` is not chart-enforced. Set `emailVerified: true` on the `KeycloakRealmUser` (or complete the email-verify flow through the Keycloak UI) so the identity holding a given `users[].email` is guaranteed authentic. The `cozy` realm's default `duplicateEmails: false` prevents a second account from claiming an already-registered address. If the issuer explicitly emits `email_verified: false` on a token the apiserver rejects it (k8s upstream behaviour); a missing claim is treated as verified. CEL `claimValidationRules` to make this a hard gate is a follow-up hardening path.
- **Custom issuer with a self-signed CA.** In `CustomConfig` mode you can supply the CA inline under `issuer.certificateAuthority`. The legacy `--oidc-*` flag path could not.

## What's out of scope for this feature

- **Per-tenant Keycloak realms.** Managed multi-tenant identity (a hosted directory the tenant self-administers) is a separate proposal, evaluated against Keycloak Organizations. Track it in the [community proposal](https://github.com/cozystack/community/pull/24).
- **Federating an external IdP into the platform `cozy` realm.** BYO-for-Cozystack-itself is a distinct problem — this feature is BYO-for-a-managed-service.
- **Cross-cluster SSO inside one tenant.** By design: each cluster has its own audience, which is the per-cluster isolation primitive.
- **RFC 8693 token exchange.** Possible future optimisation; not required for the per-cluster client + audience model.
