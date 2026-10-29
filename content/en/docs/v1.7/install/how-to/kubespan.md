---
title: How to Enable KubeSpan
linkTitle: Enable KubeSpan
description: "How to Enable KubeSpan."
weight: 120
---

Talos Linux provides a full mesh WireGuard network for your cluster.

To enable this functionality, you need to configure [KubeSpan](https://www.talos.dev/{{< version-pin "talos_minor" >}}/talos-guides/network/kubespan/) and [Cluster Discovery](https://www.talos.dev/{{< version-pin "talos_minor" >}}/kubernetes-guides/configuration/discovery/) in your Talos Linux configuration:

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

To achieve this, add the following to the `networking` component of your Platform Package:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  # ...
  components:
    networking:
      values:
        kube-ovn:
          mtu: 1222
```
