---
title: "Scheduling Classes"
linkTitle: "Scheduling Classes"
description: "Restrict tenant workloads to specific nodes or failure domains using SchedulingClass resources and the Cozystack scheduler."
weight: 150
---

SchedulingClass is a cluster-scoped custom resource that lets administrators define
placement policies for tenant workloads. When a tenant is assigned a scheduling class,
all of its pods are automatically routed to the Cozystack custom scheduler, which
merges the class-defined constraints with any constraints already present on the pod.

This allows platform operators to pin tenants to specific data centers, availability
zones, or node groups — without modifying individual application charts.

## How it works

The feature has two components:

1. **Lineage-controller webhook** (part of `cozystack`): a mutating admission webhook
   that intercepts pod creation in tenant namespaces. When a namespace carries the
   `scheduler.cozystack.io/scheduling-class` label, the webhook sets `schedulerName: cozystack-scheduler`
   and adds the `scheduler.cozystack.io/scheduling-class` annotation on every pod.
   If the referenced SchedulingClass CR does not exist (e.g. the scheduler is not installed),
   pods are left untouched and scheduled normally.

2. **Cozystack scheduler** (the `cozystack-scheduler` package): a custom Kubernetes
   scheduler that runs alongside the default scheduler. During scheduling, it resolves
   the SchedulingClass referenced by the pod annotation and merges the CR's constraints
   (node affinity, pod affinity/anti-affinity, topology spread) with the pod's own spec —
   entirely in memory, without mutating the pod in the API server.

## Prerequisites

- Cozystack v1.2+
- The `cozystack-scheduler` system package (v0.2.0+)

## Installing the scheduler

```bash
cozypkg add cozystack.cozystack-scheduler
```

## Creating a SchedulingClass

A SchedulingClass CR mirrors familiar Kubernetes scheduling primitives. All fields
are optional — include only the constraints you need.

### Example: pin workloads to a data center

```yaml
apiVersion: cozystack.io/v1alpha1
kind: SchedulingClass
metadata:
  name: dc-west
spec:
  nodeSelector:
    topology.kubernetes.io/region: us-west-2
```

Pods assigned to this class will only be scheduled on nodes labeled
`topology.kubernetes.io/region=us-west-2`.

### Example: spread across availability zones

```yaml
apiVersion: cozystack.io/v1alpha1
kind: SchedulingClass
metadata:
  name: zone-spread
spec:
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
```

{{% alert title="Note" %}}
When a `topologySpreadConstraint` or pod affinity/anti-affinity term has a nil
`labelSelector`, the scheduler automatically populates it with a selector matching
the workload's Cozystack application identity labels (`apps.cozystack.io/application.group`,
`.kind`, `.name`). This means you can define generic spreading or anti-affinity
policies without hard-coding label values per application.
{{% /alert %}}

### Example: require dedicated nodes with anti-affinity

```yaml
apiVersion: cozystack.io/v1alpha1
kind: SchedulingClass
metadata:
  name: dedicated-nodes
spec:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: node-pool
              operator: In
              values:
                - dedicated
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - topologyKey: kubernetes.io/hostname
```

This pins workloads to nodes in the `dedicated` pool and spreads pods across
hosts. The anti-affinity `labelSelector` is auto-populated per application, so
pods from different applications of the same tenant can still land on the same node.

## Full SchedulingClass spec reference

| Field | Type | Description |
|-------|------|-------------|
| `spec.nodeSelector` | `map[string]string` | Simple key-value node labels that all nodes must match. |
| `spec.nodeAffinity` | [`NodeAffinity`](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.31/#nodeaffinity-v1-core) | Required and preferred node affinity rules. |
| `spec.podAffinity` | [`PodAffinity`](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.31/#podaffinity-v1-core) | Required and preferred pod co-location rules. |
| `spec.podAntiAffinity` | [`PodAntiAffinity`](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.31/#podantiaffinity-v1-core) | Required and preferred pod anti-co-location rules. |
| `spec.topologySpreadConstraints` | [`[]TopologySpreadConstraint`](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.31/#topologyspreadconstraint-v1-core) | Topology spread constraints for even distribution across failure domains. |

## Assigning a SchedulingClass to a tenant

When creating or editing a tenant, set the `schedulingClass` parameter to the name
of an existing SchedulingClass CR:

**Via the dashboard:**

Select the scheduling class from the dropdown in the tenant creation form.

**Via Helm values (`values.yaml`):**

```yaml
schedulingClass: dc-west
```

**Via the tenant secret (child tenant inheritance):**

When a parent tenant has a scheduling class assigned, all child tenants inherit it
automatically. A child tenant cannot override the parent's scheduling class — it can
only set one if the parent has none.

The assignment writes the `scheduler.cozystack.io/scheduling-class` label on the
tenant's namespace. The webhook reads this label (or resolves it from the owning
Application CR) to inject the scheduler name and annotation into pods.

## Auto-populated label selectors

The scheduler (v0.2.0+) automatically fills in nil `labelSelector` fields on
pod affinity, pod anti-affinity, and topology spread constraint terms. It uses
the pod's Cozystack application identity labels:

- `apps.cozystack.io/application.group`
- `apps.cozystack.io/application.kind`
- `apps.cozystack.io/application.name`

This means that a generic SchedulingClass like:

```yaml
spec:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - topologyKey: kubernetes.io/hostname
```

will automatically scope the anti-affinity to pods of the same application — each
application gets its own anti-affinity behavior without needing a separate
SchedulingClass per app.

The default label keys can be overridden in the scheduler's Helm values:

```yaml
defaultLabelSelectorKeys:
  - apps.cozystack.io/application.group
  - apps.cozystack.io/application.kind
  - apps.cozystack.io/application.name
```

If a term already has an explicit `labelSelector`, it is preserved as-is.

## Operators without native schedulerName support

Some operators used by Cozystack do not expose `schedulerName` in their CRDs.
The webhook-based approach handles these transparently because it mutates pods
directly at admission time, regardless of which operator created them:

- etcd-operator
- redis-operator (spotahome)
- mariadb-operator
- clickhouse-operator (altinity)

No special configuration is needed for workloads managed by these operators.

## Verifying the setup

1. Confirm the scheduler is running:

   ```bash
   kubectl get pods -n cozy-system -l app.kubernetes.io/name=cozystack-scheduler
   ```

2. Confirm the SchedulingClass exists:

   ```bash
   kubectl get schedulingclasses
   ```

3. Check that a tenant namespace has the label:

   ```bash
   kubectl get ns tenant-example -o jsonpath='{.metadata.labels.scheduler\.cozystack\.io/scheduling-class}'
   ```

4. Check that pods in the tenant namespace use the custom scheduler:

   ```bash
   kubectl get pods -n tenant-example -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.schedulerName}{"\n"}{end}'
   ```
