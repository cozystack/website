---
title: Backup and Recovery
linkTitle: Backup and Recovery
description: "How to back up and restore resources in a Cozystack cluster."
weight: 40
aliases:
  - /docs/guides/backups
---

{{% alert color="warning" %}}
:warning: **Warning**: Backup and restore functionality is currently under development and will be exposed via user‑friendly API interfaces in future releases.
The instructions below require manual configuration and are recommended for advanced users only.
{{% /alert %}}

Cozystack uses [Velero](https://velero.io/docs/v1.17/) to manage Kubernetes resource backups and restores, including volume snapshots.
This guide explains how to configure one‑off and scheduled backups and how to perform restores, with practical examples.

The Velero add‑on is disabled by default. To enable it:

- For the **management cluster**, add `velero` to the `bundle-enable` option in the `cozystack` ConfigMap in the `cozy-system` namespace.
- For **tenant clusters**, set `spec.addons.velero.enabled` to `true` in the `Kubernetes` resource.

## Prerequisites

- Cozystack v0.37.0 or later.
- Administrator access to the Cozystack cluster. PVC backups require creating Kubernetes secrets in the management cluster, which can only be done by an administrator.
- External S3‑compatible storage.
- Velero CLI installed: [https://velero.io/docs/v1.17/basic-install/#install-the-cli](https://velero.io/docs/v1.17/basic-install/#install-the-cli).

## 1. Set up Storage Credentials and Configuration

To enable backups, the first step is to provide Cozystack with access to an S3-compatible storage.
It will require creating a number of Kubernetes secrets in the `cozy-velero` namespace of the management cluster.

### 1.1 Create a Secret with S3 credentials

Create a secret containing credentials for your S3‑compatible storage where backups will be saved.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: s3-credentials
  namespace: cozy-velero
type: Opaque
stringData:
  cloud: |
    [default]
    aws_access_key_id=<KEY>
    aws_secret_access_key=<SECRET KEY>

    services = seaweed-s3
    [services seaweed-s3]
    s3 =
        endpoint_url = https://s3.tenant-name.cozystack.example.com
```

### 1.2 Configure BackupStorageLocation

This resource defines where Velero stores backups (S3 bucket).

```yaml
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: default
  namespace: cozy-velero
spec:
  # provider name can have any value
  provider: <PROVIDER NAME>
  objectStorage:
    bucket: <BUCKET NAME>
  config:
    checksumAlgorithm: ''
    profile: "default"
    s3ForcePathStyle: "true"
    s3Url: https://s3.tenant-name.cozystack.example.com
  credential:
    name: s3-credentials
    key: cloud
```

For more information, see the [`BackupStorageLocation` API documentation](https://velero.io/docs/v1.17/api-types/backupstoragelocation/).


### 1.3 Configure VolumeSnapshotLocation

This resource defines the configuration for volume snapshots.

```yaml
apiVersion: velero.io/v1
kind: VolumeSnapshotLocation
metadata:
  name: default
  namespace: cozy-velero
spec:
  provider: aws
  credential:
    name: s3-credentials
    key: cloud
  config:
    region: "us-west-2"
    profile: "default"
```

For more information, see the [`VolumeSnapshotLocation` API documentation](https://velero.io/docs/v1.17/api-types/volumesnapshotlocation/).

## 2. Create Backups

Once storage is configured, you can create backups manually or set up a schedule.


## 2.1 Create a manual backup

To create a backup manually, run:

```
velero -n cozy-velero backup create tenant-backupexample-backup1 \
  --include-namespaces tenant-backupexample \
  --snapshot-move-data \
  --wait
```

Alternatively, apply the following resource to the cluster:

```yaml
apiVersion: velero.io/v1
kind: Backup
metadata:
  # unique backup name used for recovery and other operations
  name: manual-backup
  namespace: cozy-velero
spec:
  snapshotVolumes: true
  snapshotMoveData: true
  includedNamespaces:
    # change to the actual namespace name
    - tenant-backupexample
  labelSelector:
    matchLabels:
      # change to the actual application name
      app: test-pod
  ttl: 720h0m0s  # Backup retention (30 days)
```

Check upload progress with:

```bash
kubectl get datauploads.velero.io
```

Check the backup status with:

```bash
velero -n cozy-velero backup get
```

Check snapshot upload status with:

```bash
kubectl -n cozy-velero get datauploads.velero.io
```

For more information, see the [`Backup` API documentation](https://velero.io/docs/v1.17/api-types/backup/).


## 2.2 Create scheduled backups

To set up a schedule, apply the following resource to the cluster:

```yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  # unique backup name used for recovery and other operations
  name: backup-schedule
  namespace: cozy-velero
spec:
  schedule: "*/5 * * * *"  # Every 5 minutes (example)
  template:
    ttl: 720h0m0s # Backup retention (30 days)
    snapshotVolumes: true
    snapshotMoveData: true
    includedNamespaces:
      # change to the actual tenant name
      - tenant-backupexample
    labelSelector:
      matchLabels:
        # change to the actual application name
        app: test-pod
```

Check scheduled backups with:
```bash
velero -n cozy-velero schedule get
velero -n cozy-velero schedule describe backup-schedule
```

For more information, see the [`Schedule` API documentation](https://velero.io/docs/v1.17/api-types/schedule/).


## 3. Restore from a backup (all resources)

{{% alert color="warning" %}}
:warning: **Warning**: This operation attempts to restore all resources from the backup and may lead to conflicts with webhooks and other controllers.
Consider using a partial restore as described in the next section.
{{% /alert %}}

To restore data from a backup, apply the following resource to the cluster:

```yaml
apiVersion: velero.io/v1
kind: Restore
metadata:
  creationTimestamp: null
  name: restore-example
  namespace: cozy-velero
spec:
  backupName: <backupName>
  hooks: {}
  includedNamespaces:
  - '*'
  itemOperationTimeout: 0s
  uploaderConfig: {}
status: {}
```

Here `<backupName>` is the name assigned to the backup, as shown in the output of `velero -n cozy-velero backup get`.
In the examples above, backups were named `manual-backup` and those created by `backup-schedule`.

Check restore status with:

```bash
velero -n cozy-velero restore get
```

To see the progress of data downloads:
```bash
kubectl -n cozy-velero get datadownloads.velero.io
```

For more information, see the [`Restore` API documentation](https://velero.io/docs/v1.17/api-types/restore/).

## 4. Restore from a backup (partial)

{{% alert color="warning" %}}
:warning: **Warning**: Before restoring a backup, make sure that the resources to be restored are not already present in the cluster. Otherwise, they will be skipped.
{{% /alert %}}

Use this approach in the management cluster, as restoring all resources may lead to conflicts with webhooks and other controllers.

List available backups:

```bash
velero -n cozy-velero backup get
```

Restore PVCs only:

```bash
velero -n cozy-velero restore create manual-backup-restore-pvc \
  --from-backup manual-backup \
  --include-resources persistentvolumeclaims \
  --include-namespaces tenant-backupexample --restore-volumes=true \
  --wait
```

To see the progress of data downloads:
```bash
kubectl -n cozy-velero get datadownloads.velero.io
```

If you have virtual machine volumes, you must mark them to allow adoption by `DataVolume` resources.
The following command annotates all matching PVCs in the `tenant-backupexample` namespace with the required annotations:
```bash
kubectl -n tenant-backupexample get pvc -l app=containerized-data-importer --no-headers -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name \
  | awk '{print "kubectl annotate -n " $1 " pvc " $2 " cdi.kubevirt.io/storage.populatedFor=" $2 " cdi.kubevirt.io/allowClaimAdoption=true --overwrite"}' \
  | sh -x
```

Restore underlying Services, ConfigMaps, Secrets, and DataVolumes:
```bash
velero -n cozy-velero restore create manual-backup-restore-resources \
  --from-backup manual-backup \
  --include-resources services,configmaps,secrets,datavolumes.cdi.kubevirt.io \
  --include-namespaces tenant-backupexample \
  --wait
```

Restore `HelmRelease` resources (these represent Cozystack apps):
```bash
velero -n cozy-velero restore create manual-backup-restore-helmreleases \
  --from-backup manual-backup \
  --include-resources helmreleases.helm.toolkit.fluxcd.io \
  --include-namespaces tenant-backupexample \
  --wait
```

Verify that your HelmReleases and apps are restored:
```bash
kubectl -n tenant-backupexample get helmreleases
```
