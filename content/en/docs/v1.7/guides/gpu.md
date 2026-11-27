---
title: "GPU in Cozystack"
linkTitle: "GPU"
description: "How Cozystack serves GPUs to pods, virtual machines and tenant Kubernetes clusters: which path to pick, what each one requires, and where the boundaries are."
weight: 35
---

Cozystack can serve a GPU to a container, to a virtual machine, or to a workload inside a tenant Kubernetes cluster. Each of these is a separate path with its own guide, and they are not interchangeable: the choice is made once per management cluster, by deciding who owns the card on the host, and it fixes what every GPU node in that cluster can serve. This page is the map: which path fits, what it costs, and what it rules out.

## Pick a path

| The GPU is consumed by | Runs on | Sharing granularity | Selected through | Guide |
| --- | --- | --- | --- | --- |
| Containers: CUDA pods, training, inference | Management cluster | Whole GPU | `bundles.iaas.gpuOperatorVariant: container`, plus `cozystack.gpu-operator` in `bundles.enabledPackages` | [Containerized GPU Workloads](/docs/v1.7/operations/gpu-container-workloads/) |
| One virtual machine | Management cluster | Whole GPU | `bundles.iaas.gpuOperatorVariant: default` (the default), plus `cozystack.gpu-operator` in `bundles.enabledPackages` | [GPU Passthrough](/docs/v1.7/virtualization/gpu/) |
| Several virtual machines sharing one card | Management cluster | vGPU profile | `bundles.iaas.gpuOperatorVariant: vgpu`, plus `cozystack.gpu-operator` in `bundles.enabledPackages` | [NVIDIA vGPU](/docs/v1.7/virtualization/vgpu/) |
| Containers inside a tenant Kubernetes cluster | Tenant cluster | Whole GPU | `addons.gpuOperator.enabled` on the tenant cluster, plus GPUs declared on its worker node pool | [Managed Kubernetes](/docs/v1.7/kubernetes/) |
| Containers inside a tenant Kubernetes cluster, several per card | Tenant cluster | Memory and compute quota per pod | The above, plus `addons.hami.enabled` | [GPU Sharing with HAMi](/docs/v1.7/kubernetes/gpu-sharing/) |

Everything on this page is NVIDIA. The `cozystack.gpu-operator` package wraps NVIDIA's GPU Operator, and the KubeVirt host-device defaults the platform ships cover PCI vendor `10DE`.

## One variant per management cluster

The `cozystack.gpu-operator` package ships three variants. What separates them is who owns the GPU on the host.

- **`default`**: the operator binds `vfio-pci` to the card, so the GPU can be handed to a virtual machine. The host must not carry an NVIDIA driver of its own.
- **`vgpu`**: the proprietary NVIDIA vGPU host driver owns the card and slices it, and each slice becomes a GPU for one VM.
- **`container`**: the host owns the card through its own distro-installed driver, and the operator only advertises it to kubelet. The operator's driver, container toolkit and VFIO components are pinned off so that it does not fight the host install.

The variant is a single value for the whole management cluster. The cluster runs one `cozystack.gpu-operator` Package with one variant, and every variant installs the same `gpu-operator` release into `cozy-gpu-operator`, so it covers every GPU node at once. A cluster cannot keep container GPU nodes next to passthrough nodes: switching to `container` turns VFIO management off on all of them.

The switch is expensive because each variant expects a different owner of the card on the host. The passthrough variant refuses to bind `vfio-pci` when it finds a pre-installed host driver, and the container variant has nothing to advertise once the driver is unbound. So pick the variant before any workload exists, and treat moving a cluster from one variant to another as a migration of every GPU host rather than a values edit. If a node already ended up with the host driver and the passthrough variant both claiming the card, [GPU Operator: host driver](/docs/v1.7/operations/troubleshooting/gpu-operator-host-driver/) shows the symptom and the way back.

For the two VM-facing variants the platform sets the `HostDevices` feature gate on the KubeVirt custom resource and owns its `permittedHostDevices` list. There is no `kubectl edit kubevirt` step, and a hand edit to the live resource is not durable: it is overwritten the next time the platform upgrades the kubevirt release, for example on a version bump. Which devices the list carries by default depends on the variant; [GPU Passthrough](/docs/v1.7/virtualization/gpu/) shows how to add a card through platform values. The `container` variant gets none of this: the host driver stays bound and no GPU reaches a VM.

## Tenant clusters stack on top of passthrough

A tenant Kubernetes cluster runs its own GPU Operator, enabled as a cluster addon and configured separately from the management cluster. Its worker nodes are virtual machines, though, so the GPU has to reach them as a KubeVirt host device first. The management cluster therefore has to run a VM-facing variant before a tenant node can see a GPU at all, and a tenant node pool asks for the resource name that the management cluster advertises, such as `nvidia.com/GA102GL_A10`. Take the exact string from `kubectl describe node <node> | grep nvidia.com/` rather than guessing it from the model name: it is derived from the PCI IDs database and keeps every token that entry holds.

Inside the tenant cluster the GPU is then served to pods, whole by default, or split by memory and compute quota with [HAMi](/docs/v1.7/kubernetes/gpu-sharing/). What a tenant can run on it for AI workloads (Dynamic Resource Allocation, Kueue, DCGM metrics) is recorded on the [AI Conformance](/compliance/ai-conformance/) page, together with the command that checks each item.

## What the paths do not cover

**A MIG instance cannot be handed to a virtual machine.** MIG partitions a card into isolated instances inside one PCIe device, and VFIO passes whole devices. A VM gets either the whole card or, with vGPU, a licensed slice of it.

**vGPU needs an NVIDIA license.** It requires an NVIDIA vGPU Software or AI Enterprise subscription and a reachable NVIDIA License System instance, either cloud-hosted (CLS) or self-hosted (DLS). The driver is not redistributable, which is also why Talos Linux is not a recommended host for it: Sidero cannot ship it in a system extension under NVIDIA's current terms.

**HAMi does not stack on the `container` variant on the management cluster.** That variant keeps the NVIDIA device plugin on and HAMi ships its own, so both would register `nvidia.com/gpu`. Fractional sharing is a tenant cluster capability for now, where the tenant chart turns the operator's plugin off for you.

## Where each page lives

- [Containerized GPU Workloads](/docs/v1.7/operations/gpu-container-workloads/): CUDA pods on management cluster nodes, and the host prerequisites the `container` variant assumes.
- [GPU Passthrough](/docs/v1.7/virtualization/gpu/): a whole GPU inside a VM, the KubeVirt wiring, and adding a card the defaults do not list.
- [NVIDIA vGPU](/docs/v1.7/virtualization/vgpu/): one card sliced across several VMs, profile assignment and licensing.
- [GPU Sharing with HAMi](/docs/v1.7/kubernetes/gpu-sharing/): fractional GPU for pods in a tenant cluster, the resource names, and the isolation limits.
- [GPU Operator: host driver](/docs/v1.7/operations/troubleshooting/gpu-operator-host-driver/): recovering a node where the host driver and the passthrough variant both claim the card.
- [AI Conformance](/compliance/ai-conformance/): which AI Conformance requirements a tenant cluster meets, and the command that checks each one.
