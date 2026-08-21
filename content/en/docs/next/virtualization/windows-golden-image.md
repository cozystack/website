---
title: "Building a Windows Golden Image with Packer"
linkTitle: "Windows Golden Images"
description: "How to build a customized Windows Server golden image (pre-installed software, autologon, RDP) with Packer and register it in Cozystack as a reusable VM image."
weight: 55
---

[Running Windows VMs]({{% ref "windows.md" %}}) shows how to boot and install a Windows VM by hand (including the Virtio drivers). This guide is the automated counterpart: it bakes a Windows Server install plus your software and configuration into **one reusable image** with [Packer](https://www.packer.io/), so every VM clones from a prepared disk instead of being installed from scratch.

The [Golden Images]({{% ref "vm-image.md" %}}) guide covers *named* images cached from an HTTP(S) URL — the `vm-default-images` collection and custom entries added with `cdi_golden_image_create.sh`. That model fits cloud images that already exist as a single downloadable disk (most Linux cloud images do). A customized Windows image cannot be expressed as a plain download URL, so you build it with Packer against the KubeVirt builder, capture the configured disk, and register that disk instead.

## When to use this

- The image needs software or configuration baked in (an application, drivers, agents, autologon), so a bare cloud-image URL will not do.
- An installer is interactive or licensed and cannot be scripted end-to-end.
- You want one prepared Windows disk that many VMs clone from, instead of re-installing per VM.

For a bare, unmodified base that *is* reachable by URL, prefer the simpler [`vm-default-images`]({{% ref "vm-image.md" %}}) path instead.

## Prerequisites

- `packer`.
- A `KUBECONFIG` pointing at the target cluster, with access to a tenant namespace (e.g. `tenant-root`).
- The Windows installation ISO staged as a DataVolume, so the builder can boot from it:

```bash
kubectl apply -f win2022-iso-dv.yaml
```

## The KubeVirt builder plugin

Packer creates the VM on the cluster with the **KubeVirt builder** — the published plugin [`github.com/hashicorp/kubevirt`](https://github.com/hashicorp/packer-plugin-kubevirt), which provides the `kubevirt-iso` builder for both Linux and Windows. Declare it in `required_plugins` (see the template below) and install it with `packer init` — no manual download.

The plugin repository has a [Windows `kubevirt-iso` example](https://github.com/hashicorp/packer-plugin-kubevirt/tree/main/examples/builder/kubevirt-iso/windows) that this guide follows.

## The Packer template

A minimal `windows.pkr.hcl` has three parts: the plugin requirement, a `source` describing the VM and how Packer connects to it (WinRM), and a `build` listing the provisioners.

```hcl
packer {
  required_plugins {
    kubevirt = {
      # Published plugin — `packer init` installs it automatically.
      source  = "github.com/hashicorp/kubevirt"
      version = ">= 0.9.0"
    }
  }
}

source "kubevirt-iso" "windows" {
  kube_config = var.kube_config
  name        = var.image_name
  namespace   = var.namespace

  iso_volume_name = "windows-2022-x86-64-iso"   # the DataVolume you applied above

  disk_size          = "32Gi"
  instance_type      = "u1.large"
  instance_type_kind = "virtualmachineclusterinstancetype"
  preference         = "windows.2k22.virtio"
  preference_kind    = "virtualmachineclusterpreference"
  os_type            = "windows"

  networks {
    name = "default"
    pod {}
  }

  # Files placed on the setup CD. Windows Setup auto-reads autounattend.xml;
  # the scripts run at first boot and enable WinRM so Packer can connect.
  media_files = [
    "./autounattend.xml",
    "./scripts/enable-winrm.ps1",
    "./scripts/set-network.ps1",
  ]

  boot_command              = ["<wait1>"]   # press a key to boot from the install CD
  boot_wait                 = "5s"
  installation_wait_timeout = "20m"

  communicator       = "winrm"
  winrm_host         = "127.0.0.1"
  winrm_local_port   = 5000
  winrm_remote_port  = 5985
  winrm_username     = "Administrator"
  winrm_password     = var.build_password    # must match autounattend.xml
  winrm_wait_timeout = "45m"
}

build {
  sources = ["source.kubevirt-iso.windows"]

  # Confirm the WinRM connection is up.
  provisioner "powershell" {
    inline = ["(Get-CimInstance Win32_OperatingSystem).Caption"]
  }

  # Your software + guest configuration — replace with what you need baked in.
  provisioner "powershell" { script = "./scripts/install-software.ps1" }
  provisioner "powershell" { script = "./scripts/configure-guest.ps1" }     # RDP, disable sleep, etc.
  provisioner "powershell" { script = "./scripts/configure-autologon.ps1" } # optional: logged-in desktop on boot

  # FINAL provisioner — keep it last. Reverts the build-time WinRM/RDP
  # relaxations and strips any baked autologon password, so nothing weakened
  # from the build ships in the golden.
  provisioner "powershell" { script = "./scripts/harden.ps1" }
}
```

Declare the variables in `variables.pkr.hcl`:

```hcl
variable "kube_config" {
  type    = string
  default = "${env("KUBECONFIG")}"
}

variable "namespace" {
  type    = string
  default = "tenant-root"
}

variable "image_name" {
  type    = string
  default = "windows"
}

variable "build_password" {
  type      = string
  sensitive = true
  default   = "REPLACE_ME_BUILD_PW"   # throwaway; must match autounattend.xml
}
```

## The answer file (`autounattend.xml`)

Windows Setup reads `autounattend.xml` from the media CD and installs unattended. Two things matter for the build:

- It sets the **Administrator password** to the same value as `var.build_password` — that is how Packer's WinRM communicator authenticates.
- It runs `enable-winrm.ps1` at first logon, which opens WinRM (basic + unencrypted, port 5985) so Packer can connect. These relaxations are **temporary** — `harden.ps1` reverts them before the golden is captured.

The password in `autounattend.xml` is a build-time placeholder, not a real secret — see the note below.

## Run the build

```bash
export KUBECONFIG=/path/to/kubeconfig
export PKR_VAR_build_password='<throwaway-build-password>'   # must match autounattend.xml
packer init .    # installs the KubeVirt builder plugin
packer build .
```

Packer boots the VM from the ISO, waits for WinRM, runs the provisioners in order, and shuts the VM down. If any of your installers is **not silent** (cannot be scripted), install it interactively instead: RDP into the running VM (autologon gives you a logged-in desktop), install and verify through its GUI, then sign out and let the build continue to `harden.ps1`. When the build finishes, capture the VM disk as the golden.

{{% alert title="Never bake credentials or licences" color="warning" %}}

The build-time Administrator/WinRM password is a throwaway placeholder in `autounattend.xml` and `variables.pkr.hcl` — change it per build and reset it at deploy. The autologon password is not baked: inject it at deploy time or use Sysinternals `Autologon.exe` (which stores it as an encrypted LSA secret). Any application credentials are entered by hand in the running VM, never committed to the image or to Git.

{{% /alert %}}

{{% alert title="Sysprep on evaluation media" color="warning" %}}

On the Windows Server evaluation ISO, `sysprep /generalize` can crash (`spopk.dll`). If it does, capture the golden **without** generalize — but then clones share the same SID and computer name, which is acceptable only for a single VM; assign a unique name per clone if you run several. A purchased licence and non-evaluation media are required for production use.

{{% /alert %}}

## Register the image in Cozystack

Once you have a captured Windows disk, make it reusable one of two ways:

- **As a named image you clone per VM (recommended for customized disks).** Capture the prepared disk into a `vm-image-<name>` DataVolume in the `cozy-public` namespace, then create each `VMDisk` from it via `source.image.name` — the full flow is in [Cloneable Virtual Machines]({{% ref "cloneable-vms.md" %}}). This is the right choice for a customized Windows image, whose disk is not a single public URL. The clone strategy (a storage smart-clone vs a host-assisted copy) is chosen by CDI and the storage backend, not set in the manifest; on some backends a smart-clone can report `Succeeded` while leaving the target empty, so verify the cloned DataVolume both reaches `Succeeded` and actually contains data before relying on it. If it comes up empty, set the annotation `cdi.kubevirt.io/cloneType: copy` on the `vm-image-<name>` DataVolume to force a host-assisted, byte-for-byte copy — it either populates the target or fails loudly instead of silently succeeding.
- **As a `vm-default-images` collection entry.** This path caches an image from a public HTTP(S) URL — see [Golden Images]({{% ref "vm-image.md" %}}). It suits a *bare* base image reachable by URL, not a customized captured disk.

## Create and access the VM

Create a `VMInstance` from a cloned Windows disk, setting the Windows preference and an instance type explicitly (otherwise the VM defaults to the `ubuntu` profile and boots Windows with the wrong devices and scheduling):

```bash
kubectl -n tenant-root create -f- <<EOF
apiVersion: apps.cozystack.io/v1alpha1
kind: VMInstance
metadata:
  name: windows
spec:
  instanceProfile: windows.2k22.virtio
  instanceType: u1.large
  disks:
  - name: windows
EOF
```

Access the desktop over VNC or an RDP port-forward:

```bash
virtctl vnc vm-instance-windows -n tenant-root
# or forward RDP (3389) and connect with an RDP client
```

Autologon lands you on a ready desktop.

{{% alert title="Stopping the VM" color="info" %}}

Stop a Windows VM built this way with `virtctl stop --force` — a graceful ACPI stop does not always work reliably on it.

{{% /alert %}}
