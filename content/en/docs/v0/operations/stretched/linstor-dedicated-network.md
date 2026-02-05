---
title: "Configuring a Dedicated Network for Distributed Storage with LINSTOR"
linkTitle: "Distributed Storage Network"
description: "Configure LINSTOR to prefer local links for storage and fall back to inter-datacenter connections"
weight: 40
---

## Introduction

This guide explains how to improve storage reliability and performance in distributed Cozystack clusters.

In hyper-converged clusters, it’s common to dedicate a network to storage traffic.
However, it’s not always possible to provision separate storage links between datacenters.

If you lack dedicated inter-datacenter links for storage, you have two options:

- make storage nodes in each datacenter isolated,
- make storage traffic share the existing uplinks with other workloads.

This guide shows how to configure LINSTOR to use a dedicated network for storage traffic within each datacenter,
while falling back to shared links between datacenters when needed.


## Prerequisites

This guide builds on the [Dedicated Network for LINSTOR]({{% ref "/docs/storage/dedicated-network" %}}) guide,
adding additional methods and configuration patterns specific to multi-datacenter environments.
To apply the patterns in this guide, it's important to understand how node interfaces and connection paths work.
Be sure to review the previous guide first, as it explains these concepts in detail.

To apply different node connection settings depending on node location, you’ll need to label your nodes accordingly.
Refer to the [Topology node labels guide]({{% ref "/docs/operations/stretched/labels" %}}) for instructions.
This guide uses the `topology.kubernetes.io/zone` label to distinguish datacenters.

## Connection configuration

In this example, we have three datacenters: `dc1`, `dc2`, and `dc3`. The datacenters are interconnected with direct
optical lines, and the interface is named `region10g`. The nodes inside datacenters `dc1` and `dc2` have a separate
network switch and network interfaces named `san` for storage traffic only. The datacenter `dc3` does not have a
dedicated network switch for storage, and all traffic between nodes in `dc3` is routed through the default network. To
connect to other datacenters, there is a VPN server connected to the optical lines. The nodes in `dc3` have a VLAN
interface with an IP from the `region10g` subnet.

Consider a scenario with three datacenters: `dc1`, `dc2`, and `dc3`:

-   The datacenters are linked via direct optical lines, exposed to the nodes as an interface named `region10g`.
-   Nodes in `dc1` and `dc2` are connected to a dedicated network switch for storage,
    and use a separate interface named `san` exclusively for storage traffic.
-   Datacenter `dc3` lacks a dedicated storage network.
    All intra-datacenter traffic in `dc3` uses the default network.

Based on this setup, the optimal storage traffic routing is:

-   Nodes in `dc1` and `dc2` use the `san` interface for local storage replication.
-   Nodes in `dc3` use their default network interface for local storage replication, avoiding unnecessary hops through the VPN server.
-   Cross-datacenter storage traffic flows over the `region10g` interface.

Here’s the LINSTOR custom resource definition (CRD) to implement this logic:

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

# Nodes in `dc3` use the default network.
# No special connection is needed for replication within that datacenter.

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

After applying this configuration, you can inspect the resulting connection paths:

```console
LINSTOR ==> node-connection list
╭─────────────────────────────────────────────────────╮
┊ Node A ┊ Node B ┊ Properties                        ┊
╞═════════════════════════════════════════════════════╡
┊ node01 ┊ node02 ┊ last-applied=["Paths/intra-dat... ┊
┊ node01 ┊ node03 ┊ last-applied=["Paths/cross-dat... ┊
┊ node01 ┊ node04 ┊ last-applied=["Paths/cross-dat... ┊
....
```

Node pairs inside the `dc3` datacenter will not have any custom node connection configured,
and will use the default interface instead.
