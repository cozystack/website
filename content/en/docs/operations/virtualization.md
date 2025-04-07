---
title: "Virtualization"
linkTitle: "Virtualization"
description: "Virtualization overview"
weight: 40
---

This guide is intended to explain how virtualization works within Cozystack.

The Cozystack catalog includes three packages related to virtualization:

- `virtual-machine` - Virtual Machine (simple)
- `vm-disk` - Virtual Machine disk
- `vm-instance` - Virtual Machine instance

### Virtual Machine (simple)

This package provides a quick way to create a simple virtual machine.
It allows you to specify the bare minimum parameters to run a VM, but it only supports a single-disk virtual machine.

For production workloads, it is recommended to use `vm-disk` and `vm-instance` instead.


### Virtual Machine Disk

Before creating a Virtual Machine instance, you need to create a disk from which the VM will boot.

This package defines a virtual machine disk used to store data. You can download an image to the disk via HTTP or upload it from a local image. You can also create an empty image.

1. **HTTP:**
   
   ```yaml
   source:
     http:
       url: "https://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img"
   ```
   
   
2. **Upload:**
   
   ```yaml
   source:
     upload: {}
   ```
   After the disk is created, it will generate a command for uploading using the virtctl tool.
   
   {{< note >}}
   If you want to let virtctl know about right endpoint for uploading images, you need to configure a cluster to specify an endpoint for it:
   1. Modify your `ingress` application to enable `cni-uploadproxy` option.
      ```bash
      kubectl patch -n tenant-root ingresses.apps.cozystack.io ingress --type=merge -p '{"spec":{
        "cdiUploadProxy": true
      }}'

   <!-- TODO: automate this -->
   2. Modify your cozystack config to provide a valid CDI uploadproxy endpoint:
   ```yaml
   values-cdi: |
     uploadProxyURL: https://cdi-uploadproxy.example.org
   ```
   {{< /note >}}
   
3. **Empty:**
   
   ```yaml
   source: {}
   ```


Optionally, you can specify that the disk is an optical CD-ROM:

```yaml
optical: true
```

Created disks can be attached to a Virtual Machine instance.

### Virtual Machine Instance

This package defines a Virtual Machine instance, which requires specifying the previously created vm-disk.
The first disk is always bootable, and the VM will attempt to boot from it.

```yaml
disks:
- name: example-system
- name: example-data
```

The rest parameters are similar to Virtual Machine (simple)

## Accessing Virtual Machines

You can access the virtual machine using the virtctl tool:
- [KubeVirt User Guide - Virtctl Client Tool](https://kubevirt.io/user-guide/user_workloads/virtctl_client_tool/)

To access the serial console:

```
virtctl console <vm>
```

To access the VM using VNC:

```
virtctl vnc <vm>
```

To SSH into the VM:

```
virtctl ssh <user>@<vm>
```

## Virtual Machine Configuration

You can specify `instanceType` and `instanceProfile` for the virtual machine.

- `instanceType` - defines the size for the Virtual Machine.
- `instanceProfile` - defines the set of preferences for Virtual Machines, according to the OS being used.

You can find more information about these settings below:

## U Series

The U Series is quite neutral and provides resources for
general purpose applications.

*U* is the abbreviation for "Universal", hinting at the universal
attitude towards workloads.

VMs of instance types will share physical CPU cores on a
time-slice basis with other VMs.

### U Series Characteristics

Specific characteristics of this series are:
- *Burstable CPU performance* - The workload has a baseline compute
  performance but is permitted to burst beyond this baseline, if
  excess compute resources are available.
- *vCPU-To-Memory Ratio (1:4)* - A vCPU-to-Memory ratio of 1:4, for less
  noise per node.

## O Series

The O Series is based on the U Series, with the only difference
being that memory is overcommitted.

*O* is the abbreviation for "Overcommitted".

### UO Series Characteristics

Specific characteristics of this series are:
- *Burstable CPU performance* - The workload has a baseline compute
  performance but is permitted to burst beyond this baseline, if
  excess compute resources are available.
- *Overcommitted Memory* - Memory is over-committed in order to achieve
  a higher workload density.
- *vCPU-To-Memory Ratio (1:4)* - A vCPU-to-Memory ratio of 1:4, for less
  noise per node.

## CX Series

The CX Series provides exclusive compute resources for compute
intensive applications.

*CX* is the abbreviation of "Compute Exclusive".

The exclusive resources are given to the compute threads of the
VM. In order to ensure this, some additional cores (depending
on the number of disks and NICs) will be requested to offload
the IO threading from cores dedicated to the workload.
In addition, in this series, the NUMA topology of the used
cores is provided to the VM.

### CX Series Characteristics

Specific characteristics of this series are:
- *Hugepages* - Hugepages are used in order to improve memory
  performance.
- *Dedicated CPU* - Physical cores are exclusively assigned to every
  vCPU in order to provide fixed and high compute guarantees to the
  workload.
- *Isolated emulator threads* - Hypervisor emulator threads are isolated
  from the vCPUs in order to reduce emaulation related impact on the
  workload.
- *vNUMA* - Physical NUMA topology is reflected in the guest in order to
  optimize guest sided cache utilization.
- *vCPU-To-Memory Ratio (1:2)* - A vCPU-to-Memory ratio of 1:2.

## M Series

The M Series provides resources for memory intensive
applications.

*M* is the abbreviation of "Memory".

### M Series Characteristics

Specific characteristics of this series are:
- *Hugepages* - Hugepages are used in order to improve memory
  performance.
- *Burstable CPU performance* - The workload has a baseline compute
  performance but is permitted to burst beyond this baseline, if
  excess compute resources are available.
- *vCPU-To-Memory Ratio (1:8)* - A vCPU-to-Memory ratio of 1:8, for much
  less noise per node.

## RT Series

The RT Series provides resources for realtime applications, like Oslat.

*RT* is the abbreviation for "realtime".

This series of instance types requires nodes capable of running
realtime applications.

### RT Series Characteristics

Specific characteristics of this series are:
- *Hugepages* - Hugepages are used in order to improve memory
  performance.
- *Dedicated CPU* - Physical cores are exclusively assigned to every
  vCPU in order to provide fixed and high compute guarantees to the
  workload.
- *Isolated emulator threads* - Hypervisor emulator threads are isolated
  from the vCPUs in order to reduce emaulation related impact on the
  workload.
- *vCPU-To-Memory Ratio (1:4)* - A vCPU-to-Memory ratio of 1:4 starting from
  the medium size.

## Development

To get started with customizing or creating your own instancetypes and preferences
see [the development guide](/docs/development/development.md).

## Resources

The following instancetype resources are provided by Cozystack:

Name | vCPUs | Memory
-----|-------|-------
cx1.2xlarge  |  8  |  16Gi
cx1.4xlarge  |  16  |  32Gi
cx1.8xlarge  |  32  |  64Gi
cx1.large  |  2  |  4Gi
cx1.medium  |  1  |  2Gi
cx1.xlarge  |  4  |  8Gi
gn1.2xlarge  |  8  |  32Gi
gn1.4xlarge  |  16  |  64Gi
gn1.8xlarge  |  32  |  128Gi
gn1.xlarge  |  4  |  16Gi
m1.2xlarge  |  8  |  64Gi
m1.4xlarge  |  16  |  128Gi
m1.8xlarge  |  32  |  256Gi
m1.large  |  2  |  16Gi
m1.xlarge  |  4  |  32Gi
n1.2xlarge  |  16  |  32Gi
n1.4xlarge  |  32  |  64Gi
n1.8xlarge  |  64  |  128Gi
n1.large  |  4  |  8Gi
n1.medium  |  4  |  4Gi
n1.xlarge  |  8  |  16Gi
o1.2xlarge  |  8  |  32Gi
o1.4xlarge  |  16  |  64Gi
o1.8xlarge  |  32  |  128Gi
o1.large  |  2  |  8Gi
o1.medium  |  1  |  4Gi
o1.micro  |  1  |  1Gi
o1.nano  |  1  |  512Mi
o1.small  |  1  |  2Gi
o1.xlarge  |  4  |  16Gi
rt1.2xlarge  |  8  |  32Gi
rt1.4xlarge  |  16  |  64Gi
rt1.8xlarge  |  32  |  128Gi
rt1.large  |  2  |  8Gi
rt1.medium  |  1  |  4Gi
rt1.micro  |  1  |  1Gi
rt1.small  |  1  |  2Gi
rt1.xlarge  |  4  |  16Gi
u1.2xlarge  |  8  |  32Gi
u1.2xmedium  |  2  |  4Gi
u1.4xlarge  |  16  |  64Gi
u1.8xlarge  |  32  |  128Gi
u1.large  |  2  |  8Gi
u1.medium  |  1  |  4Gi
u1.micro  |  1  |  1Gi
u1.nano  |  1  |  512Mi
u1.small  |  1  |  2Gi
u1.xlarge  |  4  |  16Gi

The following preference resources are provided by Cozystack:

Name | Guest OS
-----|---------
alpine | Alpine
centos.7 | CentOS 7
centos.7.desktop | CentOS 7
centos.stream10 | CentOS Stream 10
centos.stream10.desktop | CentOS Stream 10
centos.stream8 | CentOS Stream 8
centos.stream8.desktop | CentOS Stream 8
centos.stream8.dpdk | CentOS Stream 8
centos.stream9 | CentOS Stream 9
centos.stream9.desktop | CentOS Stream 9
centos.stream9.dpdk | CentOS Stream 9
cirros | Cirros
fedora | Fedora (amd64)
fedora.arm64 | Fedora (arm64)
opensuse.leap | OpenSUSE Leap
opensuse.tumbleweed | OpenSUSE Tumbleweed
rhel.10 | Red Hat Enterprise Linux 10 Beta (amd64)
rhel.10.arm64 | Red Hat Enterprise Linux 10 Beta (arm64)
rhel.7 | Red Hat Enterprise Linux 7
rhel.7.desktop | Red Hat Enterprise Linux 7
rhel.8 | Red Hat Enterprise Linux 8
rhel.8.desktop | Red Hat Enterprise Linux 8
rhel.8.dpdk | Red Hat Enterprise Linux 8
rhel.9 | Red Hat Enterprise Linux 9 (amd64)
rhel.9.arm64 | Red Hat Enterprise Linux 9 (arm64)
rhel.9.desktop | Red Hat Enterprise Linux 9 Desktop (amd64)
rhel.9.dpdk | Red Hat Enterprise Linux 9 DPDK (amd64)
rhel.9.realtime | Red Hat Enterprise Linux 9 Realtime (amd64)
sles | SUSE Linux Enterprise Server
ubuntu | Ubuntu
windows.10 | Microsoft Windows 10
windows.10.virtio | Microsoft Windows 10 (virtio)
windows.11 | Microsoft Windows 11
windows.11.virtio | Microsoft Windows 11 (virtio)
windows.2k16 | Microsoft Windows Server 2016
windows.2k16.virtio | Microsoft Windows Server 2016 (virtio)
windows.2k19 | Microsoft Windows Server 2019
windows.2k19.virtio | Microsoft Windows Server 2019 (virtio)
windows.2k22 | Microsoft Windows Server 2022
windows.2k22.virtio | Microsoft Windows Server 2022 (virtio)
windows.2k25 | Microsoft Windows Server 2025
windows.2k25.virtio | Microsoft Windows Server 2025 (virtio)


## Virtual Routers

Starting with version [v0.27.0](https://github.com/cozystack/cozystack/releases/tag/v0.27.0),
Cozystack can deploy virtual routers (also known as "router appliances" or "middlebox appliances").
This feature allows you to create a virtual router based on a virtual machine instance.
The virtual router can route traffic between different networks.

### Creating a Virtual Router

Creating a virtual router requires a Cozystack administrator account.

1.  **Create a VM Instance**<br/>
    Use the standard `vm-instance` and `virtual-machine` packages to create a virtual machine instance.
    
1.  **Disable Anti-Spoofing Protection**<br/>
    To act as a virtual router, the VM instance should have anti-spoofing protection disabled:

    ```bash
    kubectl patch virtualmachines.kubevirt.io virtual-machine-example --type=merge \
        -p '{"spec":{"template":{"metadata":{"annotations":{"ovn.kubernetes.io/port_security": "false"}}}}}'
    ```

1.  **Restart the Virtual Machine**

    ```bash
    virtctl stop virtual-machine-example
    virtctl start virtual-machine-example
    ```

1.  **Retrieve the IP Address of the VM**

    ```bash
    kubectl get vmi
    ```

    The output will have a line with the new VM's IP address:

    ```console
    NAME                      AGE     PHASE     IP            NODENAME        READY
    virtual-machine-example   3d4h    Running   10.244.8.56   gld-csxhk-003   True
    ```

1.  **Configure Custom Routes for a Tenant**<br/>
    Edit the tenant namespace:

    ```bash
    kubectl edit namespace tenant-example
    ```

    Add the following annotation using the router IP you found earlier as `gw`
    and the subnet mask for the router to handle as `dst`:
    
    ```yaml
    ovn.kubernetes.io/routes: |
      [{
        "gw": "10.244.8.56",
        "dst": "10.10.13.0/24"
      }]
    ```

These custom routes will now be applied to all pods within the tenant namespace.
