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

Each Cozystack tenant gets its own dedicated Keycloak realm for its
kube-apiservers and tenant-scoped applications. The management
identity domain (the `cozy` realm) stays separated from per-tenant
identity. Users granted access to a tenant cluster live in that
tenant's realm only — they cannot accidentally log into the management
cluster or another tenant.

When the `Kubernetes` CR opts into OIDC (`spec.oidc.enabled: true`):

1. The `apps/tenant` chart auto-provisions a `ClusterKeycloakRealm`
   named after the tenant (`tenant-acme`) and the standard `groups`
   `KeycloakClientScope` inside it. The realm name is published as
   `_namespace.oidc-realm` in the tenant's `cozystack-values` Secret
   so descendants and apps pick it up.
2. The `apps/kubernetes` chart creates a per-cluster public
   `KeycloakClient kubernetes-prod-a` (with its own audience scope so
   cross-cluster token replay fails inside the same realm), the
   `KeycloakRealmGroup prod-a`, and wires the tenant kube-apiserver
   via `KamajiControlPlane.spec.apiServer.extraArgs`.
3. A post-install Job (`kubernetes-prod-a-oidc-rbac`) applies a
   `ClusterRoleBinding` inside the tenant cluster, binding the realm
   group `prod-a` to the built-in `cluster-admin` ClusterRole.
   Operators grant or revoke access by adding or removing users from
   the Keycloak group.

Operators do **not** need to pre-toggle `Tenant.spec.oidc.enabled`
during normal operation — the parent `apps/tenant` chart auto-detects
child Kubernetes CRs with `oidc.enabled: true` and provisions the
realm automatically. The explicit `Tenant.spec.oidc.enabled=true` is
only useful as a manual cleanup workaround (see Limitations below).

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

Each chart in the chain reconciles on its own loop (default interval
5 minutes), so the full cascade takes up to ~10 minutes worst case
from a cold start:

1. The `apps/tenant` reconcile creates `ClusterKeycloakRealm tenant-acme`
   and publishes `_namespace.oidc-realm=tenant-acme` to the tenant's
   `cozystack-values` Secret.
2. The `apps/kubernetes` reconcile picks up the realm, provisions the
   per-cluster `KeycloakClient kubernetes-prod-a`, the realm group
   `prod-a`, and adds OIDC flags to the kube-apiserver.
3. The post-install Job binds `Group prod-a` to `cluster-admin` inside
   the tenant cluster.

Until step 1 completes, `apps/kubernetes` renders a
`kubernetes-prod-a-awaiting-oidc-realm` ConfigMap beacon in the tenant
namespace and the kube-apiserver runs without OIDC arguments — the
client-cert (mTLS) admin kubeconfig stays usable throughout.

## Create a user and grant access

In Keycloak (the tenant realm — `tenant-acme`):

1. Create a user, set a non-temporary password, mark email verified.
2. Add the user to the realm group named after the cluster (`prod-a`).
   One membership = full `cluster-admin` access to that cluster.

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
`Kubernetes` CR with OIDC enabled does **not** trigger an
`apps/tenant` re-render, and the orphan `ClusterKeycloakRealm` stays
in the tenant namespace.

To force cleanup, the operator can:

- Toggle `Tenant.spec.oidc.enabled=true` and then back to `false`.
  Each toggle changes the HelmRelease values, which triggers a
  re-render with the up-to-date lookup result. After the second
  toggle, the chart no longer renders the realm and Helm prunes it.
  This is the only legitimate use of `Tenant.spec.oidc.enabled` —
  during normal operation the field stays at its default `false`.
- Or wait for the next platform upgrade that bumps any
  chart-affecting source — the realm cleanup happens for free as a
  side effect of the new render.

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
kubectl --context=mgmt -n tenant-acme patch keycloakclient kubernetes-prod-a \
  --type=merge --patch '{"spec":{"directAccess":true}}'
```

This is intentionally not the default — interactive flow stays
recommended for human users.

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

### Realm or scope objects stuck after CR deletion

See "Realm cleanup is not automatic" under Limitations. Operator
intervention required (toggle `Tenant.spec.oidc`).
