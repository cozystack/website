---
title: "Running Containerized GPU Workloads"
linkTitle: "GPU Containers"
description: "Run CUDA pods and other containerized GPU workloads on Cozystack management nodes that ship the NVIDIA driver and container toolkit via the distro package manager."
weight: 160
---

This page covers running GPU workloads in regular Kubernetes pods (CUDA, ML training, inference) on Cozystack management cluster nodes. It targets the typical Linux GPU node shape — `apt`-installed NVIDIA driver plus `nvidia-container-toolkit` on Ubuntu/Debian — and uses the `container` variant of the `cozystack.gpu-operator` package. Other distros with an equivalent driver + toolkit package layout should work the same way but are not regularly tested.

If instead you want to pass whole GPUs to KubeVirt VMs, see [GPU Passthrough](/docs/next/virtualization/gpu/) and [GPU Sharing with HAMi](/docs/next/kubernetes/gpu-sharing/) (HAMi provides fractional sharing in tenant Kubernetes clusters; stacking it directly on the `container` variant on the management cluster is not a supported combination yet — see [Fractional GPU sharing](#fractional-gpu-sharing) below).

{{< note >}}

The `container` variant is validated by `helm template` and unit tests upstream, but has not yet been exercised end-to-end on physical NVIDIA hardware. Treat the CUDA-pod flow below as provisional and verify it against your own GPU node before relying on it in production.

{{< /note >}}

## When to pick this variant

The `cozystack.gpu-operator` package exposes three architectural variants. Pick `container` when **all** of the following are true:

- The host already runs the NVIDIA driver, installed via the distro package manager (`apt install nvidia-driver-*` on Ubuntu/Debian; other distros with an equivalent driver package should work the same way but are not regularly tested). The operator must not load its own kernel module.
- The host already has `nvidia-container-toolkit` installed (`apt install nvidia-container-toolkit`) and registered with containerd. The operator must not deploy its own toolkit DaemonSet — that would overwrite the `/etc/containerd/config.toml` the host configured (via `nvidia-ctk runtime configure`), breaking the host runtime wiring.
- You want GPUs exposed to containers as `nvidia.com/gpu`, not passed through to KubeVirt VMs.

The other two variants exist for the opposite host shape: `default` (passthrough) unbinds the host driver and binds `vfio-pci` for VM passthrough, and `vgpu` requires the proprietary NVIDIA vGPU host driver plus a license server. Neither path produces a working setup on a host that already ships the driver and container toolkit through apt — the operator and the host install fight each other.

## Prerequisites

- A Cozystack management cluster with at least one GPU-enabled node.
- The GPU node runs Ubuntu or Debian with the NVIDIA driver installed via the distro package manager (other distros with an equivalent driver + toolkit package layout should work the same way but are not regularly tested). Verify with `nvidia-smi` over SSH or `kubectl debug node/<node-name>` — it must enumerate the physical GPUs and report a working driver version.
- The GPU node must not carry a `nvidia.com/gpu.workload.config` label left over from the passthrough setup (`kubectl label node <node-name> nvidia.com/gpu.workload.config-` to remove). The `container` variant relies on the upstream default `container` workload for unlabeled nodes; a leftover `vm-passthrough` label overrides that per-node and the device plugin will not serve the GPU. Remove it before (or together with) the containerd registration step below when migrating a node off the passthrough setup.
- `nvidia-container-toolkit` installed on the same node and registered with containerd. `apt install nvidia-container-toolkit` lays down binaries only — it does not configure containerd. Register the runtime explicitly:

  ```bash
  sudo nvidia-ctk runtime configure --runtime=containerd
  sudo systemctl restart containerd
  grep nvidia /etc/containerd/config.toml   # must show the runtime entry
  ```

- `kubectl` configured against the management cluster.

With `driver.enabled=false` the operator uses the pre-installed host driver at its standard location, so on a stock Ubuntu/Debian install no `hostPaths.driverInstallDir` override is needed. Talos installs the driver under a non-standard prefix, so the operator does not find it at the default location and requires a different starting point — see `packages/system/gpu-operator/examples/values-native-talos.yaml` in the [cozystack repo](https://github.com/cozystack/cozystack) for a working reference with the compat DaemonSet and the matching `driverInstallDir` override.

## 1. Install the GPU Operator (container variant)

**Do not** add `cozystack.gpu-operator` to `bundles.enabledPackages` for this variant. The `iaas` bundle renders the GPU operator from `bundles.iaas.gpuOperatorVariant`, which only accepts `default` or `vgpu` — any other value, `container` included, makes the platform chart fail the Helm render (`packages/core/platform/templates/bundles/iaas.yaml`). Apply the `Package` CR directly instead; the platform controller installs it without a bundle entry and without the variant restriction.

Apply a `Package` CR with `variant: container`:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.gpu-operator
spec:
  variant: container
```

```bash
kubectl apply -f gpu-operator-container.yaml
```

The platform controller resolves the variant against the `PackageSource` (`packages/core/platform/sources/gpu-operator.yaml`), pulls `values.yaml` + `values-container.yaml` from the OCI repository, and installs the chart into `cozy-gpu-operator`.

## 2. Verify the operator is healthy

All pods in the `cozy-gpu-operator` namespace should reach `Running`:

```bash
kubectl get pods --namespace cozy-gpu-operator
```

Example output (pod names will vary):

```console
NAME                                                          READY   STATUS    RESTARTS   AGE
gpu-feature-discovery-7jpzv                                   1/1     Running   0          2m
gpu-operator-7976b5b8fb-xqg2z                                 1/1     Running   0          3m
nvidia-cuda-validator-tjkfh                                   0/1     Completed 0          2m
nvidia-dcgm-exporter-rmpfg                                    1/1     Running   0          2m
nvidia-device-plugin-daemonset-cqj9w                          1/1     Running   0          2m
nvidia-operator-validator-q5n4k                               1/1     Running   0          3m
```

The `container` variant does **not** spawn `nvidia-driver-daemonset`, `nvidia-container-toolkit-daemonset`, or `nvidia-vfio-manager` — all three are pinned off by design.

The node should advertise `nvidia.com/gpu` as an allocatable resource:

```bash
kubectl describe node <node-name>
```

```console
...
Capacity:
  ...
  nvidia.com/gpu:         2
  ...
Allocatable:
  ...
  nvidia.com/gpu:         2
...
```

## 3. Run a sample CUDA pod

Create a pod that requests one GPU and runs `nvidia-smi`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cuda-smoke
spec:
  restartPolicy: OnFailure
  containers:
  - name: cuda
    image: nvcr.io/nvidia/cuda:12.4.1-base-ubuntu22.04
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

```bash
kubectl apply -f cuda-smoke.yaml
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/cuda-smoke --timeout=5m
kubectl logs cuda-smoke
```

The output should enumerate the GPU(s) visible to the pod and report the driver version that the host runs.

## Fractional GPU sharing

The `container` variant exposes whole GPUs through the upstream NVIDIA device plugin. For fractional sharing (per-pod memory and compute quotas), see [GPU Sharing with HAMi](/docs/next/kubernetes/gpu-sharing/) — currently documented for tenant Kubernetes clusters, where enabling HAMi automatically disables the GPU Operator's built-in device plugin to avoid resource-registration conflicts. Stacking the `cozystack.hami` package directly on top of the `container` variant on the management cluster is not a supported combination yet: this variant pins the NVIDIA device plugin on, and HAMi ships its own device plugin, so the two would both register `nvidia.com/gpu`. The `cozystack.hami` PackageSource only declares `dependsOn: cozystack.gpu-operator` for install ordering — it does not disable the operator's device plugin the way the tenant `kubernetes` app chart does.

## Variant comparison

| Workload shape | Variant | Host driver | Host container toolkit | Notes |
| --- | --- | --- | --- | --- |
| Containers (CUDA pods, ML) | `container` | required | required | This page |
| Whole GPU to one VM | `default` | must NOT be loaded — operator binds `vfio-pci` | not used | [GPU Passthrough](/docs/next/virtualization/gpu/) |
| Sliced GPU to multiple VMs | `vgpu` | proprietary NVIDIA vGPU host driver | not used | Requires NVIDIA vGPU license + a Delegated License Service endpoint |
