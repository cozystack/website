---
title: "Velero Backup Configuration"
linkTitle: "Velero Backup Configuration"
description: "Configure backup storage, strategies, and BackupClasses for cluster backups (for cluster administrators)."
weight: 30
---

This guide is for **cluster administrators** who configure the backup infrastructure in Cozystack: S3 storage, Velero locations, backup **strategies**, and **BackupClasses**. Tenant users then use existing BackupClasses to create [BackupJobs and Plans]({{% ref "/docs/v1.1/virtualization/backup-and-recovery" %}}).

## Prerequisites

- Administrator access to the Cozystack (management) cluster.
- S3-compatible storage: if you want to store backups in Cozy you need enable SeaweedFS and create a Bucket or can use another external S3 service.
- Enable disabled by default component `cozystack.velero` in `bundles.enabledPackages` of the [Platform Package]({{% ref "/docs/v1.1/operations/configuration/platform-package" %}}). And for **tenant clusters**, set `spec.addons.velero.enabled` to `true` in the `Kubernetes` resource.

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
  provider: aws
  objectStorage:
    bucket: <BUCKET_NAME>
  config:
    checksumAlgorithm: ''
    profile: "default"
    s3ForcePathStyle: "true"
    s3Url: https://s3.tenant-name.cozystack.example.com
  credential:
    name: s3-credentials
    key: cloud
```

`BUCKET_NAME` can be found with: 
```bash
kubectl get bucketclaim -A -o custom-columns=NAME:.metadata.name,NAMESPACE:.metadata.namespace,BUCKET_NAME:.status.bucketName,READY:.status.bucketReady
```

See [BackupStorageLocation](https://velero.io/docs/v1.17/api-types/backupstoragelocation/) in the Velero docs.

Check that creation was successful:
```bash
k get BackupStorageLocation -n cozy-velero    
```

Output should be similar to:
```bash
NAME      PHASE       LAST VALIDATED   AGE    DEFAULT
default   Available   5s               3d9h   true
```

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

A **strategy** describes [Velero Backup](https://velero.io/docs/v1.17/api-types/backup/) template. It is a reusable template referenced by BackupClasses.

In a strategy you define:

- **Scope**: namespaces and resources (e.g. a tenant namespace or resources by label).
- **Volume handling**: whether to snapshot volumes and use `snapshotMoveData`.
- **Retention**: default backup TTL.

Check the CRD group, version, and kind in your cluster:

```bash
kubectl get crd | grep -i backup
kubectl explain <strategy-kind> --recursive
```

Example strategy for VMInstance (includes all VM resources and attached volumes):

```yaml
apiVersion: strategy.backups.cozystack.io/v1alpha1
kind: Velero
metadata:
  name: vminstance-strategy
spec:
  template:
    restoreSpec:
      existingResourcePolicy: update
      includedNamespaces:
        - '{{ .Application.metadata.namespace }}'
      orLabelSelectors:
        - matchLabels:
            app.kubernetes.io/instance: 'vm-instance-{{ .Application.metadata.name }}'
        - matchLabels:
            apps.cozystack.io/application.kind: '{{ .Application.kind }}'
            apps.cozystack.io/application.name: '{{ .Application.metadata.name }}'
      includedResources:
        - helmreleases.helm.toolkit.fluxcd.io
        - virtualmachines.kubevirt.io
        - virtualmachineinstances.kubevirt.io
        - pods
        - persistentvolumeclaims
        - configmaps
        - secrets
        - controllerrevisions.apps
      includeClusterResources: false
      excludedResources:
        - datavolumes.cdi.kubevirt.io

    spec:
      includedNamespaces:
        - '{{ .Application.metadata.namespace }}'
      orLabelSelectors:
        - matchLabels:
            app.kubernetes.io/instance: 'vm-instance-{{ .Application.metadata.name }}'
        - matchLabels:
            apps.cozystack.io/application.kind: '{{ .Application.kind }}'
            apps.cozystack.io/application.name: '{{ .Application.metadata.name }}'
      includedResources:
        - helmreleases.helm.toolkit.fluxcd.io
        - virtualmachines.kubevirt.io
        - virtualmachineinstances.kubevirt.io
        - pods
        - datavolumes.cdi.kubevirt.io
        - persistentvolumeclaims
        - configmaps
        - secrets
        - controllerrevisions.apps
      includeClusterResources: false
      storageLocation: '{{ .Parameters.backupStorageLocationName }}'
      volumeSnapshotLocations:
        - '{{ .Parameters.backupStorageLocationName }}'
      snapshotVolumes: true
      snapshotMoveData: true
      ttl: 720h0m0s
      itemOperationTimeout: 24h0m0s
```

Example strategy for VMDisk (disk and its volume only):

```yaml
apiVersion: strategy.backups.cozystack.io/v1alpha1
kind: Velero
metadata:
  name: vmdisk-strategy
spec:
  template:
    restoreSpec:
      existingResourcePolicy: update
      includedNamespaces:
        - '{{ .Application.metadata.namespace }}'
      orLabelSelectors:
        - matchLabels:
            app.kubernetes.io/instance: 'vm-disk-{{ .Application.metadata.name }}'
        - matchLabels:
            apps.cozystack.io/application.kind: '{{ .Application.kind }}'
            apps.cozystack.io/application.name: '{{ .Application.metadata.name }}'
      includedResources:
        - helmreleases.helm.toolkit.fluxcd.io
        - persistentvolumeclaims
        - configmaps
      includeClusterResources: false

    spec:
      includedNamespaces:
        - '{{ .Application.metadata.namespace }}'
      orLabelSelectors:
        - matchLabels:
            app.kubernetes.io/instance: 'vm-disk-{{ .Application.metadata.name }}'
        - matchLabels:
            apps.cozystack.io/application.kind: '{{ .Application.kind }}'
            apps.cozystack.io/application.name: '{{ .Application.metadata.name }}'
      includedResources:
        - helmreleases.helm.toolkit.fluxcd.io
        - persistentvolumeclaims
        - configmaps
      includeClusterResources: false
      storageLocation: '{{ .Parameters.backupStorageLocationName }}'
      volumeSnapshotLocations:
        - '{{ .Parameters.backupStorageLocationName }}'
      snapshotVolumes: true
      snapshotMoveData: true
      ttl: 720h0m0s
      itemOperationTimeout: 24h0m0s
```

Template variables (`{{ .Application.* }}` and `{{ .Parameters.* }}`) are resolved from the ApplicationRef in the BackupJob/Plan and the parameters defined in the BackupClass.

Don't forget to apply it into management cluster:

```bash
kubectl apply -f velero-backup-strategy.yaml
```

## 3. Create a BackupClass

A **BackupClass** binds a strategy to applications, you can define some Parameters

Verify the BackupClass CRD in your cluster:

```bash
kubectl get backupclasses
kubectl explain backupclasses.spec --recursive
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
      name: vminstance-strategy
    application:
      kind: VMInstance
      apiGroup: apps.cozystack.io
    parameters:
      backupStorageLocationName: default
  - strategyRef:
      apiGroup: strategy.backups.cozystack.io
      kind: Velero
      name: vmdisk-strategy
    application:
      kind: VMDisk
      apiGroup: apps.cozystack.io
    parameters:
      backupStorageLocationName: default
```

Apply and list:

```bash
kubectl apply -f backupclass.yaml
kubectl get backupclasses
```

## 4. How users run backups

Once strategies and BackupClasses are in place, **tenant users** can run backups without touching Velero or storage configuration:

- **One-off backup**: create a [BackupJob]({{% ref "/docs/v1.1/virtualization/backup-and-recovery#one-off-backup" %}}) that references a BackupClass.
- **Scheduled backups**: create a [Plan]({{% ref "/docs/v1.1/virtualization/backup-and-recovery#scheduled-backup" %}}) with a cron schedule and a BackupClass reference.

Direct use of Velero CRDs (`Backup`, `Schedule`, `Restore`) remains available for advanced or recovery scenarios:

```bash
kubectl get backup.velero.io -n cozy-velero
kubectl get schedule.velero.io -n cozy-velero
kubectl get restores.velero.io -n cozy-velero
```

If the [Velero CLI](https://velero.io/docs/v1.17/basic-install/#install-the-cli) is installed, you can also run:

```bash
velero -n cozy-velero backup get
velero -n cozy-velero schedule get
velero -n cozy-velero restore get
```

To inspect the Velero logs, use the following command:

```bash
kubectl logs -n cozy-velero -l app.kubernetes.io/name=velero --tail=100
```

## 5. Restore from a backup

Once strategies and BackupClasses are in place, tenant users can restore from a backup using **RestoreJob** resources. See the [Backup and Recovery]({{% ref "/docs/v1.1/virtualization/backup-and-recovery" %}}) guide for restore instructions covering VMInstance and VMDisk in-place restores.
