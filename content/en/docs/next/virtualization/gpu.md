---
title: "Running VMs with GPU Passthrough"
linkTitle: "GPU Passthrough"
description: "Running VMs with GPU Passthrough"
weight: 40
aliases:
  - /docs/next/operations/virtualization/gpu
---

This section demonstrates how to deploy virtual machines (VMs) with GPU passthrough using Cozystack.
First, we’ll deploy the GPU Operator to configure the worker node for GPU passthrough
Then we will deploy a [KubeVirt](https://kubevirt.io/) VM that requests a GPU.

By default, to provision a GPU Passthrough, the GPU Operator will deploy the following components:

- **VFIO Manager** to bind `vfio-pci` driver to all GPUs on the node.
- **Sandbox Device Plugin** to discover and advertise the passthrough GPUs to kubelet.
- **Sandbox Validator** to validate the other operands.

## Prerequisites

- A Cozystack cluster with at least one GPU-enabled node.
- kubectl installed and cluster access credentials configured.

## 1. Install the GPU Operator

Follow these steps:

1.  Label the worker node explicitly for GPU passthrough workloads:

    ```bash
    kubectl label node <node-name> --overwrite nvidia.com/gpu.workload.config=vm-passthrough
    ```

2.  Enable the GPU Operator in your Platform Package by adding it to the enabled packages list:

    ```bash
    kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=json \
      -p '[{"op": "add", "path": "/spec/components/platform/values/bundles/enabledPackages/-", "value": "cozystack.gpu-operator"}]'
    ```

    This will deploy the components (operands).

3.  Ensure all pods are in a running state and all validations succeed with the sandbox-validator component:

    ```bash
    kubectl get pods -n cozy-gpu-operator
    ```

    Example output (your pod names may vary):

    ```console
    NAME                                            READY   STATUS    RESTARTS   AGE
    ...
    nvidia-sandbox-device-plugin-daemonset-4mxsc    1/1     Running   0          40s
    nvidia-sandbox-validator-vxj7t                  1/1     Running   0          40s
    nvidia-vfio-manager-thfwf                       1/1     Running   0          78s
    ```

To verify the GPU binding, access the node using `kubectl node-shell -n cozy-system -x` or `kubectl debug node` and run:

```bash
lspci -nnk -d 10de:
```

The vfio-manager pod will bind all GPUs on the node to the vfio-pci driver. Example output:

```console
3b:00.0 3D controller [0302]: NVIDIA Corporation Device [10de:2236] (rev a1)
       Subsystem: NVIDIA Corporation Device [10de:1482]
       Kernel driver in use: vfio-pci
86:00.0 3D controller [0302]: NVIDIA Corporation Device [10de:2236] (rev a1)
       Subsystem: NVIDIA Corporation Device [10de:1482]
       Kernel driver in use: vfio-pci
```

The sandbox-device-plugin will discover and advertise these resources to kubelet.
In this example, the node shows two A10 GPUs as available resources:

```bash
kubectl describe node <node-name>
```

Example output:

```console
...
Capacity:
  ...
  nvidia.com/GA102GL_A10:         2
  ...
Allocatable:
  ...
  nvidia.com/GA102GL_A10:         2
...
```

{{% alert color="info" %}}
**Note:** Resource names are constructed by combining the `device` and `device_name` columns from the [PCI IDs database](https://pci-ids.ucw.cz/v2.2/pci.ids).
For example, the database entry for A10 reads `2236  GA102GL [A10]`, which results in a resource name `nvidia.com/GA102GL_A10`.
{{% /alert %}}

## 2. KubeVirt is wired automatically

When `cozystack.gpu-operator` is in `bundles.enabledPackages`, Cozystack mirrors the chosen GPU variant into the `KubeVirt` Custom Resource for you. There is no `kubectl edit kubevirt` step.

Specifically, the platform injects:

- `HostDevices` into `spec.configuration.developerConfiguration.featureGates` (current KubeVirt splits this from the `GPU` gate; the admission webhook rejects `domain.devices.hostDevices` without it).
- A starter `spec.configuration.permittedHostDevices.pciHostDevices` table (rendered in the default `gpuOperatorVariant: default` — vfio-pci passthrough) covering common NVIDIA datacenter GPUs — Hopper (H100, H200), Ada Lovelace (L4, L40, L40S), Ampere (A100 PCIe/SXM, A40, A30, A10), Turing (T4), Volta (V100, V100S). PCI vendor:device pairs are stable; each `resourceName` slug is whatever `nvidia-sandbox-device-plugin` derives mechanically from the card's PCI-IDs database name — uppercase the name, turn `/`, `.` and whitespace into `_`, then strip the surrounding `[` / `]`. The slug therefore carries every token the PCI-IDs string holds (the `GL` die suffix, the `Tesla` brand on Turing/Volta, the form factor, the memory size), not a tidy `<arch>_<model>`: `TU104GL [Tesla T4]` becomes `nvidia.com/TU104GL_TESLA_T4`, `GA100GL [A30 PCIe]` becomes `nvidia.com/GA100GL_A30_PCIE`, and the H200 SXM becomes `nvidia.com/GH100_H200_SXM_141GB`. Confirm the exact strings your nodes advertise with `kubectl describe node <node> | grep nvidia.com/`. `externalResourceProvider: true` is set on every entry because the resources are advertised by the sandbox plugin, not by KubeVirt's in-tree device plugin.

Verify the resulting CR:

```bash
kubectl -n cozy-kubevirt get kubevirt kubevirt -o json \
  | jq '.spec.configuration | {featureGates: .developerConfiguration.featureGates, permittedHostDevices: .permittedHostDevices}'
```

{{% alert color="info" %}}

**My GPU isn't in the default table — where's the old `kubectl edit kubevirt` step?** It is gone on purpose. `permittedHostDevices` is now owned by the chart template and reconciled from platform values, so any hand edit to the live CR is reverted on the next Flux/Helm reconcile. Add your card through `.gpu.permittedHostDevices` instead — see [Extending or replacing the NVIDIA defaults](#extending-or-replacing-the-nvidia-defaults) below. If you are upgrading from a release where you hand-edited the CR, follow [Upgrading from a hand-edited KubeVirt CR](#upgrading-from-a-hand-edited-kubevirt-cr) first.

{{% /alert %}}

### Extending or replacing the NVIDIA defaults

If your cluster ships a GPU not in the default table, or your `nvidia-sandbox-device-plugin` version emits a different `resourceName` (check with `kubectl describe node <node> | grep nvidia.com/`), extend the defaults via platform values:

```yaml
# Platform Package values
gpu:
  # Append (default) — your entries land alongside the NVIDIA table.
  # Set to true to drop the NVIDIA table entirely (useful for non-NVIDIA-only
  # clusters or strict allowlists). With replaceDefaults: true and an empty
  # list below, the rendered CR carries no permittedHostDevices block at all
  # and the admission webhook rejects every GPU VM — supply your own list.
  replaceDefaults: false
  permittedHostDevices:
    pciHostDevices:
    - pciVendorSelector: "10DE:2236"
      resourceName: nvidia.com/GA102GL_A10
      externalResourceProvider: true
```

To **re-point** a card already in the NVIDIA table (for example to give `10DE:1EB8` a different `resourceName`), do not append a second entry for the same `pciVendorSelector` — both entries are rendered and KubeVirt resolves the duplicated selector non-deterministically. Set `replaceDefaults: true` and supply the full list you want instead.

### Upgrading from a hand-edited KubeVirt CR

Earlier Cozystack releases left `spec.configuration.permittedHostDevices` for operators to hand-edit (`kubectl edit kubevirt`). The bundle now **owns** that field: the first reconcile after the upgrade replaces your manual entries with the rendered NVIDIA default table.

Before upgrading:

1. Dump your current entries:

   ```bash
   kubectl -n cozy-kubevirt get kubevirt kubevirt -o json \
     | jq '.spec.configuration.permittedHostDevices'
   ```

2. Move any custom entries into the Platform Package values under `.gpu.permittedHostDevices` (set `.gpu.replaceDefaults: true` if you want only your own list instead of appending to the NVIDIA defaults).

3. Verify every `resourceName` against what your nodes actually advertise. The default table carries the slug `nvidia-sandbox-device-plugin` generates from each card's PCI-IDs name (uppercased, e.g. `nvidia.com/TU104GL_TESLA_T4` for a Tesla T4), but a different plugin build or PCI-IDs snapshot can emit a different string:

   ```bash
   kubectl describe node <node> | grep nvidia.com/
   ```

A `resourceName` mismatch is silent until a GPU VM restarts or migrates, at which point the admission webhook rejects it.

### Manual Package-CR override path

If you opt out of bundle management and hand-craft a `cozystack.gpu-operator` Package CR directly (to apply overrides the bundle does not expose — driver settings, custom node selectors, validator / dcgmExporter tweaks), the platform does NOT auto-wire `HostDevices` or `permittedHostDevices` into the KubeVirt CR. In that flow, mirror the bundle behaviour by also creating a `cozystack.kubevirt` Package CR that carries `extraFeatureGates` and the matching `permittedHostDevices` block under `spec.components.kubevirt.values` (a cozystack `Package` always nests component values under `spec.components.<name>.values`, never a top-level `spec.values`):

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.kubevirt
spec:
  variant: default
  components:
    kubevirt:
      values:
        extraFeatureGates:
        - HostDevices
        permittedHostDevices:
          pciHostDevices:
          - pciVendorSelector: "10DE:2236"
            resourceName: nvidia.com/GA102GL_A10
            externalResourceProvider: true
```

The manual Package-CR override path takes precedence over the bundle render whenever both exist.

## 3. Create a Virtual Machine

We are now ready to create a VM.

1.  Create a sample virtual machine using the following VMI specification that requests the `nvidia.com/GA102GL_A10` resource.

    **vmi-gpu.yaml**:

    ```yaml
    ---
    apiVersion: apps.cozystack.io/v1alpha1
    appVersion: '*'
    kind: VirtualMachine
    metadata:
      name: gpu
      namespace: tenant-example
    spec:
      running: true
      instanceProfile: ubuntu
      instanceType: u1.medium
      systemDisk:
        image: ubuntu
        storage: 5Gi
        storageClass: replicated
      gpus:
      - name: nvidia.com/GA102GL_A10
      cloudInit: |
        #cloud-config
        password: ubuntu
        chpasswd: { expire: False }
    ```

    ```bash
    kubectl apply -f vmi-gpu.yaml
    ```

    Example output:
    ```console
    virtualmachines.apps.cozystack.io/gpu created
    ```

2.  Verify the VM status:

    ```bash
    kubectl get vmi
    ```

    ```console
    NAME                       AGE   PHASE     IP             NODENAME        READY
    virtual-machine-gpu        73m   Running   10.244.3.191   luc-csxhk-002   True
    ```

3.  Log in to the VM and confirm that it has access to GPU:

    ```bash
    virtctl console virtual-machine-gpu
    ```

    Example output:
    ```console
    Successfully connected to vmi-gpu console. The escape sequence is ^]

    vmi-gpu login: ubuntu
    Password:

    ubuntu@virtual-machine-gpu:~$ lspci -nnk -d 10de:
    08:00.0 3D controller [0302]: NVIDIA Corporation GA102GL [A10] [10de:26b9] (rev a1)
            Subsystem: NVIDIA Corporation GA102GL [A10] [10de:1851]
            Kernel driver in use: nvidia
            Kernel modules: nvidiafb, nvidia_drm, nvidia
    ```

## GPU Sharing for Virtual Machines

GPU passthrough assigns an entire physical GPU to a single VM. To share one GPU between multiple VMs, you need **NVIDIA vGPU**.

### vGPU (Virtual GPU)

NVIDIA vGPU uses mediated devices (mdev) to create virtual GPUs assignable to VMs. This is the only production-ready solution for GPU sharing between VMs.

**Requirements:**
- NVIDIA vGPU license (commercial, purchased from NVIDIA)
- NVIDIA vGPU Manager installed on host nodes

{{% alert color="info" %}}
**Why not MIG?** MIG (Multi-Instance GPU) partitions a GPU into isolated instances, but these are logical divisions within a single PCIe device. VFIO cannot pass them to VMs — MIG only works with containers. To use MIG with VMs, you need vGPU on top of MIG partitions (still requires a license).
{{% /alert %}}

### Open-Source vGPU (Experimental)

NVIDIA is developing open-source vGPU support for the Linux kernel. Once merged, this could enable GPU sharing without a license.

- Status: RFC stage, not merged into mainline kernel
- Supports Ada Lovelace and newer (L4, L40, etc.)
- References: [Phoronix announcement](https://www.phoronix.com/news/NVIDIA-Open-GPU-Virtualization), [kernel patches](https://lore.kernel.org/all/20240922124951.1946072-1-zhiw@nvidia.com/)
