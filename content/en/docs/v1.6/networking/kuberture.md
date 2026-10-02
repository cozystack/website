---
title: "Publishing the Kubernetes API endpoint via external-dns"
linkTitle: "Kubernetes API DNS publication"
description: "Translate the default/kubernetes EndpointSlice into annotated headless Services so external-dns can publish the Kubernetes API endpoint to DNS, with the bundled kuberture component."
weight: 26
---

## What this page covers

How to publish the cluster's own Kubernetes API endpoint as a DNS record using `external-dns`, why the obvious approach (point `external-dns` directly at the `default/kubernetes` EndpointSlice) does not work, the cozystack-bundled bridge (`kuberture`, see [`lexfrei/kuberture`](https://github.com/lexfrei/kuberture)), how a single `kuberture` install can serve more than one `external-dns` instance simultaneously, and the disable path.

## Why external-dns cannot read EndpointSlice directly

`external-dns` reads DNS-relevant state from Kubernetes sources — `service`, `ingress`, `gateway-httproute`, and a handful of others. It does **not** support `EndpointSlice` as a source. The control-plane EndpointSlice that Kubernetes maintains at `default/kubernetes` is the canonical, always-up-to-date list of node addresses serving the API; it is also the only first-class object that carries that information without operator-supplied labels or selectors. Operators who want their cluster's API endpoint published to public DNS through `external-dns` (cert-manager `dns01` challenges, internal automation reaching the API by FQDN, multi-cluster service discovery, …) hit this gap immediately.

The workarounds usually proposed — a hand-maintained `Service` of type `ExternalName`, a hand-maintained headless `Service` with manually-pinned `Endpoints`, an out-of-band script that polls the API and updates a record — all share the same flaw: they stop matching reality as soon as a control-plane node is added, removed, or renumbered. The EndpointSlice already tracks this state correctly. `kuberture` bridges the two.

## How kuberture fixes it

`kuberture` is a small in-cluster controller that watches `EndpointSlice` and writes annotated headless `Service` objects. The flow is:

```text
EndpointSlice (kubernetes) → kuberture → headless Service(s) with annotations → external-dns → DNS
```

For each operator-configured output, `kuberture` creates a headless Service (`spec.clusterIP: None`) in its own namespace (`cozy-kuberture`) and stamps three annotations on it. Each key is the operator-supplied `annotationPrefix` followed by a fixed suffix:

| Full annotation key | Source |
| --- | --- |
| `<annotationPrefix>hostname` | the operator-supplied hostname(s) for this output |
| `<annotationPrefix>target` | comma-joined IP addresses resolved from the EndpointSlice or from the Nodes it points at |
| `<annotationPrefix>ttl` | the operator-supplied `recordTTL`, falling back to the controller default when omitted |

With the default prefix that resolves to `external-dns.alpha.kubernetes.io/hostname`, `external-dns.alpha.kubernetes.io/target`, `external-dns.alpha.kubernetes.io/ttl` — the keys the platform `external-dns` reads out of the box. `external-dns` reads the Service, sees the annotations, and creates the DNS record. The Service has no selector and no manually-managed Endpoints — it exists solely to carry annotations for `external-dns` consumption.

The controller does **not** write `EndpointSlice` or `Endpoints` objects (it only has read permission on `EndpointSlice`), and it does **not** touch the upstream `default/kubernetes` EndpointSlice. It is strictly additive: a separate Service per output, in its own namespace, with no side effects on existing cluster state.

## Enabling on the host

`kuberture` is an optional system package, opt-in via `bundles.enabledPackages`. The package itself ships no usable default beyond enabling `ServiceMonitor` for the platform Prometheus — the deployment fails fast if `config.outputs` is empty. The operator must declare at least one output, because the only thing `kuberture` cannot infer is the DNS hostname the operator actually wants to publish.

Single output, consumed by the platform-level `external-dns`:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full
  components:
    platform:
      values:
        bundles:
          enabledPackages:
            - cozystack.external-dns
            - cozystack.kuberture
---
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.kuberture
spec:
  variant: default
  components:
    kuberture:
      values:
        kuberture:
          config:
            outputs:
              - name: api
                hostname:
                  - api.k8s.example.com
                serviceName: kuberture-api
                addressSource: endpointslice
                recordTTL: 60
```

`annotationPrefix` is omitted here, so the controller uses the default `external-dns.alpha.kubernetes.io/` — the prefix the platform `external-dns` watches out of the box. With both packages enabled, the `external-dns` HelmRelease picks up the `kuberture-api` Service in `cozy-kuberture` and creates the `api.k8s.example.com` record in the configured provider.

The `cozystack.external-dns` Package is the cluster-wide system instance (it runs with `namespaced: false` and watches Services across the cluster). `cozystack.external-dns-application` is the tenant-namespaced variant and will not pick up Services outside its tenant namespace — pair `kuberture` with `cozystack.external-dns`, not `cozystack.external-dns-application`, on the host control plane.

## Routing to multiple external-dns instances

A single `kuberture` install can address any number of `external-dns` instances by varying `annotationPrefix` per output. Each `external-dns` instance is started with `--annotation-prefix=<your-prefix>/` so it rebuilds every `hostname`/`target`/`ttl` annotation key under that prefix and ignores everything else; `kuberture` stamps the matching prefix on each Service. This is the upstream-documented [Split Horizon DNS pattern](https://kubernetes-sigs.github.io/external-dns/v0.20.0/docs/advanced/split-horizon/) — distinct from `--annotation-filter`, which is a Kubernetes label-selector that filters *which Services* an instance considers, not which prefix it reads data from.

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.kuberture
spec:
  variant: default
  components:
    kuberture:
      values:
        kuberture:
          config:
            outputs:
              - name: public
                hostname:
                  - api.k8s.example.com
                serviceName: kuberture-public
                addressSource: endpointslice
              - name: internal
                hostname:
                  - api-internal.k8s.example.internal
                annotationPrefix: internal-dns.example.com/
                serviceName: kuberture-internal
                addressSource: endpointslice
                recordTTL: 300
```

This renders two headless Services in `cozy-kuberture`:

- `kuberture-public` carries the default `external-dns.alpha.kubernetes.io/*` annotations and is consumed by the platform `external-dns`.
- `kuberture-internal` carries `internal-dns.example.com/*` annotations and is invisible to the platform `external-dns` (which is reading the default prefix). A second `external-dns` instance started with `--annotation-prefix=internal-dns.example.com/` consumes it: the prefix flag tells that instance to look up `hostname`/`target`/`ttl` under `internal-dns.example.com/*`, so it sees `kuberture-internal` and is blind to `kuberture-public`.

Each Service carries **only** its own prefix's annotations — there is no cross-pollution between outputs.

`annotationPrefix` accepts two forms: omit the field to inherit the controller default `external-dns.alpha.kubernetes.io/`, or set it to a non-empty string ending in `/`. The empty string `""` is rejected by the chart's values schema; omission is the only way to fall back to the default prefix.

## Address resolution strategies

`addressSource` selects where each output gets its target IPs:

| `addressSource` | What `kuberture` publishes |
| --- | --- |
| `endpointslice` (default) | The addresses listed in the `default/kubernetes` EndpointSlice verbatim. Use this when the EndpointSlice IPs are the addresses you want in DNS. |
| `node-internal` | The `InternalIP` of each Node hosting an EndpointSlice endpoint. Use this when the EndpointSlice carries pod-network IPs but external-dns must publish node-internal addresses. |
| `node-external` | The `ExternalIP` of each Node. Use this for cloud-managed clusters where Nodes have public addresses on a different interface than the API listens on. |
| `node-public` | A node's public IP looked up through a public-IP discovery hook (provider-specific). |

`addressType` (`IPv4` / `IPv6`) further filters the resolved set; default is `IPv4`.

## Disable path

Removing `cozystack.kuberture` from `bundles.enabledPackages` stops the platform Helm chart from emitting the `Package` CR. As with every optional system package, the existing `Package` CR is **not** removed automatically: the platform helper stamps `helm.sh/resource-policy: keep` on each emitted Package, so Helm/Flux leaves it in place when it stops being rendered. To fully remove `kuberture`:

```bash
kubectl delete package.cozystack.io cozystack.kuberture
```

The cascade removes the HelmRelease in `cozy-kuberture`, which removes the Deployment, the operator-supplied output Services, and (eventually) the namespace. `external-dns` records previously published from those Services follow `external-dns`'s own delete policy (`policy: upsert-only` is the cozystack default, which means records are **not** retracted on Service deletion; switch to `policy: sync` ahead of time if records must be cleaned up automatically).

## Supply-chain notes

The chart is pulled from `oci://ghcr.io/lexfrei/kuberture/charts/kuberture` and the controller image from `ghcr.io/lexfrei/kuberture`. Both live in the maintainer's personal namespace and are intentionally not mirrored under `ghcr.io/cozystack/*`. Air-gapped operators must mirror both the chart and the controller image into their internal registry and override `kuberture.image.repository` in the Package values. Chart version and OCI manifest digest are pinned in the cozystack package Makefile; the controller image tag and image digest are pinned in the package's `values.yaml`. Pins advance in lockstep with each upstream release.

See the package README at [`packages/system/kuberture/`](https://github.com/cozystack/cozystack/tree/main/packages/system/kuberture) for the full values surface, the bump procedure, and the `NetworkPolicy` default-off choice.

## See also

- [Enabling and disabling components]({{% ref "/docs/v1.6/operations/configuration/components#enabling-and-disabling-components" %}}) — the `bundles.enabledPackages` / `bundles.disabledPackages` mechanism used here.
- [Platform Package reference]({{% ref "/docs/v1.6/operations/configuration/platform-package" %}}) — `bundles.enabledPackages` field reference.
- [`lexfrei/kuberture`](https://github.com/lexfrei/kuberture) — upstream controller source and chart, configuration reference, and roadmap.
- [`packages/system/kuberture/`](https://github.com/cozystack/cozystack/tree/main/packages/system/kuberture) — cozystack package: values shim, helm-unittest fixtures, end-to-end smoke test.
