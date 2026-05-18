---
title: Backup and Recovery
linkTitle: Backup and Recovery
description: "How to create and manage backups of VMInstance and VMDisk resources using BackupJobs and Plans."
weight: 40
aliases:
  - /docs/v1.1/guides/backups
  - /docs/v1.1/kubernetes/backup-and-recovery
---

Cluster backup **strategies** and **BackupClasses** are configured by cluster administrators. If your tenant does not have a BackupClass yet, ask your administrator to follow the [Velero Backup Configuration]({{% ref "/docs/v1.1/operations/services/velero-backup-configuration" %}}) guide to set up storage, strategies, and BackupClasses.

This guide covers backing up and restoring **VMInstance** and **VMDisk** resources as a tenant user: running one-off and scheduled backups, checking backup status, and restoring from a backup using RestoreJobs.

Cozystack uses [Velero](https://velero.io/docs/v1.17/) under the hood for backup storage and volume snapshots.

## Prerequisites

- The Velero add-on is enabled for your cluster (by an administrator).
- At least one **BackupClass** is available for your tenant namespace (provided by an administrator).
- `kubectl` and kubeconfig for the cluster you are backing up.

## List available BackupClasses

BackupClasses define where and how backups are stored. You can only use those that administrators have created.

```bash
kubectl get backupclasses
```

Example output:

```
NAME     AGE
velero   14m
```

Use the BackupClass name when creating a BackupJob or Plan.

## Back up a VMInstance

A VMInstance backup captures the VM configuration and all attached VMDisk volumes.

### One-off backup

Use a **BackupJob** when you want to run a backup once — for example, before a risky change.

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: BackupJob
metadata:
  name: my-vm-backup
  namespace: tenant-user
spec:
  applicationRef:
    apiGroup: apps.cozystack.io
    kind: VMInstance
    name: my-vm
  backupClassName: velero
```

Apply it and watch the status:

```bash
kubectl apply -f backupjob.yaml
kubectl get backupjobs -n tenant-user
kubectl describe backupjob my-vm-backup -n tenant-user
```

When the BackupJob completes successfully, it creates a **Backup** object with the same name (`my-vm-backup`). You will use that name when restoring.

### Scheduled backup

Use a **Plan** to run backups on a schedule.

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: Plan
metadata:
  name: my-vm-daily
  namespace: tenant-user
spec:
  applicationRef:
    apiGroup: apps.cozystack.io
    kind: VMInstance
    name: my-vm
  backupClassName: velero
  schedule:
    cron: "0 2 * * *"   # Every day at 02:00
```

Apply it and check:

```bash
kubectl apply -f plan.yaml
kubectl get plans -n tenant-user
kubectl describe plan my-vm-daily -n tenant-user
```

Each scheduled run creates a BackupJob (and, on success, a Backup object) named after the Plan with a timestamp suffix.

## Back up a VMDisk

You can back up a VMDisk independently — for example, to capture a specific disk without the VM configuration.

{{% alert color="info" %}}
The BackupClass must include a strategy for `VMDisk`. Ask your administrator to add one if it is missing (see [Velero Backup Configuration]({{% ref "/docs/v1.1/operations/services/velero-backup-configuration" %}})).
{{% /alert %}}

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: BackupJob
metadata:
  name: my-disk-backup
  namespace: tenant-user
spec:
  applicationRef:
    apiGroup: apps.cozystack.io
    kind: VMDisk
    name: my-disk
  backupClassName: velero
```

Apply and check status:

```bash
kubectl apply -f backupjob-disk.yaml
kubectl get backupjobs -n tenant-user
kubectl describe backupjob my-disk-backup -n tenant-user
```

## Check backup status

List all BackupJobs in a namespace:

```bash
kubectl get backupjobs -n tenant-user
```

Describe a specific BackupJob to see phase and any errors:

```bash
kubectl describe backupjob my-vm-backup -n tenant-user
```

List the Backup objects that were produced (one per completed BackupJob):

```bash
kubectl get backups -n tenant-user
```

List BackupJobs created by a Plan:

```bash
kubectl get backupjobs -n tenant-user -l backups.cozystack.io/plan=my-vm-daily
```

## Restore a VMInstance

You can restore a VMInstance both **in place** (rolling back a running VM) and **from scratch** (after the VM and its disks have been deleted). The VMInstance backup includes all attached VMDisk volumes and their data.

First, find the Backup object you want to restore from:

```bash
kubectl get backups -n tenant-user
```

Example output:

```
NAME            AGE
my-vm-backup    2h
```

Create a RestoreJob referencing that Backup:

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: RestoreJob
metadata:
  name: restore-my-vm
  namespace: tenant-user
spec:
  backupRef:
    name: my-vm-backup
```

Apply it and check progress:

```bash
kubectl apply -f restorejob.yaml
kubectl get restorejobs -n tenant-user
kubectl describe restorejob restore-my-vm -n tenant-user
```

{{% alert color="info" %}}
The restore controller automatically prepares the environment step-by-step:

- **Suspends HelmReleases** for the VMInstance and its VMDisks to prevent Flux from interfering.
- **Halts the VM** (sets `runStrategy=Halted`) and waits for the VMI to shut down gracefully.
- **Renames existing PVCs** to `<name>-orig-<hash>` so Velero can create fresh ones from the backup. The old PVCs are preserved in case you need to inspect them.
- **Deletes DataVolumes** so CDI does not recreate PVCs after the rename.
{{% /alert %}}


The RestoreJob goes through `Pending` → `Running` → `Succeeded` (or `Failed`). On success, the VMInstance and its VMDisks are restored to the state captured in the backup.

### Post-restore verification

After the RestoreJob succeeds, verify that the VM is actually running:

```bash
# Check that the VMInstance and VMDisk are Ready
kubectl get vminstances,vmdisks -n tenant-user

# Verify the VirtualMachineInstance is running (not just the CR)
kubectl get vmi -n tenant-user

# Verify SSH access
virtctl ssh -i ~/.ssh/my-key -l ubuntu vmi/vm-instance-my-vm -n tenant-user -c "ip a"
```

Once you have verified that the restore is successful and the VM is working correctly, you can delete the `*-orig-*` PVCs containing the original data to free up storage:

{{% alert color="warning" %}}
Do not delete the `*-orig-*` PVCs until you have confirmed the restored VM is fully functional. They are your last resort for manual recovery if something went wrong during the restore.
{{% /alert %}}

```bash
# List the -orig PVCs
kubectl get pvc -n tenant-user | grep -- '-orig-'

# Delete them when no longer needed (replace with actual PVC names from the list above)
kubectl delete pvc -n tenant-user <name>-orig-<hash>
```

## Restore a VMDisk in place

To restore only a VMDisk without touching the VM configuration.

{{% alert color="warning" %}}
Velero skips an existing DataVolume during restore. To restore the actual disk contents from the backup, delete the DataVolume first:

```bash
kubectl delete datavolume vm-disk-my-disk -n tenant-user
```

The RestoreJob will then recreate it and download disk data from the backup storage.
{{% /alert %}}

```bash
kubectl get backups -n tenant-user
```

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: RestoreJob
metadata:
  name: restore-my-disk
  namespace: tenant-user
spec:
  backupRef:
    name: my-disk-backup
```

Apply and check:

```bash
kubectl apply -f restorejob-disk.yaml
kubectl get restorejobs -n tenant-user
kubectl describe restorejob restore-my-disk -n tenant-user
```

## Troubleshooting

If a BackupJob or RestoreJob ends in `Failed` phase, check the `message` field in its status:

```bash
kubectl get backupjob my-vm-backup -n tenant-user -o jsonpath='{.status.message}'
kubectl get restorejob restore-my-vm -n tenant-user -o jsonpath='{.status.message}'
```

For lower-level details, check the Velero logs in the management cluster:

```bash
kubectl logs -n cozy-velero -l app.kubernetes.io/name=velero --tail=100
```

### Fixing SSH access (cloud-init MAC address mismatch after restore)

{{% alert color="info" %}}
The restore controller automatically attempts to preserve the VM's **OVN IP and MAC addresses** from backup time by patching the restored VirtualMachine with the original annotations. If this fails, you can retrieve the original IP/MAC manually from `Backup .status.underlyingResources` and assign them.
{{% /alert %}}

After a VMInstance is restored, the guest OS may lose network connectivity. This is known to happen on **Ubuntu Server**, where cloud-init generates a netplan configuration bound to the old VM's MAC address. After restore, the VM gets a new virtual NIC with a different MAC address, but the guest OS still has the old netplan config bound to the previous MAC — so the network interface is never configured. Other operating systems that do not pin network configuration to a specific MAC address may not be affected by this issue.

To fix this, update the `cloudInitSeed` field in the VMInstance spec and restart the VM. Changing the seed generates a new SMBIOS UUID, which makes cloud-init treat the VM as a new instance and re-run network configuration with the correct MAC address.

```bash
# Set a new cloudInitSeed value (any string different from the current one)
kubectl patch vminstance my-vm -n tenant-user --type merge \
  -p '{"spec":{"cloudInitSeed":"reseed1"}}'

# Wait for the VMInstance to reconcile
kubectl wait vminstance/my-vm -n tenant-user --for=condition=Ready --timeout=180s

# Restart the VM so the new seed takes effect
virtctl restart vm-instance-my-vm -n tenant-user
```

After the restart, verify that the VM has network connectivity:

```bash
# Check that the VMI is running
kubectl get vmi -n tenant-user

# Verify SSH access
virtctl ssh -i ~/.ssh/my-key -l ubuntu vmi/vm-instance-my-vm -n tenant-user -c "ip a"
```

{{% alert color="info" %}}
If you need to change the seed again in the future (e.g. after another restore), use a different value each time (e.g. `reseed2`, `reseed3`, etc.).
{{% /alert %}}
