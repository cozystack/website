---
title: "Running Windows VMs in Cozystack"
linkTitle: "Windows VMs"
description: "Running Windows VMs in Cozystack"
weight: 15
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

### 1. Launch with a non‑Virtio profile

When creating a VMInstance, choose the matching *legacy* profile and attach your imported system disk:

```text
windows.10
windows.11
windows.2k16
windows.2k19
windows.2k22
windows.2k25
```

You may also mount the Virtio ISO at the same time to simplify driver installation.

### 2. Install Virtio storage drivers

Follow these steps to install Virtio drivers:

1.  Mount `virtio-win.iso` inside the guest.
2.  Copy **vioscsi.inf** and **viostor.inf** to an accessible folder.
3.  For each driver file:
    
    1.  Press `Win+R` and run `hdwwiz.exe`.
    2.  Choose **Install the hardware that I manually select from a list**, then **Show All Devices**, then **Next**.
    3.  Click **Have Disk…**, browse to the `.inf`, and finish the wizard.
    
    Alternatively, right‑click the `.inf` in the Explorer and select **Install**.
 
5. Add the drivers to the CriticalDeviceDatabase so Windows can boot from a Virtio disk:

```reg
[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CriticalDeviceDatabase\PCI#VEN_1AF4&DEV_1004&SUBSYS_00081AF4&REV_00]
"ClassGUID"="{4D36E97B-E325-11CE-BFC1-08002BE10318}"
"Service"="vioscsi"

[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CriticalDeviceDatabase\PCI#VEN_1AF4&DEV_1001&SUBSYS_00021AF4&REV_00]
"ClassGUID"="{4D36E97B-E325-11CE-BFC1-08002BE10318}"
"Service"="viostor"
```

*Tip:* Open the `.inf` file in Notepad and search for **ClassGUID** to confirm the value for your OS version.

### 3. Switch to the Virtio profile

1.  Power off the VM.
2.  Edit the `VMInstance` and change the config:

    ```yaml
    spec:
      instanceProfile: windows.2k25.virtio
    ```

3. Apply the manifest and power the VM back on. Windows should boot normally using Virtio.


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
