---
title: "Tune etcd timeouts"
linkTitle: "etcd configuration"
description: "Parameters required to make etcd work in a stretched cluster"
weight: 10
aliases:
  - /docs/stretched/etcd
---

## Potential problems

**etcd** is a reliable key-value store for critical data, the place where the Kubernetes API server stores its data.
Values are not considered written until a quorum of nodes reports that data has been written. Also, etcd constantly
checks that there is a leader and every node is aware which one it is. Usually, an etcd cluster is run on nodes in the
same datacenter (where latency is low) and default timeouts are tuned for the quickest error reporting possible. In a
stretched cluster, where nodes are in different datacenters, the RTT is much higher and default timeouts can cause false
alarms as if the network was partitioned. In this case, the data is still consistent, but etcd will enter readonly mode
to prevent split-brain. This could happen so frequently that many other components of Kubernetes would start to fail
with non-descriptive and unhelpful error messages.

## Configuration

To prevent frequent leader re-elections, you need to tune the following parameters in the etcd configuration:

* `heartbeat-interval` - the time between heartbeats
* `election-timeout` - the time to wait for a heartbeat before starting an election

An example of command-line arguments for etcd:

```
--election-timeout=10000 --heartbeat-interval=1000
```

## Talos example

When using `talm` to manage your Talos nodes, add parameters to the `cluster.etcd` section of the template:

```yaml
cluster:
  etcd:
    extraArgs:
      heartbeat-interval: "1000"
      election-timeout: "10000"
```
