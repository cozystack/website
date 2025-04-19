---
title: "Linstor traffic optimization"
linkTitle: "Linstor dedicated network"
description: "A guide to an advanced dedicated network for storage traffic"
weight: 40
---

## Objective

It is common to have a dedicated network for storage in a hyper-converged cluster. However, it is not always
possible to have several dedicated network links between datacenters. If you don't have dedicated lines for storage
between datacenters, then either your storage nodes become segmented, or you need to use the single link between
datacenters for both storage traffic and other traffic.

This guide shows how to configure Linstor to use a dedicated network for storage traffic inside the single datacenter,
but fallback to the only available link between datacenters.

## Node connections

Ensure you have read and understood the
[Linstor dedicated network guide]({{% ref "/docs/operations/storage/dedicated-network" %}}) before proceeding.

## Node labels

To configure node connections differently for nodes inside and outside the datacenter, you need to label your nodes
first. See the [Topology node labels guide]({{% ref "/docs/operations/stretched/labels" %}}) for details.

The required label to proceed with this guide is `topology.kubernetes.io/zone`.

## CRD configuration

In this example, we have three datacenters: `dc1`, `dc2`, and `dc3`. The datacenters are interconnected with direct
optical lines, and the interface is named `region10g`. The nodes inside datacenters `dc1` and `dc2` have a separate
network switch and network interfaces named `san` for storage traffic only. The datacenter `dc3` does not have a
dedicated network switch for storage, and all traffic between nodes in `dc3` is routed through the default network. To
connect to other datacenters, there is a VPN server connected to the optical lines. The nodes in `dc3` have a VLAN
interface with an IP from the `region10g` subnet.

The best available network configuration for storage traffic will be as follows:

* Nodes in `dc1` and `dc2` will use the dedicated network for storage traffic inside the datacenter
* Nodes in `dc3` will use the default network for storage traffic inside the datacenter, not using additional hop via
  VPN server
* Nodes not in the same datacenter will use the `region10g` interface for storage traffic.

Here is an example of how to configure the Linstor CRD to achieve this:

```yaml
---
apiVersion: piraeus.io/v1
kind: LinstorNodeConnection
metadata:
  name: intra-datacenter
spec:
  selector:
  - matchLabels:
    - key: topology.kubernetes.io/zone
      op: Same
    - key: topology.kubernetes.io/zone
      op: In
      values:
      # Only these datacenters have the `san` interface
      - dc1
      - dc2
  paths:
  - name: intra-datacenter
    interface: san

# As nodes in `dc3` do not have a dedicated network switch, they will use the default network
#   for storage traffic. There is no need to configure any special node connections.

---
apiVersion: piraeus.io/v1
kind: LinstorNodeConnection
metadata:
  name: cross-datacenter
spec:
  selector:
  - matchLabels:
    - key: topology.kubernetes.io/zone
      op: NotSame
  paths:
  - name: cross-datacenter
    interface: region10g
```

After applying this configuration, the resulting node connections list will look like this:

```
LINSTOR ==> node-connection list
╭─────────────────────────────────────────────────────╮
┊ Node A ┊ Node B ┊ Properties                        ┊
╞═════════════════════════════════════════════════════╡
┊ node01 ┊ node02 ┊ last-applied=["Paths/intra-dat... ┊
┊ node01 ┊ node03 ┊ last-applied=["Paths/cross-dat... ┊
┊ node01 ┊ node04 ┊ last-applied=["Paths/cross-dat... ┊
....
```

and node pairs inside the `dc3` datacenter will not have any node connections configured.
