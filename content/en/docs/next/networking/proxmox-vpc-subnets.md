---
title: "Proxmox-backed VPC Subnets"
linkTitle: "Proxmox VPC Subnets"
description: "Extend a VPC subnet onto a Proxmox VE VLAN, give it a way out of the VPC, and place the workers of a Proxmox-backed Kubernetes cluster on it."
weight: 12
---

{{% alert title="Proposed feature" color="warning" %}}
This page describes a feature that is **not merged** into Cozystack and is not part of any release.
It is implemented in the draft pull request [cozystack/cozystack#4813](https://github.com/cozystack/cozystack/pull/4813),
its design is discussed in the proposal [cozystack/community#93](https://github.com/cozystack/community/pull/93),
and whether Proxmox VE becomes a supported platform is decided in [cozystack/cozystack#3481](https://github.com/cozystack/cozystack/issues/3481).
Field names and behaviour may change before it lands, or the feature may not land at all.
{{% /alert %}}

## What this page covers

How a tenant extends a subnet of its [VPC]({{% ref "/docs/next/networking/vpc" %}}) onto Proxmox VE, how to check that the subnet is ready, how virtual machines on it reach the rest of the VPC and the outside, and how to put the workers of a Proxmox-backed [Kubernetes]({{% ref "/docs/next/kubernetes" %}}) cluster on it.

The platform side, which an administrator sets up once (hypervisor bridges, the trunk to the cluster nodes, zones and the transit network), is described in [Setting up Proxmox-backed VPC subnets]({{% ref "/docs/next/operations/vpc/proxmox-network" %}}).

## How it works

A Proxmox-backed subnet is an ordinary subnet of your VPC with one more field, `proxmox: {}`.
The platform then:

- turns the Kube-OVN subnet into a VLAN-backed logical switch of your VPC's own router;
- allocates a VLAN for it from a range the administrator owns and carries that VLAN to the cluster nodes;
- creates an IP pool for the part of the subnet that Proxmox VMs take their addresses from;
- lets a Proxmox-backed `Kubernetes` cluster or `KubernetesNodes` pool refer to the subnet by name.

VMs and pods on the subnet are L2 neighbours. The subnet's gateway is the VPC router port, so the VPC's isolation and routing cover the VMs as well.
You never choose the VLAN, the Proxmox bridge or the IP pool, and you cannot set them: they come from the platform.

```text
VPC subnet "workers" (name, CIDR)          <- what you write
   |
   +-- Kube-OVN logical switch + router port (gateway)
   +-- VLAN from the administrator's zone   <- allocated by the platform
   +-- IP pool for the VMs' address range   <- used by Cluster API
   |
Proxmox VM NIC: bridge + VLAN tag + address from the pool
```

## Before you start

- The administrator has enabled the `cozystack.proxmox-network` package and created at least one zone. Without it the VPC refuses the subnet with `the proxmox.cozystack.io API is not installed` or `no ProxmoxNetworkZone exists`.
- If the platform has more than one zone, ask the administrator which one your tenant may use. A zone can be limited to some namespaces.
- Proxmox-backed subnets are IPv4 only, with a prefix between `/8` and `/28`.

## Add a Proxmox-backed subnet

Add `proxmox: {}` to a subnet of a `VirtualPrivateCloud`:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VirtualPrivateCloud
metadata:
  name: main
  namespace: tenant-example
spec:
  subnets:
    - name: workers
      cidr: 172.20.10.0/24
      proxmox: {}
    - name: data
      cidr: 172.20.11.0/24
      proxmox:
        zone: default
        vmRange: 172.20.11.100-172.20.11.199
    - name: pods
      cidr: 172.20.20.0/24
      allowSubnets:
        - 172.20.10.0/24
        - 172.20.11.0/24
  egress:
    enabled: true
```

| Field | Meaning |
| --- | --- |
| `subnets[].proxmox` | Back this subnet with a Proxmox VLAN. `{}` takes every default. |
| `subnets[].proxmox.zone` | The zone the VLAN comes from. Empty selects the only zone and fails when there are several. |
| `subnets[].proxmox.vmRange` | The addresses Proxmox VMs take, as `first-last`, inside the CIDR, after the gateway and before the broadcast address. Kube-OVN never hands these addresses to pods. Defaults to the middle half of the subnet: `172.20.10.64-172.20.10.191` for the `/24` above. |
| `egress.enabled` | Route traffic from the Proxmox-backed subnets to destinations outside the VPC through an egress gateway. See [Reaching the outside](#reaching-the-outside). |
| `egress.replicas` | Number of egress gateway pods. Default `1`. |
| `egress.internalCidr` | Optional CIDR, a `/29` is enough, for a dedicated overlay subnet that holds the gateway pods' primary interface. It must not overlap any other subnet in the cluster. By default they sit on the first Proxmox-backed subnet, which is the better choice; see the note in [Reaching the outside](#reaching-the-outside). |

The subnet is split between the two address owners:

```text
172.20.10.0/24
  .1              gateway: the VPC router port
  .2  - .63       Kube-OVN: pods attached to the subnet
  .64 - .191      VM pool: Proxmox VMs (the default vmRange)
  .192 - .254     Kube-OVN: pods attached to the subnet
```

The VPC application refuses:

- `allowSubnets` on a Proxmox-backed subnet. It is not a private subnet and accepts whatever its VPC routes to it, so the list would do nothing. Put `allowSubnets` on the overlay subnets that the Proxmox-backed ones should reach, as `pods` does above.
- A `vmRange` outside the CIDR or one that contains the gateway.
- Removing `proxmox` from a subnet and keeping its name. Remove the subnet and add it back under a new name.
- Removing a subnet while VM addresses are still allocated on it. Delete those machines first.

## Check the subnet

Every Proxmox-backed subnet has a read-only `ProxmoxNetwork` object in your namespace. Its name is generated, so select it by the VPC and subnet names:

```bash
kubectl get proxmoxnetworks --namespace tenant-example --output wide \
  --selector cozystack.io/vpcName=virtualprivatecloud-main,cozystack.io/subnetName=workers
```

```console
NAME              ZONE      VLAN   BRIDGE   CIDR             USED   FREE   READY   REASON
subnet-1a2b3c4d   default   214    vmbr1    172.20.10.0/24   0      128    True    Ready
```

The `Ready` condition sums up the others:

| Condition | Meaning |
| --- | --- |
| `VLANAllocated` | A VLAN was allocated from the zone. Reasons when it was not: `ZoneNotFound`, `NamespaceNotAllowed` (the zone does not admit your namespace), `ZoneExhausted` (no free VLAN left), `VLANConflict`. |
| `SubnetReady` | Kube-OVN created the logical switch for the subnet. |
| `IPPoolReady` | The VM pool lies inside the subnet and inside the range Kube-OVN keeps away from pods. `PoolExhausted` means every VM address is taken; VMs already on the network keep working. |
| `GatewayReady` | VMs can reach their gateway, the VPC router port. |
| `Ready` | All of the above. `GatewayReady` counts only while the platform manages gateways; with that management off it is `Unknown` with reason `Disabled`. A Kubernetes cluster or node pool is placed only on a Ready network. |

When a condition is `False`, its message says why. Most of the reasons need the administrator: an exhausted zone, a zone that does not admit your namespace, or a gateway that is not ready.

## Reaching other subnets

VMs and pods on a Proxmox-backed subnet reach each other at L2. The VPC router routes between the VPC's subnets, with two limits:

- Overlay subnets of a VPC are private. A Proxmox-backed subnet reaches an overlay subnet only when that overlay subnet lists its CIDR in `allowSubnets`.
- A pod attached to a Proxmox-backed subnet has to run on a node that carries the Proxmox trunk; which nodes do is up to the administrator. Keep overlay pods that the VMs need to reach on those nodes as well: traffic from a VM to an overlay pod on a node without the trunk was expected to fail, worked in the tests so far, and is still an open question.

There is no route between two VPCs unless both declare a peering and route to each other, as for any VPC. Peering between VPCs with Proxmox-backed subnets has not been tested on a live cluster yet.

## Reaching the outside

Traffic from a Proxmox-backed subnet stays inside the VPC unless the VPC has an egress gateway. To let the VMs out, for example so that Kubernetes workers reach their control plane, DNS, NTP and image registries, set `egress.enabled: true`.

The VPC then gets an egress gateway: pods with one leg in the VPC and one on the platform's transit network. The VPC router sends traffic from the Proxmox-backed subnets that leaves the VPC to these pods, which SNAT it onto the transit network. Where it can go from there is decided by the administrator's transit router: usually the platform's LoadBalancer range (where tenant Kubernetes control planes listen), DNS, NTP and the Internet.

- One egress gateway serves one zone. A VPC whose Proxmox-backed subnets are in two zones cannot enable egress.
- `egress.enabled` needs at least one Proxmox-backed subnet.
- A static route of the VPC to something narrower than `0.0.0.0/0`, such as a peered VPC, keeps its own next hop and does not go through the gateway.
- Leave `egress.internalCidr` unset unless you have a reason. With it the gateway's primary interface sits on an overlay subnet, and on platforms where Cilium runs in front of the overlay tunnel, VM traffic to a LoadBalancer IP can be rewritten on the way and never arrive.
- Nothing reaches the VMs from outside the VPC: there is no inbound path (floating IP or DNAT) to a Proxmox VM yet, and VMs cannot reach the management cluster's ClusterIP Services.

{{% alert color="info" %}}
Every VPC, whether it has Proxmox-backed subnets or not, now refuses a static route whose `nextHopIP` is outside the VPC's own subnets (or outside `169.254.0.0/16` when peers are declared). Such a VPC stops rendering with `route to <cidr>: next hop <ip> is outside every subnet of this VPC`.
{{% /alert %}}

## Put Kubernetes workers on the subnet

A Proxmox-backed Kubernetes cluster (`substrate: proxmox`) can take its worker addresses from a Proxmox-backed subnet instead of a raw address range. Set `proxmox.network` on the cluster and on every node pool:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Kubernetes
metadata:
  name: example
  namespace: tenant-example
spec:
  version: "v1.35"
  substrate: proxmox
  proxmox:
    dnsServers: ["198.51.100.53"]
    network:
      vpc: main
      subnet: workers
    ccm:
      credentialsSecretName: proxmox-credentials
    csi:
      credentialsSecretName: proxmox-credentials
---
apiVersion: apps.cozystack.io/v1alpha1
kind: KubernetesNodes
metadata:
  name: example-md0
  namespace: tenant-example
spec:
  cluster: example
  minReplicas: 2
  maxReplicas: 2
  resources:
    cpu: 2
    memory: 4Gi
  substrate: proxmox
  proxmox:
    templateTags: [talos, worker-template]
    dnsServers: ["198.51.100.53"]
    network:
      vpc: main
      subnet: workers
    additionalNetworks:
      - name: net1
        vpc: main
        subnet: data
```

| Field | Application | Meaning |
| --- | --- | --- |
| `proxmox.network.vpc`, `proxmox.network.subnet` | `Kubernetes` | The VPC application in this namespace and its Proxmox-backed subnet. Replaces `proxmox.ipv4Config`, which must then stay empty. |
| `proxmox.network.vpc`, `proxmox.network.subnet` | `KubernetesNodes` | The subnet for `net0` of every worker. Bridge, VLAN and IP pool come from the subnet. Cannot be combined with `proxmox.network.bridge` or `proxmox.network.vlan`. |
| `proxmox.network.mtu` | `KubernetesNodes` | NIC MTU. With a subnet, defaults to the zone's MTU. |
| `proxmox.additionalNetworks[]` | `KubernetesNodes` | Extra NICs, `net1` to `net31`, each on a Proxmox-backed subnet of this namespace, each with its own address from that subnet's pool. Changing the list rolls the pool. |

As for any `KubernetesNodes` pool, the name is `<cluster>-<pool>`, here pool `md0` of cluster `example`.

Point the cluster and all of its pools at subnets of the same VPC, and enable egress on that VPC, or the workers cannot reach their control plane.

The applications look the subnet up when they render. If its `ProxmoxNetwork` is not Ready, the render fails with the condition's message, and the HelmRelease of the cluster or pool shows why no machine was created. A subnet without `proxmox` fails with `is not Proxmox-backed`.

In a namespace that has Proxmox-backed subnets, every Cluster API machine NIC must be on one of them: a pool with a raw `bridge`/`vlan` in the same namespace is refused by admission.

The other Proxmox settings of these applications (credentials, the template, resource pools and privileges) are described in the [Kubernetes application reference]({{% ref "/docs/next/kubernetes" %}}) and in the `kubernetes-nodes` [README](https://github.com/cozystack/cozystack/tree/main/packages/apps/kubernetes-nodes).

## Pods and KubeVirt VMs on the subnet

Pods and KubeVirt VMs attach to a Proxmox-backed subnet as a secondary network, in the same way as to any VPC subnet, and must run on a node that carries the Proxmox trunk.

With the package enabled, admission limits network attachments in tenant namespaces:

- A pod or a KubeVirt VM may attach only NetworkAttachmentDefinitions and Kube-OVN subnets of its own namespace.
- A Multus default network must be written as `<namespace>/<name>`.
- Pinning a pod to a Kube-OVN logical switch with a `*.kubernetes.io/logical_switch` annotation is refused, except for the namespace's default switch. A copy of a running pod that keeps the annotations Kube-OVN wrote, such as `kubectl debug --copy-to` or a restored backup, is refused as well.

## Remove a subnet

Delete the Kubernetes clusters and node pools that use a subnet before you remove the subnet or the VPC.

If VMs still hold addresses, the platform keeps the subnet, its VLAN and its pool until the last VM is gone, and the `ProxmoxNetwork` shows `Ready=False` with reason `InUse`. Traffic inside the VLAN keeps working meanwhile, but the egress gateway goes with the VPC, so the VMs lose their way out and their control plane. Deleting a VPC under a running cluster can also remove the VPC router while the held subnets stay. The VLAN returns to the zone only after Kube-OVN has removed the subnet's switch.

## Limits

- Between two VPCs' Proxmox-backed subnets there is no drop inside OVN yet. Isolation rests on one router per VPC, one VLAN per subnet and the administrator's transit router, which does not forward into VPC address ranges.
- VMs run at the zone MTU, pods on the overlay at a smaller one, and the router does not send "fragmentation needed". A full-size packet with the DF bit set from a VM to an overlay pod is dropped silently; TCP is not affected.
- IPv4 only. No inbound path to a VM and no ClusterIP access from VMs.
- capmox, which creates the VMs, and the Proxmox cloud-controller-manager still use one Proxmox API token for every tenant.
- Chassis failover and VPC peering with Proxmox-backed subnets have not been tested on a live cluster.

The open questions are listed in the [design proposal](https://github.com/cozystack/community/pull/93).

## See also

- [Setting up Proxmox-backed VPC subnets]({{% ref "/docs/next/operations/vpc/proxmox-network" %}}): the administrator's guide.
- [VPC application reference]({{% ref "/docs/next/networking/vpc" %}}).
- [Managed Kubernetes]({{% ref "/docs/next/kubernetes" %}}).
- `docs/proxmox-networking.md` in [cozystack/cozystack#4813](https://github.com/cozystack/cozystack/pull/4813): the full design, failure handling and security model.
