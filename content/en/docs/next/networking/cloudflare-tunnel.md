---
title: "Publishing through a Cloudflare Tunnel"
linkTitle: "Cloudflare Tunnel"
description: "Optional system package registering a second Gateway API implementation whose Gateways are published by Cloudflare over an outbound tunnel, for clusters with no routable inbound address."
weight: 16
---

## What this page covers

What the `cloudflare-tunnel-gateway-controller` package is and when it is the right tool, what has to exist on the Cloudflare side before enabling it, the credentials Secret, the two-step enable, how a Gateway joins the class, the limitations that should decide whether to enable it at all, and the removal path.

## What it is

`cloudflare-tunnel-gateway-controller` is an optional system package that registers a second Gateway API implementation alongside the Cilium one. A Gateway on its class is published by Cloudflare: clients reach Cloudflare's edge, and the edge carries the request into the cluster over a Cloudflare Tunnel that the in-cluster data plane opens outbound. The Services the chart renders are `ClusterIP` — the two proxy Services unconditionally, the controller's own by a `service.type` value that defaults to it — so nothing on this path asks the cluster for an address reachable from outside.

GatewayClasses are cluster-scoped and each Gateway names the one it wants, so enabling this package does not move anything already published through Cilium.

## When to reach for it

The [Gateway a tenant publishes through]({{% ref "/docs/next/networking/gateway-api" %}}) is backed by Cilium unless the tenant is moved onto another class, and that path wants two things from the outside world — an address clients can open a connection to, and an ACME challenge that completes against the cluster. The tunnel class drops both for the hostnames it serves: inbound connections are replaced by an outbound connection from the proxy pods to Cloudflare's edge, and TLS is terminated at the edge rather than on a Gateway listener.

It fits a cluster behind NAT or CGNAT, a lab or home cluster with no routable prefix, a site whose firewall will not forward ports, or a deployment that wants Cloudflare's edge in front of a subset of hostnames.

It is the wrong tool when you need TLS passthrough or any non-HTTP protocol, when the certificate a client sees has to be one the cluster controls, or when a third party in the request path is unacceptable.

## What has to exist on the Cloudflare side

1. A zone whose DNS is served by Cloudflare, covering the hostnames you intend to publish.
2. A Tunnel, created under **Zero Trust → Networks → Tunnels** with the `cloudflared` connector type. Keep both its **Tunnel ID** and its **tunnel token**.
3. An API token with the **Account → Cloudflare Tunnel → Edit** permission.

{{% alert title="Important" color="warning" %}}

Give the controller a tunnel of its own. Its upstream documentation states that it assumes exclusive ownership of the tunnel configuration, performs a full synchronization on startup, and removes ingress rules that do not come from routes it manages — so a tunnel that also carries hand-written public hostnames, or one shared with another system, loses them.

{{% /alert %}}

The Cloudflare account ID is auto-detected when the API token has access to a single account. When it does not, supply it explicitly, either as an `account-id` key in the Secret below or through the chart's `gatewayClassConfig.accountId` value.

## The credentials Secret

Both planes read one Secret, named `cloudflare-tunnel-credentials`, in the package namespace `cozy-cloudflare-tunnel-gateway-controller`:

| Key | Read by | Contents |
| --- | --- | --- |
| `api-token` | the controller | the Cloudflare API token |
| `tunnel-token` | the proxy, as the `TUNNEL_TOKEN` environment variable | the tunnel's connector token |
| `account-id` | the controller, optional | account ID, when auto-detection cannot pick one |

This is a different credential from the Cloudflare API token used by the DNS-01 ACME solver (`publishing.certificates.dns01.cloudflare.secretName`, default `cloudflare-api-token-secret`) — that one needs zone DNS permissions, this one needs tunnel permissions. Do not assume one Secret can serve both.

Create it before or shortly after enabling the package, because the proxy pod cannot start without it:

```bash
kubectl create namespace cozy-cloudflare-tunnel-gateway-controller \
  --dry-run=client --output yaml | kubectl apply --filename -

kubectl --namespace cozy-cloudflare-tunnel-gateway-controller \
  create secret generic cloudflare-tunnel-credentials \
  --from-literal=api-token="$CF_API_TOKEN" \
  --from-literal=tunnel-token="$CF_TUNNEL_TOKEN"
```

## Enabling the package

The package is in no bundle by default, because it cannot become Ready without operator input. Enabling it takes two edits, and the second lands on an object that exists only after the first.

First, list it in `bundles.enabledPackages` on the platform values:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  components:
    platform:
      values:
        bundles:
          enabledPackages:
          - cozystack.cloudflare-tunnel-gateway-controller
```

The name also has to stay out of `bundles.disabledPackages`. The two lists are checked in different places — the bundle tests `enabledPackages` before it calls the helper that renders the Package, and that helper then vetoes on `disabledPackages` — so a name present in both is not emitted, whichever order you think of them in.

That render creates a `Package` named `cozystack.cloudflare-tunnel-gateway-controller`. Second, set the tunnel ID on it:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cloudflare-tunnel-gateway-controller
spec:
  components:
    cloudflare-tunnel-gateway-controller:
      values:
        cloudflare-tunnel-gateway-controller:
          gatewayClassConfig:
            tunnelID: "00000000-0000-4000-8000-000000000000"
```

Until that value is set the chart refuses to render and the HelmRelease reports `gatewayClassConfig.tunnelID is required`. Because the Package appears only once the name is in `enabledPackages`, the first reconcile after enabling always fails this way; setting the tunnel ID changes the values and the install is retried. While that window is open the cluster carries a HelmRelease that is not Ready. Nothing in the platform gates on that, but the platform does ship the instrument most likely to notice: `check-readiness` counts `helmreleases.helm.toolkit.fluxcd.io` among the resources whose `Ready` condition it requires, so it reports the cluster as not ready until the tunnel ID is in place, and `check-readiness --wait` blocks until everything is ready or exits non-zero at its timeout (30 minutes by default). Have the tunnel ID ready before enabling if anything in your automation waits on that.

The platform writes one key of its own inside that same component values block, `controller.clusterDomain`, taken from `networking.clusterDomain`, because the vendored chart bakes the cluster domain into the proxy's config-endpoint URL and falls back to `cluster.local` when it is empty — wrong on a Cozystack default of `cozy.local`.

Editing a Package the platform renders sounds like it should be undone by the next platform reconcile, and it is not. The tunnel ID is a sibling key of the one the platform writes, and the two have different owners: helm-controller applies Packages server-side, where field ownership is tracked per field and the platform owns only what it renders, and a release still on client-side apply patches only its own rendered fields for the same result. A platform values edit or version bump therefore leaves `gatewayClassConfig.tunnelID` alone. There is no platform-values path for it — the Package is where it lives, which is why enabling takes two edits rather than one.

## The GatewayClass, and attaching a Gateway

The package creates one `GatewayClass` named `cloudflare-tunnel`, with `spec.controllerName: cf.k8s.lex.la/tunnel-controller` and a `parametersRef` to the cluster-scoped `GatewayClassConfig` where the tunnel ID and the credentials reference land. The class name is cosmetic **to the controller**, which binds its GatewayClasses by `controllerName` — but not to Cozystack: `gateway.className`, `gateway.tenantSelectableClasses` and `gateway.edgeTerminatedClasses` all match on the name, trimmed but never case-folded. Renaming the class means updating those lists, and how that failure surfaces depends on which list is stale — a `className` no controller claims leaves the Gateway unprogrammed, a dropped `tenantSelectableClasses` entry fails the tenant's release with a message naming the class, and only a stale `edgeTerminatedClasses` entry is genuinely silent. See [GatewayClass names that match no installed class]({{% ref "/docs/next/networking/gateway-api#gatewayclass-names-that-match-no-installed-class" %}}).

A Gateway joins the class by naming it, and routes attach to that Gateway the usual way:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: tunnel
  namespace: tenant-example
spec:
  gatewayClassName: cloudflare-tunnel
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app
  namespace: tenant-example
spec:
  parentRefs:
  - name: tunnel
  hostnames:
  - app.example.com
  rules:
  - backendRefs:
    - name: app
      port: 80
```

The listener also declares no `hostname`, which is deliberate: the Gateway serves whatever its routes claim, and the platform's Gateway-listener admission policy allows a hostname-less listener rather than requiring one. Give it a hostname and that hostname must fall within the namespace's `namespace.cozystack.io/host` apex.

The listener is `protocol: HTTPS` and carries no `tls` block, which is deliberate and is the shape the chart's own installation notes prescribe: TLS ends at Cloudflare's edge, so there is no certificate for this Gateway to present. Gateway API permits it — `tls` is not a required listener field, and the CRD's only rule tying the two together constrains `tls.mode` for an HTTPS listener that *has* a `tls` block, so one without it is admitted. What the listener declares here is which routes bind to it — the port and protocol are route-binding inputs on this class, not a statement about what Cloudflare's edge serves. That is why the port-80 `HTTP` shape an edge-terminated `TenantGateway` renders works on this class too.

Routes are `HTTPRoute` and `GRPCRoute`. A backend is normally a Service, and a Service of type `ExternalName` works for an out-of-cluster origin — the proxy infers the scheme from the backendRef port. The chart also installs an `ExternalBackend` CRD for the cases that shape cannot cover: it makes the scheme explicit rather than inferred, lets the host be an address that is not a valid Service name, and can prepend a base path to the request.

The controller writes the tunnel's CNAME target, `<tunnel-id>.cfargotunnel.com`, into the Gateway's `status.addresses`. Turning that into a DNS record needs an `external-dns` that watches Gateway API, which is not how Cozystack ships either of them: the system package `cozystack.external-dns` runs the upstream chart's default sources, `service` and `ingress`, and surfaces no value of its own for adding more — a Package's component values do pass through untyped, so `sources` can still be set that way, but it is undocumented rather than supported. The per-tenant `external-dns` application does have the switch — `gatewayAPI: true` adds the `gateway-httproute` and `gateway-tlsroute` sources — and it is `false` by default. Neither path adds `gateway-grpcroute`, so a hostname published only by a `GRPCRoute` gets no record from either. Failing all that, create the CNAME in the Cloudflare zone yourself, proxied.

## Which Gateway to attach

On its default settings the per-tenant Gateway that `tenant.spec.gateway: true` renders is not a drop-in for this class. Its `tlsPassthroughServices` become `protocol: TLS`, `mode: Passthrough` listeners, a shape this controller has nothing to map onto — and a listener it does not accept holds the whole object at `Ready=False`, because cozystack-controller marks a `TenantGateway` Ready only when every listener reports both `Accepted` and `Programmed`. The remaining port-443 listeners are rendered `mode: Terminate` with a `certificateRefs` entry — cert-manager's under the ACME modes, the operator's Secret under `existingSecret` — which either way is the shape this class does not use, because the edge already terminates.

Putting the class into `gateway.edgeTerminatedClasses` resolves all of that. A tenant Gateway on an edge-terminated class renders port-80 `HTTP` listeners only, with no `tls` block, no `certificateRefs` and no passthrough listeners — see [`edge` cert mode]({{% ref "/docs/next/networking/gateway-api#edge-tls-terminated-by-the-class-provider" %}}) for the full shape and for the platform values that select it. That is a Gateway this controller can serve, so the combination works; the standalone Gateway shown above is simply the path that needs no platform configuration.

Two caveats survive the switch. Edge listeners pin `allowedRoutes.kinds` to `HTTPRoute` alone, so a `GRPCRoute` cannot attach to an edge `TenantGateway` — a route of that kind needs the standalone Gateway. And selecting the class through `gateway.className` rather than per-tenant `tenant.spec.gatewayClass` puts the publishing tenant on it too. Where the platform's TLS-passthrough endpoints are published at all — each renders its `TLSRoute` only when `gateway.enabled` is on and its name is in `publishing.exposedServices` — that unpublishes them, with nothing on the Gateway or the `TenantGateway` reporting it; put child tenants on the class instead.

Two platform values are needed for that, not one. `gateway.edgeTerminatedClasses` is what selects the certificate behaviour, and `gateway.tenantSelectableClasses` is what lets a tenant name the class at all — a tenant may only name the current `gateway.className` or something on that list, and anything else fails that tenant's own gateway release at render time. See [picking a GatewayClass]({{% ref "/docs/next/networking/gateway-api#picking-a-gatewayclass" %}}). Bear in mind that a child tenant's apex is one label below its parent's, so its application hostnames sit two labels below the zone — past what Cloudflare's Universal SSL covers, per the certificate limitation below.

## Hostname ownership between tenants

By default every Gateway of this class shares one tunnel and one proxy pool, so the data plane picks a backend by hostname across all of them — a route claiming another tenant's hostname would be answered rather than ignored, which is not the case behind a per-tenant Cilium address.

Cozystack's own hostname policies do not close that on its own: the pair — `cozystack-route-hostname-policy` for `HTTPRoute` and `cozystack-route-hostname-policy-tls` for `TLSRoute` — binds route hostnames to the namespace's `namespace.cozystack.io/host` label, but between them they cover only those two kinds in namespaces whose name starts with `tenant-`, neither sees `GRPCRoute`, and both admit a route that declares no hostnames at all.

So the package turns on the chart's own hostname-ownership layer, keyed on the same `namespace.cozystack.io/host` label and scoped to every namespace that carries it. On this class, a route in such a namespace is rejected by the controller unless it declares hostnames explicitly and each one equals the label value or is a subdomain of it. A leading `*.` is stripped before that comparison, so a wildcard hostname is allowed on the same terms — `*.<label>` and `*.<sub>.<label>` both pass. The chart's fail-fast admission half of that feature stays off on purpose, because admission cannot resolve `parentRefs` and would therefore also police routes bound to the Cilium Gateway in those same namespaces.

That layer is scoped by the label existing, so a namespace without it is not policed rather than refused — leaving a `GRPCRoute` in a tenant namespace caught without its label free to claim any hostname on the shared tunnel.

A Gateway can opt out of the shared data plane with a `GatewayConfig` (`cf.k8s.lex.la/v1alpha1`) referenced from its `spec.infrastructure.parametersRef` in the same namespace; the controller then runs a proxy Deployment and a Cloudflare Tunnel dedicated to that Gateway. Keep it an operator resource: it also names the image for a Deployment the controller creates on its behalf, with the cluster-wide grant described below. The tenant roles in `cozystack-basics` carry no access to the `cf.k8s.lex.la` group today, which is what keeps it out of tenant reach.

## Limitations

{{% alert title="Important" color="warning" %}}

The controller holds a cluster-wide write grant. Its ClusterRole is attached by a ClusterRoleBinding, so every rule applies in every namespace. On Secrets it holds `get`, `list`, `watch` **and `create`** — it does not only read them — because it resolves credential, TLS and CA-bundle references wherever a Gateway or route points at them and mints a token for its own config API. It can create, update and delete Deployments, Services, NetworkPolicies and HorizontalPodAutoscalers in any namespace, which is how it materialises a dedicated data plane next to a Gateway that asks for one. Deployments additionally carry `patch`, for a different reason: the proxy Secret reconciler merge-patches the shared proxy Deployment's pod-template annotation to roll it when the tunnel token rotates. It also holds `update` and `patch` on `gateways` and `gatewayclasses` themselves, not only their `/status` subresources, which reaches the spec of any Gateway in the cluster including ones on the Cilium class. Cluster-wide Deployment creation is the strongest of these — it places a pod in any namespace, under any ServiceAccount that already exists there — so weigh that, and the Secret write, not just the Secret read, when deciding to enable the package.

{{% /alert %}}

- **HTTP and gRPC only.** A Cloudflare Tunnel carries HTTP to the origin and this controller implements `HTTPRoute` and `GRPCRoute`. There is no TLS passthrough and no raw TCP or UDP.
- **Certificates are Cloudflare's.** The edge terminates TLS, so the certificate a client sees is the one Cloudflare serves for the zone, not one cert-manager issued in the cluster. Cloudflare's Universal SSL covers the zone apex and one label below it, so a two-label hostname such as `app.tenant.example.com` needs Advanced Certificate Manager or a separate zone per tenant apex.
- **No HTTP-to-HTTPS redirect route.** The redirect `HTTPRoute` that cozystack-controller renders next to a `TenantGateway` deliberately carries no hostnames so it matches every host, and a route without explicit hostnames is exactly what the hostname-ownership layer rejects. This only arises for a `TenantGateway` whose class is *not* in `gateway.edgeTerminatedClasses` — in edge mode the redirect route is never created, and an existing one is deleted on the switch. Either way, enforce HTTPS at the Cloudflare zone level.
- **One controller replica, no leader election.** The chart defaults are `replicaCount: 1` with leader election disabled and the package does not override them, so configuration pushes pause while the controller pod restarts. The proxy runs two replicas.
- **Tunnel dial is deferred on `protocol: auto`.** The proxy negotiates QUIC with an HTTP/2 fallback and waits for the controller's first config push before dialing, bounded at roughly 30 seconds, so a proxy on a route-less cluster can take that long to connect on each start. gRPC needs HTTP/2, since cloudflared drops HTTP trailers over QUIC and `grpc-status` is lost with them; `auto` upgrades at startup when a `GRPCRoute` already exists, so a `GRPCRoute` added later needs a proxy restart.
- **Gateway API bundle skew shows up as `SupportedVersion=False`.** The controller reads the `gateway.networking.k8s.io/bundle-version` annotation off the installed Gateway API CRD and compares it with the bundle it was built against; per its own documentation it requires an exact major-and-minor match, accepting a patch difference but not a different minor. Both halves of that comparison are worth checking rather than trusting: the vendored bundle version is pinned in `gateway-api-crds` and is the half this repository controls, while the version the controller was built against comes from the upstream project and is not recorded anywhere in this tree. Its RBAC matches that — a single uncached `get` on `customresourcedefinitions`, no watch. When they disagree the class comes up `Accepted=True` next to `SupportedVersion=False`, reason `UnsupportedVersion`, with a message naming the minor it wants. Expect to see exactly that on a stock install for as long as the two pins differ: this chart is built against Gateway API v1.6.1 while `gateway-api-crds` currently vendors the bundle at v1.5.1, and both pins move independently, so check them rather than assume either. The two conditions are set independently and nothing gates serving on the version one, so read `Accepted` for whether the class is usable — but treat the skew as a real signal rather than cosmetic noise, because the Gateway API CRDs carry structural schemas and any field the controller writes that exists only in the newer bundle is pruned by the older CRD on write, with no error anywhere. The condition is recomputed only on that GatewayClass's next reconcile: the controller deliberately does not watch the CRDs, so a spec change, a periodic resync or a controller restart is what refreshes it.
- **Nothing is scraped by default.** Both ServiceMonitors the chart carries are gated on `serviceMonitor.enabled`, which is `false` and which the package does not change. Turning it on is not sufficient on its own: the proxy serves `/metrics` on its config API port, and the proxy's NetworkPolicy — on by default — admits that port only from the package namespace, so the monitoring namespace has to be added to `proxy.networkPolicy.ingress.from` in the same change.
- **Leave the controller's own NetworkPolicy off.** `networkPolicy.enabled` is `false` in the chart and the package does not change it. Turning it on restricts controller egress to DNS, to TCP 443 and 6443 (on any destination), and to the Cloudflare address ranges on 443 — none of which covers the proxy's config API port, `8081` by default — so where the CNI enforces NetworkPolicy the controller can no longer push configuration to its data plane. The proxy's own policy is a separate value, on by default, and is not affected.
- **Coverage is template-level.** The package ships chart tests that pin its wiring; no end-to-end test exercises a live tunnel.

## Removing the package

Taking the name back out of `bundles.enabledPackages` does not remove anything on its own, and deleting the Package on its own does not stick. Both are needed, and the order matters twice over.

The platform annotates every package it emits with `helm.sh/resource-policy: keep`, so dropping the name from `enabledPackages` stops the platform rendering the Package but deletes nothing — the Package stays, the HelmRelease it owns stays, and so do the controller and proxy Deployments, the cluster-wide ClusterRole and its binding, and the GatewayClass. That is deliberate, but it means a cluster that reads as disabled is still running a controller that can read Secrets in every namespace and write Deployments in every namespace.

Deleting the Package while the name is still listed does not stick either. `keep` blocks deletion, not creation, so the next `helm upgrade` of the platform — any version bump, any platform values edit — renders the Package again. What comes back carries only what the platform renders; the `gatewayClassConfig.tunnelID` set by hand died with the object. The chart then refuses to render and that HelmRelease fails permanently, so `check-readiness` reports the cluster as not ready — indefinitely this time, rather than for the length of a window — until someone traces it back.

So, in this order:

1. Delete every Gateway on the `cloudflare-tunnel` class, and the routes attached to them.
2. Remove `cozystack.cloudflare-tunnel-gateway-controller` from `bundles.enabledPackages`, so the platform stops rendering the Package.
3. Wait for the `cozystack-platform` HelmRelease to finish reconciling step 2, then delete the Package:

   ```bash
   kubectl delete package.cozystack.io cozystack.cloudflare-tunnel-gateway-controller
   ```

   The HelmRelease carries an ownerReference back to the Package, so this garbage-collects the release and with it both Deployments, the Services, the RBAC and the GatewayClass.

Step 1 has to precede step 3 for a second, unrelated reason: while any Gateway uses the class, the controller keeps the `gateway-exists-finalizer.gateway.networking.k8s.io` finalizer on the GatewayClass, and the controller is the only thing that removes it. Delete the Package first and the GatewayClass is left in `Terminating` behind a finalizer nothing will clear, which means editing the finalizer off by hand.

Three things outlive the uninstall by design. Helm does not remove CRDs it installed from a chart's `crds/` directory, so the `GatewayClassConfig`, `GatewayConfig` and `ExternalBackend` kinds stay registered along with any objects of those kinds. The namespace `cozy-cloudflare-tunnel-gateway-controller` carries the same `keep` annotation and stays. And the `cloudflare-tunnel-credentials` Secret in it was created by hand rather than by the release, so nothing in the teardown touches it — revoke the Cloudflare API token and delete the tunnel on Cloudflare's side too, or the credentials outlive the cluster that used them.

## Supply-chain notes

The chart is vendored into this repository and the PackageSource installs it from that local path, so nothing fetches a chart at install time. What an air-gapped install does need is the two images — the controller and the proxy, both from `ghcr.io/lexfrei`, which is the maintainer's personal namespace and is not mirrored under `ghcr.io/cozystack/*`. Mirror those two into an internal registry; the chart is already in the tree. Both image tags are pinned by digest in the package `values.yaml`. The chart's own version and OCI manifest digest are pinned in the package Makefile, but that pin governs re-vendoring by a maintainer running `make update`, not anything an operator installs.

The vendored chart ships its CRDs in `crds/`, which Helm installs once and never touches again on upgrade, so the PackageSource sets `upgradeCRDs: CreateReplace`: the controller has added kinds across minor releases, and without it a chart bump would land a new controller binary against the old CRD set.

## See also

- [Gateway API]({{% ref "/docs/next/networking/gateway-api" %}}) — the per-tenant Gateway, how its GatewayClass is chosen, its cert modes including `edge`, and the layered hostname security model.
- [Enabling and disabling components]({{% ref "/docs/next/operations/configuration/components#enabling-and-disabling-components" %}}) — the `bundles.enabledPackages` / `bundles.disabledPackages` mechanism used here.
- [`lexfrei/cloudflare-tunnel-gateway-controller`](https://github.com/lexfrei/cloudflare-tunnel-gateway-controller/) — upstream controller source, chart, and full configuration reference.
- [Cloudflare Tunnel documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) — creating a tunnel, connector tokens, and edge behaviour.
- [Gateway API](https://gateway-api.sigs.k8s.io/) — GatewayClass, Gateway and route semantics.
