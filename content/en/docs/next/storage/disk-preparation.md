---
title: "Preparing Disks for LINSTOR Storage Pools"
linkTitle: "Disk Preparation"
description: "How to clean disk metadata and prepare physical storage for LINSTOR"
weight: 5
aliases:
  - /docs/operations/storage/disk-preparation
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

If you used [Talm]({{% ref "/docs/next/install/kubernetes/talm" %}}) to bootstrap your cluster, your node configurations are stored in `nodes/*.yaml` files in your cluster configuration directory.

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

Once disks are clean, choose a backend and create the LINSTOR storage pool. Cozystack ships drivers for three LINSTOR backends; pick one based on what is available on the nodes.

### Choosing a backend

| Backend | When to pick | Notes |
|---|---|---|
| **ZFS** | Default for the cozystack-tuned Talos image (the ZFS extension is baked in). Also fine on generic Linux with ZFS-on-Linux installed. | Higher RAM use (ARC); compression and snapshots built-in. |
| **LVM Thin Pool** | Generic Linux without ZFS (RHEL 10 / Rocky 10 / Alma 10 do not ship OpenZFS). Supports thin overprovisioning. | Pool fill-up beyond 100% freezes writes — keep utilisation under ~95%. |
| **LVM (thick)** | Simple, fixed allocations. No snapshots without LVM-level snapshot LVs. | Rarely the right pick in cozystack deployments; documented for completeness. |

DRBD replication works with all three — DRBD lives on top of the chosen pool, not inside it.

### ZFS storage pool

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

### LVM Thin storage pool

For nodes without ZFS, LVM thin pool is the recommended LINSTOR backend.

#### Prerequisites

- `lvm2` package installed on every storage node (`pvcreate` / `vgcreate` / `lvcreate` available).
- Kernel module `dm_thin_pool` loaded on every storage node. Verify from the satellite pod:

  ```bash
  kubectl exec -n cozy-linstor <satellite-pod-name> -c linstor-satellite -- \
    lsmod | grep dm_thin_pool
  ```

  On generic Linux distributions the module loads on demand the first time `lvcreate --type thin-pool` runs. On Talos the kernel modules are immutable and must be declared in the machine-config:

  ```yaml
  machine:
    kernel:
      modules:
        - name: dm_thin_pool
  ```

  Apply with `talm apply` and reboot the node. Confirm with `lsmod | grep dm_thin_pool` afterwards.

#### Step 1: Create the LVM thin pool

For each storage node, create a Physical Volume, Volume Group, and Thin Pool Logical Volume. The recommended path is the LINSTOR helper; the manual path is documented as a fallback.

##### Option A — via LINSTOR (recommended)

```bash
linstor physical-storage create-device-pool lvmthin <node-name> /dev/nvme0n1 \
  --pool-name thinpool0 \
  --vg-name vg-data \
  --storage-pool data
```

The helper takes one device per invocation; for multi-disk thin pools, create a VG manually (Option B) and register it with LINSTOR.

##### Option B — manually inside the satellite pod

```bash
kubectl exec -n cozy-linstor <satellite-pod-name> -c linstor-satellite -- sh -c '
  pvcreate /dev/nvme0n1
  vgcreate vg-data /dev/nvme0n1
  lvcreate --type thin-pool --extents 95%FREE --name thinpool0 vg-data
'
linstor storage-pool create lvmthin <node-name> data vg-data/thinpool0
```

`--extents 95%FREE` leaves room for thin-pool metadata growth. `lvm2` sizes the metadata LV automatically on create — do not pass `--poolmetadatasize` unless you know exactly what you need.

#### Step 2: Verify

```bash
linstor storage-pool list
```

Expected output:
```
+----------------------------------------------------------------------------------+
| StoragePool | Node  | Driver   | PoolName          | FreeCapacity | TotalCapacity | State |
|==================================================================================|
| data        | node1 | LVM_THIN | vg-data/thinpool0 | 3.32 TiB     | 3.49 TiB      | Ok    |
| data        | node2 | LVM_THIN | vg-data/thinpool0 | 3.32 TiB     | 3.49 TiB      | Ok    |
+----------------------------------------------------------------------------------+
```

{{< alert color="warning" >}}
**Thin pool utilisation**: never let actual data usage exceed roughly 95% of the thin pool. Writes block when the underlying pool runs out of space, regardless of how much virtual capacity each volume claims. Monitor with `linstor storage-pool list` and the LINSTOR Prometheus exporter.
{{< /alert >}}

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

### LVM Thin: `Pool creation failed` or `dm_thin_pool not loaded`

**Symptom**

`linstor physical-storage create-device-pool lvmthin ...` fails, or the manual `lvcreate --type thin-pool` reports `device-mapper: thin: kernel-side fix required` / `Failed to activate thin pool`.

**Cause**

The `dm_thin_pool` kernel module is not loaded on the node. On generic Linux it loads on demand, but only if `lvm2` was already installed at the time of the first thin-pool create; otherwise the module is missing. On Talos it must be declared in the machine-config (see [LVM Thin storage pool prerequisites](#lvm-thin-storage-pool) above).

**Fix on generic Linux**:

```bash
kubectl exec -n cozy-linstor <satellite-pod-name> -c linstor-satellite -- \
  modprobe dm_thin_pool
```

Persist by adding `dm_thin_pool` to `/etc/modules-load.d/cozystack.conf`.

**Fix on Talos**: add the module to the machine-config and re-apply with `talm apply`. Reboot the affected node.

### LVM Thin: `Volume group "vg-data" not found` after node reboot

**Symptom**

The thin pool was created successfully, but after a node reboot LINSTOR reports the storage pool as `Error` and `vgs` on the node shows no `vg-data`.

**Cause**

The Physical Volume signature was wiped (`wipefs` or partition tool) or the underlying device was renamed (`/dev/nvme0n1` became `/dev/nvme1n1` after a controller swap).

**Fix**

Re-detect the PV (`pvscan --cache`) and re-activate the VG (`vgchange --activate y vg-data`). If the device path actually changed, update the LINSTOR storage pool registration with the new path.

## Quick Reference

| Command | Description |
|---------|-------------|
| `linstor sp l` | List storage pools |
| `linstor ps l` | List available physical storage |
| `linstor ps cdp zfs <node> <disks> --pool-name <name> --storage-pool <name>` | Create ZFS storage pool |
| `linstor ps cdp lvmthin <node> <disk> --pool-name <thin-lv> --vg-name <vg> --storage-pool <name>` | Create LVM thin pool |
| `linstor sp create lvmthin <node> <storage-pool> <vg>/<thin-lv>` | Register an existing thin pool with LINSTOR |
| `lsmod \| grep dm_thin_pool` | Verify the thin-pool kernel module is loaded |
| `talm -f nodes/<node>.yaml wipe disk <disks>` | Wipe disk metadata |
| `talm -f nodes/<node>.yaml get disks` | List disks on node |

## Related Documentation

- [Using Talm to Bootstrap Cozystack]({{% ref "/docs/next/install/kubernetes/talm" %}})
- [Configuring a Dedicated Network for LINSTOR]({{% ref "/docs/next/storage/dedicated-network" %}})
- [Configuring DRBD Resync Controller]({{% ref "/docs/next/storage/drbd-tuning" %}})
- [LINSTOR Troubleshooting]({{% ref "/docs/next/operations/troubleshooting/linstor-controller" %}})
