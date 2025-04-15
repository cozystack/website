---
title: "Kube scheduler configuration"
linkTitle: "Kube scheduler configuration"
description: "Kube scheduler configuration"
weight: 20
aliases:
  - /docs/stretched/kubeSchedulerConfiguration
---

## Label nodes

```bash
kubectl label node <nodename> topology.kubernetes.io/zone=A
```

## Create global app topology spread constraints
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack-scheduling
  namespace: cozy-system
data:
  globalAppTopologySpreadConstraints: |
    topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
```

## Configure PodTopologySpread

See: https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/#cluster-level-default-constraints

For Talm installation:
Add to `templates/_helpers.tpl`.

```yaml
cluster:
...
  scheduler:
    config:
      apiVersion: kubescheduler.config.k8s.io/v1beta3
      kind: KubeSchedulerConfiguration
      profiles:
        - schedulerName: default-scheduler
          pluginConfig:
            - name: PodTopologySpread
              args:
                defaultConstraints:
                  - maxSkew: 1
                    topologyKey: topology.kubernetes.io/zone
                    whenUnsatisfiable: ScheduleAnyway
                defaultingType: List
```

Apply changes:

```bash
talm template -f nodes/node1.yaml -I
talm apply -f nodes/node1.yaml
```
