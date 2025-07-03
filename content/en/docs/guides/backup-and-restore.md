---
title: Back up and Restore
linkTitle: Back up and Restore
description: "How to back up and restore resources in cozystack cluster."
weight: 40
aliases:
  - /docs/backup-and-restore
---

CozyStack uses [Velero](https://velero.io/docs/v1.16/) to manage Kubernetes resource backups and recovery, including volume snapshots.
This guide explains how to configure Velero and perform backups and recovery with practical examples.


## Prerequisites

To back up data in Cozystack, you need an S3-compatible storage ready and enable velero bundle

Enable the Velero bundle in your Cozystack configuration:
```
kubectl edit -n cozy-system configmap cozystack
```
Add velero to the list of bundle-enabled packages:

```
bundle-enable: velero
```

We recommend using the Velero CLI: [https://velero.io/docs/v1.16/basic-install/#install-the-cli](https://velero.io/docs/v1.16/basic-install/#install-the-cli)

## 1. Set up Storage Credentials and Configuration

To enable backups, the first step is to provide Cozystack with access to an S3-compatible storage.

All configuration settings are created as secrets in the `cozy-velero` namespace.

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

This configuration defines the S3 bucket where Velero stores backups.
For more information, see: https://velero.io/docs/v1.16/api-types/backupstoragelocation/.

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

Check what phase is `Available`
```bash
velero backup-location get
```

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

Check what velero havens errors in logs
```bash
kubectl logs -n cozy-velero deploy/velero | grep error
```

For more information see: https://velero.io/docs/v1.16/api-types/volumesnapshotlocation/.


## 2. Create Backups

Once the storage is configured, you can create backups manually or set up a schedule.

## 2.1. Create a Backup Manually

To create a backup manually, apply the following resource to the cluster:

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

Check the results, status must be `completed`:

```bash
velero backup get
```



For more information see: https://velero.io/docs/v1.16/api-types/backup/

## 2.2. Create Scheduled Backups

To set up a schedule, apply the following resource to the cluster:

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
And check what status `Enabled`

For more information see: https://velero.io/docs/v1.16/api-types/schedule/

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
  backupName: < backupName >
  hooks: {}
  includedNamespaces:
  - '*'
  itemOperationTimeout: 0s
  uploaderConfig: {}
status: {}
```

Here `backupName` is the name from `velero backup get` (in our examples, `manual-backup` and `).

Check the backup by executing command:
```bash
velero restore get
```

For more information, see: https://velero.io/docs/v1.16/api-types/restore/.
