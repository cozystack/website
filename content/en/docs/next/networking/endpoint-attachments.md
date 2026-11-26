---
title: "Attaching addresses to application endpoints"
linkTitle: "Endpoint attachments"
description: "Give one Service of a managed application its own external address, minted from an IPAddressClass or bound from a reserved IPAddressClaim, with EndpointAttachment."
weight: 28
---

## What this page covers

`EndpointAttachment` (`local.sdn.cozystack.io/v1alpha1`, namespaced) attaches one external address to one tenant-facing Service of one managed application. The address comes from the address substrate described in [Reserved IP addresses]({{% ref "/docs/next/networking/reserved-ip-addresses" %}}): it is either minted for the attachment from an `IPAddressClass` or bound from an `IPAddressClaim` the tenant reserved earlier.

This is the Network load-balancing path, a dedicated address per attachment. It sits beside, not in place of, the Application load-balancing path through the tenant [Gateway]({{% ref "/docs/next/networking/gateway-api" %}}), where several databases share one address and are routed by SNI. Publish through the Gateway to save addresses. Attach an address when a client allow-lists an IP, when the protocol cannot carry SNI, or when you need an address you can hold and move between applications.

Attaching and detaching never touches the application's own Services, values or Helm release. The chart-level `external: true` keeps its exact behaviour in every chart, and attachments are additive beside it.

## Prerequisites

- The `cozystack.address-controller` and `cozystack.metallb-iad` packages enabled, and at least one `IPAddressClass` to draw from, as set up in [Reserved IP addresses]({{% ref "/docs/next/networking/reserved-ip-addresses" %}}). A tenant that names no class draws from the class annotated as the default.
- For the VM datapath modes below, cozy-proxy deployed. The platform's system bundle deploys it on the full variants and declares it to the controller; on the slim variants it is opt-in.
- `EndpointAttachment`s follow the access tenants have to applications: the roles that can manage applications in a tenant namespace can manage attachments there, and every access level from view upward can read them. `count/endpointattachments.local.sdn.cozystack.io` works with a stock `ResourceQuota`. The scarce resource, addresses, is already bounded at the claim.

## The resource

```yaml
apiVersion: local.sdn.cozystack.io/v1alpha1
kind: EndpointAttachment
metadata:
  name: mydb-replicas-public
  namespace: tenant-a
spec:
  applicationRef:            # immutable; the application, in this namespace
    kind: Postgres           # group defaults to apps.cozystack.io
    name: mydb
  endpoint:
    serviceName: postgres-mydb-ro
  loadBalancer:              # the only mechanism member; exactly one is required
    className: public        # mint a claim from this IPAddressClass (omit both for the default class)
    # claimName: held-ip     # ...or bind a reserved IPAddressClaim (exclusive with className)
    # family: IPv4           # IPv4 | IPv6 | Dual
    # ports: [5432]          # a subset of the endpoint's ports
    # method: WholeIP        # WholeIP | PortList, VM datapath modes (see below)
    # allowICMP: true        # PortList only
status:
  phase: Attached            # Pending | Attached | Detached, a projection of the conditions
  serviceName: mydb-replicas-public-x7ktq
  claimName: mydb-replicas-public-k2m9p
  addresses: ["203.0.113.7"]
  conditions: [...]          # Resolved, Provisioned
```

```sh
kubectl -n tenant-a get endpointattachment mydb-replicas-public -o jsonpath='{.status.addresses[*]}'
```

`applicationRef`, `className`, `claimName` and `family` are immutable: they select the address, and changing one under a live attachment could re-mint or release an address a client has allow-listed. Changing the address source is delete-and-recreate, and a reserved claim is how an address survives that. `ports`, `method`, `allowICMP` and the endpoint stay mutable.

## Which Services can be attached

The endpoint must be a Service in the attachment's namespace carrying both label families the platform stamps: the lineage labels `apps.cozystack.io/application.{group,kind,name}` matching `applicationRef` on all three, and the tenant-facing marker `internal.cozystack.io/tenantresource: "true"`. The platform writes the marker on exactly the Services the application's [`ApplicationDefinition.spec.services`]({{% ref "/docs/next/cozystack-api/application-definitions#tenant-facing-services" %}}) selects, so what is attachable is whatever that list declares, per kind.

A Service the list leaves out is refused with `Resolved=False`, whether it belongs to another application, to the system, to the tenant Gateway, or to the application itself without being declared (MariaDB's `-metrics` Service, for one). The list is not a filter for internal or headless Services: some kinds declare such Services and they are attachable, among them OpenBao's `-internal` and Qdrant's `-headless` Services and, for a managed Kubernetes cluster, every Service carrying its `cluster.x-k8s.io/cluster-name` label. Resolution is by condition, not admission, because the Service set is dynamic: a MariaDB `-secondary` Service exists only while `replicas > 1`, and an attachment created before its application resolves once the Service appears.

One kind of Service passes both label checks and is still refused with `EndpointNotTenantFacing`: a LoadBalancer Service the cloud-controller-manager of a tenant Kubernetes cluster creates for a Service inside that cluster, recognised by the `cluster.x-k8s.io/tenant-service-name` label that controller writes. It carries the cluster's labels but serves a workload inside the tenant cluster.

Publishing a Service also needs a selector, because the rendered Service mirrors the endpoint's selector, not its endpoints. A Service whose endpoints are managed by hand has no selector, so it reports `Provisioned=False` with `NothingToPublish` and nothing is rendered. Headless Services with a selector are published like any other.

The tenant Gateway's own LoadBalancer Service is not attachable.

## What the controller renders

One additive `type: LoadBalancer` Service per attachment, created with `generateName` from the attachment's name so it can never collide with the Service it publishes. The Service:

- mirrors the endpoint's selector and ports, or the `ports` subset;
- carries the substrate's consumption annotation `local.sdn.cozystack.io/ip-address-claim: <claim>`;
- is created with the `loadBalancerClass` the class's provisioner reports in `status.loadBalancerClass`, read before creation because a Service's `loadBalancerClass` is immutable. An empty value is the cluster's default load-balancer implementation, and the Service then carries none. The value counts only once the class's `Accepted` condition is True for its current generation; until then the attachment renders nothing and reports `ClassNotAccepted` with the provisioner's reason, and a Service already published stays;
- asks for the claim's families: `SingleStack` in the claim's family for an `IPv4` or `IPv6` claim, `RequireDualStack` for a `Dual` one. A cluster with no dual-stack service range refuses a `Dual` attachment's Service, which the attachment reports as `RenderFailed`.

The rendered Service copies nothing else from the endpoint, no labels and no annotations, so it is never read as a second tenant-facing endpoint or as a route backend. The controller identifies its Service by the controller owner reference alone. The `cozystack.io/endpoint-attachment` label on it is diagnostic, and a Service carrying it without the owner reference is ignored, never adopted.

The attachment itself is owned by the application's HelmRelease and stamped with the application's lineage labels. Deleting the application collects its attachments, their Services and any minted claims, and a same-name recreated application does not re-acquire the previous one's attachments.

## Address lifecycle

- `className`, or neither field: a claim is minted under the attachment and collected with it. The address then follows the class's reclaim policy, which defaults to `Retain`: the `IPAddress` stays `Released`. If the class sets `releaseDelay`, it returns to `Available` once that delay has passed, unless the address is annotated `ipaddress.local.sdn.cozystack.io/held: "true"`; otherwise it stays until an admin clears its `claimRef`.
- `claimName`: the reserved claim is referenced, never owned or written. Detaching leaves the address held, and the same claim can be attached to another endpoint or application later; the address follows.
- A claim already worn by another Service reports `Provisioned=False` with `ClaimInUse` and is not contended.
- An endpoint Service that disappears, for example on a scale-down, turns the attachment `Detached`: the rendered Service is withdrawn, the claim and its address are kept, and the attachment reattaches when the Service returns.

## Conditions

`Resolved=True` means the endpoint Service exists and passed the tenant-facing check. `Provisioned=True` means the claim is bound and the rendered Service has been assigned its address. That is all it asserts: address and Service wiring. Reachability also depends on the CNI's own policy objects (SecurityGroups, NetworkPolicies and, under a VPC-capable CNI, the VPC gateway's ingress setting), which the controller does not read. `status.phase` is `Attached` when both conditions are true, `Detached` when the endpoint went away after an address was held, and `Pending` otherwise. A failing condition's message says what the attachment waits for.

## TLS

Attaching a database does not turn its TLS on or make the server refuse plaintext. The controller mirrors a Service and knows nothing about engines, and an attachment never sets `external`, which several charts key their TLS defaults on. PostgreSQL, for one, always serves TLS but accepts plaintext sessions unless `tls.required` is on, and that defaults to the value of `external`: set `tls.required: true` on the application before attaching a public address to it. `tls.enabled` controls only whether the external hostname is added to the certificate, and does not refuse plaintext. For other database kinds, check what each chart does with TLS before attaching. No chart adds an IP SAN to a server certificate, so a client dialing an attached address verifies by hostname only if DNS also points a name the certificate carries at the address.

## VM datapath modes

A VMInstance's tenant-facing Service is headless with a single placeholder port until the chart exposes it, so a VM attachment must set `ports` or `method`; with neither it reports `Provisioned=False` with `NothingToPublish`. `method: PortList` publishes the listed ports and `method: WholeIP` publishes every port through 1:1 NAT, both through cozy-proxy. Where the platform does not deploy cozy-proxy, an attachment with a `method` renders no Service and reports `DatapathContractUnavailable`, because a load balancer would still attract an address nothing forwards.

Three rules follow from the datapath:

- `WholeIP` presumes a single backend. While the endpoint resolves to more than one ready pod, the attachment keeps its Service and its address but selects nothing and reports `MultipleBackends`. A rolling update or a live migration passes through this state and recovers on its own.
- The datapath maps one address per backend pod in either mode. A second delegated Service on the same pod is refused with `BackendAlreadyDelegated`. A chart Service rendered with `external: true` always wins, even when it appears after the attachment, which then withdraws its own Service; between attachments, the oldest wins. The controller detects the conflict; cozy-proxy itself does not refuse it.
- cozy-proxy maps IPv4 only. An `IPv6` or `Dual` claim on this path renders no Service and reports `FamilyUnsupportedByDatapath`; use an `IPv4` claim. A VM in a cozyplane VPC is served through a FloatingIP instead (below), which takes an `IPv6` claim.

`allowICMP` is honoured by cozy-proxy in `PortList` mode.

### VMs in a VPC

What a VM in a VPC can be given depends on how the VPC application is built on the cluster.

- **kube-ovn.** The VM keeps its pod-network interface and joins each VPC subnet through an additional interface. The modes above apply unchanged: the public address reaches the VM on its pod-network interface, not on a VPC subnet.
- **cozyplane.** The VM's only interface is in the VPC, so the pod address cozy-proxy maps to never reaches it. For `method: WholeIP`, the controller instead creates a cozyplane `FloatingIP` in the attachment's namespace, binding the VM's VPC address and wearing the attachment's claim. The FloatingIP is owned by the attachment and removed with it. `Provisioned` turns true once the FloatingIP is `Ready` with the claim's address in a status computed for its current spec, so a VM moving to a new VPC address is not reported attached on the old binding's status. No Service is rendered, so `status.serviceName` stays empty. A FloatingIP wears one address, so this path needs an `IPv4` or `IPv6` claim; a `Dual` claim is refused with `DualStackUnsupportedInVPC` and nothing is bound.

A cozyplane VPC backend is recognised by the `sdn.cozystack.io/vpc` annotation the VM chart puts on the launcher pod, and its address is the one cozyplane's CNI copies into `sdn.cozystack.io/vpc-ip`; until it is there, the attachment reports `WaitingForVPCAddress`. On a cluster that does not serve `sdn.cozystack.io` FloatingIP, a VPC backend reports `DatapathContractUnavailable` and gets no Service. Several refusals follow from what a FloatingIP is:

- `method: PortList` reports `MethodUnsupportedInVPC`, because a FloatingIP binds every port and cozy-proxy cannot reach the VPC address. To publish chosen ports into a VPC, omit `method` and list `ports`: the plain LoadBalancer Service that renders reaches VPC pods through cozyplane's load-balancer datapath, once the VPC's gateway admits LoadBalancer ingress.
- A VPC owned by another namespace reports `VPCNotInNamespace`, because a FloatingIP references a VPC, and a claim, in its own namespace only.
- Backends holding different VPC addresses, or mixing VPC and non-VPC pods, report `MultipleBackends`, and the address stays held by the claim. The source and target pods of a live migration share the VM's VPC address, so a migration is a single target and keeps its binding.
- A stopped VM keeps its FloatingIP, which stays pending until the VM runs again.

Only a backend pod says whether a VM sits in a VPC, so an attachment with a `method` that has published nothing yet waits for one, reporting `WaitingForBackend`. An attachment created before its VM starts therefore publishes nothing until the launcher pod exists, and then gets the FloatingIP or the cozy-proxy Service its pod calls for. The claim holds the address meanwhile, and anything already published stays when the VM stops.

## Engines with in-protocol discovery

Kafka, MongoDB replica sets and NATS hand clients other addresses in-protocol. Attaching an address to their Services does not give a working external endpoint, because the engine keeps advertising its internal addresses and an attachment does not rewrite engine configuration.
