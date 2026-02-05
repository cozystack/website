---
title: "Virtualization Features in Cozystack"
linkTitle: "Virtualization"
description: "Everything about deploying, configuring, and using virtual machines in Cozystack."
weight: 50
aliases:
   - /docs/operations/virtualization
   - /docs/operations/virtualization/virtual-machines
---

This guide explains how virtualization works within Cozystack.

## Virtualization Packages

The Cozystack catalog includes three packages related to virtualization:

- `virtual-machine` - Virtual Machine (simple)
- `vm-disk` - Virtual Machine disk
- `vm-instance` - Virtual Machine instance

### Virtual Machine (simple)

This package provides a quick way to create a simple virtual machine.
It allows you to specify the bare minimum parameters to run a VM, but it only supports a single-disk virtual machine.

For production workloads, it is recommended to use `vm-disk` and `vm-instance` instead.

See the application reference: [`virtual-machine`]({{% ref "/docs/virtualization/virtual-machine" %}}).

### Virtual Machine Disk

Before creating a Virtual Machine instance, you need to create a disk from which the VM will boot.

This package defines a virtual machine disk used to store data.
You can use a prepared image (also known as golden image), download an image to the disk via HTTP or upload it from a local image.
You can also create an empty image.

1. **Golden Image**:

   ```yaml
   ## @param source The source image location used to create a disk
   source:
     image:
       name: ubuntu
   ```
    

1. **HTTP:**

   ```yaml
   source:
     http:
       url: "https://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img"
   ```

3. **Upload:**

   ```yaml
   source:
     upload: {}
   ```
   After the disk is created, it will generate a command for uploading using the virtctl tool.

   {{< note >}}
   If you want to let virtctl know about right endpoint for uploading images, you need to configure a cluster to specify an endpoint for it:
   1. Modify your cozystack config map, to enable cdi-uploadproxy along with the dashboard:
      ```bash
      kubectl patch cm -n cozy-system cozystack --type merge -p='{"data":{
        "expose-services": "dashboard,cdi-uploadproxy"
      }}'
      ```

   <!-- TODO: automate this -->
   2. Modify your cozystack config to provide a valid CDI uploadproxy endpoint:
   ```yaml
   values-cdi: |
     uploadProxyURL: https://cdi-uploadproxy.example.org
   ```
   {{< /note >}}

4. **Empty:**

   ```yaml
   source: {}
   ```


Optionally, you can specify that the disk is an optical CD-ROM:

```yaml
optical: true
```

Created disks can be attached to a Virtual Machine instance.

See the application reference: [`vm-disk`]({{% ref "/docs/virtualization/vm-disk" %}}).

### Virtual Machine Instance

This package defines a Virtual Machine instance, which requires specifying the previously created vm-disk.
The first disk is always bootable, and the VM will attempt to boot from it.

```yaml
disks:
- name: example-system
- name: example-data
```

The rest parameters are similar to Virtual Machine (simple).

See the application reference: [`vm-instance`]({{% ref "/docs/virtualization/vm-instance" %}}).

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

