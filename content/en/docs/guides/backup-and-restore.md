---
title: Backup and restore
linkTitle: Backup and restore
description: "How to backup and restore resources in cozystack cluster."
weight: 10
aliases:
  - /docs/backup-and-restore
---

CozyStack uses [Velero](https://velero.io/docs/v1.16/) to manage Kubernetes resource backups and restores, including volume snapshots. This guide explains how to configure Velero and perform backups and restores with practical examples.

For easier management, we recommend installing the Velero CLI: [https://velero.io/docs/v1.16/basic-install/#install-the-cli](https://velero.io/docs/v1.16/basic-install/#install-the-cli)


## 1. Create Required Resources

All resources must be in `cozy-velero` namespace.

### 1.1 Create a Secret with S3 Credentials
This secret contains credentials for your S3-compatible storage where backups will be saved.
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
For more information see: https://velero.io/docs/v1.16/api-types/backupstoragelocation/

```yaml
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: default
  namespace: cozy-velero
spec:
  provider: aws
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

### 1.3 Configure Volume Snapshot Location
Defines configuration for volume snapshots.
For more information see: https://velero.io/docs/v1.16/api-types/volumesnapshotlocation/

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

## 2. Create a Backup Manually
Apply resource to cluster:
For more information see: https://velero.io/docs/v1.16/api-types/backup/

```yaml
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: manual-backup
  namespace: cozy-velero
spec:
  snapshotVolumes: true
  includedNamespaces:
    - tenant-backuppvc
  labelSelector:
    matchLabels:
      app: test-pod
  ttl: 720h0m0s  # Backup retention (30 days)
```
Check backup executing command: `velero backup get`

## 3. Create Scheduled Backups
Apply resource to cluster:
For more information see: https://velero.io/docs/v1.16/api-types/schedule/

```yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: backup-schedule
  namespace: cozy-velero
spec:
  schedule: "*/5 * * * *"  # Every 5 minutes (example)
  template:
    ttl: 720h0m0s
    snapshotVolumes: true
    includedNamespaces:
      - tenant-backuppvc
    labelSelector:
      matchLabels:
        app: test-pod
```

Check backup executing command: `velero schedule get` and `velero schedule describe`

## 4. Restore from Backup
Apply resource to cluster:
For more information see: https://velero.io/docs/v1.16/api-types/restore/

```yaml
apiVersion: velero.io/v1
kind: Restore
metadata:
  creationTimestamp: null
  name: restore-example
  namespace: cozy-velero
spec:
  backupName: < backupName >
  hooks: {}
  includedNamespaces:
  - '*'
  itemOperationTimeout: 0s
  uploaderConfig: {}
status: {}
```
Where `backupName` is name from `velero backup get` (in our case `manual-backup`).

Check backup executing command: `velero restore get`
