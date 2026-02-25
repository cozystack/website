---
title: "Upgrading from v0.41 to v1.0"
linkTitle: "Upgrading to v1.0"
description: "Step-by-step guide for upgrading Cozystack from v0.41.x to v1.0"
weight: 1
---

## Overview

Version 1.0 introduces a major change to the Cozystack control plane: it is now completely modular
and composed of independent packages managed by the new `cozystack-operator`.

Key changes:

- The old installer deployment is replaced by `cozystack-operator`.
- Configuration is no longer stored in ConfigMaps — it is now defined by a `Package` custom resource.
- The assets server is replaced with a single OCI image.
- New CRDs are introduced: `Package` and `PackageSource`.

The underlying entities are still Helm releases, so during the upgrade no workloads are recreated or affected.

## Breaking Changes

This section lists all user-facing breaking changes introduced in v1.0.
Most changes are handled automatically by platform migrations that run during the upgrade.
Review this list before upgrading to understand the impact on your workloads.

{{% alert color="warning" %}}
**FerretDB users**: The FerretDB application has been removed without automatic migration.
You must back up your data **before** upgrading. See [FerretDB removed](#ferretdb-removed) below.
{{% /alert %}}

### MySQL renamed to MariaDB

The `mysql` application has been renamed to `mariadb` to accurately reflect the underlying database engine.

All Kubernetes resources are renamed automatically during the upgrade:

| Resource | Before | After |
|----------|--------|-------|
| Application Kind | `MySQL` | `MariaDB` |
| HelmRelease prefix | `mysql-` | `mariadb-` |
| Service names | `mysql-<name>-primary` | `mariadb-<name>-primary` |
| Secret names | `mysql-<name>-credentials` | `mariadb-<name>-credentials` |
| PVC names | `storage-mysql-<name>-*` | `storage-mariadb-<name>-*` |

{{% alert color="info" %}}
If your applications connect to MySQL services by their Kubernetes DNS name
(e.g. `mysql-mydb-primary.<namespace>.svc`), you will need to update the connection
strings to use the new `mariadb-` prefix after the migration.
{{% /alert %}}

### FerretDB removed

The FerretDB application has been completely removed from the platform. There is no automatic migration.

If you have running FerretDB instances, you must **back up all data before upgrading**.
After the upgrade, FerretDB will no longer be available as a managed application.

### Virtual Machine split into VM Disk and VM Instance

The monolithic `virtual-machine` application has been replaced by two separate applications:

- **vm-disk** — manages virtual machine disk images.
- **vm-instance** — manages virtual machine instances and references disks created by `vm-disk`.

The migration is automatic and preserves:
- Disk data (PersistentVolumes are retained and rebound).
- Kube-OVN IP and MAC addresses.
- LoadBalancer IPs for externally exposed VMs.

Additionally, the `running` boolean field has been replaced by `runStrategy`:

| Old value | New value |
|-----------|-----------|
| `running: true` | `runStrategy: Always` |
| `running: false` | `runStrategy: Halted` |

The `runStrategy` field also accepts `Manual`, `RerunOnFailure`, and `Once` values.

### Monitoring moved to new deployment scheme

The monitoring stack has been restructured. The HelmRelease named `monitoring` in each
tenant namespace is migrated to a new release named `monitoring-system`.

The migration is automatic — all monitoring resources (VictoriaMetrics, Grafana, Alerta,
VLogs) are re-labeled and adopted by the new HelmRelease.

### VPC subnets format changed from map to array

The `subnets` field in VPC (VirtualPrivateCloud) configuration has changed from a map to an array.

**Before:**
```yaml
subnets:
  my-subnet:
    cidr: 10.0.0.0/24
```

**After:**
```yaml
subnets:
  - name: my-subnet
    cidr: 10.0.0.0/24
```

The migration is automatic for existing VPC resources.

### MongoDB users and databases configuration unified

The MongoDB user configuration format has been restructured. Users and databases
are now defined in separate sections.

**Before:**
```yaml
users:
  myuser:
    db: mydb
    roles:
      - name: readWrite
        db: mydb
```

**After:**
```yaml
users:
  myuser: {}
databases:
  mydb:
    roles:
      admin:
        - myuser
```

The migration is automatic for existing MongoDB instances.

### Tenant `isolated` flag removed

The `isolated` field has been removed from Tenant configuration. Network isolation via
NetworkPolicy is now always enforced for all tenants. If you previously relied on
`isolated: false` to allow unrestricted traffic between tenants, this is no longer possible.

### Internal architecture changes

The following internal changes do not affect application workloads directly but are
relevant for automation scripts or custom tooling that interacts with Cozystack internals:

- **Flux AIO** is now installed and managed by the `cozystack-operator` instead of being a standalone component.
- **CozystackResourceDefinition** CRD has been renamed to **ApplicationDefinition**.
- **Legacy installer** components (the `cozystack` Deployment and `cozystack-assets` StatefulSet) have been removed.
- **tenant-root** namespace and HelmRelease are now managed by Helm via the `cozystack-basics` release.

## Prerequisites

### 1. Install required tools

The following tools are required for the migration:

- **kubectl** and **jq** — standard cluster administration tools.
- **helm** — required for installing the new operator.
- **cozypkg** — new CLI for managing Package and PackageSource resources.
  Download from the [Cozystack Releases page](https://github.com/cozystack/cozystack/releases).
- **cozyhr** — optional tool for managing HelmRelease values.
  Download from the [cozyhr repository](https://github.com/cozystack/cozyhr/releases).

### 2. Verify kubectl context

Make sure your current kubectl context points to the cluster you are upgrading:

```bash
kubectl config current-context
```

### 3. Upgrade to the latest v0.41.x

Before migrating to v1.0, make sure you are running the most recent v0.41 patch release.

Check your current version:

```bash
kubectl get configmap -n cozy-system cozystack -o jsonpath='{.metadata.labels.cozystack\.io/version}'
```

If you are on an older version, upgrade to the latest v0.41.x first using the
[standard upgrade procedure]({{% ref "/docs/v0/operations/cluster/upgrade" %}}).

### 4. Verify cluster health

Before upgrading, verify that all HelmReleases are in a healthy state:

```bash
kubectl get hr -A | grep -v "True"
```

If any releases are not `Ready`, resolve those issues before proceeding.

## Upgrade Steps

### Step 1. Install the Cozystack Operator

Install the new operator using Helm from the OCI registry.
This deploys the `cozystack-operator`, installs two new CRDs (`Package` and `PackageSource`),
and creates the `PackageSource` resource for the platform.

```bash
helm upgrade --install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version <TARGET_VERSION> \
  --namespace cozy-system \
  --create-namespace \
  --take-ownership
```

Replace `<TARGET_VERSION>` with the desired release version (e.g., `1.0.0`).

Verify the operator is running:

```bash
kubectl get pods -n cozy-system -l app=cozystack-operator
```

### Step 2. Generate the Platform Package

The migration script reads your existing ConfigMaps (`cozystack`, `cozystack-branding`, `cozystack-scheduling`)
from the `cozy-system` namespace and converts them into a `Package` resource with the new values structure.

Download and run the migration script from the Cozystack repository:

```bash
curl -fsSL https://raw.githubusercontent.com/cozystack/cozystack/main/hack/migrate-to-version-1.0.sh | bash
```

The script will:

1. Read configuration from existing ConfigMaps.
2. Convert old bundle naming (`paas-*`) to new variant naming (`isp-*`).
3. Generate a `Package` resource and display it for review.
4. Prompt for confirmation before applying.

{{% alert color="info" %}}
You can also download the script and run it locally to review it before execution:

```bash
curl -fsSL -o migrate-to-version-1.0.sh \
  https://raw.githubusercontent.com/cozystack/cozystack/main/hack/migrate-to-version-1.0.sh
chmod +x migrate-to-version-1.0.sh
./migrate-to-version-1.0.sh
```
{{% /alert %}}

### Step 3. Monitor the Migration

As soon as the Platform Package is applied, the operator starts the migration process.
Migrations remove the old installer deployment and assets server, transform existing manifests
to the new format, and reconcile all components under the new Package-based management.

Monitor HelmRelease statuses:

```bash
kubectl get hr -A
```

Wait until all releases show `READY: True`.

### Step 4. Clean Up Old ConfigMaps

After verifying that all components are healthy, delete the old ConfigMaps
that are no longer used:

```bash
kubectl delete configmap -n cozy-system cozystack cozystack-branding cozystack-scheduling
```

### Step 5. Verify the Migration

Check that the Platform Package is reconciled:

```bash
kubectl get packages.cozystack.io cozystack.cozystack-platform
```

Run a full cluster health check:

```bash
kubectl get hr -A | grep -v "True"
kubectl get pods -n cozy-system
```

If any HelmReleases are not Ready, check the operator logs for details.

## Troubleshooting

### Operator fails to start

If the operator pod is in CrashLoopBackOff, check the logs:

```bash
kubectl logs -n cozy-system deploy/cozystack-operator --previous
```

### HelmReleases stuck after migration

During the migration, some HelmReleases may temporarily show errors while the operator reconciles them.
Wait a few minutes and check again. If issues persist, consult the
[Troubleshooting Checklist]({{% ref "/docs/v1/operations/troubleshooting/#troubleshooting-checklist" %}}).
