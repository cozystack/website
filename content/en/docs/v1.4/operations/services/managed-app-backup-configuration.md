---
title: "Managed Application Backup Configuration"
linkTitle: "Managed Application Backup Configuration"
description: "Configure strategies and BackupClasses for logical data backups of managed databases (Postgres, MariaDB, ClickHouse)."
weight: 31
---

This guide is for **cluster administrators** who configure backup strategies for Cozystack-managed database applications: Postgres, MariaDB, and ClickHouse. Once strategies and `BackupClass` resources are in place, tenants run backups and restores by creating [BackupJob, Plan, and RestoreJob]({{% ref "/docs/v1.4/applications/backup-and-recovery" %}}) resources with no further admin action.

{{% alert color="info" %}}
This page covers **data-only** backups driven by each operator's native backup mechanism (CloudNativePG barman, mariadb-operator dumps, Altinity `clickhouse-backup`). The `apps.cozystack.io/*` CR, its `HelmRelease`, chart values, and operator-managed Secrets are **not** captured by these strategies.

For backups that bundle Helm release + CRs + PVC snapshots (used by VMInstance / VMDisk), see [Velero Backup Configuration]({{% ref "/docs/v1.4/operations/services/velero-backup-configuration" %}}).
{{% /alert %}}

## Prerequisites

- Administrator access to the Cozystack (management) cluster.
- The `backup-controller` and `backupstrategy-controller` components are installed and running.
- S3-compatible storage reachable from the management cluster — either the in-cluster SeaweedFS provisioned via the `Bucket` application, or any external S3 endpoint.
- The corresponding upstream operator is deployed for each application Kind you want to back up: CloudNativePG, mariadb-operator, or ClickHouse operator. These ship with Cozystack by default.

## How a managed-application strategy works

The flow on every `BackupJob`:

1. A tenant creates a `BackupJob` (or a `Plan` that materialises one on a cron) that references a `BackupClass` and an `apps.cozystack.io/<Kind>` application.
2. The core backup controller resolves the `BackupClass` and matches the application Kind to a driver-specific `strategy.backups.cozystack.io/<Kind>` strategy.
3. The driver renders its strategy template against the live application object (`.Application`) and the BackupClass parameters (`.Parameters`), then creates the operator-native backup CR (`Backup` for mariadb, an HTTP call against the in-pod sidecar for ClickHouse, a barman-driven snapshot in `cnpg.io` for Postgres).
4. On success the driver creates a Cozystack `Backup` artefact in the same namespace; `RestoreJob` resources reference that artefact later.

`BackupClass` is **cluster-scoped**: a single instance covers every tenant namespace.

{{% alert color="info" %}}
Tenant users cannot list `BackupClass` resources under their kubeconfig (cluster-scoped resources are not reachable through the tenant `RoleBinding`). Once you create a `BackupClass`, **publish its name to tenants out-of-band** — in the platform handbook, in the ticket that onboards their application, or in your internal Slack channel. Tenants reference the name verbatim in `BackupJob.spec.backupClassName`.
{{% /alert %}}

## Per-driver setup

The strategies below are written for the in-cluster SeaweedFS `Bucket` application. If you use external S3 storage, drop the `endpointCA` / TLS sections and point the endpoint at your provider.

### Postgres (CNPG strategy)

The CNPG driver delegates to CloudNativePG's native barman backup. Each `BackupJob` is a barman snapshot streamed to S3; `RestoreJob` recreates the `cnpg.io/Cluster` from the archive.

Create the strategy:

```yaml
apiVersion: strategy.backups.cozystack.io/v1alpha1
kind: CNPG
metadata:
  name: postgres-data-cnpg-strategy
spec:
  template:
    serverName: "{{ .Application.metadata.name }}"
    barmanObjectStore:
      destinationPath: "s3://REPLACE_WITH_COSI_BUCKET_NAME/{{ .Application.metadata.name }}/"
      endpointURL: "https://REPLACE_WITH_S3_ENDPOINT"
      retentionPolicy: "30d"
      endpointCA:
        secretRef:
          name: "{{ .Application.metadata.name }}-cnpg-backup-ca"
        key: "ca.crt"
      s3Credentials:
        secretRef:
          name: "{{ .Application.metadata.name }}-cnpg-backup-creds"
      data:
        compression: gzip
      wal:
        compression: gzip
```

Bind the application Kind:

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: BackupClass
metadata:
  name: postgres-data-backup
spec:
  strategies:
    - application:
        apiGroup: apps.cozystack.io
        kind: Postgres
      strategyRef:
        apiGroup: strategy.backups.cozystack.io
        kind: CNPG
        name: postgres-data-cnpg-strategy
```

Per-application Secrets the tenant must provision in the application namespace:

| Secret | Keys | Purpose |
|---|---|---|
| `<app>-cnpg-backup-creds` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 credentials consumed by barman |
| `<app>-cnpg-backup-ca` *(only for self-signed endpoints)* | `ca.crt` | CA bundle the barman client trusts |

Drop the `endpointCA` block in the strategy when your S3 endpoint has a publicly-trusted certificate.

### MariaDB

The MariaDB driver delegates to [mariadb-operator](https://github.com/mariadb-operator/mariadb-operator). Backups materialise as `k8s.mariadb.com/v1alpha1 Backup` CRs (logical `mariadb-dump`); restores materialise as `Restore` CRs that `mariadb-import` the dump back into the live database.

Create the strategy:

```yaml
apiVersion: strategy.backups.cozystack.io/v1alpha1
kind: MariaDB
metadata:
  name: mariadb-data-strategy
spec:
  template:
    storage:
      s3:
        bucket: "REPLACE_WITH_COSI_BUCKET_NAME"
        endpoint: "REPLACE_WITH_S3_ENDPOINT"
        prefix: "{{ .Application.metadata.name }}/"
        accessKeyIdSecretKeyRef:
          name: "{{ .Application.metadata.name }}-mariadb-backup-creds"
          key: "AWS_ACCESS_KEY_ID"
        secretAccessKeySecretKeyRef:
          name: "{{ .Application.metadata.name }}-mariadb-backup-creds"
          key: "AWS_SECRET_ACCESS_KEY"
        tls:
          enabled: true
          caSecretKeyRef:
            name: "{{ .Application.metadata.name }}-mariadb-backup-ca"
            key: "ca.crt"
    compression: gzip
```

The `endpoint` is **path-style without scheme** (e.g. `seaweedfs-s3.<seaweedfs-namespace>.svc:8333` for the default in-cluster SeaweedFS — substitute the namespace where SeaweedFS is deployed in your environment). Drop the `tls` block entirely when the endpoint serves a publicly-trusted certificate.

Bind the application Kind:

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: BackupClass
metadata:
  name: mariadb-data-backup
spec:
  strategies:
    - application:
        apiGroup: apps.cozystack.io
        kind: MariaDB
      strategyRef:
        apiGroup: strategy.backups.cozystack.io
        kind: MariaDB
        name: mariadb-data-strategy
```

Per-application Secrets the tenant must provision in the application namespace:

| Secret | Keys | Purpose |
|---|---|---|
| `<app>-mariadb-backup-creds` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 credentials consumed by mariadb-operator |
| `<app>-mariadb-backup-ca` *(only for self-signed endpoints)* | `ca.crt` | CA bundle for TLS verification |

{{% alert color="info" %}}
The chart-level `backup.*` block in `apps.cozystack.io/MariaDB` (the legacy `mariadb-dump` + `restic` path) is **deprecated** in favour of this BackupClass flow. Existing tenants with `backup.enabled=true` continue to render the legacy resources unchanged.
{{% /alert %}}

### ClickHouse (Altinity strategy)

The Altinity driver does **not** template a backup CR. It renders a small `PodTemplateSpec` that runs `curl + jq` against the in-pod [`clickhouse-backup`](https://github.com/Altinity/clickhouse-backup) HTTP API (port 7171) provided by a sidecar inside every `chi-*` Pod.

{{% alert color="warning" %}}
The Altinity strategy **requires** `backup.enabled=true` on every ClickHouse application instance — that flag is what materialises the in-pod sidecar and the `clickhouse-<release>-backup-api-auth` Secret the strategy authenticates with. Unlike MariaDB, ClickHouse's chart-level `backup.*` block is **not** deprecated; the BackupClass flow piggybacks on the same sidecar.
{{% /alert %}}

Create the strategy. The `template` is a `PodTemplateSpec` driving the sidecar; for the full reference template (with the shell script that POSTs `create_remote` / `restore_remote` and polls the action log) see [`examples/backups/clickhouse/01-create-strategy.sh`](https://github.com/cozystack/cozystack/blob/main/examples/backups/clickhouse/01-create-strategy.sh) in the cozystack repo.

```yaml
apiVersion: strategy.backups.cozystack.io/v1alpha1
kind: Altinity
metadata:
  name: clickhouse-data-altinity-strategy
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: ch-backup-client
          image: alpine:3.19
          env:
            - name: API_USERNAME
              valueFrom:
                secretKeyRef:
                  name: clickhouse-{{ .Release.Name }}-backup-api-auth
                  key: username
            - name: API_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: clickhouse-{{ .Release.Name }}-backup-api-auth
                  key: password
          command: ["/bin/sh", "-c"]
          args:
            # See examples/backups/clickhouse/01-create-strategy.sh for the
            # full script: branches on .Mode (backup|restore) and either
            # POSTs /backup/create_remote or /backup/restore_remote/<name>,
            # then polls /backup/actions for terminal status.
            - |
              # ... (truncated; see linked example)
```

Bind the application Kind. No parameters are required — the strategy template addresses the sidecar by deterministic Pod DNS and reads S3 credentials from the chart-emitted `<release>-backup-s3` Secret directly.

```yaml
apiVersion: backups.cozystack.io/v1alpha1
kind: BackupClass
metadata:
  name: clickhouse-data-backup
spec:
  strategies:
    - application:
        apiGroup: apps.cozystack.io
        kind: ClickHouse
      strategyRef:
        apiGroup: strategy.backups.cozystack.io
        kind: Altinity
        name: clickhouse-data-altinity-strategy
```

## Apply and verify

Apply the strategy and `BackupClass` manifests:

```bash
kubectl apply -f <strategy>.yaml
kubectl apply -f <backupclass>.yaml
```

List the resources:

```bash
kubectl get cnpgs.strategy.backups.cozystack.io
kubectl get mariadbs.strategy.backups.cozystack.io
kubectl get altinities.strategy.backups.cozystack.io
kubectl get backupclasses
```

Each strategy should report no error conditions; each `BackupClass` should list the strategy entries you defined.

## Tenant onboarding

Tenant users cannot create `Secret` objects under the standard Cozystack RBAC, and they cannot read `Bucket`-emitted credential Secrets. Before a tenant can run their first `BackupJob`, an administrator must provision per-tenant storage and the per-application credential Secrets each driver expects. Perform these steps once per managed-DB application the tenant wants to back up. Examples use `tenant-user` for the tenant namespace and `my-postgres` / `my-mariadb` / `my-clickhouse` for the application name — substitute as appropriate.

### Provision the storage Bucket

If the tenant does not have external S3 coordinates, provision an in-cluster `Bucket` in their namespace:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Bucket
metadata:
  name: db-backups
  namespace: tenant-user
spec:
  users:
    backup:
      readonly: false
```

```bash
kubectl apply -f bucket.yaml
kubectl -n tenant-user wait hr/bucket-db-backups --for=condition=ready --timeout=300s
```

The `Bucket` controller materialises a `bucket-<name>-backup` Secret in the namespace carrying a `BucketInfo` JSON blob — the S3 endpoint, bucket name, and access keys come from there.

### Read the bucket credentials

Run this once per shell session. Every per-driver block below reuses `$ACCESS_KEY`, `$SECRET_KEY`, and `/tmp/bucket.json`:

```bash
kubectl -n tenant-user get secret bucket-db-backups-backup \
  -o jsonpath='{.data.BucketInfo}' | base64 -d > /tmp/bucket.json
ACCESS_KEY=$(jq -r .spec.secretS3.accessKeyID /tmp/bucket.json)
SECRET_KEY=$(jq -r .spec.secretS3.accessSecretKey /tmp/bucket.json)
```

### Create per-application credential Secrets

Each driver expects per-application credential Secrets in the application namespace — the strategy templates reference them by name (`{{ .Application.metadata.name }}-...`).

#### Postgres (CNPG)

Project the credentials in the keys CNPG's barman client expects:

```bash
kubectl -n tenant-user create secret generic my-postgres-cnpg-backup-creds \
  --from-literal=AWS_ACCESS_KEY_ID="$ACCESS_KEY" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$SECRET_KEY"
```

When the S3 endpoint uses a self-signed certificate (the SeaweedFS default), also create a CA Secret:

```bash
kubectl -n tenant-user create secret generic my-postgres-cnpg-backup-ca \
  --from-file=ca.crt=/path/to/ca.crt
```

#### MariaDB

```bash
kubectl -n tenant-user create secret generic my-mariadb-mariadb-backup-creds \
  --from-literal=AWS_ACCESS_KEY_ID="$ACCESS_KEY" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$SECRET_KEY"
```

For self-signed endpoints, add `my-mariadb-mariadb-backup-ca` carrying `ca.crt` the same way.

#### ClickHouse

No extra Secret is needed for the BackupClass flow. The Altinity strategy reads S3 credentials from the chart-emitted `<release>-backup-s3` Secret directly. Make sure `backup.enabled: true` is set on every ClickHouse application instance the tenant wants to back up, and that the `backup.*` block in the application values carries the bucket coordinates (see the [ClickHouse application reference]({{% ref "/docs/v1.4/applications/clickhouse" %}})).

## Handing off to tenants

Tenants run backups and restores against the `BackupClass` names you created above using `BackupJob`, `Plan`, and `RestoreJob` resources. Walk them through the [Application Backup and Recovery]({{% ref "/docs/v1.4/applications/backup-and-recovery" %}}) guide; they do not need admin permissions to operate against an existing `BackupClass`. Before pointing them at the guide:

- Communicate the available `BackupClass` names (tenants cannot list them — cluster-scoped resources are not reachable through the tenant `RoleBinding`).
- Ensure that for every managed application the tenant wants to back up, the per-application credential Secret described in [Tenant onboarding](#tenant-onboarding) already exists in their namespace.

## Tenant escalation: driver-side diagnostics

When a tenant's `BackupJob` or `RestoreJob` ends in `phase: Failed` and the `status.message` does not pinpoint the cause, the tenant cannot inspect operator-native CRs themselves — their RBAC excludes `cnpg.io`, `k8s.mariadb.com`, and the `pods/log` subresource. Run these commands on their behalf, using the `BackupJob` name they hand you:

```bash
# Postgres (CloudNativePG)
kubectl -n tenant-user get backups.cnpg.io
# MariaDB
kubectl -n tenant-user get backups.k8s.mariadb.com,restores.k8s.mariadb.com
# ClickHouse — the strategy runs as a one-shot Pod that talks to the in-pod sidecar
kubectl -n tenant-user logs -l backups.cozystack.io/owned-by.BackupJobName=my-clickhouse-adhoc
```

For ClickHouse archive purges, the tenant cannot reach the in-pod `clickhouse-backup` sidecar HTTP API directly; on their request, exec into the ClickHouse pod and call `DELETE /backup/<name>/remote` against the local sidecar (the chart-emitted `clickhouse-<release>-backup-api-auth` Secret carries the credentials).
