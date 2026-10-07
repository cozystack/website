---
title: "Setting up Proxmox-backed VPC Subnets"
linkTitle: "Proxmox VPC Subnets"
description: "Enable the opt-in proxmox-network package, prepare the Proxmox VE hosts, the cluster nodes and the transit network, and operate the zones that back tenant VPC subnets with Proxmox VLANs."
weight: 30
---

{{% alert title="Proposed feature" color="warning" %}}
This page describes a feature that is **not merged** into Cozystack and is not part of any release.
It is implemented in the draft pull request [cozystack/cozystack#4813](https://github.com/cozystack/cozystack/pull/4813),
its design is discussed in the proposal [cozystack/community#93](https://github.com/cozystack/community/pull/93),
and whether Proxmox VE becomes a supported platform is decided in [cozystack/cozystack#3481](https://github.com/cozystack/cozystack/issues/3481).
Package names, values and behaviour may change before it lands, or the feature may not land at all.
{{% /alert %}}

## What this page covers

What a platform administrator sets up so that tenants can add `proxmox: {}` to a VPC subnet and put Proxmox VE virtual machines on it, the workers of Proxmox-backed Kubernetes clusters included:

- the Proxmox VE hosts: a VLAN-aware zone bridge, QinQ on the uplink and the MTU;
- the cluster nodes: one trunk NIC each for Kube-OVN;
- the transit network and the router that gives the VPCs their way out;
- the `cozystack.proxmox-network` package and its zones;
- admission, status, metrics and alerts, and day-2 operations.

The tenant side is described in [Proxmox-backed VPC subnets]({{% ref "/docs/next/networking/proxmox-vpc-subnets" %}}).

## How the pieces fit

A tenant's Proxmox-backed subnet becomes a VLAN-backed (underlay) logical switch of the tenant's own Kube-OVN VPC router. Each subnet gets one VLAN from a range the administrator owns. The VLANs reach the cluster nodes over a single trunk NIC per node, and Kube-OVN tags each subnet's localnet port with its VLAN. VMs and pods on a subnet are L2 neighbours, and the VPC router port is the VMs' gateway.

```text
 Proxmox VM (net0, tag 201)       Proxmox VM (net0, tag 202)
        |                                  |
 ---- zone bridge vmbr1 (VLAN-aware, on bond0.40, every Proxmox VE host) ----
        |   trunk 199-299: one virtio NIC per cluster node, no address
        v
 node trunk NIC -> OVS bridge of the provider network
                     -> localnet port, tag 201 -> switch of tenant A's subnet -> VPC A router
                     -> localnet port, tag 202 -> switch of tenant B's subnet -> VPC B router
                     -> transit VLAN 199       -> egress gateways of every VPC -> transit router
```

| Object | Scope | Created by | Tenant access |
| --- | --- | --- | --- |
| `ProxmoxNetworkZone` | cluster | the administrator, through the package values | none |
| Kube-OVN `ProviderNetwork` (the trunk) | cluster | the package | none |
| Transit `Vlan`, `Subnet` and NetworkAttachmentDefinition | cluster, package namespace | the package | none |
| Kube-OVN `Subnet` with `vlan` set | cluster | the vpc application | through the application |
| `InClusterIPPool` for the VMs' range | tenant namespace | the vpc application | read |
| `ProxmoxNetwork` | tenant namespace | the vpc application; the controller fills its status | read |
| Kube-OVN `Vlan` | cluster | `proxmox-network-controller` | none |
| `VpcEgressGateway` | the zone's gateway namespace | the vpc application | none |

The controller allocates the VLANs, holds the Subnet, the Vlan and the pool with finalizers until no VM holds an address, makes each router port reachable from the VLAN (see [Gateway management](#gateway-management)), maintains a namespace annotation that admission reads, and exports metrics.

## Requirements

- The `isp-full` or `isp-full-generic` variant with the `iaas` bundle. The package needs Kube-OVN and Multus.
- A Proxmox VE cluster that runs both the management cluster's nodes, as VMs, and the tenant VMs, so that both reach the zone bridge. This guide assumes that layout. The implementation was tested with Proxmox VE 9.
- For Proxmox-backed Kubernetes clusters, also the opt-in `cozystack.capi-provider-infra-proxmox` package and its credentials. The networks themselves do not need it: pods can use a zone before any Proxmox-backed cluster exists.
- A router for the transit network outside the cluster: a Linux host or VM, or a physical router.

## Example topology

The examples on this page use one topology. Every value is an example, not a default, unless it is named as the package default.

- The hosts' uplink is a bond, `bond0`. Tenant traffic rides on an outer VLAN of it, `40`, as the VLAN device `bond0.40`. `vmbr0` is the hosts' own bridge directly on `bond0`.
- The zone bridge is `vmbr1`, VLAN-aware, on `bond0.40`.
- Tenant VLANs come from `200-299`. The transit VLAN is `199`, with the network `192.0.2.0/24` and the transit router at `192.0.2.1`.
- The Kube-OVN provider network is `pxtenant` on the trunk NIC `ens19` (both package defaults), and the transit subnet is `px-transit` (the package default).
- The uplink runs a 9000-byte MTU, so the zone MTU is `8996`.

## Prepare the Proxmox VE hosts

### Zone bridge

On every host, create a VLAN-aware bridge on its own outer VLAN of the uplink, carrying the tenant VLANs and the transit VLAN:

```text
auto bond0.40
iface bond0.40 inet manual
    mtu 9000

auto vmbr1
iface vmbr1 inet manual
    bridge-ports bond0.40
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 199-299
    mtu 9000
    post-up sysctl -w net.ipv6.conf.vmbr1.disable_ipv6=1
```

- Disabling IPv6 on the zone bridge keeps the host itself, with its link-local address, off the tenant transport.
- Bring up only the new interfaces, with `ifup bond0.40 vmbr1`. Do not run `ifreload -a` on a host whose interfaces file has stale entries.
- Add the outer VLAN to the switch ports of every path between the hosts, the backup path of the bond included.

Tenant VLANs ride inside the outer VLAN, so a tag a guest sends on a tenant VLAN never reaches the hosts' own VLANs. That holds only while no guest NIC sits on a bridge that enslaves the uplink's parent device, such as `vmbr0` over `bond0`: such a NIC is a trunk on which the guest can set the outer tag itself and reach the zone bridge with any inner tag. Admission keeps Cluster API machines off those bridges (`uplinkBridges`, below). For any other guest on them, make the host drop guest 802.1Q and 802.1ad frames, for example with ebtables on the guest ports, or make that bridge VLAN-aware with `bridge-vids` that exclude the uplink and host VLANs.

### QinQ on the uplink

Between the hosts, tenant and transit frames carry two 802.1Q tags: the outer VLAN of the uplink and the inner tenant VLAN. The uplink must keep both.

- A frame that loses its inner tag lands in the far bridge's VLAN 1 and reaches the trunk NICs untagged. No localnet port matches it, so everything that crosses hosts breaks, and the tenant VLANs of the other host are no longer apart on that bridge.
- Some NICs overwrite the inner tag when they insert the outer one in hardware. This was seen with Mellanox ConnectX-3 (`mlx4_en`) ports in an active-backup bond. Other NICs may behave the same, so test every pair of hosts, in both directions.
- To test a pair, send traffic on an inner VLAN from one host to the other, for example a ping from the transit router to an egress gateway. On the receiving host, `tcpdump -nei <active bond slave> vlan` must show both tags, and `bridge fdb show br vmbr1` must list the sender's MAC under the inner VLAN, not `vlan 1`. A VM-to-VM ping across hosts on one tenant VLAN is the end-to-end check.
- If the inner tag is lost, turn off hardware VLAN insertion with `ethtool -K <slave> txvlan off` on every slave of the uplink bond, the backup slaves included, so the kernel inserts the outer tag. Persist it, for example as a `post-up` of the bond or of its VLAN device, and check it again after host changes.

### MTU

Choose one number, the zone MTU, and make every hop fit it:

- The zone MTU is the uplink VLAN device's MTU minus 4, because the inner tag is payload of that device. In the example `bond0`, `bond0.40`, `vmbr1` and the trunk NICs run 9000, and the zone, the transit network and the transit router's interface 8996.
- A switch on the uplink path must pass 9000 bytes plus the Ethernet header, two tags and the FCS.
- The zone MTU goes into the VM NICs that capmox creates and, through the vpc application, into the Kube-OVN subnets of the Proxmox-backed subnets, so that the egress gateway pods run at the VMs' MTU. Set `transit.mtu` of the package to the same value.
- Overlay pods keep Kube-OVN's own MTU, typically 1400. OVN sends no "fragmentation needed" between the two, so a full-size packet with the DF bit set from a VM to an overlay pod is dropped silently. TCP is not affected.
- A changed zone MTU reaches only VMs that are created after the change, and pods that are recreated after it.

The acceptance check is a DF ping of the VM's full MTU from a VM, through the egress gateway, to the transit router: it must arrive, or the VM must receive "fragmentation needed".

## Prepare the cluster nodes

Each management cluster node that should carry tenant networks needs one extra virtio NIC on the zone bridge, trunking the tenant and transit VLANs, with no address:

```bash
qm set <vmid> --net1 virtio,bridge=vmbr1,trunks=199-299,mtu=9000
```

The NIC's name inside the node is the package's `providerNetwork.defaultInterface` (`ens19` by default). A node with another name goes into `providerNetwork.customInterfaces`, and a node without the NIC into `providerNetwork.excludeNodes`.

On Talos Linux, tell Talos to leave the NIC alone. `dhcp: false` is not enough:

```yaml
machine:
  network:
    interfaces:
      - interface: ens19
        ignore: true
```

Without `ignore: true`, Talos keeps trying to take the NIC back from Open vSwitch, logs `error enslaving/unslaving link ... operation not supported`, and leaves the link down while Kube-OVN still reports the node ready. After patching a running node, restart its `kube-ovn-cni` pod, which brings the link up when it starts.

Pods attached to a Proxmox-backed subnet, the egress gateways included, can run only on nodes with the trunk.

## Prepare the transit router

The egress gateways of all VPCs SNAT the traffic of their Proxmox-backed subnets onto the shared transit network. The router at the transit gateway address decides where it goes next, and it carries the L3 boundary between VPCs on its own. It must:

- forward from the transit network, with SNAT, only to the LoadBalancer range the tenant control planes use, DNS (UDP 53), NTP (UDP 123) and the Internet;
- use as that LoadBalancer range the address pool the tenant Kubernetes control planes get their LoadBalancer addresses from, with a free address for each Proxmox-backed cluster;
- drop every other private destination and have no route into any VPC address range;
- decide transit traffic in both directions ahead of any other forwarding rule;
- keep its rules across restarts and netfilter reloads. A reload that removes them, under a forwarding policy of accept, leaves the router open.

Inside the transit network, an ACL keeps each egress gateway to the router: one gateway cannot reach another VPC's gateway.

## Enable the package

Add `cozystack.proxmox-network` to `bundles.enabledPackages` of the Platform Package, and give the package its values. Enabling it also installs the in-cluster IPAM provider, `cozystack.capi-provider-ipam-in-cluster`. Listing that provider in `bundles.disabledPackages` at the same time fails the platform render.

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
            - cozystack.proxmox-network
---
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.proxmox-network
spec:
  variant: default
  components:
    proxmox-network:
      values:
        providerNetwork:
          create: true
          name: pxtenant
          defaultInterface: ens19
          excludeNodes: []
        zones:
          - name: default
            bridge: vmbr1
            vlanRanges: ["200-299"]
            mtu: 8996
            uplinkVLAN: 40
            uplinkBridges: [vmbr0]
        transit:
          enabled: true
          vlan: 199
          cidr: 192.0.2.0/24
          gateway: 192.0.2.1
          mtu: 8996
```

The package installs two components into `cozy-proxmox-network`: `proxmox-network-crds` first, which is kept on uninstall, and then `proxmox-network` with the controller.

### Package values

| Value | Default | Meaning |
| --- | --- | --- |
| `providerNetwork.create` | `false` | Create the Kube-OVN ProviderNetwork that carries the trunk. Set `true` unless you manage it yourself. |
| `providerNetwork.name` | `pxtenant` | ProviderNetwork name, at most 12 characters. |
| `providerNetwork.defaultInterface` | `ens19` | The trunk NIC inside the nodes. |
| `providerNetwork.customInterfaces` | `[]` | Nodes whose trunk NIC has another name, as `[{interface: ens20, nodes: [node-3]}]`. |
| `providerNetwork.excludeNodes` | `[]` | Node names without a trunk. A name that matches no Node excludes nothing, and the node it meant keeps the provider network from becoming ready. |
| `providerNetwork.nodeSelector` | `{}` | Select trunk nodes by label instead. |
| `zones` | `[]` | The `ProxmoxNetworkZone` objects, see below. |
| `transit.enabled` | `false` | Create the transit `Vlan`, `Subnet` and NetworkAttachmentDefinition. Zones without their own `egress` then use it. |
| `transit.name` | `px-transit` | Name of the transit subnet. |
| `transit.vlan`, `transit.cidr`, `transit.gateway` | | VLAN, network and router address of the transit network. |
| `transit.excludeIps` | `[]` | Addresses the router side keeps, in Kube-OVN notation (`a..b`). |
| `transit.mtu` | `""` | MTU of the egress gateways' transit interface. Match the zone MTU. |
| `ovn.manageGatewayChassis` | `true` | Make each Proxmox-backed router port reachable from its VLAN. See [Gateway management](#gateway-management). |
| `ovn.nbAddress` | `ssl:ovn-nb.cozy-kubeovn.svc:6641` | OVN northbound address(es), comma-separated. Writes must reach the RAFT leader, which the `ovn-nb` Service selects. |
| `ovn.tlsSecret.namespace`, `ovn.tlsSecret.name` | `cozy-kubeovn`, `kube-ovn-tls` | Kube-OVN's client TLS material. |
| `admission.enabled` | `true` | The machine binding policy. |
| `admission.vmNetworkNamespace`, `admission.podNetworkNamespace` | `true` | The attachment policies for KubeVirt VMs and for pods. |
| `admission.exemptNamespaces` | `[]` | Namespaces the attachment policies skip, on top of the platform's own. |
| `admission.validationActions` | `[Deny]` | Validation actions of every policy of the package. |
| `alerts.enabled` | `true` | Ship the PrometheusRule. |
| `proxmoxNetworkController.subnetPruneTimeout` | `""` (10m) | How long a deleted subnet may stay listed on its Kube-OVN Vlan before the VLAN is released anyway. Raise it above twice the longest Kube-OVN or OVN outage you expect. |

### Zones

A zone is the pool of VLANs on one Proxmox bridge that tenant subnets draw from.

| Field | Meaning |
| --- | --- |
| `name` | Zone name. Tenants name it in `subnets[].proxmox.zone`; with a single zone they may leave it out. |
| `bridge` | The VLAN-aware bridge present on every Proxmox VE host the VMs may run on. |
| `providerNetwork` | The Kube-OVN ProviderNetwork that carries the zone's VLANs. Defaults to `providerNetwork.name`. |
| `vlanRanges` | The only VLANs the allocator may hand out, such as `["200-299"]`. |
| `reservedVLANs` | VLANs inside the ranges that are never allocated. |
| `mtu` | Written into the VM NICs and into the Kube-OVN subnets of the zone's networks. |
| `namespaceSelector` | Which namespaces may have networks in this zone. Empty admits every namespace. |
| `staticAssignments` | Explicit VLANs for given networks, as `{namespace, name, vlan}`. |
| `egress.externalSubnet`, `egress.gatewayNamespace` | The subnet the VPC egress gateways attach to, and the platform namespace they run in. Default to the transit subnet and the package namespace when `transit.enabled` is set. Tenant egress needs both. |
| `uplinkVLAN` | Admission only, not part of the zone object. The outer VLAN that carries the zone bridge between hosts (`40` in the example). A machine NIC on any other bridge may not use it as its tag. |
| `uplinkBridges` | Admission only. Every other bridge that enslaves the uplink's parent device (`vmbr0` in the example). No machine NIC may sit on them. |

Leaving `uplinkVLAN` or `uplinkBridges` unset leaves that path into the zone open.

Extending a zone's range is safe. Shrinking it never takes a VLAN away from a network that holds one; the zone's Ready message lists the VLANs stranded outside the new ranges until those networks are deleted.

### Verify

```bash
kubectl get proxmoxnetworkzones
kubectl get provider-networks.kubeovn.io pxtenant
kubectl get nodes --selector pxtenant.provider-network.kubernetes.io/ready=true
```

The zone must be Ready, and every node that should carry the trunk must have the ready label. On each of those nodes the trunk NIC must be up, and `ovs-vsctl get interface ens19 link_resets` must stay steady.

## Admission policies

The package installs three ValidatingAdmissionPolicies, all bound with `admission.validationActions`:

- `proxmox-network-machine-binding` (`admission.enabled`), on CREATE of `ProxmoxMachine` and `ProxmoxMachineTemplate` in every namespace:
  - a NIC on a zone bridge must be one of the namespace's own networks (bridge, VLAN and pool together), so a namespace without Proxmox networks cannot reach the trunk through a raw bridge and VLAN;
  - a NIC on any other bridge may not be tagged with a zone's `uplinkVLAN`;
  - no NIC may sit on a zone's `uplinkBridges`;
  - in a namespace that owns networks, every NIC must be one of them.
- `proxmox-network-vm-attachments` (`admission.vmNetworkNamespace`): a KubeVirt VM or VMI attaches only NetworkAttachmentDefinitions and Kube-OVN subnets of its own namespace.
- `proxmox-network-pod-attachments` (`admission.podNetworkNamespace`): the same rule for pods, including those other controllers create. A `*.kubernetes.io/logical_switch` pin other than the namespace's default switch is refused on CREATE, so a copy of a running pod that keeps Kube-OVN's annotations (`kubectl debug --copy-to`, a restored backup) is refused too.

The attachment policies hold in every namespace except `cozy-*`, `kube-system`, the package namespace, each zone's egress gateway namespace and `admission.exemptNamespaces`. They apply as soon as the package is enabled, whether or not a tenant uses a Proxmox-backed subnet. The bridges, uplink VLANs and uplink bridges the machine policy checks come only from the package values: a zone created outside them is not protected, and VMs created outside Cluster API are not covered at all.

## Gateway management

Kube-OVN's OVN drops ARP requests that arrive from a localnet port for the address of a router port, unless that router port is a gateway port. Without a change, a VM on a Proxmox VLAN never resolves its gateway: it reaches pods on its own subnet at L2, but nothing routed.

With `ovn.manageGatewayChassis: true` (the default), the controller turns each Proxmox-backed router port into a distributed gateway port. It writes one OVN `HA_Chassis_Group` per port, named `px-<router port>`, listing the chassis of the zone's trunk nodes, and points the port at it. The chassis priorities are keyed by the VPC, not the network, so all Proxmox-backed ports of one VPC are active on the same chassis, and different VPCs spread over the trunk nodes. Routed traffic of a subnet passes through its active chassis; L2 traffic inside a VLAN does not.

What this means for operations:

- Kube-OVN has no field for this, so the controller writes the OVN northbound database directly. It writes only the groups it owns (`external_ids` `owner=proxmox-network`), their chassis rows and the `ha_chassis_group` pointer of its networks' router ports. It never takes a group or a port that someone else has set; such a network turns `GatewayReady=False/ForeignGroup`.
- It connects with Kube-OVN's client certificate, read from the `kube-ovn-tls` Secret through a Role limited to that one Secret by name.
- A network is Ready only once its gateway is (`GatewayReady`). When the northbound database cannot be reached, existing groups keep working, and a network whose gateway was up stays Ready for 10 minutes.
- `ovn.manageGatewayChassis: false` removes the Role and every northbound write. Existing groups stay and keep working, but nothing repairs or removes them, and the VMs of new networks have no gateway.
- This is a stopgap until Kube-OVN sets such groups itself. Before upgrading to a Kube-OVN version that manages `ha_chassis_group` on subnet router ports, set `ovn.manageGatewayChassis: false`, upgrade, check that the router ports point at Kube-OVN's groups, and delete the `px-*` groups. Otherwise every network whose port Kube-OVN takes over turns `ForeignGroup` and not Ready.

To read the groups, run in an `ovn-central` pod:

```bash
ovn-nbctl --no-leader-only --columns=name,external_ids,ha_chassis list ha_chassis_group
```

## Status, metrics and alerts

Each tenant subnet has a `ProxmoxNetwork` in the tenant's namespace. `kubectl get proxmoxnetworks --all-namespaces` lists them with their zone, VLAN, bridge, CIDR, pool usage and readiness. The conditions:

| Condition | Typical reasons when not True |
| --- | --- |
| `VLANAllocated` | `ZoneNotFound`, `NamespaceNotAllowed`, `ZoneExhausted`, `VLANConflict` |
| `SubnetReady` | the reason Kube-OVN reports for the subnet |
| `IPPoolReady` | `PoolOverlapsSubnet`; `True/PoolExhausted` when the pool is full |
| `GatewayReady` | `WaitingForVLAN`, `RouterPortMissing`, `NoTrunkNodes`, `NBUnavailable`, `ForeignGroup`; `Unknown/Disabled` with gateway management off |
| `Ready` | `InUse`, `SubnetDeleting`, `SwitchDeleting`, `GatewayReleasePending` while a network is being deleted |

The controller serves Prometheus metrics, among them:

| Metric | Labels |
| --- | --- |
| `cozy_proxmox_zone_vlans_total`, `_allocated`, `_free` | zone |
| `cozy_proxmox_zone_networks` | zone |
| `cozy_proxmox_network_ready` | namespace, network, zone, vlan |
| `cozy_proxmox_network_ippool_addresses` | namespace, network, state (`total`, `used`, `free`) |
| `cozy_proxmox_network_consumers` | namespace, network |
| `cozy_proxmox_network_deleting` | namespace, network |
| `cozy_proxmox_vlan_allocations_total` | zone, result |
| `cozy_proxmox_orphaned_vlans` | zone |
| `cozy_proxmox_network_gateway_ready`, `cozy_proxmox_network_gateway_chassis` | namespace, network |
| `cozy_proxmox_gateway_nb_errors_total` | |

With `alerts.enabled`, the package ships these alerts:

| Alert | Fires when |
| --- | --- |
| `ProxmoxNetworkNotReady` | a network that is not being deleted is not Ready for 15 minutes |
| `ProxmoxNetworkGatewayNotReady` | a network's VMs have had no gateway for 10 minutes |
| `ProxmoxNetworkGatewayNBErrors` | northbound errors keep growing for 10 minutes |
| `ProxmoxNetworkPoolNearlyFull` | a VM pool is more than 90% used |
| `ProxmoxNetworkZoneExhausted` | a zone has no free VLAN |
| `ProxmoxNetworkOrphanedVLANs` | a zone has had Kube-OVN Vlans whose network is gone for 30 minutes |
| `ProxmoxNetworkStuckDeleting` | a network has been deleting for an hour |
| `ProxmoxNetworkControllerDown` | the controller has not been scraped for 10 minutes |

## Day-2 operations

- A network stuck in `InUse` waits for machines. `kubectl get ipaddresses --namespace <tenant namespace>` shows who holds addresses. Delete the clusters or pools on a network before the VPC: deleting a VPC under a running cluster cuts the workers off their control plane, and the network stays `InUse` meanwhile.
- A network in `SwitchDeleting` waits for Kube-OVN to remove the subnet's switch and is released, at the latest, at the time its Ready message gives.
- Never delete a Kube-OVN `Vlan` that carries zone labels by hand; delete the tenant's subnet instead.
- A `ForeignGroup` network needs a decision by hand; the condition's message names what the controller found.
- An egress gateway can stay Terminating with Kube-OVN's finalizer when its VPC router went first. Once `ovn-nbctl lr-list` no longer lists the VPC router, remove the finalizer by hand.

## Changes that reach existing installations

- Every VPC refuses a static route whose `nextHopIP` is outside the VPC's own subnets, or outside `169.254.0.0/16` when peers are declared. A VPC with such a route stops rendering after the upgrade. Check the routes of existing VPCs before upgrading.
- VPC peering link addresses carry their `/30`.
- The Proxmox cloud-controller-manager of Proxmox-backed Kubernetes clusters moves to v0.16.1.
- The admission policies apply only once the package is enabled.

## Limits and open questions

- There is no drop between VPCs inside OVN yet: a Proxmox-backed subnet is not private, and the transit router alone stops one VPC from reaching another VPC's address range at L3. Moving that boundary into OVN needs a platform-owned list of the tenant address space, which is an open question of the proposal.
- VMs run at the zone MTU next to overlay pods at a smaller one, with no "fragmentation needed" between them.
- Traffic from a VM to an overlay pod on a node without the trunk was expected to fail and worked in tests, without an explanation yet.
- Deleting a VPC may delete its router while the held subnets stay.
- Failover of the active gateway chassis and VPC peering with Proxmox-backed subnets have not been tested on a live cluster.
- IPv4 only. No inbound path (floating IP or DNAT) to a VM, no ClusterIP access from VMs, and capmox and the cloud-controller-manager use one Proxmox API token for every tenant.
- Management access to tenant VMs, and egress narrowed to a tenant's own control plane, are open questions.
- Proxmox SDN is not used. The proposal describes a phased plan for it.

The full list, with the decisions the feature needs, is in the [design proposal](https://github.com/cozystack/community/pull/93) and in `docs/proxmox-networking.md` of [cozystack/cozystack#4813](https://github.com/cozystack/cozystack/pull/4813).

## See also

- [Proxmox-backed VPC subnets]({{% ref "/docs/next/networking/proxmox-vpc-subnets" %}}): the tenant side.
- [Enabling and disabling components]({{% ref "/docs/next/operations/configuration/components#enabling-and-disabling-components" %}}): the `bundles.enabledPackages` mechanism used here.
- [Cozystack variants]({{% ref "/docs/next/operations/configuration/variants" %}}).
