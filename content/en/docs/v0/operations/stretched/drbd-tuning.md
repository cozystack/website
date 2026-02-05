---
title: "LINSTOR DRBD Configuration"
linkTitle: "LINSTOR DRBD"
description: "Parameters required to make Linstor work in a stretched cluster"
weight: 30
aliases:
  - /docs/stretched/linstor
  - /docs/operations/stretched/linstor
---

## Introduction

This guide explains the configuration needed to use LINSTOR storage in a stretched (distributed) Cozystack cluster.

DRBD (Distributed Replicated Block Device) is a kernel-level block device replication system that works over the network.
LINSTOR server manages DRBD volumes, including their creation, deletion, and orchestration across nodes.

## Challenges of using DRBD

DRBD only considers data as written once it reaches a quorum of nodes.
But as it presents itself as a block device to the end user, it must return an error within a given timeout if there are not enough nodes to establish a quorum.

The potential problem is that the default timeouts are tuned for local-area networks with high bandwidth and low latency.
In the case of cross-datacenter communication, the acknowledgement from the remote node can take a long time due to network congestion.
This is similar to how `etcd` behaves under stretched conditions, where default timeouts can lead to false quorum failures.

If a single DRBD device is reported as having lost quorum, the Piraeus HA controller will fence the node to prevent other workloads from failing.
This can lead to non-schedulable workloads and even a rebalance storm.

## Configuration

The most efficient approach is to set global connection parameters for the LINSTOR cluster,
using the `linstor controller drbd-options` command.
It applies settings to all existing DRBD resources immediately, without the need for individual adjustments or restarts:

```bash
# Applies to existing DRBD resources as well
linstor controller drbd-options --connect-int 15 --ping-int 15 --ping-timeout 20 --drbd-timeout 120
```

These values are tuned for inter-datacenter environments with higher latency than a typical local network.

| Parameter        | Meaning                                                                                       | Default Value | Recommended Value |
|------------------|-----------------------------------------------------------------------------------------------|---------------|-------------------|
| `--connect-int`  | Interval in seconds between TCP connection attempts (in seconds).                             | 10            | 15                |
| `--ping-int`     | Interval in seconds between keepalive pings (in seconds).                                     | 10            | 15                |
| `--ping-timeout` | Time to wait for a ping response before considering the peer dead (in tenths of a second).    | 5             | 20                |
| `--drbd-timeout` | Maximum time to wait for a network reply before triggering a timeout (in tenths of a second). | 60            | 120               |

Adjusting these settings helps avoid unnecessary fencing and workload disruption in stretched clusters.

Also note the guide on [generic DRBD tuning]({{% ref "/docs/storage/drbd-tuning" %}}).
