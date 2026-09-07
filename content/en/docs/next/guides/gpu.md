---
title: "GPU in Cozystack"
linkTitle: "GPU"
description: "How Cozystack serves GPUs to pods, virtual machines and tenant Kubernetes clusters: which path to pick, what each one requires, and where the boundaries are."
weight: 35
---

Cozystack has no single "GPU feature". It has several paths that serve a GPU to a different kind of consumer, and they are not interchangeable — the choice is made once per node, at the level of who owns the host driver, and it decides what that node can serve. Each path is documented in full on its own page. This one is the map: how to pick a path, what it costs, and what it rules out.

## Pick a path

| The GPU is consumed by | Runs on | Sharing granularity | Selected through | Guide |
| --- | --- | --- | --- | --- |
| Containers — CUDA pods, training, inference | Management cluster | Whole GPU | `cozystack.gpu-operator`, `container` variant | [Containerized GPU Workloads](/docs/next/operations/gpu-container-workloads/) |
| One virtual machine | Management cluster | Whole GPU | `bundles.iaas.gpuOperatorVariant: default` | [GPU Passthrough](/docs/next/virtualization/gpu/) |
| Several virtual machines sharing one card | Management cluster | vGPU profile per VF | `bundles.iaas.gpuOperatorVariant: vgpu` | [NVIDIA vGPU](/docs/next/virtualization/vgpu/) |
| Containers inside a tenant Kubernetes cluster | Tenant cluster | Whole GPU | `addons.gpuOperator.enabled` on the tenant cluster, plus GPUs declared on its worker node pool | [Managed Kubernetes](/docs/next/kubernetes/) |
| Containers inside a tenant Kubernetes cluster, several per card | Tenant cluster | Memory and compute quota per pod | The above, plus `addons.hami.enabled` | [GPU Sharing with HAMi](/docs/next/kubernetes/gpu-sharing/) |

Everything on this page is NVIDIA. The `cozystack.gpu-operator` package wraps NVIDIA's GPU Operator, and the KubeVirt host-device defaults the platform ships cover PCI vendor `10DE`.

## A management cluster node serves one variant, and only one

The `cozystack.gpu-operator` package ships three variants, and they differ in exactly one thing that matters: who is allowed to own the GPU on the host.

- **`default`** — the operator unbinds whatever holds the card and binds `vfio-pci`, so the GPU can be handed to a virtual machine. The host must not carry an NVIDIA driver of its own.
- **`vgpu`** — the proprietary NVIDIA vGPU host driver owns the card and slices it into SR-IOV virtual functions, each of which becomes a GPU to one VM.
- **`container`** — the host owns the card through its own distro-installed driver, and the operator only advertises it to kubelet. The operator's driver, container-toolkit and VFIO components are pinned off precisely so that it does not fight the host install.

These are not degrees of the same setting. Two of them on one node is a broken node: the passthrough variant refuses to bind `vfio-pci` when it detects a pre-installed host driver, and the container variant has nothing to advertise when the driver has been unbound. That is why the variant is the first decision, before any workload exists — and why moving a node from one to the other is a host-level migration, not a values edit. If a node has ended up in the crossed state, [GPU Operator: host driver](/docs/next/operations/troubleshooting/gpu-operator-host-driver/) describes the symptom and the way out.

For the two VM-facing variants the platform also mirrors the choice into the KubeVirt custom resource — the `HostDevices` feature gate and a starter `permittedHostDevices` table — so there is no `kubectl edit kubevirt` step, and a hand edit to the live resource is reverted on the next reconcile. Extend that table through platform values instead; see [GPU Passthrough](/docs/next/virtualization/gpu/). The `container` variant serves pods and gets none of this wiring, by design: the host driver stays bound and no GPU reaches a VM.

## Tenant clusters stack on top of passthrough

A tenant Kubernetes cluster runs its own GPU Operator instance, enabled as a cluster addon and configured independently of the management cluster. Its worker nodes, however, are virtual machines — so the GPU has to reach them as a KubeVirt host device first. In practice this means the management cluster must be on a VM-facing variant for a tenant node to see a GPU at all, and the resource name a tenant node pool asks for is the one the management cluster's sandbox device plugin advertises, such as `nvidia.com/GA102GL_A10`. Confirm the exact string with `kubectl describe node <node> | grep nvidia.com/` rather than guessing it from the model name; the slug is derived mechanically from the PCI IDs database and carries every token that string holds.

Inside the tenant cluster the GPU is then served to pods — whole by default, or split by memory and compute quota with [HAMi](/docs/next/kubernetes/gpu-sharing/).

## What the paths do not cover

**MIG is a container mechanism only.** MIG partitions a card into isolated instances, but they are logical divisions inside one PCIe device and VFIO cannot pass them to a virtual machine; reaching MIG from a VM requires vGPU layered on top, which is licensed. None of the three variants configures MIG geometry.

**vGPU is not free and not open.** It needs an NVIDIA vGPU Software or AI Enterprise subscription and a reachable Delegated License Service endpoint. The driver is not redistributable, which is also why Talos Linux is not a recommended host for it — Sidero cannot ship the guest driver in a system extension under NVIDIA's current terms.

**HAMi's isolation depends on the workload image, not on the cluster.** HAMi-core loads through `LD_PRELOAD` into the workload container and relies on a glibc symbol removed in 2.34, so on a modern base image compute isolation degrades or disappears — silently, with the workload still running and no limit enforced. The compatibility table is on the [HAMi page](/docs/next/kubernetes/gpu-sharing/); read it before sizing a shared node.

**HAMi does not stack on the `container` variant on the management cluster.** That variant pins the NVIDIA device plugin on and HAMi ships its own, so both would register `nvidia.com/gpu`. Fractional sharing is currently a tenant-cluster capability, where the tenant chart disables the operator's plugin for you.

## Where each page lives

- [Containerized GPU Workloads](/docs/next/operations/gpu-container-workloads/) — CUDA pods on management cluster nodes, and the host prerequisites the `container` variant assumes.
- [GPU Passthrough](/docs/next/virtualization/gpu/) — a whole GPU inside a VM, the automatic KubeVirt wiring, and how to extend the device table for a card the defaults do not list.
- [NVIDIA vGPU](/docs/next/virtualization/vgpu/) — slicing one card across several VMs, SR-IOV profile assignment and DLS licensing.
- [GPU Sharing with HAMi](/docs/next/kubernetes/gpu-sharing/) — fractional GPU for pods in a tenant cluster, the resource names, and the isolation limits.
- [GPU Operator: host driver](/docs/next/operations/troubleshooting/gpu-operator-host-driver/) — recovering a node where the host driver and the passthrough variant are both trying to own the card.
