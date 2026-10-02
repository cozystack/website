---
title: "Application Backup and Recovery"
linkTitle: "Backup and Recovery"
description: "Back up and restore managed databases (Postgres, MariaDB, ClickHouse) with BackupJob, Plan, and RestoreJob."
weight: 4
---

This guide covers backing up and restoring **Cozystack-managed databases** — Postgres, MariaDB, and ClickHouse — as a tenant user: running one-off and scheduled backups, checking status, and restoring from a backup either in place or into a separate target instance.

{{% alert color="info" %}}
**Storage, credentials, and the `BackupClass` are admin-provisioned.** Before you can run a `BackupJob`, an administrator provisions the S3 storage and the per-application credential Secrets your driver expects, and creates the cluster-scoped `BackupClass` you reference. Ask your administrator for:

- the `BackupClass` name to use for your application Kind (you cannot list `BackupClass` resources under your tenant kubeconfig — they are cluster-scoped);
- confirmation that the per-application credential Secrets exist in your namespace for every managed-DB application you want to back up.

Admins follow the [Managed Application Backup Configuration]({{% ref "/docs/v1.4/operations/services/managed-app-backup-configuration" %}}) guide.
{{% /alert %}}

{{% alert color="warning" %}}
**These backups are data-only.** Each strategy snapshots the database contents through the operator's native mechanism (CloudNativePG barman, mariadb-operator dumps, Altinity `clickhouse-backup`). They do **not** capture the `apps.cozystack.io/*` CR, its `HelmRelease`, chart values, or operator-managed Secrets.

To restore you must either:
- keep the source application alive and restore in place (each driver re-bootstraps data into the existing operator-managed cluster), **or**
- pre-provision an empty target application of the same Kind, then restore into it.

For backups that include the application's Helm release, CRs, and PVC snapshots (used for VMInstance / VMDisk), see [Backup and Recovery (VMs)]({{% ref "/docs/v1.4/virtualization/backup-and-recovery" %}}).
{{% /alert %}}

## Prerequisites

- A `BackupClass` name handed to you by your administrator (for example, `postgres-data-backup` for a `Postgres` application).
- An existing managed-DB application (`Postgres`, `MariaDB`, or `ClickHouse`) in your tenant namespace.
- `kubectl` and a tenant kubeconfig with the `tenant-<ns>-admin` role.

The examples below assume `tenant-user` for the tenant namespace; substitute your own.

## Run a backup

### One-off backup

Use a `BackupJob` for an ad-hoc backup (for example, before a risky change):

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: BackupJob
metadata:
  name: my-postgres-adhoc
  namespace: tenant-user
spec:
  applicationRef:
    apiGroup: apps.cozystack.io
    kind: Postgres
    name: my-postgres
  backupClassName: postgres-data-backup
```

```bash
kubectl apply -f backupjob.yaml
kubectl -n tenant-user get backupjobs
kubectl -n tenant-user describe backupjob my-postgres-adhoc
```

When the `BackupJob` reaches `phase: Succeeded`, the driver creates a `Backup` object with the same name. That name is what you reference when restoring.

Replace `Postgres` / `postgres-data-backup` with `MariaDB` / `mariadb-data-backup` or `ClickHouse` / `clickhouse-data-backup` for the other drivers.

### Scheduled backup

Use a `Plan` for cron-driven recurring backups:

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: Plan
metadata:
  name: my-postgres-daily
  namespace: tenant-user
spec:
  applicationRef:
    apiGroup: apps.cozystack.io
    kind: Postgres
    name: my-postgres
  backupClassName: postgres-data-backup
  schedule:
    type: cron
    cron: "0 */6 * * *"   # every 6 hours
```

Each scheduled run creates a `BackupJob` (and, on success, a `Backup`) named after the `Plan` with a timestamp suffix.

```bash
kubectl apply -f plan.yaml
kubectl -n tenant-user get plans
kubectl -n tenant-user get backupjobs -l backups.cozystack.io/plan=my-postgres-daily
```

## Check backup status

List `BackupJob` and `Backup` resources in the namespace:

```bash
kubectl -n tenant-user get backupjobs
kubectl -n tenant-user get backups
```

Inspect a failed run:

```bash
kubectl -n tenant-user get backupjob my-postgres-adhoc -o jsonpath='{.status.message}'
kubectl -n tenant-user describe backupjob my-postgres-adhoc
kubectl -n tenant-user get events --field-selector involvedObject.name=my-postgres-adhoc
```

If `status.message` does not pinpoint the failure, hand the `BackupJob` name to your administrator and they will inspect the operator-native CR the driver created (see [Tenant escalation: driver-side diagnostics]({{% ref "/docs/v1.4/operations/services/managed-app-backup-configuration#tenant-escalation-driver-side-diagnostics" %}}) in the admin guide).

## Restore in place

An **in-place restore** replays the backup into the **same** application. Use this to roll back accidental deletion or corruption on a live database you intend to keep using under the same name.

{{% alert color="warning" %}}
In-place restore is **destructive**. Each driver wipes or replaces existing data on the source application; any writes since the backup point are lost. If you cannot afford to lose recent writes, use [Restore to a copy](#restore-to-a-copy) instead.
{{% /alert %}}

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: RestoreJob
metadata:
  name: my-postgres-restore-inplace
  namespace: tenant-user
spec:
  backupRef:
    name: my-postgres-adhoc
  # targetApplicationRef omitted: driver restores into Backup.spec.applicationRef.
  # options:
  #   recoveryTime: "2026-05-01T12:00:00Z"   # Postgres only; RFC3339 PITR
```

```bash
kubectl apply -f restorejob.yaml
kubectl -n tenant-user get restorejobs
kubectl -n tenant-user describe restorejob my-postgres-restore-inplace
```

### Per-driver caveats

- **Postgres (CNPG)** — the driver deletes the live `cnpg.io/Cluster` and its PVCs, then re-bootstraps from the Barman archive. Connections drop for the duration. `spec.options.recoveryTime` (RFC3339) is supported for point-in-time recovery; omit it to restore to the latest WAL.
- **MariaDB** — the operator replays the logical dump into the live `MariaDB` via `mariadb-import`. Pre-existing tables will collide; pre-truncate the relevant schemas if your dump does not include `DROP TABLE`.
- **ClickHouse** — the Altinity strategy does **not** pass `clickhouse-backup --rm`. You are responsible for dropping conflicting tables on the source before submitting the `RestoreJob`; otherwise the operation fails with a duplicate-table error.

## Restore to a copy

A **to-copy restore** replays the backup into a **different**, freshly-provisioned application of the same Kind. Use this for disaster-recovery drills, side-by-side validation, branch databases, or migrating to a new version of the upstream operator.

First, provision an empty target application with the same Kind. For example, an empty `Postgres`:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Postgres
metadata:
  name: my-postgres-restored
  namespace: tenant-user
spec:
  # ...same shape as the source, no bootstrap data required...
```

Wait for the target to become Ready, then submit a `RestoreJob` that points at it:

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: RestoreJob
metadata:
  name: my-postgres-restore-to-copy
  namespace: tenant-user
spec:
  backupRef:
    name: my-postgres-adhoc
  targetApplicationRef:
    apiGroup: apps.cozystack.io
    kind: Postgres
    name: my-postgres-restored
```

The source application stays untouched. Cross-namespace restores are **not** supported — `targetApplicationRef` is a local reference; the target must live in the same namespace as the `RestoreJob`.

## Limitations and lifecycle

- **Data-only scope.** Application CRs, HelmReleases, chart values, and operator-managed Secrets (e.g. `cnpg.io` superuser secret, `clickhouse-installation` users) are not captured. Pre-provision the target application before a to-copy restore.
- **Archive retention is driver-owned.** Deleting a Cozystack `Backup` CR removes the artefact reference but leaves the actual S3 object intact. Each driver enforces its own retention:
  - CNPG: `retentionPolicy` on the strategy (admin-owned; default `30d` in the admin example).
  - MariaDB: `cleanupStrategy` on the operator-side `Backup` CR or rotation at the bucket level (admin-owned).
  - ClickHouse: governed by the in-pod sidecar's retention configuration. To purge an archive ahead of schedule, ask your administrator — the call goes against the `clickhouse-backup` HTTP API on the sidecar.
- **ClickHouse depends on the in-chart sidecar.** The Altinity strategy is a thin HTTP client; the backup itself runs inside each `chi-*` Pod via `clickhouse-backup`. Disabling `backup.enabled` on the application also disables the BackupClass flow.

## Troubleshooting

If a `BackupJob` or `RestoreJob` ends in `phase: Failed`, start with what you can see in your namespace:

```bash
kubectl -n tenant-user get backupjob my-postgres-adhoc -o jsonpath='{.status.message}'
kubectl -n tenant-user get restorejob my-postgres-restore-inplace -o jsonpath='{.status.message}'
kubectl -n tenant-user describe backupjob my-postgres-adhoc
kubectl -n tenant-user get events --field-selector involvedObject.name=my-postgres-adhoc
```

If those do not explain the failure, the next layer of diagnostics lives on the operator-native CR the driver created (`cnpg.io/Backup`, `k8s.mariadb.com/Backup`, or the ClickHouse strategy `Pod` logs). These resources are not reachable under the tenant kubeconfig — hand the `BackupJob` name to your administrator and they will follow [Tenant escalation: driver-side diagnostics]({{% ref "/docs/v1.4/operations/services/managed-app-backup-configuration#tenant-escalation-driver-side-diagnostics" %}}).

## See also

- [Managed Application Backup Configuration]({{% ref "/docs/v1.4/operations/services/managed-app-backup-configuration" %}}) — how administrators define strategies and `BackupClass` resources.
- [Backup and Recovery (VMs)]({{% ref "/docs/v1.4/virtualization/backup-and-recovery" %}}) — the parallel guide for VMInstance / VMDisk backups (HelmRelease + CRs + PVC snapshots).
- [Velero Backup Configuration]({{% ref "/docs/v1.4/operations/services/velero-backup-configuration" %}}) — administrator setup for the Velero-driven VM backups.
