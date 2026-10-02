---
title: "Backups with the Velero addon"
linkTitle: "Backups with the Velero addon"
description: "Enable the Velero addon in a tenant Kubernetes cluster, point it at a SeaweedFS bucket, and back up and restore workloads."
weight: 60
---

The `velero` addon of the [Managed Kubernetes]({{% ref "/docs/v1.3/kubernetes" %}}) application installs [Velero](https://velero.io/) inside a tenant Kubernetes cluster. Combined with a tenant [Bucket]({{% ref "/docs/v1.3/operations/services/object-storage/buckets" %}}), it lets tenant users back up workloads to S3 and restore them later.

{{% alert color="info" %}}
This guide is for the **tenant-side** Velero addon, which runs inside a tenant Kubernetes cluster and is operated by the tenant user.

For the platform-level Velero used by cluster administrators to back up `VMInstance`/`VMDisk` resources from the management cluster, see [Velero Backup Configuration]({{% ref "/docs/v1.3/operations/services/velero-backup-configuration" %}}).
{{% /alert %}}

## What the addon installs

When `spec.addons.velero.enabled` is `true` on a `Kubernetes` resource, Cozystack deploys Velero into the `cozy-velero` namespace of the tenant cluster. The chart wraps the upstream `vmware-tanzu/velero` chart as a subchart and pre-configures the AWS S3 plugin, the KubeVirt plugin, the node agent (file-system backup), and the CSI feature (`features: EnableCSI`). The `kubevirt-snapshots` `VolumeSnapshotClass` (driver `csi.kubevirt.io`) ships in every tenant cluster and is labelled for Velero's CSI plugin, so volume snapshots work out of the box.

The default install does not create a `BackupStorageLocation`. You provide one through `valuesOverride` — typically pointing at a SeaweedFS `Bucket` that lives in your tenant.

## Prerequisites

- SeaweedFS is enabled on your tenant (`spec.seaweedfs: true`). See [Object Storage]({{% ref "/docs/v1.3/operations/services/object-storage" %}}).
- The [`velero` CLI](https://velero.io/docs/v1.17/basic-install/#install-the-cli) is installed locally.
- You have admin access to the tenant namespace in the management cluster (to create `Bucket` and `Kubernetes` resources) and can fetch the resulting kubeconfig.

## 1. Create a bucket for backups

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Bucket
metadata:
  name: velero-backups
  namespace: tenant-example
spec:
  users:
    velero: {}
```

Cozystack creates a credentials secret named `bucket-<bucket-name>-<user>-credentials` with `accessKey`, `secretKey`, `endpoint`, and `bucketName` fields. Read the values you will plug into the addon configuration:

```bash
NS=tenant-example
SECRET=bucket-velero-backups-velero-credentials

BUCKET_NAME=$(kubectl get secret "$SECRET" -n "$NS" -o jsonpath='{.data.bucketName}' | base64 -d)
ACCESS_KEY=$(kubectl get secret "$SECRET" -n "$NS" -o jsonpath='{.data.accessKey}' | base64 -d)
SECRET_KEY=$(kubectl get secret "$SECRET" -n "$NS" -o jsonpath='{.data.secretKey}' | base64 -d)
ENDPOINT=$(kubectl get secret "$SECRET" -n "$NS" -o jsonpath='{.data.endpoint}' | base64 -d)
echo "$BUCKET_NAME / https://$ENDPOINT"
```

`endpoint` is a hostname only — Velero needs `https://$ENDPOINT` as the S3 URL.

## 2. Deploy a tenant cluster with the Velero addon

{{% alert color="warning" %}}
The addon chart embeds the upstream Velero chart **as a subchart under the `velero` key**. Override values **must** be nested under `velero:` — placing them at the top level (e.g. `valuesOverride.configuration.backupStorageLocation`) is silently ignored.
{{% /alert %}}

Render and apply a `Kubernetes` manifest using the values from the previous step:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps.cozystack.io/v1alpha1
kind: Kubernetes
metadata:
  name: my-cluster
  namespace: $NS
spec:
  host: my-cluster.tenant-example.cozystack.example.com
  addons:
    velero:
      enabled: true
      valuesOverride:
        velero:
          credentials:
            useSecret: true
            secretContents:
              cloud: |
                [default]
                aws_access_key_id=$ACCESS_KEY
                aws_secret_access_key=$SECRET_KEY
          configuration:
            backupStorageLocation:
              - name: default
                provider: aws
                bucket: $BUCKET_NAME
                default: true
                config:
                  region: us-east-1
                  s3ForcePathStyle: "true"
                  s3Url: https://$ENDPOINT
            volumeSnapshotLocation:
              - name: default
                provider: aws
                config:
                  region: us-east-1
EOF
```

Once the cluster is `Ready`, fetch its kubeconfig and point your shell at it:

```bash
kubectl get secret -n "$NS" kubernetes-my-cluster-admin-kubeconfig \
  -o go-template='{{ printf "%s\n" (index .data "admin.conf" | base64decode) }}' \
  > my-cluster-kubeconfig
export KUBECONFIG=$PWD/my-cluster-kubeconfig
```

The remaining steps run against the **tenant** cluster.

## 3. Verify Velero is running

```bash
kubectl -n cozy-velero get deploy
velero -n cozy-velero backup-location get
```

Expected output:

```text
NAME      STATUS      PROVIDER   BUCKET                                            ACCESS MODE   DEFAULT
default   Available   aws        bucket-91bbb59f-30ba-46fe-9a44-535d8332a464       ReadWrite     true
```

`STATUS: Available` means Velero successfully connected to the bucket.

## 4. Back up a namespace

Create a sample workload (skip if you already have one to back up):

```bash
kubectl create namespace demo
kubectl -n demo create configmap demo-cm \
  --from-literal=marker=backup-restore-validation
```

Take the backup:

```bash
velero -n cozy-velero backup create demo-1 \
  --include-namespaces demo --snapshot-move-data
velero -n cozy-velero backup describe demo-1 --details
```

`--snapshot-move-data` uploads CSI snapshot data to the bucket so the backup is self-contained — restores no longer need access to the source PVs.

Wait until `Phase: Completed`.

## 5. Restore from the backup

Simulate a loss by deleting the namespace, then restore it from the backup:

```bash
kubectl delete namespace demo
velero -n cozy-velero restore create \
  --from-backup demo-1
velero -n cozy-velero restore describe demo-1 --details
```

When the restore reaches `Phase: Completed`, the namespace and its objects are recreated. Verify:

```bash
kubectl -n demo get all,configmaps
```

The same pattern restores into a **different** tenant Kubernetes cluster as well — point a second cluster at the same bucket with an identical `addons.velero.valuesOverride`, and `velero backup get` in the second cluster will see `demo-1` once the bucket sync ticks (default interval one minute). See the upstream [migration scenario](https://velero.io/docs/v1.17/migration-case/) for cross-cluster considerations.

## Related

- [Managed Kubernetes — `addons.velero` parameters]({{% ref "/docs/v1.3/kubernetes#parameters" %}})
- [Buckets and Users]({{% ref "/docs/v1.3/operations/services/object-storage/buckets" %}})
- [Velero Backup Configuration (platform admin)]({{% ref "/docs/v1.3/operations/services/velero-backup-configuration" %}})
