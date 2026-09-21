---
title: "GPU in Cozystack"
linkTitle: "GPU"
description: "How Cozystack serves GPUs to pods, virtual machines and tenant Kubernetes clusters: which path to pick, what each one requires, and where the boundaries are."
weight: 35
---

Cozystack can serve a GPU to a container, to a virtual machine, or to a workload inside a tenant Kubernetes cluster. Each of these is a separate path with its own guide, and they are not interchangeable: the choice is made once per node, by deciding who owns the card on the host, and it fixes what that node can serve. This page is the map: which path fits, what it costs, and what it rules out.

## Pick a path

| The GPU is consumed by | Runs on | Sharing granularity | Selected through | Guide |
| --- | --- | --- | --- | --- |
| Containers: CUDA pods, training, inference | Management cluster | Whole GPU | `cozystack.gpu-operator`, `container` variant | [Containerized GPU Workloads](/docs/v1.6/operations/gpu-container-workloads/) |
| One virtual machine | Management cluster | Whole GPU | `bundles.iaas.gpuOperatorVariant: default` | [GPU Passthrough](/docs/v1.6/virtualization/gpu/) |
| Several virtual machines sharing one card | Management cluster | vGPU profile | `bundles.iaas.gpuOperatorVariant: vgpu` | [NVIDIA vGPU](/docs/v1.6/virtualization/vgpu/) |
| Containers inside a tenant Kubernetes cluster | Tenant cluster | Whole GPU | `addons.gpuOperator.enabled` on the tenant cluster, plus GPUs declared on its worker node pool | [Managed Kubernetes](/docs/v1.6/kubernetes/) |
| Containers inside a tenant Kubernetes cluster, several per card | Tenant cluster | Memory and compute quota per pod | The above, plus `addons.hami.enabled` | [GPU Sharing with HAMi](/docs/v1.6/kubernetes/gpu-sharing/) |

Everything on this page is NVIDIA. The `cozystack.gpu-operator` package wraps NVIDIA's GPU Operator, and the KubeVirt host-device defaults the platform ships cover PCI vendor `10DE`.

## A management cluster node serves one variant

The `cozystack.gpu-operator` package ships three variants. What separates them is who owns the GPU on the host.

- **`default`**: the operator unbinds whatever holds the card and binds `vfio-pci`, so the GPU can be handed to a virtual machine. The host must not carry an NVIDIA driver of its own.
- **`vgpu`**: the proprietary NVIDIA vGPU host driver owns the card and slices it, and each slice becomes a GPU for one VM.
- **`container`**: the host owns the card through its own distro-installed driver, and the operator only advertises it to kubelet. The operator's driver, container toolkit and VFIO components are pinned off so that it does not fight the host install.

Two of them on one node make a broken node. The passthrough variant refuses to bind `vfio-pci` when it finds a pre-installed host driver, and the container variant has nothing to advertise once the driver is unbound. So pick the variant before any workload exists, and treat moving a node from one to another as a host migration rather than a values edit. If a node already ended up in that state, [GPU Operator: host driver](/docs/v1.6/operations/troubleshooting/gpu-operator-host-driver/) shows the symptom and the way back.

For the two VM-facing variants the platform sets the `HostDevices` feature gate on the KubeVirt custom resource and owns its `permittedHostDevices` list. There is no `kubectl edit kubevirt` step, and a hand edit to the live resource is reverted on the next reconcile. Which devices the list carries by default depends on the variant; [GPU Passthrough](/docs/v1.6/virtualization/gpu/) shows how to add a card through platform values. The `container` variant gets none of this: the host driver stays bound and no GPU reaches a VM.

## Tenant clusters stack on top of passthrough

A tenant Kubernetes cluster runs its own GPU Operator, enabled as a cluster addon and configured separately from the management cluster. Its worker nodes are virtual machines, though, so the GPU has to reach them as a KubeVirt host device first. The management cluster therefore has to run a VM-facing variant before a tenant node can see a GPU at all, and a tenant node pool asks for the resource name that the management cluster advertises, such as `nvidia.com/GA102GL_A10`. Take the exact string from `kubectl describe node <node> | grep nvidia.com/` rather than guessing it from the model name: it is derived from the PCI IDs database and keeps every token that entry holds.

Inside the tenant cluster the GPU is then served to pods, whole by default, or split by memory and compute quota with [HAMi](/docs/v1.6/kubernetes/gpu-sharing/). What else a tenant cluster offers AI workloads (Dynamic Resource Allocation, Kueue, DCGM metrics) is recorded on the [AI Conformance](/compliance/ai-conformance/) page, together with the command that checks each item.

## What the paths do not cover

**A MIG instance cannot be handed to a virtual machine.** MIG partitions a card into isolated instances inside one PCIe device, and VFIO passes whole devices. A VM gets either the whole card or, with vGPU, a licensed slice of it.

**vGPU needs an NVIDIA license.** It requires an NVIDIA vGPU Software or AI Enterprise subscription and a reachable Delegated License Service endpoint. The driver is not redistributable, which is also why Talos Linux is not a recommended host for it: Sidero cannot ship it in a system extension under NVIDIA's current terms.

**HAMi isolation depends on the workload image.** HAMi-core is loaded into the workload container through `LD_PRELOAD` and relies on a glibc symbol removed in 2.34. On a recent base image compute isolation degrades or disappears, silently: the workload keeps running and no limit is enforced. Check the compatibility table on the [HAMi page](/docs/v1.6/kubernetes/gpu-sharing/) before sizing a shared node.

**HAMi does not stack on the `container` variant on the management cluster.** That variant keeps the NVIDIA device plugin on and HAMi ships its own, so both would register `nvidia.com/gpu`. Fractional sharing is a tenant cluster capability for now, where the tenant chart turns the operator's plugin off for you.

## Where each page lives

- [Containerized GPU Workloads](/docs/v1.6/operations/gpu-container-workloads/): CUDA pods on management cluster nodes, and the host prerequisites the `container` variant assumes.
- [GPU Passthrough](/docs/v1.6/virtualization/gpu/): a whole GPU inside a VM, the KubeVirt wiring, and adding a card the defaults do not list.
- [NVIDIA vGPU](/docs/v1.6/virtualization/vgpu/): one card sliced across several VMs, profile assignment and DLS licensing.
- [GPU Sharing with HAMi](/docs/v1.6/kubernetes/gpu-sharing/): fractional GPU for pods in a tenant cluster, the resource names, and the isolation limits.
- [GPU Operator: host driver](/docs/v1.6/operations/troubleshooting/gpu-operator-host-driver/): recovering a node where the host driver and the passthrough variant both claim the card.
- [AI Conformance](/compliance/ai-conformance/): what a tenant cluster certifies for AI workloads, and how to verify it.
