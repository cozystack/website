---
title: "Running Windows VMs in Cozystack"
linkTitle: "Windows VMs"
description: "Running Windows VMs in Cozystack"
weight: 50
aliases:
  - /docs/operations/virtualization/windows
---

Cozystack can run Windows virtual machines.
This guide explains the prerequisites and steps required to boot up a virtual machine running Windows OS.


## Prerequisites

-   Windows installation ISO image.
-   Virtio drivers ISO image.
-   KubeVirt client `virtctl` [installed in your local environment](https://kubevirt.io/user-guide/user_workloads/virtctl_client_tool/)
    and configured for your tenant's namespace.
-   Cozystack version v0.34.2 or later.

## Installation 

Creating a virtual machine running Windows OS starts with creating `VMDisk` objects
and continues with creating a `VMInstance`.

### 1. Create VMDisk objects

You need **three disks**:

1.  **Installation ISO** – optical.
2.  **Virtio drivers ISO** – optical.
3.  **System disk** – non‑optical.

The following example uses minimally recommended storage volumes.

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VMDisk
metadata:
  name: win2k25-iso
spec:
  source:
    http:
      url: https://software-static.download.prss.microsoft.com/dbazure/888969d5-f34g-4e03-ac9d-1f9786c66749/26100.1742.240906-0331.ge_release_svc_refresh_SERVER_EVAL_x64FRE_en-us.iso
  optical: true
  storage: 6Gi
  storageClass: replicated
---
apiVersion: apps.cozystack.io/v1alpha1
kind: VMDisk
metadata:
  name: virtio-drivers
spec:
  source:
    http:
      url: https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso
  optical: true
  storage: 1Gi
  storageClass: replicated
---
apiVersion: apps.cozystack.io/v1alpha1
kind: VMDisk
metadata:
  name: win2k25-system
spec:
  optical: false
  storage: 50Gi
  storageClass: replicated
```

### 2. Create a VMInstance

Pick a **Virtio‑ready** instance profile and attach an empty system disk.
Choose from the available Virtio profiles:

```text
windows.10.virtio
windows.11.virtio
windows.2k16.virtio
windows.2k19.virtio
windows.2k22.virtio
windows.2k25.virtio
```

Create a `VMInstance` object as shown in this example:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VMInstance
metadata:
  name: win2k25-demo
spec:
  running: true
  instanceType: "u1.xlarge"
  instanceProfile: windows.2k25.virtio # picked from the list above
  disks:
    - name: win2k25-system
    - name: win2k25-iso
    - name: virtio-drivers
```

### 3. Install Windows

1.  Open the console using the `virtctl` client:

    ```bash
    virtctl vnc vm-instance-win2k25-demo
    ```

2.  Proceed with the standard Windows setup.

3.  When prompted **"Where do you want to install Windows?"** select **Load driver**,
    then browse to the Virtio CD‑ROM, for example `E:\viostor\amd64\`.

4.  After the virtual disk appears, continue installation and let Windows reboot.

5.  After the first reboot, detach the Windows installation disk (`win2k25-iso`) and Virtio drivers (`virtio-drivers`) from the VMInstance.


## Converting an Existing Windows Image

If you already have a Windows disk produced on VMware, Hyper‑V, or another cloud,
you can follow this path to make it Virtio‑ready in Cozystack.


### 1. Create a dummy VMDisk for Virtio driver

Create a dummy VMDisk which will be used to handle the installation of Virtio driver:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VMDisk
metadata:
  name: dummy-disk-for-virtio
spec:
  optical: false
  storage: "1Gi"
  storageClass: "replicated"
```

### 2. Launch with a drive and non‑Virtio bus

When creating a `VMInstance`, attach your system disk with bus `sata` and the dummy disk with an unspecified bus — 
the disk will then default to the Virtio SCSI bus.
You may also mount the Virtio ISO at the same time to simplify driver installation.

```yaml
spec:
  instanceProfile: windows.2k25.virtio
  disks:
    - name: win2k19-system
      bus: sata
    - name: dummy-disk-for-virtio
    - name: virtio-drivers
      bus: sata
```


### 3. Install Virtio storage drivers

Follow these steps to install Virtio drivers:

1.  Mount `virtio-win.iso` inside the guest.
2.  Run setup wizard to install the drivers
3.  Make sure that driver installation is successful:
    1.  Open the Device Manager
    2.  You should see the SCSI device listed with the exclamation point icon beside it.
    3.  If driver is not installed, right‑click the device and select **Update Driver**.
    4.  Choose **Install the hardware that I manually select from a list**, then **Show All Devices**, then **Next**.
    5.  Click **Have Disk…**, browse to the `.inf`, and finish the wizard.

Alternatively, right‑click the `.inf` in the Explorer and select **Install**.

### 4. Switch to the Virtio bus

Once drivers are installed, you need to switch to the Virtio bus.
Follow these steps:

1.  Power off the VM.
2.  Edit the `VMInstance` and remove the `bus: sata` line from the system disk, as well the dummy disk:

    ```yaml
    spec:
      disks:
        - name: win2k19-system
        #  bus: sata
        #- name: dummy-disk-for-virtio
    ```

3.  Apply the manifest and power the VM back on. Windows should boot normally using Virtio.
4.  The dummy disk can now be removed:

    ```bash
    kubectl delete vmdisk dummy-disk-for-virtio
    ```

## Network MTU considerations

Cozystack sets MTU size to 1400 on every vNIC.
Windows correctly detects this only when using VirtioNet.
With legacy network drivers you may experience packet loss.

To force Windows to respect MTU 1400, run the following commands in PowerShell:

```powershell
# List interfaces
Get-NetIPInterface

# Set MTU permanently
Set-NetIPInterface -InterfaceAlias "Ethernet Instance 0" -NlMtuBytes 1400
```

Using a Virtio profile is strongly recommended.
