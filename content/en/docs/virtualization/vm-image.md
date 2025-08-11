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

## Creating Golden Images

Creating named VM images (golden images) requires an administrator account in Cozystack.

The simplest way to create named VM images is by using the CLI script.  
The [`cdi_golden_image_create.sh`](https://github.com/cozystack/cozystack/blob/main/hack/cdi_golden_image_create.sh) script can be downloaded from the Cozystack repository:

```bash
wget https://github.com/cozystack/cozystack/blob/main/hack/cdi_golden_image_create.sh
chmod +x cdi_golden_image_create.sh
```

This script uses your `kubectl` configuration.  
Before running it, ensure that your configuration points to the target Cozystack cluster.

To create a named image, or to download one of the default images, run the script with the image name and its URL:

```bash
cdi_golden_image_create.sh '<name>' 'https://<image-url>'
```

For example, all five default images, available with the `virtual-machine` application, can be downloaded for faster use:

```bash
cdi_golden_image_create.sh 'ubuntu' 'https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img'
cdi_golden_image_create.sh 'fedora' 'https://download.fedoraproject.org/pub/fedora/linux/releases/40/Cloud/x86_64/images/Fedora-Cloud-Base-Generic.x86_64-40-1.14.qcow2'
cdi_golden_image_create.sh 'cirros' 'https://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img'
cdi_golden_image_create.sh 'alpine' 'https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/cloud/nocloud_alpine-3.20.2-x86_64-bios-tiny-r0.qcow2'
cdi_golden_image_create.sh 'talos' 'https://github.com/siderolabs/talos/releases/download/v1.7.6/nocloud-amd64.raw.xz'
```

Internally, the script creates Kubernetes resources of `kind: DataVolume` in the `cozy-public` namespace.
The resource name is the disk’s name prefixed with `vm-image-`.
For example, the resource `vm-image-ubuntu` creates a saved image named `ubuntu`.


## Using Golden Images

### Simple Virtual Machine

Simple virtual machines (deployed with the `virtual-machine` application in Cozystack) already include a set of predefined named disk images.
By default, users can choose from `ubuntu`, `fedora`, `cirros`, `alpine`, and `talos`.

These images are named but, in the default configuration, they are downloaded each time a VM is created.
Using golden images allows these files to be downloaded once and stored locally, significantly speeding up VM deployment.

To use a named VM image, specify the image name in `systemDisk.image` as you normally would:

```yaml
systemDisk:
  image: ubuntu
  storage: 5Gi
  storageClass: replicated
```

### Virtual Machine and VM-disk

Regular virtual machines (`vm-instance`) require a `vm-disk`, which has several options for image source.
To use a named VM image, use the `source.image.name`

```yaml               
## @param source The source image location used to create a disk
source:
  image:
    name: ubuntu
```