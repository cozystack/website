---
title: "Virtual Machine Resources"
linkTitle: "Resources Reference"
description: "Reference for VM Instance Types and Instance Profiles"
weight: 60
aliases:
  - /docs/operations/virtualization/resources
---

Each virtual machine has these two configuration settings:

- `instanceType` defines the resourced provided to the Virtual Machine.
- `instanceProfile` defines the set of preferences for Virtual Machines, according to the OS being used.

## Instance Type Resources

### Reference table

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


### U Series

The U Series is quite neutral and provides resources for
general purpose applications.

*U* is the abbreviation for "Universal", hinting at the universal
attitude towards workloads.

VMs of instance types will share physical CPU cores on a
time-slice basis with other VMs.

Specific characteristics of this series are:
- *Burstable CPU performance* - The workload has a baseline compute
  performance but is permitted to burst beyond this baseline, if
  excess compute resources are available.
- *vCPU-To-Memory Ratio (1:4)* - A vCPU-to-Memory ratio of 1:4, for less
  noise per node.

### O Series

The O Series is based on the U Series, with the only difference
being that memory is overcommitted.

*O* is the abbreviation for "Overcommitted".

Specific characteristics of this series are:
- *Burstable CPU performance* - The workload has a baseline compute
  performance but is permitted to burst beyond this baseline, if
  excess compute resources are available.
- *Overcommitted Memory* - Memory is over-committed in order to achieve
  a higher workload density.
- *vCPU-To-Memory Ratio (1:4)* - A vCPU-to-Memory ratio of 1:4, for less
  noise per node.

### CX Series

The CX Series provides exclusive compute resources for compute
intensive applications.

*CX* is the abbreviation of "Compute Exclusive".

The exclusive resources are given to the compute threads of the
VM. In order to ensure this, some additional cores (depending
on the number of disks and NICs) will be requested to offload
the IO threading from cores dedicated to the workload.
In addition, in this series, the NUMA topology of the used
cores is provided to the VM.

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

### M Series

The M Series provides resources for memory intensive
applications.

*M* is the abbreviation of "Memory".

Specific characteristics of this series are:
- *Hugepages* - Hugepages are used in order to improve memory
  performance.
- *Burstable CPU performance* - The workload has a baseline compute
  performance but is permitted to burst beyond this baseline, if
  excess compute resources are available.
- *vCPU-To-Memory Ratio (1:8)* - A vCPU-to-Memory ratio of 1:8, for much
  less noise per node.

### RT Series

The RT Series provides resources for realtime applications, like Oslat.

*RT* is the abbreviation for "realtime".

This series of instance types requires nodes capable of running
realtime applications.

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

## Instance Profile Resources

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


## Developing Instance Types and Profiles

To get started with customizing or creating your own instancetypes and preferences
see [the development guide](/docs/development/development.md).

