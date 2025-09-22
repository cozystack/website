---
title: "How to install Talos on a single-disk machine"
linkTitle: "Install on a single disk"
description: "How to install Talos on a single-disk machine, allocating space on system disk for user storage"
weight: 100
aliases:
  - /docs/operations/faq/single-disk-installation
---

Default Talos setup assumes that each node has a primary and secondary disks, used for system and user storage, respectively.
However, it's possible to use a single disk, allocating space for user storage.

This configuration must be applied with the first [`talosctl apply`]({{% ref "/docs/install/kubernetes/talosctl#3-apply-node-configuration" %}})
or [`talm apply`]({{% ref "/docs/install/kubernetes/talm#3-apply-node-configuration" %}})
— the one with the `-i` (`--insecure`) flag.
Applying changes after initialization will not have any effect.

For `talosctl`, append the following lines to `patch.yaml`:

```yaml
---
apiVersion: v1alpha1
kind: VolumeConfig
name: EPHEMERAL
provisioning:
  minSize: 70GiB

---
apiVersion: v1alpha1
kind: UserVolumeConfig
name: data-storage
provisioning:
  diskSelector:
    match: disk.transport == 'nvme'
  minSize: 400GiB
```

For `talm`, append the same lines at end of the first node's configuration file, such as `nodes/node1.yaml`.

Read more in the Talos documentation: https://www.talos.dev/v1.10/talos-guides/configuration/disk-management/.

After applying the configuration, wipe the `data-storage` partition:

```bash
kubectl -n kube-system debug -it --profile sysadmin --image=alpine node/node1

apk add util-linux

umount /dev/nvme0n1p6 ### The partition allocated for user storage
rm -rf /host/var/mnt/data-storage
wipefs -a /dev/nvme0n1p6
exit
```

When the storage is configured, add the new partition to LINSTOR:
```bash
linstor ps cdp zfs node1 nvme0n1p6 --pool-name data --storage-pool data1
```

Check the result:
```bash
linstor sp l
```

Output will be similar to this example:

```text
+---------------------------------------------------------------------------------------------------------------------------------------+
| StoragePool          | Node  | Driver   | PoolName | FreeCapacity | TotalCapacity | CanSnapshots | State | SharedName                 |
|=======================================================================================================================================|
| DfltDisklessStorPool | node1 | DISKLESS |          |              |               | False        | Ok    | node1;DfltDisklessStorPool |
| data                 | node1 | ZFS      | data     |   351.46 GiB |       476 GiB | True         | Ok    | node1;data                 |
| data1                | node1 | ZFS      | data     |   378.93 GiB |       412 GiB | True         | Ok    | node1;data1                |
```
