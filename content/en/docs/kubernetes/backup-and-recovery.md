---
title: Backup and Recovery for Tenant Kubernetes
linkTitle: Backup and Recovery
description: "How to back up and restore resources in cozystack cluster."
weight: 40
aliases:
  - /docs/guides/backups
---

Cozystack uses [Velero](https://velero.io/docs/v1.16/) to manage Kubernetes resource backups and recovery, including volume snapshots.
This guide explains how to configure one-time and regular backups and to perform recovery with practical examples.


## Prerequisites

- Cozystack v0.33.0 or later.
- Administrator account in the Cozystack cluster. PVC backups require setting up Kubernetes secrets in the management cluster, which can only be done by an administrator.
- External S3-compatible storage.
- Velero CLI installed: [https://velero.io/docs/v1.16/basic-install/#install-the-cli](https://velero.io/docs/v1.16/basic-install/#install-the-cli).

## 1. Set up Storage Credentials and Configuration

To enable backups, the first step is to provide Cozystack with access to an S3-compatible storage.
It will require creating a number of Kubernetes secrets in the `cozy-velero` namespace of the management cluster.

### 1.1 Create a Secret with S3 Credentials

Create a secret containing credentials for your S3-compatible storage where backups will be saved.

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

### 1.2 Configure Backup Storage Location

Defines where Velero stores backups (S3 bucket).  

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

For more information, see the [`BackupStorageLocation` API documentation](https://velero.io/docs/v1.16/api-types/backupstoragelocation/).


### 1.3 Configure Volume Snapshot Location

Defines configuration for volume snapshots.  

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

For more information, see the [`VolumeSnapshotLocation` API documentation](https://velero.io/docs/v1.16/api-types/volumesnapshotlocation/).


## 2. Create Backups

Once the storage is configured, you can create backups manually or set up a schedule.


## 2.1. Create a Manual Backup

To create a backup manually, apply the following resource to the cluster:

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
    # change to the actual tenant name
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
velero backup get
```

For more information, see the [`Backup` API type documentation](https://velero.io/docs/v1.16/api-types/backup/).


## 2.2. Create Scheduled Backups

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
velero schedule get
velero schedule describe
```

For more information see the [`Schedule` API type documentation](https://velero.io/docs/v1.16/api-types/schedule/).


## 3. Restore from Backup

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

Here `<backupName>` is the name assigned to the backup and seen in the output of `velero backup get`.
In the examples above, backups were named `manual-backup` and `backup-schedule`.

Check the backup by executing command:

```bash
velero restore get
```

For more information see the [`Restore` API documentation](https://velero.io/docs/v1.16/api-types/restore/).
