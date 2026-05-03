---
title: "PROXY-protocol and the hairpin-NAT fix"
linkTitle: "PROXY-protocol and hairpin"
description: "Enable PROXY-protocol on ingress-nginx in cozystack and fix the resulting hairpin-NAT problem with the bundled ouroboros component."
weight: 25
---

## What this page covers

PROXY-protocol on the host ingress-nginx, the hairpin-NAT problem it introduces, the cozystack-bundled fix (`ouroboros`, a Go reimplementation of [`compumike/hairpin-proxy`](https://github.com/compumike/hairpin-proxy) — see [`lexfrei/ouroboros`](https://github.com/lexfrei/ouroboros)), the single platform flag that wires both pieces, the per-tenant addon for the same fix inside tenant clusters, and the asymmetric disable path on each layer.

## Why PROXY-protocol breaks intra-cluster traffic

When the upstream L4 load balancer (cloud LB, hcloud-CCM, F5, MetalLB-fronted haproxy, …) prepends a [PROXY-protocol v1 header](https://www.haproxy.org/download/1.8/doc/proxy-protocol.txt) to every connection landing on ingress-nginx, ingress-nginx is configured with `use-proxy-protocol: "true"` and accepts only headered connections. External traffic works.

Intra-cluster traffic does not. A pod that resolves the cluster's own public hostname (cert-manager HTTP-01 self-checks, internal `https://` calls to public DNS, ArgoCD-to-self, …) hits CoreDNS and gets the LoadBalancer IP back. kube-proxy / Cilium-KPR sees that LB IP and short-circuits to the local Service, bypassing the upstream LB. The connection arrives at ingress-nginx **without** the PROXY header it now requires. Ingress-nginx closes the connection. Hairpin breaks silently.

[KEP-1860](https://kubernetes.io/blog/2023/12/18/kubernetes-1-29-feature-loadbalancer-ip-mode-alpha/) (`status.loadBalancer.ingress[].ipMode: Proxy`) is the upstream answer in clusters fronted by an external CCM-managed proxy LB. It is **not** a fit for cozystack defaults: with `kubeProxyReplacement: true` and Cilium-announced LB IPs, Cilium drops the LB frontend entirely when `ipMode != VIP`, breaking the Service for both intra- and extra-cluster traffic. cozystack uses ouroboros instead.

## How ouroboros fixes it

ouroboros is a small in-cluster controller that watches `Ingress` (and optionally `Gateway` / `HTTPRoute`) for hostnames and rewrites cluster-internal DNS so those hostnames resolve to a small in-cluster proxy that prepends the PROXY-protocol header before forwarding to ingress-nginx. Two cooperating pieces:

- a **controller** that watches Ingress / Gateway resources and adds CoreDNS `rewrite name <host> ouroboros-proxy.…svc.cluster.local.` lines;
- a **TCP proxy** that listens on 8080/8443, prepends the PROXY-protocol v1 header, and forwards to the real ingress-nginx Service.

cozystack uses two operating modes depending on layer:

| Layer | Mode | What ouroboros writes |
| --- | --- | --- |
| Host control plane | `coredns` | The live `kube-system/coredns` Corefile, between `# === BEGIN ouroboros (do not edit by hand) ===` markers. The host CoreDNS is Talos-managed and does not include an `import` directive, so the alternative mode would silently no-op there. |
| Tenant Kubernetes clusters | `coredns-import` | Plugin-only `rewrite name` lines into the `ouroboros.override` data key of `kube-system/coredns-custom`, a separate ConfigMap that the cozystack-coredns chart ships and pulls into the Corefile via `import /etc/coredns/custom/*.override`. ouroboros never touches the chart-rendered Corefile, so it does not race the chart on every Flux reconcile. |

## Enabling on the host

One platform flag turns on PROXY-protocol at the host ingress-nginx **and** auto-deploys the host-side ouroboros:

```yaml
publishing:
  proxyProtocol: true
```

Default is `false` — clusters that do not run PROXY-protocol get zero new resources, zero RBAC delta, zero behaviour change.

### Upstream-LB precondition

The flag does not configure the L4 load balancer in front of ingress-nginx for you — that lives outside the cluster (cloud LB, F5, MetalLB+haproxy, hcloud-cloud-controller-manager, …). The upstream LB **must** already be injecting PROXY-protocol v1 headers before the flag flips on.

PROXY-protocol frames travel from the upstream LB to ingress-nginx (the LB opens a fresh TCP connection to the backend and prepends the frame on that connection), not back to the original client — `nc` from a laptop will never see one. Two practical verification paths, pick one:

- Run `tcpdump --interface any port 80 or port 443 -A` on the node hosting ingress-nginx **before** flipping the flag and watch for a leading `PROXY TCP4 …\r\n` frame on inbound TCP from the LB. If the frame is there, the LB is injecting and the flag is safe to flip.
- Make any external HTTP request **after** the LB-side change but **before** flipping `publishing.proxyProtocol`, and watch ingress-nginx logs (`kubectl --namespace cozy-ingress-nginx logs deploy/ingress-nginx-controller`) for `client sent invalid proxy protocol header` — that error means the LB started injecting PROXY frames but ingress-nginx is not yet configured to accept them, which is exactly the transition state the flag is meant to resolve. The opposite log (`broken header` after the flag flips with the LB **not** injecting) signals the precondition was not actually in place and is the failure to roll back from.

Without the precondition, every external request to ingress-nginx breaks the moment the flag flips on. If neither verification path shows PROXY frames, fix the upstream LB before touching `publishing.proxyProtocol`.

### Talos re-render flap window

The host CoreDNS is a Talos-managed Deployment; ouroboros mutates its live Corefile in place between BEGIN/END markers. A Talos machine-config push or upgrade re-renders the Corefile and overwrites the markers — there is a flap window of one ouroboros reconcile loop (chart default `controller.resync: 10m`, bounded above by the next Ingress/Gateway event) until the controller re-applies the block. Any Ingress or Gateway event during the window fires reconcile early and shortens it. In-cluster DNS for hairpinned hostnames briefly returns the upstream LB IP instead of the proxy ClusterIP during that window, which fails the same way intra-cluster hairpin fails when ouroboros is not installed at all (the kube-proxy short-circuit reasserts itself; PROXY-less requests hit ingress-nginx and get rejected). Acceptable, but worth knowing during a Talos roll.

### The cozystack-coredns wrapper

cozystack ships its own thin wrapper around the upstream `coredns/helm-charts` package: the Corefile gets an `import /etc/coredns/custom/*.override` directive in the `.:53` server block, and the CoreDNS Deployment mounts an empty `coredns-custom` ConfigMap at `/etc/coredns/custom/` (with `optional: true`). The wrapper template renders that ConfigMap with **no `data:` field at all** — Helm's three-way merge therefore has no template-side keys to compare against on each reconcile, and the apiserver-side `data.ouroboros.override` writes ouroboros adds at runtime survive every chart upgrade intact. The `helm.sh/resource-policy: keep` annotation on the same ConfigMap is a separate, weaker concern: it only blocks `helm uninstall` from deleting the ConfigMap, not chart-upgrade strip. The invariant is pinned by `notExists: data` in `packages/system/coredns/tests/coredns_custom_test.yaml` — a future chart change that adds even `data: {}` "to be explicit" trips that assertion before the regression ships. This wiring is consumed by **tenant** CoreDNS Deployments today (where ouroboros runs in `coredns-import` mode); the host CoreDNS is Talos-managed and never consumes this chart, which is why the host install runs in `coredns` mode against the live Corefile instead.

### Cluster DNS domain on tenants

The ouroboros chart bakes the rewrite target FQDN (`--proxy-fqdn=...svc.<cluster-domain>.`) at chart-render time, defaulting to `cluster.local` when `controller.clusterDomain` is left empty. That default matches the kubeadm default for kubelet `--cluster-domain` (cozystack tenants are bootstrapped via kubeadm and do not override that flag), the cozystack-coredns wrapper kubernetes-plugin zone, and the underlying Kamaji `TenantControlPlane.spec.networkProfile.clusterDomain` default — all of them `cluster.local` end-to-end. cozystack therefore leaves `controller.clusterDomain` unset in the tenant addon wrapper; passing the host's `networking.clusterDomain` (often `cozy.local`) would write a rewrite target the tenant CoreDNS does not serve and silently yield NXDOMAIN.

The chart binary's runtime auto-detect of `--cluster-domain` (added upstream in 0.6.0) is a sanity check only — it parses `/etc/resolv.conf` inside the controller pod and WARN-logs a mismatch against the chart-time `--proxy-fqdn` via `ClusterDomainMismatch`; it does NOT recompose the rewrite target. Tenant operators that run a tenant on a non-default cluster-domain MUST override the chart-render default by setting `addons.ouroboros.valuesOverride.ouroboros.controller.clusterDomain` in the `Kubernetes` CR — the controller pod's startup log surfaces a mismatch warning if they forget.

## Enabling per tenant

Tenants that run their own ingress-nginx with PROXY-protocol need ouroboros inside the tenant cluster. The `addons.ouroboros` knob on the per-tenant `Kubernetes` CR turns on the chart there:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Kubernetes
metadata:
  name: production
  namespace: tenant-acme
spec:
  addons:
    ingressNginx:
      enabled: true
      hosts: [acme.example.org]
      valuesOverride:
        ingress-nginx:
          controller:
            config:
              use-proxy-protocol: "true"
              use-forwarded-headers: "true"
              compute-full-forwarded-for: "true"
              real-ip-header: proxy_protocol
              enable-real-ip: "true"
              # SECURITY: when use-forwarded-headers is on, ALWAYS pair it with
              # proxy-real-ip-cidr scoped to the upstream LB's CIDR. Without
              # that pairing, any client can spoof X-Forwarded-For and
              # bypass IP-based controls. The host platform deliberately
              # omits use-forwarded-headers / compute-full-forwarded-for
              # for this reason — turn them on at the tenant only when you
              # have a paired CIDR.
              # proxy-real-ip-cidr: "10.0.0.0/24"
    ouroboros:
      enabled: true
```

See the [Disable path](#disable-path) section below before flipping `enabled` back to `false` — the rewrite block ouroboros wrote into the tenant CoreDNS does not get cleaned up automatically.

`addons.ouroboros.enabled: true` requires `addons.ingressNginx.enabled: true`. The tenant chart fails the render with a clear error otherwise — the hairpin fix has nothing to fix against without ingress-nginx, and a no-op addon that quietly does nothing is harder to debug than an explicit render-time error. Toggle ingress-nginx on first if ouroboros is the addon you actually want. Unlike the host flag, the tenant addon does **not** automatically enable PROXY-protocol on the tenant ingress-nginx — the `use-proxy-protocol` / `use-forwarded-headers` / `real-ip-header` config is wired manually via `valuesOverride` because tenants commonly have different upstream-LB configurations (some get PROXY frames from the cozystack-host load balancer, some from a tenant-specific edge). ouroboros is a no-op without it, so leaving it off when PROXY-protocol is off saves the resources.

## Disable path

Disabling has different shapes on the two layers, by design. The host path has a render-time acknowledgement gate (`publishing.proxyProtocolAcknowledgeUnclean`) because `helm.sh/resource-policy: keep` on the platform Package CR creates a stop-emit-but-stay-installed asymmetry that is dangerous to discover late. The tenant path has **no** gate — `addons.ouroboros.enabled: false` triggers `helm uninstall` directly, the chart's pre-delete hook handles cleanup on the way out, and the cozystack tenant template deliberately omits a `lookup`-based render-guard there (gating on a leftover HelmRelease would deadlock the routine disable: the parent render runs before helm-controller applies the missing-child diff, so the lookup would always find the leftover at the moment of the flag flip).

**Host scope.** Flipping `publishing.proxyProtocol` from `true` to `false` does two things:

- ingress-nginx side: the next reconcile re-emits `cozystack.ingress-application` without `use-proxy-protocol` / `real-ip-header` / `enable-real-ip` (cozystack deliberately does NOT set `use-forwarded-headers` or `compute-full-forwarded-for` on the host: those keys would let any upstream proxy spoof `X-Forwarded-For` without a paired `proxy-real-ip-cidr`). ingress-nginx stops accepting PROXY-protocol headers. **If the upstream L4 LB is still prepending PROXY frames at that moment, every external request to ingress-nginx breaks until the LB is also reconfigured.** Flip the LB OFF first, then flip this flag.
- ouroboros side: stops emitting the `cozystack.ouroboros` Package CR, but every Package CR carries `helm.sh/resource-policy: keep`. Helm leaves the existing Package on the cluster, ouroboros stays installed, and the live Corefile rewrite block keeps pointing at the still-running `ouroboros-proxy` Service. The flag flip alone does **not** uninstall ouroboros.

The platform refuses to render the bare flag flip when a `cozystack.ouroboros` Package CR is already on the cluster — `helm template` / `helm upgrade` fails fast with an error that points at `kubectl delete package.cozystack.io cozystack.ouroboros` (which triggers helm uninstall and the chart's pre-delete cleanup hook) and the acknowledgement field. The chart shipped at `0.6.0` carries a vendored pre-delete hook (`charts/ouroboros/templates/coredns-cleanup-hook.yaml`) that quiesces the controller and `sed`-strips the `# === BEGIN ouroboros … END ouroboros ===` block from `kube-system/coredns` automatically when helm actually uninstalls the chart — operators do **not** need to run the manual `sed` recipe in the normal disable path. The full host disable sequence is:

1. Flip the upstream LB off PROXY-protocol injection (external traffic precondition).
2. Remove the Package CR with `kubectl delete package.cozystack.io cozystack.ouroboros` (or add it to `bundles.disabledPackages`). This triggers helm uninstall, which fires the chart's pre-delete hook and patches `kube-system/coredns` automatically.
3. Set `publishing.proxyProtocol: false` in the platform values. The render guard now passes (the `lookup` for `cozystack.ouroboros` returns nil after step 2), so `publishing.proxyProtocolAcknowledgeUnclean` stays at its default `false`.

If the operator has reason to flip `publishing.proxyProtocol: false` BEFORE deleting the Package CR (strict GitOps where `kubectl delete` is not in-band, parallel rollbacks, etc.), set `publishing.proxyProtocolAcknowledgeUnclean: true` together with the flag flip in the same commit, then drive the Package deletion separately. Flip `proxyProtocolAcknowledgeUnclean` back to `false` once the cluster has been clean for one reconcile cycle. This is the escape valve, not the recommended path — the staged sequence above keeps the ack flag at its default and avoids the round-trip.

The host cleanup recipe below is the manual fallback for the rare case where the chart's pre-delete hook fails to land (controller pod stuck in CrashLoop blocking the quiesce step, ConfigMap RBAC drift, helm uninstall interrupted before the hook ran). Reach for it only when the automatic path failed and the BEGIN/END block is still in `kube-system/coredns` after the package was deleted.

**Known hole**: an operator who deletes the Package CR before flipping the flag bypasses the guard entirely (the `lookup` returns nil, the platform render proceeds). In `0.6.0+` that path is mostly safe — `kubectl delete package` triggers helm uninstall and the chart's pre-delete hook patches the Corefile on its way out. The hole is the rare case where the hook itself fails (controller stuck, RBAC drift, hook timeout) and the operator never noticed. The acknowledgement gate is defence-in-depth, not an airtight lock.

**Tenant scope.** Flipping `addons.ouroboros.enabled` from `true` to `false` stops the HelmRelease from rendering and Flux uninstalls the chart on the next tenant-side reconcile. The `helm.sh/resource-policy: keep` annotation referenced in the host scope above lives on the platform Package CR — it is **not** in play on the tenant side, so disabling there really does delete the workload, not just stop emitting it. helm uninstall fires the same chart pre-delete hook on the tenant: it nulls the `ouroboros.override` key in `kube-system/coredns-custom` automatically before the controller pod goes away. The full tenant disable sequence is one step:

1. Set `addons.ouroboros.enabled: false` in the tenant `Kubernetes` CR. Flux runs `helm uninstall` and the chart's pre-delete hook patches `kube-system/coredns-custom` for you.

If the chart's pre-delete hook fails to land (controller pod stuck CrashLooping, ConfigMap RBAC drift, Job timeout, manual `kubectl delete hr` bypassing helm uninstall), the symptom is a stale rewrite in the tenant `kube-system/coredns-custom` ConfigMap pointing at a Service that is now gone. Recover by running the tenant cleanup recipe below against the tenant admin-kubeconfig.

Tenant ingress-nginx is unaffected by toggling `addons.ouroboros` on its own — PROXY-protocol on the tenant ingress is wired manually via `valuesOverride` and stays where the operator put it.

### Host cleanup recipe (fallback)

This recipe is the manual fallback for the rare case where the chart's pre-delete hook failed to land (see the host disable sequence above for the happy path that runs the hook automatically). Prerequisites: `kubectl` against the host kubeconfig, plus `jq` and `sed` on the operator workstation. The block is delimited by `# === BEGIN ouroboros (do not edit by hand) ===` and `# === END ouroboros ===` (the `(do not edit by hand)` parenthetical is on the BEGIN line only). The `sed` range below uses prefix matches on each end so the markers are matched regardless of the trailing form.

```bash
# === BEGIN cleanup-recipe ===
existing=$(kubectl --namespace kube-system get configmap coredns \
  --output jsonpath='{.data.Corefile}')
cleaned=$(printf '%s\n' "$existing" \
  | sed '/# === BEGIN ouroboros/,/# === END ouroboros/d')
kubectl --namespace kube-system patch configmap coredns \
  --type merge \
  --patch "$(jq --null-input --arg c "$cleaned" \
      '{data: {Corefile: $c}}')"
kubectl --namespace kube-system rollout restart deployment/coredns
# === END cleanup-recipe ===
```

The recipe uses a JSON merge-patch so labels, annotations, and other data keys on the `coredns` ConfigMap (including any Talos-managed metadata) are preserved.

### Tenant cleanup recipe (fallback)

This recipe is the manual fallback for the rare case where the chart's pre-delete hook failed to null the `ouroboros.override` key on its own (the tenant happy path leaves cleanup to the chart and does not run a manual recipe at all). Prerequisites: `kubectl` against the tenant admin kubeconfig (no `jq` / `sed` needed — the tenant recipe is a single one-shot patch). Run it after a failed disable to bring the ConfigMap back to a clean state.

```bash
kubectl --kubeconfig <tenant-admin-kubeconfig> --namespace kube-system patch \
  configmap coredns-custom --type merge \
  --patch '{"data":{"ouroboros.override":null}}'
```

`ouroboros.override` is the only key ouroboros owns inside `coredns-custom`; nulling it leaves any other keys (operator-owned `*.override` snippets, future cozystack additions) intact.

## Air-gapped operators

The chart and image are pulled directly from the upstream `lexfrei/ouroboros` registry — they are not mirrored under `ghcr.io/cozystack/*`. Air-gapped operators have to mirror two additional locations:

- `oci://ghcr.io/lexfrei/charts/ouroboros:0.6.0` (the chart, digest-pinned in `packages/system/ouroboros/Makefile` as `OUROBOROS_CHART_DIGEST=sha256:ce51fb5c273af36cfd1061f2010c4ee20aab7f539a0d13b7223f63d24188fe25`);
- `ghcr.io/lexfrei/ouroboros:0.6.0@sha256:b33c415cd2edf231eb62076297fee1b75657bef2bfcc0be916b84088aa49479d` (the image, digest-pinned in `packages/system/ouroboros/values.yaml` — feed this exact reference to `regsync` / `crane copy` / `skopeo copy`).

The cozystack image reference includes the `@sha256:…` digest above. Mirror tooling has to either preserve that digest end-to-end (the standard behaviour of `regsync`, `crane copy`, `skopeo copy`) or drop the `@sha256:…` pin from `values.yaml` post-mirror — otherwise the kubelet pull resolves against the upstream digest, fails to find it under the mirror's tags, and lands in `ErrImagePull`.

## Why not KEP-1860 in cozystack defaults

Cozystack's `kubeProxyReplacement: true` default means Cilium drops the LB frontend entirely when `ipMode != VIP`, breaking Service ingress for L2/BGP-announced IPs. KEP-1860's `Proxy` mode is reserved for clusters fronted by an external CCM-managed proxy LB that handles the connection itself; that contract is not the one cozystack ships. ouroboros is the right fix for the L2/BGP-announce topologies cozystack ships by default.
