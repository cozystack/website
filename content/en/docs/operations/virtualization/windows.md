---
title: "Running Windows VMs in Cozystack"
linkTitle: "Windows"
description: "Running Windows VMs in Cozystack"
weight: 50
----------

## Prerequisites

* `virtctl` installed in your local environment.
* Two ISO images:
  * **Windows installation media**
  * **Virtio drivers**

---

## Installation

### Create the VMDisk objects

You need **three disks**:
1. **Installation ISO** – optical.
2. **Virtio drivers ISO** – optical.
3. **System disk** – non‑optical.

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

### Create the VMInstance

Pick a **Virtio‑ready** instance profile and attach an empty system disk:

Available Virtio profiles:

```
windows.10.virtio
windows.11.virtio
windows.2k16.virtio
windows.2k19.virtio
windows.2k22.virtio
windows.2k25.virtio
```

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VMInstance
metadata:
  name: win2k25-demo
spec:
  running: true
  instanceType: "u1.xlarge"
  instanceProfile: windows.2k25.virtio
  disks:
    - name: win2k25-system
    - name: win2k25-iso
    - name: virtio-drivers
```


### Install Windows

1. Open a console:

   ```bash
   virtctl vnc vm-instance-win2k25-demo
   ```

2. Proceed with the standard Windows setup.

3. When prompted **“Where do you want to install Windows?”** select **Load driver** → browse to the Virtio CD‑ROM (e.g. `E:\viostor\amd64\`).

4. After the virtual disk appears, continue installation and let Windows reboot.

5. After the first reboot, detach the Windows installation disk (`win2k25-iso`) and virtio drivers (`virtio-drivers`) from the VMInstance.


## Converting an Existing Windows Image

Already have a Windows disk produced on VMware®, Hyper‑V™, or another cloud? Follow this path to make it Virtio‑ready in Cozystack.

### Launch with a non‑Virtio profile

Choose the matching *legacy* profile and attach your imported system disk.

```
windows.10
windows.11
windows.2k16
windows.2k19
windows.2k22
windows.2k25
```

> You may also mount the Virtio ISO at the same time to simplify driver installation.

### Install Virtio storage drivers

Below is the proven procedure from Alibaba Cloud’s conversion guide (works unchanged on Cozystack).

**Step‑by‑step driver injection**

1. Mount `virtio-win.iso` inside the guest.
2. Copy **vioscsi.inf** and **viostor.inf** to an accessible folder.
3. For each driver file:

   1. Press <kbd>Win + R</kbd>, run `hdwwiz.exe`.
   2. Choose **Install the hardware that I manually select from a list** → **Show All Devices** → **Next**.
   3. Click **Have Disk…**, browse to the `.inf`, and finish the wizard.
   4. Alternatively, right‑click the `.inf` in Explorer and select **Install**.
4. Add the drivers to the CriticalDeviceDatabase so Windows can boot from a Virtio disk:

```reg
[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CriticalDeviceDatabase\PCI#VEN_1AF4&DEV_1004&SUBSYS_00081AF4&REV_00]
"ClassGUID"="{4D36E97B-E325-11CE-BFC1-08002BE10318}"
"Service"="vioscsi"

[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CriticalDeviceDatabase\PCI#VEN_1AF4&DEV_1001&SUBSYS_00021AF4&REV_00]
"ClassGUID"="{4D36E97B-E325-11CE-BFC1-08002BE10318}"
"Service"="viostor"
```

*Tip:* Open the `.inf` file in Notepad and search for **ClassGUID** to confirm the value for your OS version.

### Switch to the Virtio profile

1. Power off the VM.
2. Edit the `VMInstance` and change

```yaml
spec:
  instanceProfile: windows.2k25.virtio
```

3. Apply the manifest and power the VM back on. Windows should boot normally using Virtio.


### Network MTU considerations

Cozystack sets **MTU 1400** on every vNIC. Windows correctly detects this only when using **VirtioNet**. With legacy network drivers you may experience packet loss.

To force Windows to respect MTU 1400:

```powershell
# List interfaces
Get-NetIPInterface

# Set MTU permanently
Set-NetIPInterface -InterfaceAlias "Ethernet Instance 0" -NlMtuBytes 1400
```

Using a Virtio profile is strongly recommended.
