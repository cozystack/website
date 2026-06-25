---
title: "OIDC for tenant Kubernetes clusters"
linkTitle: "Tenant Kubernetes OIDC"
description: "Per-tenant Keycloak realms and OIDC authentication on tenant kube-apiservers"
weight: 40
aliases:
  - /docs/next/oidc/tenant-kubernetes
---

This page covers OIDC authentication on the tenant Kubernetes clusters
managed by Cozystack (the per-tenant kube-apiservers backed by Kamaji).
It complements [Enable OIDC Server]({{< relref "enable_oidc.md" >}}),
which covers OIDC for the **management** cluster (dashboard, kubeapps,
mgmt kubectl) using the platform `cozy` realm.

In all examples below the tenant is `acme` (so its namespace is
`tenant-acme`), the tenant Kubernetes CR is `prod-a` (so its release
name is `kubernetes-prod-a`), and the platform root host is
`acme.example.com`. Substitute your own names accordingly.

## Overview

Per-tenant identity is delivered through a tenant-module: when a
tenant opts in via `Tenant.spec.oidc=true`, the platform provisions a
dedicated Keycloak realm + a realm-admin user + a `keycloak-admin`
Secret with the credentials. Tenant operators self-manage users in
their realm; child Kubernetes CRs and tenant-scoped applications wire
themselves to the realm declaratively through cozystack manifests.

The management identity domain (the `cozy` realm) stays separated from
per-tenant identity. Users granted access to a tenant cluster live in
that tenant's realm only — they cannot accidentally log into the
management cluster or another tenant.

When `Tenant.spec.oidc=true` is set:

1. `apps/tenant` renders an `oidc` HelmRelease in the tenant namespace
   (same tenant-module pattern as `etcd`, `monitoring`, `ingress`).
2. The HR resolves to the `extra/oidc` chart, which provisions
   `ClusterKeycloakRealm tenant-acme`, the standard `groups`
   `KeycloakClientScope`, a `KeycloakRealmUser admin` with the
   built-in `realm-admin` client role on `realm-management`, and a
   `Secret keycloak-admin` carrying the URL + username + password the
   tenant operator uses to log into the realm's admin console.
3. The realm name is published to `_namespace.oidc-realm` in the
   tenant's `cozystack-values` Secret so descendant tenants and
   tenant-scoped apps inherit it the same way they inherit
   `etcd` / `monitoring` / `ingress`.

When a Kubernetes CR opts into OIDC (`spec.oidc.enabled: true`):

1. `apps/kubernetes` reads `_namespace.oidc-realm` (own OR inherited).
   If empty, the chart soft-renders an
   `<release>-awaiting-oidc-realm` ConfigMap beacon and the
   kube-apiserver runs without OIDC arguments — the client-cert (mTLS)
   admin kubeconfig stays usable.
2. Once the realm name is non-empty, the chart creates a per-cluster
   public `KeycloakClient tenant-acme-kubernetes-prod-a` (with its own
   audience scope so cross-cluster token replay fails inside the same
   realm), creates `KeycloakRealmGroup tenant-acme-kubernetes-prod-a`,
   and wires the tenant kube-apiserver via
   `KamajiControlPlane.spec.apiServer.extraArgs`.
3. A post-install Job (`kubernetes-prod-a-oidc-rbac`) applies a
   `ClusterRoleBinding` inside the tenant cluster, binding the realm
   group `tenant-acme-kubernetes-prod-a` to the built-in
   `cluster-admin` ClusterRole. Operators grant or revoke access by
   adding or removing users from the Keycloak group.

## Realm inheritance

Descendant tenants without their own `spec.oidc=true` inherit the
nearest ancestor's realm name through the cozystack-values
propagation chain. Their `Kubernetes` CRs wire against the ancestor's
realm; the chart renders the per-cluster `KeycloakClient` and
`KeycloakRealmGroup` into the descendant's own namespace, with
`realmRef` pointing at the ancestor's cluster-scoped realm.

| Tenant | `spec.oidc` | `_namespace.oidc-realm` |
| --- | --- | --- |
| `tenant-acme` | `true` | `tenant-acme` (owns) |
| `tenant-acme-prod` | `false` | `tenant-acme` (inherited) |
| `tenant-acme-prod-eu` | `false` | `tenant-acme` (inherited via chain) |
| `tenant-acme-staging` | `true` | `tenant-acme-staging` (owns — override) |

Realm-wide unique names prevent collisions when two siblings under the
same parent realm each have a `Kubernetes` CR of the same
metadata.name — `tenant-acme-prod-kubernetes-dev` and
`tenant-acme-staging-kubernetes-dev` are distinct identifiers in the
shared `tenant-acme` realm.

Identity-admin delegation lives with the realm-owning tenant only:
only that tenant gets the `keycloak-admin` Secret. Descendants
consume the realm declaratively but do not gain admin access to it.

## Prerequisites

- Platform-level OIDC must be enabled
  (`authentication.oidc.enabled: true` in the platform values →
  `_cluster.oidc-enabled=true`).
- A publicly resolvable platform DNS name with a valid TLS certificate
  on the Keycloak ingress. The tenant apiserver validates the OIDC
  issuer over HTTPS using its system trust store — self-signed
  Keycloak deployments are not supported (see Limitations).

## Enable OIDC on a tenant

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Tenant
metadata:
  name: acme
  namespace: tenant-root
spec:
  etcd: true
  ingress: true
  oidc: true
```

On the next `apps/tenant` reconcile (default interval 5 min) the
`oidc` HR appears in `tenant-acme`. The `extra/oidc` chart then takes
1-2 minutes to provision the realm + admin user + Secret. Open the
`keycloak-admin` Secret through the cozystack dashboard or kubectl to
grab the realm admin URL + credentials:

```bash
kubectl --context=mgmt -n tenant-acme get secret keycloak-admin -o yaml
```

The Secret carries:

- `url` — the admin console URL (e.g. `https://keycloak.acme.example.com/admin/tenant-acme/console/`)
- `username` — `admin`
- `password` — random alphanumeric, stable across re-renders
- `realm` — `tenant-acme`
- `email` — `admin@tenant-acme.local` (or operator override)

The tenant operator logs into the admin URL with these credentials and
manages users, groups, identity providers, password policies inside
their realm — independently of the platform admin.

## Enable OIDC on a tenant Kubernetes cluster

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Kubernetes
metadata:
  name: prod-a
  namespace: tenant-acme
spec:
  controlPlane:
    replicas: 1
  nodeGroups:
    md0:
      minReplicas: 0
      maxReplicas: 3
      instanceType: u1.medium
      roles: [worker]
  storageClass: replicated
  version: "v1.32"
  oidc:
    enabled: true
```

Each chart in the chain reconciles on its own loop (default 5 min),
so the full cascade takes up to ~10 minutes worst case from a cold
start:

1. `apps/tenant` reconcile creates the `oidc` HR; `extra/oidc`
   provisions `ClusterKeycloakRealm tenant-acme` and publishes
   `_namespace.oidc-realm=tenant-acme` to cozystack-values.
2. `apps/kubernetes` reconcile picks up the realm, provisions the
   per-cluster `KeycloakClient tenant-acme-kubernetes-prod-a`, the
   realm group `tenant-acme-kubernetes-prod-a`, and adds OIDC flags
   to the kube-apiserver.
3. The post-install Job binds `Group tenant-acme-kubernetes-prod-a`
   to `cluster-admin` inside the tenant cluster.

## Create a user and grant access

In Keycloak (the tenant realm — `tenant-acme`):

1. Create a user, set a non-temporary password, mark email verified.
2. Add the user to the realm group named after the cluster in the
   format `<tenant-namespace>-kubernetes-<cluster-name>` (e.g.
   `tenant-acme-kubernetes-prod-a`). One membership = full
   `cluster-admin` access to that cluster.

To revoke access, remove the user from the group.

## Wire kubectl with kubelogin

Install [kubelogin](https://github.com/int128/kubelogin):

```bash
brew install int128/kubelogin/kubelogin
# or: kubectl krew install oidc-login
```

Extract the cluster CA from the Kamaji admin kubeconfig Secret in the
tenant namespace of the management cluster:

```bash
kubectl --context=mgmt -n tenant-acme \
  get secret kubernetes-prod-a-admin-kubeconfig \
  -o jsonpath='{.data.super-admin\.conf}' | base64 -d \
  > /tmp/prod-a-admin.kubeconfig

CA=$(awk '/certificate-authority-data/{print $2}' \
       /tmp/prod-a-admin.kubeconfig)
```

Save the snippet below as `~/.kube/config-prod-a`, paste the value of
`$CA` into `certificate-authority-data`, and run
`export KUBECONFIG=~/.kube/config-prod-a`:

```yaml
apiVersion: v1
kind: Config
clusters:
- name: prod-a
  cluster:
    server: https://prod-a.acme.example.com:443
    certificate-authority-data: <paste the value of $CA>
contexts:
- name: prod-a
  context:
    cluster: prod-a
    user: oidc
current-context: prod-a
users:
- name: oidc
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1
      command: kubectl
      args:
      - oidc-login
      - get-token
      - --oidc-issuer-url=https://keycloak.acme.example.com/realms/tenant-acme
      - --oidc-client-id=tenant-acme-kubernetes-prod-a
```

Running `kubectl get pods` opens the browser, logs the user into
Keycloak, returns the id_token, and the apiserver authenticates based
on the `groups` claim.

## Limitations

### Self-signed Keycloak is not supported

The tenant apiserver validates the OIDC issuer over HTTPS using the
system trust store inside the Kamaji apiserver pod. If the platform
Keycloak ingress uses a private CA, the apiserver fails the TLS
handshake and all OIDC logins return 401. The chart does not expose a
`caBundle` field for the tenant apiserver — public DNS with a valid
certificate (e.g. via cert-manager + Let's Encrypt) is required.

Note: [Self-signed certificates]({{< relref "self-signed-certificates.md" >}})
covers the workaround for the **management cluster** apiserver only.
That workaround does **not** apply to tenant apiservers because their
machine config is managed by Kamaji, not by the operator's Talos /
talm flow.

### JWT claims are not configurable

`--oidc-username-claim` is fixed to `preferred_username` and
`--oidc-groups-claim` is fixed to `groups`. These match the Keycloak
defaults; deployments using non-default claim mappings need a chart
change.

### Runtime oidc.enabled toggle does not clean up bindings

Helm hooks only fire on install / upgrade / delete, not on values
changes. If an operator flips `Kubernetes.spec.oidc.enabled` from
`true` to `false`, the chart stops rendering the in-cluster
`ClusterRoleBinding` Job but the existing binding inside the tenant
cluster is not removed. The apiserver also drops the OIDC arguments
on the next reconcile, so the binding is inert — no realm group can
match it once OIDC is off. Manual cleanup:

```bash
KUBECONFIG=/tmp/prod-a-admin.kubeconfig kubectl delete clusterrolebinding \
  --selector cozystack.io/oidc-cluster=prod-a
```

(reuse the admin kubeconfig extracted in the "Wire kubectl" section).

### CI / headless access requires manual KeycloakClient patch

The chart-rendered `KeycloakClient` is public and does **not** enable
`directAccessGrantsEnabled` (password grant). This is correct for
browser-flow logins. For CI pipelines that need a non-interactive
token, the cluster-admin can patch the client on the live cluster:

```bash
kubectl --context=mgmt -n tenant-acme patch keycloakclient tenant-acme-kubernetes-prod-a \
  --type=merge --patch '{"spec":{"directAccess":true}}'
```

This is intentionally not the default — interactive flow stays
recommended for human users.

### Disabling parent OIDC while descendant clusters use the inherited realm

If a parent tenant flips `spec.oidc=false` while descendant tenants
still have `Kubernetes` CRs with `spec.oidc.enabled=true` referencing
the parent's realm, convergence takes up to one helm-controller
reconcile interval (default 5 min):

1. Parent's `oidc` HR uninstalls — realm + admin user +
   `keycloak-admin` Secret are removed.
2. `_namespace.oidc-realm` in descendant cozystack-values reverts to
   empty on the next tenant reconcile.
3. Descendant's `apps/kubernetes` reconciles, drops the OIDC apiserver
   args, and prunes the per-cluster KeycloakClient + RealmGroup CRs.

During the window, descendant KeycloakClient / RealmGroup CRs
reference a deleted realm — the EDP Keycloak Operator logs errors but
does not damage cluster state. OIDC tokens stop working immediately;
the per-cluster client-cert admin kubeconfig remains usable as the
recovery path.

## Troubleshooting

### Apiserver returns 401 with a valid token

Check the apiserver flags in the Kamaji pod (in the management
cluster):

```bash
kubectl --context=mgmt -n tenant-acme get pod \
  -l kamaji.clastix.io/name=kubernetes-prod-a \
  -o jsonpath='{.items[0].spec.containers[?(@.name=="kube-apiserver")].args}' | \
  tr ',' '\n' | grep oidc
```

Confirm the issuer URL matches the realm — decode the id_token and
compare `iss` against the `--oidc-issuer-url` flag. Confirm `aud` in
the token equals `--oidc-client-id`; mismatch is the most common
cause when running multiple clusters in the same realm.

### Apiserver returns 403 for a user that is in the right group

Extract the admin kubeconfig and check the in-cluster
`ClusterRoleBinding`:

```bash
kubectl --context=mgmt -n tenant-acme \
  get secret kubernetes-prod-a-admin-kubeconfig \
  -o jsonpath='{.data.super-admin\.conf}' | base64 -d \
  > /tmp/prod-a-admin.kubeconfig

KUBECONFIG=/tmp/prod-a-admin.kubeconfig kubectl get clusterrolebinding \
  --selector cozystack.io/oidc-cluster=prod-a
```

The bootstrap Job runs as a `post-install` / `post-upgrade` hook;
check its logs in the management cluster:

```bash
kubectl --context=mgmt -n tenant-acme logs \
  job/kubernetes-prod-a-oidc-rbac
```

### Realm or scope objects stuck after Tenant.spec.oidc=false

Flux uninstalls the `oidc` HR on the next tenant reconcile, which
drops the realm + scope + user + Secret automatically — no orphan
workaround required (unlike the previous design where realm
provisioning was inline in `apps/tenant`). If a stale object persists,
check the Keycloak Operator's logs for reconciliation errors.
