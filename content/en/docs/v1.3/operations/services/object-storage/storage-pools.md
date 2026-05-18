---
title: "Storage Pools"
linkTitle: "Storage Pools"
description: "Configure SeaweedFS storage pools for tiered object storage"
weight: 10
---

Storage pools let you partition SeaweedFS volume servers by disk type.
Each pool creates a separate Volume StatefulSet tagged with a SeaweedFS `diskType`, and a matching set of COSI resources (BucketClasses and BucketAccessClasses) that buckets can reference.

## When to Use Pools

Use storage pools when your cluster has different storage tiers and you want to control which tier a bucket uses.
For example, you might have fast NVMe drives for hot data and large HDD drives for archival storage.

If all your volume servers use the same storage, you do not need pools -- the default BucketClass is sufficient.

## Enabling SeaweedFS on a Tenant

Before configuring pools, enable SeaweedFS on the tenant:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '{
  "spec":{
    "seaweedfs": true
  }
}'
```

Wait for the SeaweedFS HelmRelease to become ready:

```bash
kubectl -n tenant-root get hr seaweedfs
```

Expected output:

```console
NAME        AGE   READY   STATUS
seaweedfs   2m    True    Helm upgrade succeeded for release tenant-root/seaweedfs.v1 with chart seaweedfs@...
```

## Pool Configuration

Once SeaweedFS is running, patch its HelmRelease to add storage pools:

```bash
kubectl patch -n tenant-root helmreleases.helm.toolkit.fluxcd.io seaweedfs --type=merge -p '{
  "spec":{
    "values":{
      "volume":{
        "pools":{
          "ssd":{
            "diskType": "ssd",
            "size": "50Gi",
            "storageClass": "local-nvme"
          },
          "hdd":{
            "diskType": "hdd",
            "size": "500Gi",
            "storageClass": "local-hdd",
            "replicas": 3
          }
        }
      }
    }
  }
}'
```

The equivalent full resource looks like this:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: SeaweedFS
metadata:
  name: seaweedfs
  namespace: tenant-example
spec:
  host: s3.example.com
  topology: Simple
  volume:
    replicas: 2
    size: 100Gi
    pools:
      ssd:
        diskType: ssd
        size: 50Gi
        storageClass: local-nvme
      hdd:
        diskType: hdd
        size: 500Gi
        storageClass: local-hdd
        replicas: 3
```

### Pool Parameters

| Parameter | Required | Description |
| --- | --- | --- |
| `diskType` | Yes | SeaweedFS disk type tag (lowercase alphanumeric, e.g. `ssd`, `hdd`, `nvme`) |
| `replicas` | No | Number of volume server replicas. Defaults to `volume.replicas` |
| `size` | No | PVC size per replica. Defaults to `volume.size` |
| `storageClass` | No | Kubernetes StorageClass for PVCs. Defaults to `volume.storageClass` |
| `resources` | No | Explicit CPU/memory limits. Defaults to `volume.resources` |
| `resourcesPreset` | No | Sizing preset when `resources` is omitted. Defaults to `volume.resourcesPreset` |

### Naming Rules

Pool names must be valid DNS labels (lowercase letters, digits, hyphens). The following suffixes are reserved and must not be used as pool names:

- Names ending in `-lock` (reserved for object-lock BucketClasses)
- Names ending in `-readonly` (reserved for read-only BucketAccessClasses)

## COSI Resources Created per Pool

Each pool automatically creates four COSI resources:

| Resource | Name Pattern | Purpose |
| --- | --- | --- |
| BucketClass | `{namespace}-{pool}` | Standard bucket provisioning |
| BucketClass | `{namespace}-{pool}-lock` | Bucket provisioning with object locking enabled |
| BucketAccessClass | `{namespace}-{pool}` | Read-write credentials |
| BucketAccessClass | `{namespace}-{pool}-readonly` | Read-only credentials |

For example, a pool named `ssd` in namespace `tenant-example` creates:

- BucketClass `tenant-example-ssd`
- BucketClass `tenant-example-ssd-lock`
- BucketAccessClass `tenant-example-ssd`
- BucketAccessClass `tenant-example-ssd-readonly`

{{< note >}}
A default (non-pool) set of COSI resources is always created using just the namespace name (e.g. `tenant-example`, `tenant-example-lock`).
These correspond to the volume servers running with the top-level `volume.diskType` setting.
{{< /note >}}

## MultiZone Topology with Pools

In MultiZone topology, pools are defined per zone under `volume.zones[zone].pools`.

### Zone Parameters

Each zone accepts the following parameters in addition to pools:

| Parameter | Required | Description |
| --- | --- | --- |
| `replicas` | No | Number of volume server replicas in this zone. Defaults to `volume.replicas` |
| `size` | No | PVC size per replica. Defaults to `volume.size` |
| `storageClass` | No | Kubernetes StorageClass for PVCs. Defaults to `volume.storageClass` |
| `dataCenter` | No | SeaweedFS data center name. Defaults to the zone key name (e.g. zone `dc1` gets `dataCenter: dc1`) |
| `nodeSelector` | No | YAML nodeSelector for scheduling volume server pods. Defaults to `topology.kubernetes.io/zone: <zoneName>` |
| `pools` | No | Map of storage pools for this zone. Same structure as `volume.pools` |

### Example

Patch the SeaweedFS HelmRelease to add per-zone pools:

```bash
kubectl patch -n tenant-example helmreleases.helm.toolkit.fluxcd.io seaweedfs --type=merge -p '{
  "spec":{
    "values":{
      "volume":{
        "zones":{
          "dc1":{
            "pools":{
              "ssd":{"diskType": "ssd", "size": "50Gi"},
              "hdd":{"diskType": "hdd", "size": "500Gi"}
            }
          },
          "dc2":{
            "pools":{
              "ssd":{"diskType": "ssd", "size": "50Gi"},
              "hdd":{"diskType": "hdd", "size": "500Gi"}
            }
          }
        }
      }
    }
  }
}'
```

In this example, zone `dc1` automatically gets `dataCenter: dc1` and `nodeSelector: {topology.kubernetes.io/zone: dc1}`.

To override these defaults, specify them explicitly:

```yaml
volume:
  zones:
    us-east-1a:
      dataCenter: us-east
      nodeSelector:
        topology.kubernetes.io/zone: us-east-1a
        node.kubernetes.io/instance-type: storage-optimized
      pools:
        ssd:
          diskType: ssd
          size: 50Gi
```

The equivalent full resource with explicit zone settings:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: SeaweedFS
metadata:
  name: seaweedfs
  namespace: tenant-example
spec:
  host: s3.example.com
  topology: MultiZone
  volume:
    replicas: 2
    size: 100Gi
    zones:
      dc1:
        pools:
          ssd:
            diskType: ssd
            size: 50Gi
          hdd:
            diskType: hdd
            size: 500Gi
      dc2:
        pools:
          ssd:
            diskType: ssd
            size: 50Gi
          hdd:
            diskType: hdd
            size: 500Gi
```

Each zone+pool combination creates its own Volume StatefulSet.
In this example, that means four StatefulSets: `seaweedfs-volume-dc1-ssd`, `seaweedfs-volume-dc1-hdd`, `seaweedfs-volume-dc2-ssd`, and `seaweedfs-volume-dc2-hdd`.

COSI resources are deduplicated across zones -- if both `dc1` and `dc2` define a pool named `ssd` with the same `diskType`, only one set of BucketClass/BucketAccessClass resources is created.

{{< alert color="warning" >}}
`volume.pools` (top-level) is not allowed in MultiZone topology. Define pools inside each zone instead.
{{< /alert >}}

## Verification

After deploying SeaweedFS with pools, verify the resources:

```bash
# Check that volume server StatefulSets were created for each pool
kubectl get statefulset -n tenant-example -l app.kubernetes.io/name=seaweedfs

# Check BucketClasses
kubectl get bucketclass

# Check BucketAccessClasses
kubectl get bucketaccessclass
```

You should see BucketClass and BucketAccessClass resources for each pool name.

## Related Documentation

- [Buckets]({{% ref "buckets" %}}) -- create buckets targeting a specific storage pool
- [SeaweedFS Service Reference]({{% ref "/docs/v1.3/operations/services/seaweedfs" %}}) -- full parameter reference
- [SeaweedFS Multi-DC Configuration]({{% ref "/docs/v1.3/operations/stretched/seaweedfs-multidc" %}}) -- multi-DC deployment guide
