---
title: Resource Management in Cozystack
linkTitle: Resource Management
description: >
  How CPU, memory, and presets work across VMs, Kubernetes clusters, and managed
  workloads in Cozystack; and how to reconfigure resources via the UI, CLI, or API.
weight: 25
---

## Introduction

Cozystack runs everything, including system components and user-side applications, as services in a Kubernetes cluster,
having a finite pool of CPU and memory.

This guide explains how users can configure available resources for an application, and how Cozystack handles this configuration.


## Service Resource Configuration

Resources, available to each service (managed application, VM, or tenant cluster), are defined in its configuration file.
There are two ways to specify CPU time and memory available for a service in Cozystack:

-   Using resource presets.
-   Using explicit resource configurations.


### Using Resource Presets

Cozystack provides a number of named resource presets.
Each user-side service, including managed applications, tenant Kubernetes clusters and virtual machines, has a default preset value.

When deploying a service, a preset is defined in `resourcesPreset` configuration variable, for example:

```yaml
## @param resourcesPreset Default sizing preset used when `resources` is omitted.
resourcesPreset: "t1.small"
```

Presets follow a cloud-style `<series>.<size>` naming convention. Five series cover the full CPU-to-memory ratio range, and each series ships eight sizes (`nano` through `4xlarge`):

| Series | Ratio CPU:Mem | Typical use case                                  |
| ------ | ------------- | ------------------------------------------------- |
| `t1`   | `1:0.5`       | Tiny / burstable, low memory                      |
| `c1`   | `1:1`         | Compute-balanced, CPU-bound workloads             |
| `s1`   | `1:2`         | Standard — proxies, caches, lightweight services  |
| `u1`   | `1:4`         | Universal — databases and messaging               |
| `m1`   | `1:8`         | Memory-heavy — search, analytics, large caches    |

CPU per size:

| Size       | CPU    |
| ---------- | ------ |
| `nano`     | `250m` |
| `micro`    | `500m` |
| `small`    | `1`    |
| `medium`   | `2`    |
| `large`    | `4`    |
| `xlarge`   | `8`    |
| `2xlarge`  | `16`   |
| `4xlarge`  | `32`   |

Memory follows from the series ratio. For example, `t1.small` is 1 CPU / 512Mi, `c1.small` is 1 CPU / 1Gi, `s1.small` is 1 CPU / 2Gi, `u1.small` is 1 CPU / 4Gi, and `m1.small` is 1 CPU / 8Gi. Ephemeral storage is 2Gi for every preset.

In CPU, the `m` unit is 1/1000th of a full CPU time.

#### Watch out: legacy and instance-type `medium` differ

The legacy flat preset `medium` had **1 CPU / 1Gi**. The new `*.medium` sizes have **2 CPU**. The names overlap but the resources do not. The legacy table below stays correct — `medium → c1.small (1 CPU / 1Gi)` — but if you read the instance-type sizing matrix first and pick `c1.medium` "to keep things the same as before", you will double your CPU. When in doubt, consult the legacy-to-instance-type mapping below.

#### Legacy flat preset names (deprecated)

The seven short names that existed before the instance-type rename remain accepted as backward-compatibility aliases. They render exactly the CPU and memory they did before — so an existing HelmRelease or app CR continues to behave identically. The 1:1 mapping is:

| Legacy    | CPU    | Memory  | Instance-type equivalent |
| --------- | ------ | ------- | ------------------------ |
| `nano`    | `250m` | `128Mi` | `t1.nano`                |
| `micro`   | `500m` | `256Mi` | `t1.micro`               |
| `small`   | `1`    | `512Mi` | `t1.small`               |
| `medium`  | `1`    | `1Gi`   | `c1.small`               |
| `large`   | `2`    | `2Gi`   | `c1.medium`              |
| `xlarge`  | `4`    | `4Gi`   | `c1.large`               |
| `2xlarge` | `8`    | `8Gi`   | `c1.xlarge`              |

Legacy names are scheduled for removal in a future Cozystack release; new manifests should use the instance-type form. The Cozystack API server logs a deprecation warning whenever an app CR carries a legacy value, naming the suggested replacement.

A platform upgrade runs a one-shot migration (Migration 39) that walks every `HelmRelease.spec.values` and every app CR under `apps.cozystack.io/v1alpha1` and rewrites legacy values to their instance-type equivalents in place. The conversion is idempotent, best-effort, and never changes CPU or memory.

Cozystack presets are defined in an internal library
[`cozy-lib`](https://github.com/cozystack/cozystack/tree/main/packages/library/cozy-lib). The canonical reference, including the full size matrix and migration table, lives in [`docs/operations/resource-presets.md`](https://github.com/cozystack/cozystack/blob/main/docs/operations/resource-presets.md).


### Defining Resources Explicitly

A service configuration can define available CPU and memory explicitly, using the `resources` variable.
Cozystack has a simple resource configuration format for `cpu` and `memory`:

```yaml
## @param resources Explicit CPU and memory configuration for each ClickHouse replica.
## When left empty, the preset defined in `resourcesPreset` is applied.
resources:
  cpu: 1
  memory: 2Gi
```

If both `resources` and `resourcesPreset` are defined, `resources` is used and `resourcesPreset` is ignored.


## Resource Requests and Limits

Everything in Cozystack runs as Kubernetes services, and Kubernetes uses two important mechanisms in resource management:
requests and limits.
First, let's understand what they are.

-   **Resource request** defines the amount of resource that will be reserved for a service and always provided.
    If there is not enough resource to fulfill a request, a service will not run at all.

-   **Resource limit** defines how much a service can use from a free resource pool.

{{% alert color="info" %}}
For a detailed explanation of how requests and limits work in Kubernetes, read [Resource Management for Pods and Containers](
https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).
{{% /alert %}}

CPU time is easily shared between multiple services with uneven CPU load.
For this reason, it's a common practice to set low CPU requests with much higher limits.
For services that are CPU-intensive, the optimal ratio can be 1:2 or 1:4.
For less CPU-intensive services, as much as 1:10 can provide great resource efficiency and still be enough.

On the other hand, memory is a resource that, once given to a service, usually can't be taken back without OOM-killing the service.
For this reason, it's usually best to set memory requests at a level that guarantees service operation.


## CPU Allocation Ratio

Cozystack has a single-point-of-truth configuration variable `cpuAllocationRatio`.
It defines the ratio between CPU requests and limits for all services.

CPU allocation ratio is defined in the Platform Package:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full
  components:
    platform:
      values:
        # ...
        resources:
          cpuAllocationRatio: 4
```

By default, `cpuAllocationRatio` equals 10, which means that CPU requests will be 1/10th of CPU limits.
Cozystack borrows this default value from [KubeVirt](https://kubevirt.io/user-guide/compute/resources_requests_and_limits/#cpu).

### How Cozystack Derives CPU Requests and Limits

```yaml
## @param resources Explicit CPU and memory configuration for each ClickHouse replica.
## When left empty, the preset defined in `resourcesPreset` is applied.
resources:
  cpu: 1
  ## actual cpu limit: 1
  ## actual cpu request: (cpu / cpu-allocation-ratio)
  memory: 2Gi
```

### Example 1, default setting: `cpu-allocation-ratio: 10`

Preset CPU shown for the `t1` series (the legacy `nano … 2xlarge` aliases use the same CPU values; other series share the same `cpu` column per size, so a `c1.small`, `s1.small`, `u1.small`, or `m1.small` each have `cpu: 1` too).

| Preset name | `resources.cpu` | actual CPU request | actual CPU limit |
|-------------|-----------------|--------------------|------------------|
| `t1.nano`   | `250m`          | `25m`              | `250m`           |
| `t1.micro`  | `500m`          | `50m`              | `500m`           |
| `t1.small`  | `1`             | `100m`             | `1`              |
| `t1.medium` | `2`             | `200m`             | `2`              |
| `t1.large`  | `4`             | `400m`             | `4`              |
| `t1.xlarge` | `8`             | `800m`             | `8`              |
| `t1.2xlarge`| `16`            | `1600m`            | `16`             |
| `t1.4xlarge`| `32`            | `3200m`            | `32`             |

### Example 2: `cpu-allocation-ratio: 4`

| Preset name | `resources.cpu` | actual CPU request | actual CPU limit |
|-------------|-----------------|--------------------|------------------|
| `t1.nano`   | `250m`          | `62m`              | `250m`           |
| `t1.micro`  | `500m`          | `125m`             | `500m`           |
| `t1.small`  | `1`             | `250m`             | `1`              |
| `t1.medium` | `2`             | `500m`             | `2`              |
| `t1.large`  | `4`             | `1`                | `4`              |
| `t1.xlarge` | `8`             | `2`                | `8`              |
| `t1.2xlarge`| `16`            | `4`                | `16`             |
| `t1.4xlarge`| `32`            | `8`                | `32`             |

## Configuration Format Before v0.31.0

Before Cozystack v0.31.0, service configuration allowed users to define requests and limits explicitly.
After updating Cozystack from earlier versions to v0.31.0 or later, such services will require no immediate action.

When users update such applications, they need to change the configuration to the new form.

```yaml
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 1
    memory: 2Gi
```

There were several reasons for this change.

Managed applications assume that the user doesn't need in-depth knowledge of Kubernetes.
However, explicit request/limit configuration was a “leaky abstraction”, confusing users and leading to misconfigurations.

For hosting companies that run public clouds on Cozystack, a unified ratio across the cloud is crucial.
This approach helps ensure a stable level of service and simplifies billing.

Users who deploy their own applications to tenant Kubernetes clusters still have the freedom to define precise resource requests and limits.

