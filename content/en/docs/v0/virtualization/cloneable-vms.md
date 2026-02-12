---
title: "Cloneable Virtual Machines"
linkTitle: "Cloneable Virtual Machines"
description: "Creating cloneable virtual machines"
weight: 40
aliases:
  - /docs/virtualization/cloneable-vms
---

To create a cloneable VM, you will need to create a `VMDisk` and a `VMInstance`. This guide uses an `ubuntu` base image
as an example.

1. **Create VMDisk**

   ```yaml
   apiVersion: apps.cozystack.io/v1alpha1
   kind: VMDisk
   metadata:
     name: ubuntu-source
     namespace: tenant-root
   spec:
     optical: false
     source:
       http:
         url: https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
     storage: 20Gi
     storageClass: replicated
   ```

   {{% alert color="info" %}}
   Since expanding a disk can be complicated, we recommend creating it with extra space to accommodate future growth.
   {{% /alert %}}

2. **Create VMInstance**

   Since the `VirtualMachine` custom resource does not provide an easy way to work with multiple disks, use `VMInstance`
   instead.

   Create `VMInstance` using the following template:

   ```yaml
   apiVersion: apps.cozystack.io/v1alpha1
   kind: VMInstance
   metadata:
     name: sourcevm
     namespace: tenant-root
   spec:
     externalMethod: PortList
     disks:
       - name: ubuntu-source
     externalPorts:
       - 22
     instanceProfile: ubuntu
     instanceType: ""
     running: true
     sshKeys:
       - <paste your ssh public key here>
     external: true
     resources:
       cpu: "2"
       memory: 4Gi
   ```

   When VM is created, it will get load balancer external IP address. You can get it using:

   ```bash
   kubectl get svc -n tenant-root vm-instance-sourcevm
   ```

3. **SSH into VM**

   Now you can SSH into VM using the external IP address. Default user for `ubuntu` base image is `ubuntu`.
   ```bash
   ssh ubuntu@<external IP>
   ```

   Configure the virtual machine before cloning.

4. **Delete VMInstance**

   Data on the disk will be preserved.
   ```bash
   kubectl delete vminstance -n tenant-root sourcevm
   ```

5. **Create disk image**
   ```yaml
   apiVersion: cdi.kubevirt.io/v1beta1
   kind: DataVolume
   metadata:
     name: "vm-image-sourcevm" # prefix vm-image is necessary
     namespace: cozy-public # do not change
     annotations:
       cdi.kubevirt.io/storage.bind.immediate.requested: "true"
   spec:
     source:
       pvc:
         name: vm-disk-ubuntu-source
         namespace: tenant-root
     storage:
       resources:
         requests:
           storage: 20Gi
       storageClassName: replicated
   ```

   It will take some time to complete. Wait before continuing.
   You can check the progress using:
   ```bash
   kubectl get datavolume -n cozy-public vm-image-sourcevm
   ```
   Example output when ready:

   ```text
   NAME                PHASE       PROGRESS   RESTARTS   AGE
   vm-image-sourcevm   Succeeded   100.0%                7m32s
   ```

6. **Create VMDisk from cloned image**
   ```yaml
   apiVersion: apps.cozystack.io/v1alpha1
   kind: VMDisk
   metadata:
     name: ubuntu-cloned-1
     namespace: tenant-root
   spec:
     optical: false
     source:
       image:
         name: sourcevm # image name without prefix
     storage: 20Gi # size greater or equal to the disk image size
     storageClass: replicated
   ```

7. **Create VMInstance from cloned disk**
   ```yaml
   apiVersion: apps.cozystack.io/v1alpha1
   kind: VMInstance
   metadata:
     name: cloned-vm
     namespace: tenant-root
   spec:
     external: true
     externalMethod: PortList
     cloudInit: "hostname: my-cloned-vm"
     cloudInitSeed: "1"
     disks:
       - name: ubuntu-cloned-1
     externalPorts:
       - 22
     instanceProfile: ubuntu
     running: true
   ```

   To ensure the cloned VM's network functions correctly, you must override its `hostname` via `.spec.cloudInit` and
   provide a unique `.spec.cloudInitSeed` to prevent conflicts with the source VM.
