---
title: Backup and Recovery
linkTitle: Backup and Recovery
description: "How to create and manage backups in your Kubernetes cluster using BackupJobs and BackupPlans."
weight: 40
aliases:
  - /docs/v1/guides/backups
---

Cluster backup **strategies** and **BackupClasses** are configured by cluster administrators. If your tenant does not have a BackupClass yet, ask your administrator to follow the [Velero Backup Configuration]({{% ref "/docs/v1/operations/services/velero-backup-configuration" %}}) guide to set up storage, strategies, and BackupClasses.

This guide is for **tenant users**: how to run one-off and scheduled backups using existing BackupClasses, check backup status, and where to look for restore options.

Cozystack uses [Velero](https://velero.io/docs/v1.17/) under the hood. Backups and restores run in the `cozy-velero` namespace (management cluster) or the equivalent namespace in your tenant cluster, depending on your setup.

## Prerequisites

- The Velero add-on is enabled for your cluster (by an administrator).
- At least one **BackupClass** is available for your tenant or namespace (provided by an administrator).
- `kubectl` and kubeconfig for the cluster you are backing up.

## 1. List available BackupClasses

BackupClasses define where and how backups are stored. You can only use those that administrators have created and made available to you.

```bash
kubectl get backupclasses -n cozy-velero
```

Use the BackupClass **name** in the next steps when creating a BackupJob or BackupPlan.

## 2. Create a one-off backup (BackupJob)

Use a **BackupJob** when you want to run a backup once (for example, before a risky change).

Replace `<BACKUPCLASS_NAME>` with a name from the list above, and `<API_VERSION>` with the API version used in your cluster (e.g. `backup.cozystack.io/v1alpha1`). Check with:

```bash
kubectl get backupclass -n cozy-velero -o yaml
```

Example BackupJob:

```yaml
apiVersion: <API_VERSION>   # e.g. backup.cozystack.io/v1alpha1
kind: BackupJob
metadata:
  name: my-manual-backup
  namespace: cozy-velero
spec:
  backupClassRef:
    name: <BACKUPCLASS_NAME>
  # Optional overrides (if supported by your CRD):
  # ttl: 168h0m0s
  # snapshotVolumes: true
```

Apply and check status:

```bash
kubectl apply -f backupjob.yaml
kubectl get backupjobs -n cozy-velero
kubectl describe backupjob my-manual-backup -n cozy-velero
```

Underlying Velero backups can be listed with:

```bash
kubectl get backups.velero.io -n cozy-velero
```

## 3. Create scheduled backups (BackupPlan)

Use a **BackupPlan** to run backups on a schedule (e.g. daily or every 6 hours).

Example (replace `<BACKUPCLASS_NAME>` and `<API_VERSION>` as above):

```yaml
apiVersion: <API_VERSION>   # e.g. backup.cozystack.io/v1alpha1
kind: BackupPlan
metadata:
  name: my-backup-plan
  namespace: cozy-velero
spec:
  backupClassRef:
    name: <BACKUPCLASS_NAME>
  schedule: "0 */6 * * *"   # Every 6 hours (cron)
  # Optional: ttl: 720h0m0s
```

Apply and check:

```bash
kubectl apply -f backupplan.yaml
kubectl get backupplans -n cozy-velero
kubectl describe backupplan my-backup-plan -n cozy-velero
kubectl get backups.velero.io -n cozy-velero
```

## 4. Check backup status

- **BackupJobs**: `kubectl get backupjobs -n cozy-velero` and `kubectl describe backupjob <name> -n cozy-velero`
- **BackupPlans**: `kubectl get backupplans -n cozy-velero` and `kubectl describe backupplan <name> -n cozy-velero`
- **Velero backups**: `kubectl get backups.velero.io -n cozy-velero`
- **Upload progress (snapshots)**: `kubectl get datauploads.velero.io -n cozy-velero`

If the [Velero CLI]](https://velero.io/docs/v1.17/basic-install/#install-the-cli) is installed, you can also run:

```bash
velero -n cozy-velero backup get
velero -n cozy-velero schedule get
```

## 5. Restore from a backup

Restore is typically performed by cluster administrators or via the Velero API, because it can affect many resources and may require care (e.g. partial restore, namespace mapping).

- **Full or partial restore** using Velero: see the [Velero Restore documentation](https://velero.io/docs/v1.17/api-types/restore/) and, in your environment, the [Velero Backup Configuration]({{% ref "/docs/v1/operations/services/velero-backup-configuration" %}}) guide for context on storage and namespaces.
- List existing backups: `velero -n cozy-velero backup get` or `kubectl get backups.velero.io -n cozy-velero`.
- Restore operations may create `Restore` resources in the `cozy-velero` namespace; check with `kubectl get restores.velero.io -n cozy-velero` and `kubectl get datadownloads.velero.io -n cozy-velero` for download progress.

If your platform exposes a higher-level restore API (e.g. a custom Restore CRD), use that as documented by your administrator.
