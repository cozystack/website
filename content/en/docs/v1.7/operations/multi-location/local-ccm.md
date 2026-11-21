---
title: "Local Cloud Controller Manager"
linkTitle: "Local CCM"
description: "Node IP detection and lifecycle management for multi-location clusters."
weight: 15
---

The `local-ccm` package provides a lightweight cloud controller manager for self-managed clusters.
It handles node IP detection and node lifecycle without requiring an external cloud provider.

## What it does

- **External IP detection**: Detects each node's external IP via `ip route get` (default target: `8.8.8.8`)
- **Node initialization**: Removes the `node.cloudprovider.kubernetes.io/uninitialized` taint so pods can be scheduled
- **Node lifecycle controller** (optional): Monitors NotReady nodes via ICMP ping and removes them after a configurable timeout

## Install

```bash
cozypkg add cozystack.local-ccm
```

## Talos machine config

All nodes in the cluster (including control plane) must have `cloud-provider: external` set
so that kubelet defers node initialization to the cloud controller manager:

```yaml
machine:
  kubelet:
    extraArgs:
      cloud-provider: external
```

{{% alert title="Important" color="warning" %}}
The `cloud-provider: external` setting must be present on **all** nodes in the cluster,
including control plane nodes. Without it, the cluster-autoscaler cannot match Kubernetes
nodes to cloud provider instances (e.g. Azure VMSS).
{{% /alert %}}
