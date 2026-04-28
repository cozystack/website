---
title: "GPU Sharing with HAMi"
linkTitle: "GPU Sharing"
description: "Enable fractional GPU sharing in tenant Kubernetes clusters using HAMi."
weight: 50
---

[HAMi](https://github.com/Project-HAMi/HAMi) (Heterogeneous AI Computing Virtualization Middleware) is a CNCF Sandbox project that enables fractional GPU sharing in Kubernetes. Instead of dedicating an entire GPU to a single workload, HAMi lets containers request specific amounts of GPU memory and compute cores.

{{% alert color="info" %}}
This guide covers GPU sharing for **containers in tenant Kubernetes clusters**. For GPU passthrough to virtual machines on the management cluster, see [GPU Passthrough](/docs/next/virtualization/gpu/).
{{% /alert %}}

## How it works

HAMi sits between the Kubernetes scheduler and the NVIDIA GPU driver:

- A **Scheduler Extender** adds GPU-aware scheduling decisions (filtering and binding) so pods land on nodes with enough GPU capacity.
- A **Device Plugin** registers virtual GPU resources (`nvidia.com/gpu`, `nvidia.com/gpumem`, `nvidia.com/gpucores`) with kubelet.
- A **MutatingWebhook** automatically routes GPU pods to the HAMi scheduler.
- **HAMi-core** (`libvgpu.so`) is injected into workload containers via `LD_PRELOAD` to enforce memory and compute isolation at the CUDA API level.

When HAMi is enabled, GPU Operator's built-in device plugin is automatically disabled to avoid resource registration conflicts.

## Prerequisites

- A tenant Kubernetes cluster with GPU-enabled worker nodes (node groups with GPUs configured).
- GPU Operator addon enabled on the tenant cluster.

## Enable HAMi

Enable both GPU Operator and HAMi in your tenant Kubernetes cluster configuration:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Kubernetes
metadata:
  name: my-cluster
  namespace: tenant-example
spec:
  nodeGroups:
    gpu-workers:
      minReplicas: 1
      maxReplicas: 3
      instanceType: u1.xlarge
      gpus:
        - name: nvidia.com/GA102GL_A10
  addons:
    gpuOperator:
      enabled: true
    hami:
      enabled: true
```

Apply this configuration:

```bash
kubectl apply -f my-cluster.yaml
```

## Request fractional GPU resources

Once HAMi is running, workloads can request fractional GPU resources:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
    - name: cuda-app
      image: nvcr.io/nvidia/cuda:11.8.0-base-ubuntu20.04
      resources:
        limits:
          nvidia.com/gpu: 1
          nvidia.com/gpumem: 3000
          nvidia.com/gpucores: 30
```

The example above uses absolute memory (`gpumem`). Use `gpumem-percentage` for portability across GPU models with different memory sizes.

| Resource | Description |
| --- | --- |
| `nvidia.com/gpu` | Number of virtual GPUs (always `1` per container) |
| `nvidia.com/gpumem` | GPU memory limit in MiB |
| `nvidia.com/gpucores` | Percentage of GPU compute cores (1–100) |
| `nvidia.com/gpumem-percentage` | GPU memory limit as a percentage (1–100) |

Use `nvidia.com/gpumem-percentage` instead of `nvidia.com/gpumem` when you want a portable limit that works across different GPU models without knowing exact memory sizes.

If `gpumem` and `gpucores` are omitted, the container gets access to the full GPU's memory and compute capacity. Note that HAMi's virtualization layer is still active — this is not the same as bare-metal GPU passthrough.

## Custom configuration

HAMi's behavior can be tuned through `valuesOverride` in the addon configuration:

```yaml
addons:
  hami:
    enabled: true
    valuesOverride:
      hami:
        devicePlugin:
          deviceSplitCount: 10
          deviceMemoryScaling: 1
        scheduler:
          defaultSchedulerPolicy:
            nodeSchedulerPolicy: binpack
            gpuSchedulerPolicy: spread
```

All parameters below are relative to the `valuesOverride.hami` key shown in the example above.

| Parameter | Description | Default |
| --- | --- | --- |
| `devicePlugin.deviceSplitCount` | Maximum virtual GPUs per physical GPU | `10` |
| `devicePlugin.deviceMemoryScaling` | Memory overcommit factor (>1.0 enables overcommit) | `1` |
| `scheduler.defaultSchedulerPolicy.nodeSchedulerPolicy` | Node packing strategy: `binpack` or `spread` | `binpack` |
| `scheduler.defaultSchedulerPolicy.gpuSchedulerPolicy` | GPU packing strategy: `binpack` or `spread` | `spread` |

## Known limitations

### glibc compatibility

HAMi-core relies on a private glibc symbol (`_dl_sym`) that was removed in glibc 2.34. This affects **workload container images only** — HAMi's own components and the host OS are not affected.

| Base image | glibc | Isolation |
| --- | --- | --- |
| Ubuntu 20.04 | 2.31 | Full (memory + compute) |
| Ubuntu 22.04 | 2.35 | Memory isolation only (compute isolation fails silently) |
| Ubuntu 24.04 | 2.39 | No isolation (HAMi-core fails to load silently) |
| Alpine (musl) | N/A | Incompatible |

{{% alert color="warning" %}}
When HAMi-core fails to load, workloads still run but without any GPU resource limits. This can cause GPU out-of-memory errors for colocated workloads.
{{% /alert %}}

The distinction between Ubuntu 22.04 and 24.04 behavior is based on upstream testing — see [HAMi-core #174](https://github.com/Project-HAMi/HAMi-core/issues/174) for details.

Most current CUDA 12.x and PyTorch 2.x images use Ubuntu 22.04+, so compute isolation will not work with them. Use images based on Ubuntu 20.04 or older for full isolation until the [upstream fix](https://github.com/Project-HAMi/HAMi-core/issues/174) lands.

### Alpine / musl libc

HAMi-core is incompatible with musl libc. Only glibc-based container images (Debian, Ubuntu, RHEL) are supported.
