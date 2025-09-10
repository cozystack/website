---
title: "Configuring a Dedicated Network for LINSTOR"
linkTitle: "Dedicated Network"
description: "Redirect LINSTOR replication traffic to a dedicated network interface for better reliability and performance."
weight: 10
aliases:
  - /docs/operations/storage/dedicated-network
---

This guide explains how to improve storage reliability and performance by redirecting LINSTOR replication traffic
to a dedicated network interface.

## Introduction

The Cozystack platform is built to support high-availability (HA) workloads,
which means the system must continue operating even if one or more nodes go offline.
Kubernetes handles this well for stateless workloads.
However, stateful workloads, such as file storage or virtual machine disks, require a reliable storage backend.

When you choose the `replicated` storage class for a PersistentVolumeClaim (PVC) or DataVolume,
LINSTOR creates multiple synchronous replicas of the data across different nodes.
This ensures that if a node fails (due to a power outage, hardware issue, etc.),
the data remains instantly available on another node.

This level of reliability comes with a trade-off: storage replication can generate significant network traffic,
depending on workload intensity.

If your nodes have multiple network interfaces, you can improve performance by dedicating one of them to storage traffic.
This isolates replication traffic from other workloads, preventing potential network bottlenecks.

## When is a dedicated storage network required?

It is not always necessary to set up a dedicated network for storage traffic from the start.
In small-scale or proof-of-concept (PoC) clusters, the default network configuration is typically sufficient.
Premature optimization can lead to unnecessary complexity.

However, in larger clusters, storage replication traffic often becomes a performance bottleneck.
This traffic can saturate available bandwidth and interfere with other workloads sharing the same network.

If your nodes have only one network interface, and you're unsure whether a dedicated interface is required,
start by observing actual storage traffic under realistic workloads.
One practical approach is to assign a VLAN on the existing interface for storage replication traffic.
This allows you to monitor bandwidth usage without adding hardware.

If traffic levels remain consistently high or affect application performance,
migrating to a dedicated network becomes a worthwhile optimization.


## Terms and definitions

Before continuing, it's helpful to clarify the terminology used for network interfaces in a LINSTOR-based setup:

-   **Kubernetes node default route**<br/>
    This is the default route used for outgoing traffic from the node.
    You can view it with `ip route show default`.

-   **Kubernetes node default source IP**<br/>
    This is the IP address associated with the default route.
    It is typically the source IP for all outbound traffic and can be verified with the same command.

-   **Kubernetes node internal IP**<br/>
    This is the address used by Kubernetes for internal communication.
    It is often the same as the default source IP, but not always.
    You can check it with `kubectl get nodes -o wide`.

-   **LINSTOR satellite default interface**<br/>
    This is where configuration becomes less obvious.
    When the Piraeus Operator starts the LINSTOR Satellite, it sets one or two default interfaces: `default-ipv4` and `default-ipv6`.
    Typically, only IPv4 is available.
    The default interface is set to the node’s default source IP at startup and remains unchanged until the Satellite is restarted.
    You can modify this interface while the Satellite is running, but the Piraeus Operator will reset it on the next restart.

-   **LINSTOR satellite additional interfaces**<br/>
    You can manually add more interfaces to a LINSTOR Satellite.
    These are stored in the LINSTOR Controller database and persist across restarts.
    The Piraeus Operator will not modify or delete them.
    At the time of writing, the Piraeus Operator does not support declaring additional interfaces via Kubernetes custom resources.

-   **LINSTOR active satellite connection**<br/>
    Exactly one interface is used by the LINSTOR Controller to communicate with each Satellite.
    By default, this is the `default-ipv4` interface.
    While the LINSTOR CLI allows changing it, the Piraeus Operator will revert it at the next Satellite restart.

-   **LINSTOR node connection (path)**<br/>
    This defines how LINSTOR Satellites communicate with each other for synchronous replication.
    This is the setting we will configure in this guide.
    Node connections can be defined using either Piraeus CRDs or CLI commands.
    The Piraeus Operator does not manage or override them.
    However, the most recently applied configuration takes precedence.


## Understanding default IP assignment

Here’s a typical `node list` output from LINSTOR:

```
LINSTOR ==> node list
╭───────────────────────────────────────────────────────╮
┊ Node   ┊ NodeType  ┊ Addresses               ┊ State  ┊
╞═══════════════════════════════════════════════════════╡
┊ node01 ┊ SATELLITE ┊ 10.78.22.146:3367 (SSL) ┊ Online ┊
┊ node02 ┊ SATELLITE ┊ 10.78.22.37:3367 (SSL)  ┊ Online ┊
┊ node03 ┊ SATELLITE ┊ 10.78.22.53:3367 (SSL)  ┊ Online ┊
┊ node04 ┊ SATELLITE ┊ 10.78.22.230:3367 (SSL) ┊ Online ┊
┊ node05 ┊ SATELLITE ┊ 10.78.22.150:3367 (SSL) ┊ Online ┊
╰───────────────────────────────────────────────────────╯
```

These IP addresses usually match the Kubernetes node internal IPs and the default route IPs.
By default, they are used for storage replication traffic.

You might consider changing them to redirect storage traffic to a different interface.
However, this will not work.

The Piraeus Operator retrieves the Satellite pod's current IP address on each restart.
It then uses this IP—typically the Kubernetes node internal address—to configure the default LINSTOR interface.

Even if you try to change the Kubernetes internal IP, the storage replication traffic will not move to a different interface.
Moreover, such a change would affect **all** traffic from the node, not just LINSTOR replication.

To properly isolate storage traffic from other workloads, use **node connections**, as described in the next section.

## Satellite interfaces

By default, LINSTOR configures only one interface per satellite: the `default-ipv4`,
derived from the Kubernetes node’s default IP.
Here is an example of how a Linstor satellite default interface list looks:

```
LINSTOR ==> node interface list node01
╭─────────────────────────────────────────────────────────────────╮
┊ node01    ┊ NetInterface ┊ IP           ┊ Port ┊ EncryptionType ┊
╞═════════════════════════════════════════════════════════════════╡
┊ + StltCon ┊ default-ipv4 ┊ 10.78.22.146 ┊ 3367 ┊ SSL            ┊
╰─────────────────────────────────────────────────────────────────╯
```

This IP is taken from the Kubernetes node at Satellite startup.
If additional interfaces exist on the node, they are not added automatically.

To enable storage traffic over another network, you can manually add a second interface:

```
LINSTOR ==> node interface create node01 optic-san 10.78.24.201
SUCCESS:
Description:
    New netInterface 'optic-san' on node 'node01' registered.
Details:
    NetInterface 'optic-san' on node 'node01' UUID is: aa28f583-ca91-4cac-b749-67fe54e72c10

LINSTOR ==> node interface list node01
╭─────────────────────────────────────────────────────────────────╮
┊ node01    ┊ NetInterface ┊ IP           ┊ Port ┊ EncryptionType ┊
╞═════════════════════════════════════════════════════════════════╡
┊ + StltCon ┊ default-ipv4 ┊ 10.78.22.146 ┊ 3367 ┊ SSL            ┊
┊ +         ┊ optic-san    ┊ 10.78.24.201 ┊      ┊                ┊
╰─────────────────────────────────────────────────────────────────╯
```

You don’t need to know the name of the underlying Linux network interface.
You can use any name you like—LINSTOR does not validate whether the IP is actually assigned to the node.

Only the `default-ipv4` interface is marked with the `StltCon` flag.
This indicates it is used by the LINSTOR Controller to communicate with the Satellite.

While you can manually change the active Satellite connection using the LINSTOR CLI,
the Piraeus Operator will reset it on the next restart.
This behavior applies to non-Kubernetes installations only.

To use the new interface for storage replication, you’ll need to define node connections.
But first, repeat the interface creation for the other nodes:

```
LINSTOR ==> node interface create node02 optic-san 10.78.24.202
LINSTOR ==> node interface create node03 optic-san 10.78.24.203
LINSTOR ==> node interface create node04 optic-san 10.78.24.204
LINSTOR ==> node interface create node05 optic-san 10.78.24.205
```

## Node connections

LINSTOR node connections define how satellites communicate with each other to replicate data synchronously.
Each pair of satellites should have a connection path defined between them.

Unlike satellite interfaces, node connections can be defined either manually using the CLI
or declaratively via Kubernetes Custom Resources.
For small clusters, creating connections manually is usually manageable.
However, as your cluster grows, it's more efficient to use a naming convention and describe
all connection paths in a single resource definition.

The following sections explain both approaches.


### Manual method

You can create node connections manually using the LINSTOR CLI.
Here’s how to check the command syntax:

```
LINSTOR ==> node-connection path create -h
usage: linstor node-connection path create [-h]
                                           node_a node_b path_name
                                           netinterface_a netinterface_b
Creates a new node connection path.

positional arguments:
  node_a          1. Node of the connection
  node_b          2. Node of the connection
  path_name       Name of the created path
  netinterface_a  Netinterface name to use for 1. node
  netinterface_b  Netinterface name to use for the 2. node
```

Example: create a connection between `node01` and `node02`, using the `optic-san` interface on both sides:

```
LINSTOR ==> node-connection path create node01 node02 node01-02 optic-san optic-san
SUCCESS:
    Successfully set property key(s): Paths/node01-02/node01,Paths/node01-02/node02
SUCCESS:
Description:
    Node connection between nodes 'node01' and 'node02' modified.
Details:
    Node connection between nodes 'node01' and 'node02' UUID is: c1f4ee6a-776e-46ba-9e74-99afce38d90f
SUCCESS:
    (node02) Node changes applied.
SUCCESS:
    (node02) Resource '`pvc-6f535d3a-82c1-46ab-80fe-5a59ee8bff44`' [DRBD] adjusted.
....
```

When the connection is created, LINSTOR immediately updates all affected DRBD resources to use the new path.

A path is created once per each pair of nodes.
There is no need to define a separate reverse path.

You can verify the configuration:

```
LINSTOR ==> node-connection path list node01 node02
╭────────────────────────────────────╮
┊ Key                    ┊ Value     ┊
╞════════════════════════════════════╡
┊ Paths/node01-02/node01 ┊ optic-san ┊
┊ Paths/node01-02/node02 ┊ optic-san ┊
╰────────────────────────────────────╯

LINSTOR ==> node-connection path list node02 node01
╭────────────────────────────────────╮
┊ Key                    ┊ Value     ┊
╞════════════════════════════════════╡
┊ Paths/node01-02/node01 ┊ optic-san ┊
┊ Paths/node01-02/node02 ┊ optic-san ┊
╰────────────────────────────────────╯

LINSTOR ==> node-connection list node01 node02
╭─────────────────────────────────────────────────────╮
┊ Node A ┊ Node B ┊ Properties                        ┊
╞═════════════════════════════════════════════════════╡
┊ node01 ┊ node02 ┊ node01=optic-san,node02=optic-... ┊
╰─────────────────────────────────────────────────────╯

LINSTOR ==> node-connection list node02 node01
╭─────────────────────────────────────────────────────╮
┊ Node A ┊ Node B ┊ Properties                        ┊
╞═════════════════════════════════════════════════════╡
┊ node01 ┊ node02 ┊ node01=optic-san,node02=optic-... ┊
╰─────────────────────────────────────────────────────╯
```

### CRD method

Let's observe the method using Kubernetes CRD (Custom Resource Definition).

{{% alert color="warning" %}}
At the time of writing, the Piraeus Operator has a known issue with handling missing interfaces.
There is no backoff between reconciliation attempts.
If even one interface is missing, the controller may consume 100% of its CPU limit.

Always verify that all required interfaces exist before applying the CRD.
Monitor the controller pod to make sure it is not overloaded after the change.
{{% /alert %}}

As the number of nodes increases, the number of required node connections grows rapidly.
With 3 nodes, you need 3 connections.
With 5 nodes, you need 10.
With 10 nodes, you need 45, and so on.

Instead of creating each connection manually, you can define all paths once using a single `LinstorNodeConnection` custom resource.

To use this method, the following conditions must be met:

-   All involved nodes must have the same interface name.
-   The interface must already be created on all nodes before applying the CRD.

Here is an example of LinstorNodeConnection CR:

```yaml
apiVersion: piraeus.io/v1
kind: LinstorNodeConnection
metadata:
  name: dedicated
spec:
  paths:
    - name: dedicated
      interface: optic-san
```

Apply the CRD using:

```bash
kubectl apply -f linstor-node-connections.yaml
```

After applying, you can verify the connections:

```
LINSTOR ==> node-connection list
╭─────────────────────────────────────────────────────╮
┊ Node A ┊ Node B ┊ Properties                        ┊
╞═════════════════════════════════════════════════════╡
┊ node01 ┊ node02 ┊ last-applied=["Paths/dedicated... ┊
┊ node01 ┊ node03 ┊ last-applied=["Paths/dedicated... ┊
┊ node01 ┊ node04 ┊ last-applied=["Paths/dedicated... ┊
┊ node01 ┊ node05 ┊ last-applied=["Paths/dedicated... ┊
┊ node02 ┊ node03 ┊ last-applied=["Paths/dedicated... ┊
┊ node02 ┊ node04 ┊ last-applied=["Paths/dedicated... ┊
┊ node02 ┊ node05 ┊ last-applied=["Paths/dedicated... ┊
┊ node03 ┊ node04 ┊ last-applied=["Paths/dedicated... ┊
┊ node03 ┊ node05 ┊ last-applied=["Paths/dedicated... ┊
┊ node04 ┊ node05 ┊ last-applied=["Paths/dedicated... ┊
╰─────────────────────────────────────────────────────╯
```

You may still see the old manual paths.
The most recently applied connection takes precedence.

In this example the old paths for `node01` and `node02` are seen:

```
LINSTOR ==> node-connection path list node01 node02
╭────────────────────────────────────╮
┊ Key                    ┊ Value     ┊
╞════════════════════════════════════╡
┊ Paths/dedicated/node01 ┊ optic-san ┊
┊ Paths/dedicated/node02 ┊ optic-san ┊
┊ Paths/node01-02/node01 ┊ optic-san ┊
┊ Paths/node01-02/node02 ┊ optic-san ┊
╰────────────────────────────────────╯

LINSTOR ==> node-connection path list node01 node03
╭────────────────────────────────────╮
┊ Key                    ┊ Value     ┊
╞════════════════════════════════════╡
┊ Paths/dedicated/node01 ┊ optic-san ┊
┊ Paths/dedicated/node03 ┊ optic-san ┊
╰────────────────────────────────────╯
```

To keep the configuration clean, you can remove the old manual path:

```
LINSTOR ==> linstor node-connection path delete node01 node02 node01-02
SUCCESS:
    Successfully deleted property key(s): Paths/node01-02/node02,Paths/node01-02/node01
....
```

After deletion:

```console
LINSTOR ==> node-connection path list node01 node02
╭────────────────────────────────────╮
┊ Key                    ┊ Value     ┊
╞════════════════════════════════════╡
┊ Paths/dedicated/node01 ┊ optic-san ┊
┊ Paths/dedicated/node02 ┊ optic-san ┊
╰────────────────────────────────────╯
```

### Advanced CRD method

See the example in
[Multi Datacenter dedicated storage network guide]({{% ref "/docs/operations/stretched/linstor-dedicated-network" %}})
