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
## Allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge.
resourcesPreset: "small"
```

| Preset name | CPU    | memory  |
|-------------|--------|---------|
| `nano`      | `100m` | `128Mi` |
| `micro`     | `250m` | `256Mi` |
| `small`     | `500m` | `512Mi` |
| `medium`    | `500m` | `1Gi`   |
| `large`     | `1`    | `2Gi`   |
| `xlarge`    | `2`    | `4Gi`   |
| `2xlarge`   | `4`    | `8Gi`   |

In CPU, the `m` unit is 1/1000th of a full CPU time.

Cozystack presets are defined in an internal library
[`cozy-lib`](https://github.com/cozystack/cozystack/tree/main/packages/library/cozy-lib).


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

If both `resources` and `resourcesPreset` are defined, `resource` is used and `resourcsePreset` is ignored.


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

Cozystack has a single-point-of-truth configuration variable `cpu-allocation-ratio`.
It defines the ratio between CPU requests and limits for all services.

CPU allocation ratio is defined in the main Cozystack config:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-full"
  # ...
  cpu-allocation-ratio: 4
```

By default, `cpu-allocation-ratio` equals 10, which means that CPU requests will be 1/10th of CPU limits.
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

| Preset name | `resources.cpu` | actual CPU request | actual CPU limit |
|-------------|-----------------|--------------------|------------------|
| `nano`      | `100m`          | `10m`              | `100m`           |
| `micro`     | `250m`          | `25m`              | `250m`           |
| `small`     | `500m`          | `50m`              | `500m`           |
| `medium`    | `500m`          | `50m`              | `500m`           |
| `large`     | `1`             | `100m`             | `1`              |
| `xlarge`    | `2`             | `200m`             | `2`              |
| `2xlarge`   | `4`             | `400m`             | `4`              |

### Example 2: `cpu-allocation-ratio: 4`

| Preset name | `resources.cpu` | actual CPU request | actual CPU limit |
|-------------|-----------------|--------------------|------------------|
| `nano`      | `100m`          | `25m`              | `100m`           |
| `micro`     | `250m`          | `63m`              | `250m`           |
| `small`     | `500m`          | `125m`             | `500m`           |
| `medium`    | `500m`          | `125m`             | `500m`           |
| `large`     | `1`             | `250m`             | `1`              |
| `xlarge`    | `2`             | `500m`             | `2`              |
| `2xlarge`   | `4`             | `1`                | `4`              |

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

