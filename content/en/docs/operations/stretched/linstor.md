---
title: "Linstor DRBD parameters"
linkTitle: "Linstor configuration"
description: "Parameters required to make Linstor work in a stretched cluster"
weight: 30
---

## Potential problems

Linstor server manages DRBD volumes and is responsible for creating, deleting, and managing them. DRBD itself is a
kernel-level block device replication system that works over the network. It requires that data has been written to a
quorum of nodes before it is considered written. But it also poses as a block device to the end user, so it must return
an error in a timely manner if there are not enough nodes to establish a quorum.

The potential problem is the same as with etcd - the default timeouts are tuned for local-area networks with high
bandwidth and low latency. In the case of cross-datacenter communication, the ack from the remote node can take a long
time due to network congestion.

If a single DRBD device is reported as having lost quorum, the Piraeus HA controller will fence the node to prevent
other workloads from failing. This can lead to non-schedulable workloads and even a rebalance storm.

## Configuration

While it's possible to tune the timeouts for every DRBD resource, it's much easier to set global parameters for the
Linstor cluster once:

```
# this will also adjust the timeouts for existing DRBD resources immediately
linstor controller drbd-options --connect-int 15 --ping-int 15 --ping-timeout 20 --drbd-timeout 120
```
