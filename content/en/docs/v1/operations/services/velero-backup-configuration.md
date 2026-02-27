---
title: "Velero Backup Configuration"
linkTitle: "Velero Backup Configuration"
description: "Configure backup storage, strategies, and BackupClasses for cluster backups (for cluster administrators)."
weight: 30
---

This guide is for **cluster administrators** who configure the backup infrastructure in Cozystack: S3 storage, Velero locations, backup **strategies**, and **BackupClasses**. Tenant users then use existing BackupClasses to create [BackupJobs and BackupPlans]({{% ref "/docs/v1/kubernetes/backup-and-recovery" %}}).

Cozystack uses [Velero](https://velero.io/docs/v1.17/) for Kubernetes resource backups and restores, including volume snapshots. The Velero add-on is disabled by default:

- For the **management cluster**, add `velero` to `bundles.enabledPackages` in the [Platform Package]({{% ref "/docs/v1/operations/configuration/platform-package" %}}).
- For **tenant clusters**, set `spec.addons.velero.enabled` to `true` in the `Kubernetes` resource.

## Prerequisites

- Administrator access to the Cozystack (management) cluster.
- S3-compatible storage: if you want store backups in Cozy you need enable SeaweedFS and create a Bucket or can use another external S3 service.

## 1. Set up storage credentials and configuration

Create the following resources in the **management cluster** in the `cozy-velero` namespace so that Velero can store backups and volume snapshots.

### 1.1 Create a secret with S3 credentials

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

See [BackupStorageLocation](https://velero.io/docs/v1.17/api-types/backupstoragelocation/) in the Velero docs.

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

See [VolumeSnapshotLocation](https://velero.io/docs/v1.17/api-types/volumesnapshotlocation/) in the Velero docs.

## 2. Define a backup strategy

A **strategy** describes *what* is backed up and with which Velero options. It is a reusable template referenced by BackupClasses.

In a strategy you define:

- **Scope**: namespaces and resources (e.g. a tenant namespace or resources by label).
- **Volume handling**: whether to snapshot volumes and use `snapshotMoveData`.
- **Retention**: default backup TTL.

Check the CRD group, version, and kind in your cluster:

```bash
kubectl get crd | grep -i backup
kubectl explain <strategy-kind> --recursive
```

Example strategy (replace `<API_VERSION>` and `<KIND>` with the values from your cluster):

```yaml
apiVersion: strategy.backups.cozystack.io/v1alpha1
kind: Velero
metadata:
  name: velero-backup-strategy
spec:
  template:
    spec: # see https://velero.io/docs/v1.17/api-types/backup/
      includedNamespaces:
      - '{{ .Application.metadata.namespace }}'

      labelSelector:
        matchLabels:
          apps.cozystack.io/application.Kind: '{{ .Application.kind }}'

      includedResources:
        - helmreleases.helm.toolkit.fluxcd.io
        - virtualmachines.kubevirt.io
        - virtualmachineinstances.kubevirt.io
        - datavolumes.cdi.kubevirt.io
        - persistentvolumeclaims
        - services
        - configmaps
        - secrets

      storageLocation: '{{ .Parameters.backupStorageLocationName }}'

      volumeSnapshotLocations:
        - '{{ .Parameters.backupStorageLocationName }}'
      snapshotVolumes: true
      snapshotMoveData: true

      ttl: 720h0m0s
      itemOperationTimeout: 24h0m0s
```

Template context for substitutions in template spec will be resolved according defined Parameters in BackupClass and desired ApplicationRef defined in BackupJob / Plan.

Don't forget apply it into management cluster:

```bash
kubectl apply -f velero-backup-strategy.yaml
```

## 3. Create a BackupClass

A **BackupClass** binds a strategy to applications, you can define some Parameters

Verify the BackupClass CRD in your cluster:

```bash
kubectl get backupclasses
kubectl explain backupclass.spec --recursive
```

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: BackupClass
metadata:
  name: velero
spec:
  strategies:
  - strategyRef:
      apiGroup: strategy.backups.cozystack.io
      kind: Velero
      name: velero-backup-strategy
    application:
      kind: VirtialMachine
    parameters:
      backupStoragelocationName: default
```

Apply and list:

```bash
kubectl apply -f backupclass.yaml
kubectl get backupclasses
```

## How users run backups

Once strategies and BackupClasses are in place, **tenant users** can run backups without touching Velero or storage configuration:

- **One-off backup**: create a [BackupJob]({{% ref "/docs/v1/kubernetes/backup-and-recovery#create-a-one-off-backup-backupjob" %}}) that references a BackupClass.
- **Scheduled backups**: create a [BackupPlan]({{% ref "/docs/v1/kubernetes/backup-and-recovery#create-scheduled-backups-backupplan" %}}) with a cron schedule and a BackupClass reference.

Direct use of Velero CRDs (`Backup`, `Schedule`, `Restore`) remains available for advanced or recovery scenarios; see the [Backup and Recovery]({{% ref "/docs/v1/kubernetes/backup-and-recovery" %}}) guide and the [Velero documentation](https://velero.io/docs/v1.17/).
