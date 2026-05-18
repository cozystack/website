---
title: "Creating and Using Named VM Images"
linkTitle: "Golden Images"
description: "Guide to creating, managing, and using golden (named) VM images in Cozystack to speed up virtual machine deployment."
weight: 35
---

<!--
https://app.read.ai/analytics/meetings/01K0BTTJ1VMJHJ6A5FVV81A3PD
-->

Golden images in Cozystack allow administrators to prepare **named operating system images** that users can later reuse when creating virtual machines.  
This guide explains the benefits of golden images, how to create them, and how to use them when deploying VMs.

By default, every time a user creates a virtual machine, Cozystack downloads the required image from its source URL.  
This can become a bottleneck when multiple VMs are created in quick succession.  
Golden images solve this problem by caching the image locally, eliminating repeated downloads and speeding up deployment.

## Naming Conventions (Important)

Cozystack automatically adds prefixes to internal Kubernetes resources:

| User-visible name | Resource Kind | Actual resource name |
|-------------------|---------------|----------------------|
| `<image>`         | DataVolume in `cozy-public` (golden image) | `vm-default-images-<image>` |
| `<disk>`          | DataVolume created from VMDisk             | `vm-disk-<disk>`   |
| `<vm>`            | VirtualMachine created from VMInstance     | `vm-instance-<vm>` |

This means if you create a VMInstance named `ubuntu`, the VirtualMachine in Kubernetes will be `vm-instance-ubuntu`.

## Default Image Collection

Cozystack ships with the **`vm-default-images`** system package that automatically provisions a curated collection of OS images in the `cozy-public` namespace.
No manual setup is required — images become available as soon as the package is installed.

The default collection includes:

| Image name | Description |
|---|---|
| `ubuntu-20.04` | Ubuntu 20.04 LTS (Focal Fossa) |
| `ubuntu-22.04` | Ubuntu 22.04 LTS (Jammy Jellyfish) |
| `ubuntu-24.04` | Ubuntu 24.04 LTS (Noble Numbat) |
| `debian-12` | Debian 12 (Bookworm) |
| `debian-13` | Debian 13 (Trixie) |
| `rocky-8` | Rocky Linux 8 |
| `rocky-9` | Rocky Linux 9 |
| `rocky-10` | Rocky Linux 10 |
| `almalinux-8` | AlmaLinux 8 |
| `almalinux-9` | AlmaLinux 9 |
| `almalinux-10` | AlmaLinux 10 |
| `centos-stream-9` | CentOS Stream 9 |
| `centos-stream-10` | CentOS Stream 10 |
| `opensuse-leap-15.6` | openSUSE Leap 15.6 |
| `opensuse-leap-16.0` | openSUSE Leap 16.0 |
| `alpine-3.21` | Alpine Linux 3.21 |

You can list all available images with:
```bash
kubectl -n cozy-public get dv -l app.kubernetes.io/managed-by=cozystack
```

## Adding Custom Golden Images

Creating additional named VM images requires an administrator account in Cozystack.

The simplest way to add a custom image is by using the CLI script.  
The [`cdi_golden_image_create.sh`](https://github.com/cozystack/cozystack/blob/{{< version-pin "cozystack_tag" >}}/hack/cdi_golden_image_create.sh) script can be downloaded from the Cozystack {{< version-pin "cozystack_tag" >}} release tag:

```bash
wget https://raw.githubusercontent.com/cozystack/cozystack/{{< version-pin "cozystack_tag" >}}/hack/cdi_golden_image_create.sh
chmod +x cdi_golden_image_create.sh
```

This script uses your `kubectl` configuration.  
Before running it, ensure that your configuration points to the target Cozystack cluster.

To add a custom image, run the script with the image name and its URL:

```bash
cdi_golden_image_create.sh '<name>' 'https://<image-url>'
```

For example, to add a Talos image:

```bash
cdi_golden_image_create.sh 'talos' 'https://github.com/siderolabs/talos/releases/download/v1.7.6/nocloud-amd64.raw.xz'
```

Internally, the script creates a Kubernetes resource of `kind: DataVolume` in the `cozy-public` namespace.  
The resource name is the image name prefixed with `vm-default-images-`.  
For example, the resource `vm-default-images-talos` creates an image accessible as `talos`.

You can track progress with:
```bash
kubectl -n cozy-public get dv
kubectl -n cozy-public describe dv vm-default-images-talos
```

## Using Golden Images

### Creating a VMDisk from a Golden Image

To use a golden image as the source for a VM disk, create a VMDisk with `source.image.name` referencing the image name:

```bash
kubectl -n tenant-root create -f- <<EOF
apiVersion: apps.cozystack.io/v1alpha1
kind: VMDisk
metadata:
  name: ubuntu
spec:
  source:
    image:
      name: ubuntu-24.04
  storage: 20Gi
EOF
```

You can monitor the process using the following commands:
```bash
kubectl -n tenant-root get vmdisk
kubectl -n tenant-root get dv
kubectl -n tenant-root describe dv vm-disk-ubuntu
```

### Attaching the Disk to a VM

Next, create a VMInstance that uses the disk:
```bash
kubectl -n tenant-root create -f- <<EOF
apiVersion: apps.cozystack.io/v1alpha1
kind: VMInstance
metadata:
  name: ubuntu
spec:
  disks:
  - name: ubuntu
EOF
```

You can check the status of the VirtualMachine with:
```bash
kubectl get vm -n tenant-root
```

To connect to the VM, run:
```bash
virtctl console vm-instance-ubuntu -n tenant-root
```
