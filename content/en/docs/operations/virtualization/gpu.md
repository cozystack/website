---
title: "Running VMs with GPU Passthrough"
linkTitle: "GPU Passthrough"
description: "Running VMs with GPU Passthrough"
weight: 40
---

This section runs through the deployment scenario of running VMs with GPU Passthrough.
We will first deploy the GPU Operator, such that our worker node will be provisioned for GPU Passthrough,
then we will deploy a KubeVirt VM which requests a GPU.

By default, to provision GPU Passthrough, the GPU Operator will deploy the following components:

- **VFIO Manager** - to bind `vfio-pci` driver to all GPUs on the node
- **Sandbox Device Plugin** - to discover and advertise the passthrough GPUs to kubelet
- **Sandbox Validator** - to validate the other operands

## 1. Install the GPU Operator

Follow the below steps.

Label the worker node explicitly for GPU passthrough workloads:

```bash
kubectl label node <node-name> --overwrite nvidia.com/gpu.workload.config=vm-passthrough
```

Install the GPU Operator, by enabling the GPU operator bundle in your Cozystack configuration.

```bash
kubectl edit -n cozy-system configmap cozystack-config
```

Add `gpu-operator` to the list of bundle-enabled packages:

```yaml
bundle-enable: gpu-operator
```

The following operands get deployed. Ensure all pods are in a running state and all validations succeed with the sandbox-validator component:

```bash
kubectl get pods -n cozy-gpu-operator
```

Example output:

```console
NAME                                            READY   STATUS    RESTARTS   AGE
...
nvidia-sandbox-device-plugin-daemonset-4mxsc    1/1     Running   0          40s
nvidia-sandbox-validator-vxj7t                  1/1     Running   0          40s
nvidia-vfio-manager-thfwf                       1/1     Running   0          78s
```

You can use `kubectl debug node` or `kubectl node-shell -x` to access the node and check the GPU status.

```bash
lspci --nnk -d 10de:
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

The sandbox-device-plugin will discover and advertise these resources to kubelet. In this example, we have two A10 GPUs:

```bash
# kubectl describe node <node-name>
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
The resource name is currently constructed by joining the device and device_name columns from the [PCI IDs database](https://pci-ids.ucw.cz/v2.2/pci.ids).
For example, the entry for A10 in the database reads `2236  GA102GL [A10]`, which results in a resource name `nvidia.com/GA102GL_A10`.
{{% /alert %}}

## 2. Update the KubeVirt CR

Next, we will update the KubeVirt Custom Resource, as documented in the [KubeVirt user guide](https://kubevirt.io/user-guide/virtual_machines/host-devices/#listing-permitted-devices),
so that the passthrough GPUs are permitted and can be requested by a KubeVirt VM.
Note, replace the values for `pciVendorSelector` and `resourceName` to correspond to your GPU model.
We set `externalResourceProvider=true` to indicate that this resource is being provided by an external device plugin,
in this case the `sandbox-device-plugin` which is deployed by the Operator.

```yaml
kubectl edit kubevirt -n kubevirt
  ...
  spec:
    permittedHostDevices:
      pciHostDevices:
      - externalResourceProvider: true
        pciVendorSelector: 10DE:2236
        resourceName: nvidia.com/GA102GL_A10
  ...
```

## 3. Create a VM

We are now ready to create a VM. Let’s create a sample VM using a simple VMI spec which requests a `nvidia.com/GA102GL_A10` resource:

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
  - name: nvidia.com/AD102GL_L40S
  cloudInit: |
    #cloud-config
    password: ubuntu
    chpasswd: { expire: False }
```

```console
# kubectl apply -f vmi-gpu.yaml
virtualmachines.apps.cozystack.io/gpu created

# k get vmi
NAME                       AGE   PHASE     IP             NODENAME        READY
virtual-machine-gpu        73m   Running   10.244.3.191   luc-csxhk-002   True
```

Let’s console into the VM and verify we have a GPU:
```console
# virtctl console virtctl console virtual-machine-gpu
Successfully connected to vmi-gpu console. The escape sequence is ^]

vmi-gpu login: ubuntu
Password:

ubuntu@virtual-machine-gpu:~$ lspci -nnk -d 10de:
08:00.0 3D controller [0302]: NVIDIA Corporation AD102GL [L40S] [10de:26b9] (rev a1)
        Subsystem: NVIDIA Corporation AD102GL [L40S] [10de:1851]
        Kernel driver in use: nvidia
        Kernel modules: nvidiafb, nvidia_drm, nvidia
```
