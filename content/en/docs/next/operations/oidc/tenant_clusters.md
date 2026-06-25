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

## Overview

Each Cozystack tenant gets its own dedicated Keycloak realm for its
kube-apiservers and tenant-scoped applications. The management
identity domain (the `cozy` realm) stays separated from per-tenant
identity. Users granted access to a tenant cluster live in that
tenant's realm only — they cannot accidentally log into the management
cluster or another tenant.

When the `Kubernetes` CR opts into OIDC (`spec.oidc.enabled: true`):

1. The `apps/tenant` chart auto-provisions a `ClusterKeycloakRealm`
   named after the tenant and the standard `groups`
   `KeycloakClientScope` inside it. The realm name is published as
   `_namespace.oidc-realm` in the tenant's `cozystack-values` Secret
   so descendants and apps pick it up.
2. The `apps/kubernetes` chart creates a per-cluster public
   `KeycloakClient kubernetes-<cluster>` (with its own audience scope
   so cross-cluster token replay fails inside the same realm), the
   `KeycloakRealmGroup <cluster>`, and wires the tenant kube-apiserver
   via `KamajiControlPlane.spec.apiServer.extraArgs`.
3. A post-install Job applies a `ClusterRoleBinding` inside the tenant
   cluster, binding the realm group to the built-in `cluster-admin`
   ClusterRole. Operators grant or revoke access by adding or removing
   users from the Keycloak group.

Operators do **not** need to pre-toggle `Tenant.spec.oidc.enabled` —
the parent `apps/tenant` chart auto-provisions the realm when any
child `Kubernetes` CR requests OIDC.

## Prerequisites

- Platform-level OIDC must be enabled
  (`authentication.oidc.enabled: true` in the platform values →
  `_cluster.oidc-enabled=true`).
- A publicly resolvable platform DNS name with a valid TLS certificate
  on the Keycloak ingress. The tenant apiserver validates the OIDC
  issuer over HTTPS using its system trust store — self-signed
  Keycloak deployments are not supported (see Limitations).

## Enable OIDC on a tenant cluster

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

Within ≤ 5 minutes:

- The `apps/tenant` reconcile creates `ClusterKeycloakRealm tenant-acme`.
- The `apps/kubernetes` reconcile picks up the realm, provisions the
  per-cluster `KeycloakClient kubernetes-prod-a`, the realm group
  `prod-a`, and adds OIDC flags to the kube-apiserver.
- A post-install Job binds `Group prod-a` to `cluster-admin` inside the
  tenant cluster.

## Create a user and grant access

In Keycloak (the tenant realm — e.g. `tenant-acme`):

1. Create a user, set a non-temporary password, mark email verified.
2. Add the user to the realm group named after the cluster (`prod-a`).
   One membership = full kubectl access to that cluster.

To revoke access, remove the user from the group.

## Wire kubectl with kubelogin

Install [kubelogin](https://github.com/int128/kubelogin):

```bash
brew install int128/kubelogin/kubelogin
# or: kubectl krew install oidc-login
```

The chart prints a ready-to-paste kubeconfig snippet in its
`NOTES.txt`:

```bash
helm get notes -n tenant-acme prod-a
```

Or write it by hand — pasting the cluster CA from the admin
kubeconfig Secret:

```yaml
apiVersion: v1
kind: Config
clusters:
- name: prod-a
  cluster:
    server: https://prod-a.acme.example.com:443
    certificate-authority-data: <base64 cluster CA>
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
      - --oidc-client-id=kubernetes-prod-a
```

Running `kubectl get pods` opens the browser, logs the user into
Keycloak, returns the id_token, and the apiserver authenticates based
on the `groups` claim.

## Limitations

### Realm cleanup is not automatic after the last child OIDC cluster is removed

The `apps/tenant` chart uses Helm's `lookup` function to discover
whether any child `Kubernetes` CR has `spec.oidc.enabled=true`.
Helm-controller does **not** re-render a chart when a `lookup` result
changes — it only re-renders when the chart source artifact or the
HelmRelease values change. Consequently, deleting the last
`Kubernetes` CR with OIDC enabled does **not** trigger an `apps/tenant`
re-render, and the orphan `ClusterKeycloakRealm` stays in the tenant
namespace.

To force cleanup, the operator can:

- Explicitly toggle `Tenant.spec.oidc.enabled=true` and then back to
  `false`. Each toggle changes the HelmRelease values, which triggers
  a re-render with the up-to-date lookup result. After the second
  toggle, the chart no longer renders the realm and Helm prunes it.
- Or wait for the next platform upgrade that bumps any chart-affecting
  source — the realm cleanup happens for free as a side effect.

### Self-signed Keycloak is not supported

The tenant apiserver validates the OIDC issuer over HTTPS using the
system trust store inside the Kamaji apiserver pod. If the platform
Keycloak ingress uses a private CA, the apiserver fails the TLS
handshake and all OIDC logins return 401. The chart does not currently
expose a `caBundle` field — public DNS with a valid certificate (e.g.
via cert-manager + Let's Encrypt) is required. See
[Self-signed certificates]({{< relref "self-signed-certificates.md" >}})
for the management-cluster workaround pattern.

### JWT claims are not configurable

`--oidc-username-claim` is fixed to `preferred_username` and
`--oidc-groups-claim` is fixed to `groups`. These match the Keycloak
defaults; deployments using non-default claim mappings need a chart
change.

### Runtime toggle of `oidc.enabled` from `true` to `false`

Helm hooks only fire on install / upgrade / delete, not on values
changes. If an operator flips `Kubernetes.spec.oidc.enabled` from
`true` to `false`, the chart stops rendering the in-cluster
`ClusterRoleBinding` Job but the existing binding inside the tenant
cluster is not removed. The apiserver also drops the OIDC arguments on
the next reconcile, so the orphan binding is inert (no realm group
matches against the now-disabled OIDC path). Manual cleanup:

```bash
kubectl --kubeconfig=<admin-kubeconfig> delete clusterrolebinding \
  --selector cozystack.io/oidc-cluster=<cluster>
```

### CI / headless access requires manual KeycloakClient patch

The chart-rendered `KeycloakClient` is public and does **not** enable
`directAccessGrantsEnabled` (password grant). This is correct for
browser-flow logins. For CI pipelines that need a non-interactive
token, the cluster-admin can patch the client on the live cluster:

```bash
kubectl -n <tenant-namespace> patch keycloakclient kubernetes-<cluster> \
  --type=merge --patch '{"spec":{"directAccess":true}}'
```

This is intentionally not the default — interactive flow stays
recommended for human users.

## Troubleshooting

### Apiserver returns 401 with a valid token

Check the apiserver flags in the Kamaji pod:

```bash
kubectl --context=mgmt -n <tenant-ns> get pod \
  -l kamaji.clastix.io/name=<cluster> \
  -o jsonpath='{.items[0].spec.containers[?(@.name=="kube-apiserver")].args}' | \
  tr ',' '\n' | grep oidc
```

Confirm the issuer URL matches the realm — decode the id_token and
compare `iss` against the `--oidc-issuer-url` flag. Confirm `aud` in
the token equals `--oidc-client-id`; mismatch is the most common cause
when running multiple clusters in the same realm.

### Apiserver returns 403 for a user that is in the right group

Check the in-cluster `ClusterRoleBinding`:

```bash
kubectl --kubeconfig=<admin-kubeconfig> get clusterrolebinding \
  --selector cozystack.io/oidc-cluster=<cluster>
```

The bootstrap Job runs as a `post-install` / `post-upgrade` hook;
check its logs in the management cluster:

```bash
kubectl --context=mgmt -n <tenant-ns> logs \
  job/<release-name>-oidc-rbac
```

### Realm or scope objects stuck after CR deletion

See [Realm cleanup is not automatic](#realm-cleanup-is-not-automatic-after-the-last-child-oidc-cluster-is-removed)
under Limitations. Operator intervention required (toggle
`Tenant.spec.oidc`).
