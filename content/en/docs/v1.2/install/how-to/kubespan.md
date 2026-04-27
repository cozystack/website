---
title: Как включить KubeSpan
linkTitle: Включение KubeSpan
description: "Как включить KubeSpan."
weight: 120
---

Talos Linux предоставляет full-mesh сеть WireGuard для вашего кластера.

Чтобы включить эту функциональность, настройте [KubeSpan](https://www.talos.dev/v1.8/talos-guides/network/kubespan/) и [Cluster Discovery](https://www.talos.dev/v1.2/kubernetes-guides/configuration/discovery/) в конфигурации Talos Linux:

```yaml
machine:
  network:
    kubespan:
      enabled: true
cluster:
  discovery:
    enabled: true
```

Поскольку KubeSpan инкапсулирует трафик в туннель WireGuard, для Kube-OVN также нужно настроить более низкое значение MTU.

Для этого добавьте следующее в компонент `networking` вашего Platform Package:

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
