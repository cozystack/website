---
title: "Node labels"
linkTitle: "Topology node labels"
description: "Label your nodes to help the workloads to be scheduled correctly"
weight: 20
---

## How topology labels work

When running a Kubernetes cluster in multiple datacenters, it's important to know when you want to schedule workloads
close to each other (for example, a database and a backend application) or when you want to spread them out (for
example, multiple replicas of frontend, or database replicas, or volume replicas). The first step to achieving this is
to label Kubernetes nodes. Public clouds typically use the `zone` and `region` terms. In Kubernetes, the most common way
to designate a geographical location is to use `topology.kubernetes.io/zone` and `topology.kubernetes.io/region`
labels (or only the zone one).

## Talos example

While labels are usually set manually in other Kubernetes distributions, with Talos you can describe the topology as
code.

Example `talm` configuration:

`values.yaml`:

```yaml
nodes:
  node1:
    labels:
      topology.kubernetes.io/zone: "us-west-1"
      topology.kubernetes.io/region: "us-west"
  node2:
    labels:
      topology.kubernetes.io/zone: "us-east-1"
      topology.kubernetes.io/region: "us-east"
```

`_helpers.tpl`:

```helm
{{- $nodeLabels := .Values.nodes | dig (include "talm.discovered.hostname" .) "labels" nil }}
machine:
  {{- with $nodeLabels }}
  nodeLabels:
    {{- toYaml . | nindent 4 }}
  {{- end }}
```
