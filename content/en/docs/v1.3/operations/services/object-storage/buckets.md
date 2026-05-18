---
title: "Buckets and Users"
linkTitle: "Buckets"
description: "Create S3 buckets and manage user credentials"
weight: 20
---

The Bucket application creates an S3 bucket via COSI and provisions per-user credentials as Kubernetes Secrets.

## Creating a Bucket

A minimal bucket uses the default BucketClass and creates no users:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
  namespace: tenant-example
spec: {}
```

This provisions a BucketClaim against the default BucketClass (`tenant-example`).
To make the bucket useful, add at least one user (see [Users](#users) below).

## Selecting a Storage Pool

If your SeaweedFS instance defines [storage pools]({{% ref "storage-pools" %}}), use the `storagePool` field to target a specific pool:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
  namespace: tenant-example
spec:
  storagePool: ssd
```

This provisions the BucketClaim against the `tenant-example-ssd` BucketClass.

When `storagePool` is empty (the default), the bucket uses the default BucketClass.

## Object Locking

To create a bucket with object locking enabled, set `locking: true`:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
  namespace: tenant-example
spec:
  storagePool: ssd
  locking: true
```

This provisions the BucketClaim against the `-lock` BucketClass (e.g. `tenant-example-ssd-lock`).
Lock-enabled BucketClasses use a `Retain` deletion policy and configure COMPLIANCE-mode object locking with a default retention period.

{{< note >}}
Object locking cannot be enabled or disabled after bucket creation. Create a new bucket if you need to change this setting.
{{< /note >}}

## Users

The `users` map defines named S3 users for the bucket.
Each entry creates a COSI BucketAccess resource and a corresponding Kubernetes Secret with S3 credentials.

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
  namespace: tenant-example
spec:
  storagePool: ssd
  users:
    admin: {}
    reader:
      readonly: true
```

This creates two users:

| User | Access | BucketAccessClass Used | Secret Name |
| --- | --- | --- | --- |
| `admin` | read-write | `tenant-example-ssd` | `my-bucket-admin` |
| `reader` | read-only | `tenant-example-ssd-readonly` | `my-bucket-reader` |

### User Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `readonly` | `bool` | `false` | When `true`, provisions credentials from the `-readonly` BucketAccessClass |

### Accessing Credentials

Each user gets a Kubernetes Secret named `{bucket-name}-{username}` in the same namespace.
The Secret contains S3 credentials provisioned by the COSI driver:

```bash
kubectl get secret my-bucket-admin -n tenant-example -o yaml
```

The Secret contains the fields needed to configure an S3 client (endpoint, access key, secret key).
The exact fields depend on the COSI driver implementation.

### Rotating Credentials

Bucket user credentials (access key and secret key) are generated once when the user is first created and cannot be updated in place.
To rotate credentials for a user, remove the user from the `users` map and apply, then add the user back and apply again:

```yaml
# Step 1: remove the user to delete existing credentials
spec:
  users: {}
```

```yaml
# Step 2: re-add the user to provision a fresh set of credentials
spec:
  users:
    admin: {}
```

{{< warning >}}
Any applications using the old credentials will lose access between step 1 and step 2.
Update your applications with the new credentials from the Secret after step 2 completes.
{{< /warning >}}

## BucketClass Selection Logic

The BucketClass name is composed from three parts:

```text
{seaweedfs-namespace}[-{storagePool}][-lock]
```

| storagePool | locking | BucketClass Used |
| --- | --- | --- |
| *(empty)* | `false` | `tenant-example` |
| *(empty)* | `true` | `tenant-example-lock` |
| `ssd` | `false` | `tenant-example-ssd` |
| `ssd` | `true` | `tenant-example-ssd-lock` |

Similarly, the BucketAccessClass is composed as:

```text
{seaweedfs-namespace}[-{storagePool}][-readonly]
```

## Complete Example

Deploy a bucket on the `ssd` pool with one admin user and one read-only user:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Bucket
metadata:
  name: media-assets
  namespace: tenant-example
spec:
  storagePool: ssd
  locking: false
  users:
    app:
      readonly: false
    backup-reader:
      readonly: true
```

After the bucket is provisioned, retrieve the credentials:

```bash
# Read-write credentials for the "app" user
kubectl get secret media-assets-app -n tenant-example \
  -o jsonpath='{.data}' | jq 'map_values(@base64d)'

# Read-only credentials for the "backup-reader" user
kubectl get secret media-assets-backup-reader -n tenant-example \
  -o jsonpath='{.data}' | jq 'map_values(@base64d)'
```

## Related Documentation

- [Storage Pools]({{% ref "storage-pools" %}}) -- configure tiered storage for pool selection
- [SeaweedFS Service Reference]({{% ref "/docs/v1.3/operations/services/seaweedfs" %}}) -- full parameter reference
