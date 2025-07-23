---
title: "Running VMs with GPU Passthrough"
linkTitle: "GPU Passthrough"
description: "Running VMs with GPU Passthrough"
weight: 40
aliases:
  - /docs/operations/virtualization/gpu
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

2.  Enable the GPU Operator bundle in your Cozystack configuration:

    ```bash
    kubectl edit -n cozy-system configmap cozystack
    ```

3.  Add `gpu-operator` to the list of bundle-enabled packages:

    ```yaml
    bundle-enable: gpu-operator
    ```
    This will deploy the components (operands).

4.  Ensure all pods are in a running state and all validations succeed with the sandbox-validator component:

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

To verify the GPU binding, access the node using `kubectl debug node` or `kubectl node-shell -x` and run:

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

## 2. Update the KubeVirt Custom Resource

Next, we will update the KubeVirt Custom Resource, as documented in the
[KubeVirt user guide](https://kubevirt.io/user-guide/virtual_machines/host-devices/#listing-permitted-devices),
so that the passthrough GPUs are permitted and can be requested by a KubeVirt VM.

Adjust the `pciVendorSelector` and `resourceName` values to match your specific GPU model.
Setting `externalResourceProvider=true` indicates that this resource is provided by an external device plugin,
in this case the `sandbox-device-plugin` which is deployed by the Operator.

```bash
kubectl edit kubevirt -n cozy-kubevirt
```
example config:
```yaml
  ...
  spec:
    configuration:
      permittedHostDevices:
        pciHostDevices:
        - externalResourceProvider: true
          pciVendorSelector: 10DE:2236
          resourceName: nvidia.com/GA102GL_A10
  ...
```

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
