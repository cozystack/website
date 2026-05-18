---
title: "Object Storage"
linkTitle: "Object Storage"
description: "S3-compatible object storage in Cozystack using SeaweedFS and COSI"
weight: 10
---

Cozystack provides S3-compatible object storage powered by [SeaweedFS](https://github.com/seaweedfs/seaweedfs) and the [SeaweedFS COSI Driver](https://github.com/seaweedfs/seaweedfs-cosi-driver/).

## How It Works

Object storage in Cozystack is built from several layers:

1. **SeaweedFS** runs as a cluster service in the tenant namespace, providing the S3 backend.
2. **Storage pools** (optional) partition volume servers by disk type (SSD, HDD, NVMe), each creating its own set of COSI resources.
3. **BucketClasses** define how buckets are provisioned. Each pool creates a standard and a `-lock` BucketClass (for object locking).
4. **BucketAccessClasses** define credential policies: read-write and read-only.
5. **Buckets** are user-facing resources that claim storage from a BucketClass and create per-user credentials via BucketAccess.

```text
SeaweedFS Cluster
  └── Storage Pool "ssd" (diskType: ssd)
  │     ├── BucketClass:       tenant-seaweedfs-ssd
  │     ├── BucketClass:       tenant-seaweedfs-ssd-lock
  │     ├── BucketAccessClass: tenant-seaweedfs-ssd          (readwrite)
  │     └── BucketAccessClass: tenant-seaweedfs-ssd-readonly (readonly)
  └── Storage Pool "hdd" (diskType: hdd)
        ├── BucketClass:       tenant-seaweedfs-hdd
        ├── ...
```

## Guides

- [Storage Pools]({{% ref "storage-pools" %}}) -- configure SeaweedFS storage pools for tiered storage
- [Buckets]({{% ref "buckets" %}}) -- create buckets and manage user credentials

## Reference

- [SeaweedFS Service Reference]({{% ref "/docs/next/operations/services/seaweedfs" %}}) -- auto-generated parameter table for the SeaweedFS package
- [SeaweedFS Multi-DC Configuration]({{% ref "/docs/next/operations/stretched/seaweedfs-multidc" %}}) -- deploying SeaweedFS across multiple data centres
