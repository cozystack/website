---
title: "Preparing Disks for LINSTOR Storage Pools"
linkTitle: "Disk Preparation"
description: "How to clean disk metadata and prepare physical storage for LINSTOR"
weight: 5
aliases:
  - /docs/operations/storage/disk-preparation
  - /docs/storage/disk-preparation
---

This guide explains how to prepare physical disks for use with LINSTOR when they contain old metadata that prevents automatic detection.

## Problem Description

When setting up storage on new or repurposed nodes, physical disks may contain remnants from previous installations:

- RAID superblocks
- Partition tables
- LVM signatures
- Filesystem metadata

This old metadata prevents LINSTOR from detecting disks as available storage.

### Symptoms

1. `linstor physical-storage list` shows empty output or missing disks
2. Disks appear with unexpected filesystem types (e.g., `linux_raid_member`)
3. Storage pools only show `DfltDisklessStorPool` without actual storage

## Diagnostics

### Set up LINSTOR alias

For easier access to LINSTOR commands, set up an alias:

```bash
alias linstor='kubectl exec -n cozy-linstor deploy/linstor-controller -- linstor'
```

### Check LINSTOR nodes

List your nodes and check their readiness:
```bash
linstor node list
```

Expected output should show all nodes in `Online` state.

### Check storage pools

Check current storage pools:
```bash
linstor storage-pool list
```

### Check available physical storage

Check what physical disks LINSTOR can see:
```bash
linstor physical-storage list
```

If this command shows empty output or is missing expected disks, the disks likely contain old metadata and need to be wiped.

### Check disk state on node

Check disk state on a specific node via satellite pod:
```bash
# List LINSTOR satellite pods
kubectl get pod -n cozy-linstor -l app.kubernetes.io/component=linstor-satellite

# Check disk state
kubectl exec -n cozy-linstor <satellite-pod-name> -c linstor-satellite -- \
  lsblk -f
```

Expected output for clean disks should show no `FSTYPE`:
```
NAME    FSTYPE LABEL UUID MOUNTPOINT
nvme0n1
nvme1n1
```

If you see `linux_raid_member`, `LVM2_member`, or other filesystem types, the disks need to be wiped.

## Solution: Wiping Disk Metadata

{{< alert color="warning" >}}
**WARNING**: Wiping disks destroys all data on the specified devices.
Only wipe disks that are **NOT** used for the operating system or Talos installation.
{{< /alert >}}

### Step 1: Identify System Disks

Before wiping, identify which disk contains your Talos installation.
Check your Talos configuration in `nodes/<node-name>.yaml`:

```yaml
# In nodes/<node-name>.yaml
machine:
  install:
    disk: /dev/sda  # This disk should NOT be wiped
```

Typically, the system disk is `/dev/sda`, `/dev/vda`, or similar.

### Step 2: Locate Node Configuration

If you used [Talm]({{% ref "/docs/v0/install/kubernetes/talm" %}}) to bootstrap your cluster, your node configurations are stored in `nodes/*.yaml` files in your cluster configuration directory.

Each file corresponds to a specific node (e.g., `nodes/node1.yaml`, `nodes/node2.yaml`).

### Step 3: Wipe Disks

List all disks on the node:
```bash
talm -f nodes/<node-name>.yaml get disks
```

Wipe all non-system disks:
```bash
talm -f nodes/<node-name>.yaml wipe disk nvme0n1 nvme1n1 nvme2n1 ...
```

{{< note >}}
List all disks you want to wipe in a single command.
Do NOT include the system disk (e.g., `sda` if that's where Talos is installed).
{{< /note >}}

### Step 4: Verify Disks are Clean

After wiping, verify that disks are now visible to LINSTOR:

```bash
linstor physical-storage list
```

Expected output should now show your disks:
```
+----------------------------------------------------------------+
| Device    | Size       | Rotational |
|================================================================|
| /dev/nvme0n1 | 3.49 TiB   | False      |
| /dev/nvme1n1 | 3.49 TiB   | False      |
| ...          | ...        | ...        |
+----------------------------------------------------------------+
```

You can also check directly on the node:
```bash
kubectl exec -n cozy-linstor <satellite-pod-name> -c linstor-satellite -- \
  lsblk -f
```

Clean disks should show no `FSTYPE`.

## Creating Storage Pools

Once disks are clean, create a LINSTOR storage pool.

For ZFS storage pools with multiple disks:
```bash
linstor physical-storage create-device-pool zfs <node-name> \
  /dev/nvme0n1 /dev/nvme1n1 /dev/nvme2n1 ... \
  --pool-name data \
  --storage-pool data
```

{{< note >}}
Specify all disks in a single command to create one unified ZFS pool.
Running the command multiple times with the same pool name will fail.
{{< /note >}}

Verify the storage pool was created:
```bash
linstor storage-pool list
```

Expected output:
```
+-----------------------------------------------------------------------+
| StoragePool | Node  | Driver | PoolName | FreeCapacity | TotalCapacity | State |
|=======================================================================|
| data        | node1 | ZFS    | data     | 47.34 TiB    | 47.62 TiB     | Ok    |
| data        | node2 | ZFS    | data     | 47.34 TiB    | 47.62 TiB     | Ok    |
+-----------------------------------------------------------------------+
```

## Troubleshooting

### Disks Still Show Old Metadata After Wipe

Try wiping with the ZEROES method for more thorough cleaning:
```bash
talm -f nodes/<node-name>.yaml wipe disk --method ZEROES nvme0n1
```

This writes zeros to the disk, which takes longer but ensures complete removal of metadata.

### "Zpool name already used" Error

If you need to recreate a storage pool:

1. Delete from LINSTOR:
   ```bash
   linstor storage-pool delete <node-name> <pool-name>
   ```

2. Destroy ZFS pool on the node:
   ```bash
   kubectl exec -n cozy-linstor <satellite-pod-name> -c linstor-satellite -- \
     zpool destroy <pool-name>
   ```

3. Recreate the pool with all disks in one command.

### Permission Denied on Worker Nodes

Worker nodes may not allow direct Talos API access. Use the satellite pod to check disk state:
```bash
kubectl exec -n cozy-linstor <satellite-pod-name> -c linstor-satellite -- lsblk -f
```

If you need to wipe disks on worker nodes, ensure your node configuration allows access or consult your cluster administrator.

## Quick Reference

| Command | Description |
|---------|-------------|
| `linstor sp l` | List storage pools |
| `linstor ps l` | List available physical storage |
| `linstor ps cdp zfs <node> <disks> --pool-name <name> --storage-pool <name>` | Create ZFS storage pool |
| `talm -f nodes/<node>.yaml wipe disk <disks>` | Wipe disk metadata |
| `talm -f nodes/<node>.yaml get disks` | List disks on node |

## Related Documentation

- [Using Talm to Bootstrap Cozystack]({{% ref "/docs/v0/install/kubernetes/talm" %}})
- [Configuring a Dedicated Network for LINSTOR]({{% ref "/docs/v0/storage/dedicated-network" %}})
- [Configuring DRBD Resync Controller]({{% ref "/docs/v0/storage/drbd-tuning" %}})
- [LINSTOR Troubleshooting]({{% ref "/docs/v0/operations/troubleshooting/linstor-controller" %}})
