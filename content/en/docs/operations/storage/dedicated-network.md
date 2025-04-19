---
title: "Configure dedicated network for storage traffic"
linkTitle: "Dedicated Storage network"
description: "How to re-route storage traffic to a dedicated network"
weight: 10
---

## Motivation

The Cozystack platform is designed to run HA workloads. That means the whole system must tolerate the loss of one
or more nodes. Kubernetes handles this very well for stateless workloads. But for stateful workloads, such as
file storages or virtual machine disks, there needs to be a reliable storage system. When you choose the `replicated`
storage class for PVC or DataVolume, Linstor creates replicas of the data on different nodes. Data is replicated
synchronously, so if one node suddenly disappears (power outage, hardware failure, etc.), the data is immediately
available on another node.

Such a reliable storage system comes at a cost: storage replication traffic could be very high, depending on the
workload.

If you have enough network interfaces on your nodes, you can dedicate some of them to the storage traffic.

## Do I ever need this?

You probably will not know until you try it. For small-scale or PoC clusters, the default network setup is usually fine.
But for large-scale installations, the storage traffic can saturate the network bandwidth and cause performance issues
with other types of workloads.

If you only have one network available and you want to know whether you need another one, you should measure traffic
volume for some time. It's easiest to add a VLAN to the main hardware network interface and use it for storage traffic.
This way, you can monitor storage traffic volume without any additional hardware cost.

## About default interfaces

Before continuing, let's clarify some terms:

- **Kubernetes node default route** - the route that is used by default for all traffic from the node. The one shown by
  `ip route show default`.
- **Kubernetes node default source IP** - the IP address that is used by default for all traffic from the node. It can
  be checked by the same command.
- **Kubernetes node internal IP** - the IP that is used for Kubernetes internal communications. It is usually the same
  as the default source IP, but your mileage may vary. It can be checked by the `kubectl get nodes -o wide` command.
- **Linstor satellite default interface** - this is where things begin to be less obvious. When the Piraeus operator
  starts the Linstor satellite, it reconfigures one or two Linstor satellite interfaces: `default-ipv4` and
  `default-ipv6`. Usually, only IPv4 is available. By default, it's set to the Kubernetes node default source IP upon
  Satellite startup and is not modified until the Satellite is restarted. You can modify it while the Satellite is
  running, but the Piraeus operator will reset it to the default value upon the next restart.
- **Linstor satellite other interfaces** - you can add other interfaces to the Linstor satellite. They are stored in the
  Linstor controller database and will be added back after restart. The Piraeus operator will not modify or delete it.
  At the time of writing, Piraeus operator does not have a way to declare additional interfaces using Kubernetes custom
  resources.
- **Linstor active satellite connection** - exactly one Linstor satellite interface is used by the Linstor controller to
  communicate with the satellite. By default, it is the `default-ipv4` interface. You can change it, but Piraeus
  operator will revert it at the next restart.
- **Linstor node connection (path)** - a setting that defines how the Linstor satellite nodes communicate with each
  other to sync replicated storage. This is what we are going to change in this guide. Linstor node connections can be
  both defined declaratively with Piraeus CRD and created with commands. The Piraeus operator will not delete or modify
  it. The last applied configuration wins though.

Here is an example of how a Linstor node list typically looks:

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

IPs here usually match the Kubernetes node internal IPs and default route IPs. Yes, they are used by default for storage
sync. But do not try to change them to get storage traffic running through another interface. The Piraeus will revert
your settings. Upon each restart, Piraeus looks into the Satellite pod status and gets the current IP address, which in
turn is the same as Kubernetes node internal address. If you change the Kubernetes node internal address trying to force
Piraeus to use it, you will still not solve the issue, because **all other** traffic will also be routed through this
interface. Instead, use node connections.

## Satellite interfaces

Here is an example of how a Linstor satellite default interface list looks:

```
LINSTOR ==> node interface list node01
╭─────────────────────────────────────────────────────────────────╮
┊ node01    ┊ NetInterface ┊ IP           ┊ Port ┊ EncryptionType ┊
╞═════════════════════════════════════════════════════════════════╡
┊ + StltCon ┊ default-ipv4 ┊ 10.78.22.146 ┊ 3367 ┊ SSL            ┊
╰─────────────────────────────────────────────────────────────────╯
```

IP here is taken from the Kubernetes node on each startup. If there are other interfaces on the node, they will not be
added automatically. Let's add another interface to the Satellite:

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

You don't have to know the underlying network interface name. You can use any name you want. Actually, Linstor does not
even check if that IP is assigned to the node.

You can see that the `StltCon` tag only applies to the `default-ipv4` interface. This means that this interface is used
by the Linstor controller to communicate with the Satellite. The Linstor CLI allows you to change it, but the Piraeus
operator will revert it back later. This setting is for non-Kubernetes installations.

Now add interface definitions to the other nodes. It's required to have the same interface name on all nodes for the CRD
method.

```
LINSTOR ==> node interface create node02 optic-san 10.78.24.202
LINSTOR ==> node interface create node03 optic-san 10.78.24.203
LINSTOR ==> node interface create node04 optic-san 10.78.24.204
LINSTOR ==> node interface create node05 optic-san 10.78.24.205
```

## Node connections

Linstor node connections are used to define how the Linstor satellites communicate with each other. Each pair of
Satellites should have its own node connection path. Unlike Satellite interfaces, node connections could be defined with
Piraeus CRD, or manually. While the number of nodes is small, you can create node connections manually. But if you scale
up, it's better to develop a naming scheme and create a single Custom resource that describes connection paths for all
nodes.

### Manual method

Linstor node connections can be created manually. Here is an example:

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

When the `node-connection path create` command is executed, all DRBD devices are also adjusted immediately to use the
new connection path.

Please note that a path is created once for a pair of nodes. There is no need to create the reverse path.

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

{{% alert color="warning" %}}
At the time of writing, the Piraeus operator has a bug in the handling of missing interface. There is no timeout between
reconciliation attempts, and if at least one interface is missing, the controller will consume 100% of its CPU limit.

Always check that all interfaces are present before applying the CRD, and that the controller is not hogging the CPU
after making changes.
{{% /alert %}}

With 3 nodes, you need 3 node connections. With 5 nodes, you need 10 connections. With 10 nodes, you need 45
connections, and so on. Instead of creating them manually, you can create a single Custom Resource that describes all
connections once.

The requirements for the CRD method are:

* All nodes must have the same interface name.
* The interface must be added to all involved nodes before applying the CRD.

The example of LinstorNodeConnection CR:

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

Apply the CR with `kubectl apply -f linstor-node-connections.yaml` and check the results:

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

The old manual path for `node01` and `node02` is still there. The new path has precedence since it's applied last. We
can remove the manual one to keep the list clean:

```
LINSTOR ==> linstor node-connection path delete node01 node02 node01-02
SUCCESS:
    Successfully deleted property key(s): Paths/node01-02/node02,Paths/node01-02/node01
....

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
