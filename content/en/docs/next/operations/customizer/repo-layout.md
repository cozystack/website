---
title: "Repo Layout and Worked Examples"
linkTitle: "Repo Layout"
description: "Recommended customizer-repo directory tree, with three end-to-end examples."
weight: 20
---

This page covers what to put inside the customizer repo once the loop is wired up (see **[Setup]({{< relref "setup.md" >}})** if you haven't enabled the package yet).

## Recommended layout

```
cozystack-customizer/
  README.md
  clusters/
    prod/
      kustomization.yaml
      platform.yaml                # patch for cozystack.cozystack-platform
      packages/
        metallb.yaml               # patch — spec.components.metallb.values
        ingress-nginx.yaml
      sources/
        myorg-charts.yaml          # extra OCIRepository
      packagesources/
        myorg-internal-portal.yaml # extra PackageSource using myorg-charts
      keycloak/
        realm-cozy.yaml
      apps/                        # admin-owned HelmReleases
        ns-platform-tools.yaml
        my-monitoring-stack.yaml
      rbac/
        readonly-engineers.yaml
      networkpolicies/
        default-deny.yaml
```

The corresponding entry-point `clusters/prod/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - platform.yaml
  - packages/
  - sources/
  - packagesources/
  - keycloak/
  - apps/
  - rbac/
  - networkpolicies/
```

You can use any layout that kustomize accepts. The structure above groups files by what they target (`packages/` = patches to Cozystack Packages, `apps/` = your own HelmReleases, etc.), which makes review of a PR scope obvious.

For a multi-cluster setup, put one folder per cluster under `clusters/`, share common manifests via a `base/` folder, and point each cluster's customizer at its own `clusters/<env>` path.

## Example 1 — Enable OIDC on the host

The in-cluster recipe:

```sh
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=merge --patch '{
  "spec": {
    "components": {
      "platform": {
        "values": {
          "authentication": {
            "oidc": {
              "enabled": true,
              "keycloakInternalUrl": "http://keycloak-http.cozy-keycloak.svc:8080/realms/cozy"
            }
          }
        }
      }
    }
  }
}'
```

becomes a file in the customizer repo — `clusters/prod/platform.yaml`:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  components:
    platform:
      values:
        authentication:
          oidc:
            enabled: true
            keycloakInternalUrl: http://keycloak-http.cozy-keycloak.svc:8080/realms/cozy
```

Same write to the same Package CR, but as a reviewable commit. The customizer Kustomization patches `spec.components.platform.values.authentication.oidc.*` via SSA — chart-managed fields (`spec.variant`, `metadata.annotations["helm.sh/resource-policy"]`) are untouched.

To complete OIDC setup, see **[OIDC Server]({{< relref "/docs/next/operations/oidc/enable_oidc.md" >}})** for the wider configuration (API server flags, identity provider, etc.); only the in-cluster `kubectl patch` step is replaced by the customizer manifest above.

## Example 2 — Override a system-component option

Turn on `frrk8s` mode in MetalLB. The Package CR for MetalLB doesn't have `spec.components.metallb.values.*` set out of the box, so any keys you add are admin-owned and the chart will not fight them.

`clusters/prod/packages/metallb.yaml`:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.metallb
spec:
  components:
    metallb:
      values:
        metallb:
          frrk8s:
            enabled: true
```

Crucially, **do not** include `spec.variant` here. The variant is chart-owned. See **[Field ownership]({{< relref "field-ownership.md" >}})** for why this matters and what the current enforcement gap looks like.

After the commit lands, watch the underlying HelmRelease pick up the new value:

```sh
kubectl --namespace cozy-metallb get helmrelease metallb -o yaml | grep -A2 frrk8s
```

## Example 3 — Ship an in-house HelmRelease

The customizer SA is bound to `cluster-admin` inside the `cozy-customizer` namespace (default) — and any other namespace you list under `customizer.rbac.ownedNamespaces` in the Platform Package values. Inside those namespaces, the customizer can create arbitrary resources.

First make sure the chart source is registered. If your charts live in an OCI registry:

`clusters/prod/sources/myorg-charts.yaml`:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: OCIRepository
metadata:
  name: myorg-charts
  namespace: cozy-customizer
spec:
  interval: 5m
  url: oci://ghcr.io/<your-org>/cozystack-charts
  ref:
    tag: v0.4.0
```

Then the HelmRelease itself:

`clusters/prod/apps/internal-portal.yaml`:

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: internal-portal
  namespace: cozy-customizer
spec:
  interval: 5m
  chartRef:
    kind: OCIRepository
    name: myorg-charts
    namespace: cozy-customizer
  values:
    host: portal.example.org
```

After reconcile:

```sh
kubectl --namespace cozy-customizer get helmrelease internal-portal
kubectl --namespace cozy-customizer get pods
```

## Custom packages — your own charts as Cozystack Packages

For a more integrated experience (Package-CR lifecycle, dependency tracking, `kubectl get package` visibility, status reporting), you can register your charts as Cozystack `PackageSource`s and treat them like platform packages.

`clusters/prod/packagesources/myorg-internal-portal.yaml`:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: PackageSource
metadata:
  name: myorg.internal-portal
spec:
  sourceRef:
    kind: OCIRepository
    name: myorg-charts
    namespace: cozy-customizer
    path: /
  variants:
    - name: default
      components:
        - name: internal-portal
          path: internal-portal
          install:
            namespace: myorg-portal
            releaseName: internal-portal
```

Plus the `Package` instance:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: myorg.internal-portal
spec:
  variant: default
  components:
    internal-portal:
      values:
        host: portal.example.org
```

Cozystack's reconciler doesn't care whether the PackageSource came from the platform chart or the customizer Kustomization — the same engine, dashboards, and `kubectl get package` apply.

The `myorg-portal` namespace in the example above is **not** under `customizer.rbac.ownedNamespaces`, so the customizer SA can't create resources directly there. That's fine — the Cozystack reconciler runs as `cozystack-controller` (cluster-admin) and creates the actual HelmRelease into `myorg-portal` on the customizer's behalf, with the values the customizer declared.

## Operational tips

- **Always include `kustomize.config.k8s.io/v1beta1` kustomization.yaml at the path** — a missing entry-point file is the most common first-commit failure.
- **`prune: true` is on by default.** Removing a manifest from the kustomization deletes the corresponding resource from the cluster. Test removals on a non-prod cluster first.
- **`wait: true` is on by default.** The Kustomization waits for all applied resources to be `Ready` before reporting success — slow chart installs (cert-manager waiting on issuers, etc.) can make the Kustomization look stuck. Set `customizer.kustomization.wait: false` in the Platform Package values if you find this gets in the way.
- **Force-reconcile is fast:** `flux --namespace cozy-system reconcile kustomization cozystack-customizer --with-source` syncs the GitRepository and the Kustomization in one command.
