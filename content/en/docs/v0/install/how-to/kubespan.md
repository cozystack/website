---
title: How to Enable KubeSpan
linkTitle: Enable KubeSpan
description: "How to Enable KubeSpan."
weight: 120
---

Talos Linux provides a full mesh WireGuard network for your cluster.

To enable this functionality, you need to configure [KubeSpan](https://www.talos.dev/v1.8/talos-guides/network/kubespan/) and [Cluster Discovery](https://www.talos.dev/v1.2/kubernetes-guides/configuration/discovery/) in your Talos Linux configuration:

```yaml
machine:
  network:
    kubespan:
      enabled: true
cluster:
  discovery:
    enabled: true
```

Since KubeSpan encapsulates traffic into a WireGuard tunnel, Kube-OVN should also be configured with a lower MTU value.

To achieve this, add the following to the Cozystack ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  values-kubeovn: |
    kube-ovn:
      mtu: 1222
```
