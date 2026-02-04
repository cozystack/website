---
title: "Migrating Virtual Machines from Proxmox"
linkTitle: "Proxmox Migration"
description: "Step-by-step guide to migrating virtual machines from Proxmox VE to Cozystack"
weight: 65
---

This guide describes the process of migrating virtual machines from Proxmox VE to Cozystack by exporting VM disk images and uploading them to the target environment.

{{< note >}}
Migration is performed by exporting VM disks to files and uploading them to Cozystack.
VM state and snapshots are not preserved during migration.
{{< /note >}}

## Prerequisites

Before starting the migration, ensure you have:

1. **KubeVirt client `virtctl`** installed on your local machine:
   - Installation guide: [KubeVirt User Guide - Virtctl Client Tool](https://kubevirt.io/user-guide/user_workloads/virtctl_client_tool/)

2. **Upload proxy access configured** in your Cozystack cluster:
   - Modify your Cozystack ConfigMap to enable `cdi-uploadproxy`:
     ```bash
     kubectl patch cm -n cozy-system cozystack --type merge -p='{"data":{
       "expose-services": "dashboard,cdi-uploadproxy"
     }}'
     ```
   - Configure the CDI upload proxy endpoint in your Cozystack values:
     ```yaml
     values-cdi: |
       uploadProxyURL: https://cdi-uploadproxy.example.org
     ```

3. **DNS or hosts file configuration** for upload proxy access:
   - If needed, add an entry to `/etc/hosts` on your local machine:
     ```
     <UPLOAD_PROXY_IP> cdi-uploadproxy.example.org
     ```

## Step 1: Export VM Disks from Proxmox

Before exporting, ensure the virtual machines are stopped in Proxmox.

Export the VM disk to a file in qcow2 format (or another format supported by KubeVirt):

```bash
# Example: Export VM disk from Proxmox storage
qm disk export <vmid> <disk> /tmp/vm-disk.qcow2
```

The output should be a disk image file (e.g., `vm-disk.qcow2`) ready for upload.

{{< note >}}
Specific commands for exporting disks may vary depending on your Proxmox storage backend and configuration.
Refer to [Proxmox VE documentation](https://pve.proxmox.com/wiki/Qm_status) for details.
{{< /note >}}

## Step 2: Create a VMDisk for Upload

Create a `VMDisk` resource in Cozystack with `source.upload` to prepare for image upload:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VMDisk
metadata:
  name: proxmox-vm-disk
  namespace: tenant-root
spec:
  source:
    upload: {}
  storage: 10Gi
  storageClass: replicated
```

Apply the manifest:

```bash
kubectl apply -f vmdisk-upload.yaml
```

Monitor the disk creation status:

```bash
kubectl get vmdisk -n tenant-root
kubectl describe vmdisk proxmox-vm-disk -n tenant-root
```

## Step 3: Upload the Disk Image

Once the VMDisk is created and ready for upload, use `virtctl` to upload the disk image:

```bash
virtctl image-upload dv vm-disk-proxmox-vm-disk \
  -n tenant-root \
  --image-path=./vm-disk.qcow2 \
  --uploadproxy-url https://cdi-uploadproxy.example.org \
  --insecure
```

{{< note >}}
The DataVolume name follows the pattern `vm-disk-<vmdisk-name>`.
If your VMDisk is named `proxmox-vm-disk`, the DataVolume will be `vm-disk-proxmox-vm-disk`.
{{< /note >}}

Wait for the upload to complete. You can monitor the progress:

```bash
kubectl get dv -n tenant-root
kubectl describe dv vm-disk-proxmox-vm-disk -n tenant-root
```

The upload is complete when the status shows `Succeeded`.

## Step 4: Create a VMInstance

After the disk upload is complete, create a VMInstance to boot from the uploaded disk:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VMInstance
metadata:
  name: migrated-vm
  namespace: tenant-root
spec:
  running: true
  instanceType: u1.medium
  disks:
    - name: proxmox-vm-disk
  # Optional: configure network, cloud-init, etc.
```

Apply the manifest:

```bash
kubectl apply -f vminstance.yaml
```

Verify the VM is running:

```bash
kubectl get vm -n tenant-root
kubectl get vmi -n tenant-root
```

## Step 5: Access the Migrated VM

Access the VM console using virtctl:

```bash
# Serial console
virtctl console vm-instance-migrated-vm -n tenant-root

# VNC access
virtctl vnc vm-instance-migrated-vm -n tenant-root

# SSH (if configured)
virtctl ssh user@vm-instance-migrated-vm -n tenant-root
```

## Migration Checklist

Use this checklist to track your migration progress:

- [ ] Export VM disks from Proxmox (qcow2 or compatible format)
- [ ] Install `virtctl` on your local machine
- [ ] Configure upload proxy access in Cozystack
- [ ] Add DNS/hosts entry for upload proxy (if needed)
- [ ] Create VMDisk with `source.upload` in Cozystack
- [ ] Upload disk image using `virtctl image-upload`
- [ ] Wait for upload to complete (status: Succeeded)
- [ ] Create VMInstance with the uploaded disk
- [ ] Verify VM boots successfully
- [ ] Test VM connectivity and functionality

## Troubleshooting

### Upload Fails with Connection Error

**Problem:** `virtctl image-upload` fails with connection refused or timeout.

**Solution:**
- Verify upload proxy is accessible: `curl -k https://cdi-uploadproxy.example.org`
- Check `/etc/hosts` entry matches the upload proxy IP
- Ensure Cozystack ConfigMap has `expose-services: "dashboard,cdi-uploadproxy"`

### Upload Stuck at 0%

**Problem:** Upload starts but never progresses.

**Solution:**
- Check DataVolume status: `kubectl describe dv vm-disk-<name> -n tenant-root`
- Verify storage class has available capacity
- Check CDI pod logs: `kubectl logs -n cozy-system -l app=cdi-uploadproxy`

### VM Fails to Boot After Migration

**Problem:** VM boots but fails to start properly.

**Solution:**
- Check VM disk is attached as the first disk in VMInstance spec
- Verify disk format is compatible (qcow2, raw)
- Review VM logs: `virtctl console vm-instance-<name> -n tenant-root`
- Ensure VM drivers are compatible with KubeVirt (VirtIO recommended)

## Next Steps

After successful migration:

- Configure [cloud-init]({{% ref "/docs/virtualization/virtual-machine" %}}) for automated VM setup
- Review [instance types and profiles]({{% ref "/docs/virtualization/resources" %}}) for optimal resource allocation
- Consider creating [golden images]({{% ref "/docs/virtualization/vm-image" %}}) for future VM deployments
