---
title: "Managed Clickhouse Service"
linkTitle: "Clickhouse"
---


ClickHouse is an open source high-performance and column-oriented SQL database management system (DBMS).
It is used for online analytical processing (OLAP).
Cozystack platform uses Altinity operator to provide ClickHouse.

### How to restore backup:

1. Find a snapshot:
    ```
    restic -r s3:s3.example.org/clickhouse-backups/table_name snapshots
    ```

2.  Restore it:
    ```
    restic -r s3:s3.example.org/clickhouse-backups/table_name restore latest --target /tmp/
    ```

For more details, read [Restic: Effective Backup from Stdin](https://blog.aenix.io/restic-effective-backup-from-stdin-4bc1e8f083c1).

## Parameters

### Common parameters

| Name             | Description                                              | Value  |
| ---------------- | -------------------------------------------------------- | ------ |
| `size`           | Size of Persistent Volume for data                       | `10Gi` |
| `logStorageSize` | Size of Persistent Volume for logs                       | `2Gi`  |
| `shards`         | Number of Clickhouse shards                              | `1`    |
| `replicas`       | Number of Clickhouse replicas                            | `2`    |
| `storageClass`   | StorageClass used to store the data                      | `""`   |
| `logTTL`         | TTL (expiration time) for query_log and query_thread_log | `15`   |

### Configuration parameters

| Name    | Description         | Value |
| ------- | ------------------- | ----- |
| `users` | Users configuration | `{}`  |

### Backup parameters

| Name                     | Description                                                                 | Value                                                  |
| ------------------------ | --------------------------------------------------------------------------- | ------------------------------------------------------ |
| `backup.enabled`         | Enable periodic backups                                                     | `false`                                                |
| `backup.s3Region`        | AWS S3 region where backups are stored                                      | `us-east-1`                                            |
| `backup.s3Bucket`        | S3 bucket used for storing backups                                          | `s3.example.org/clickhouse-backups`                    |
| `backup.schedule`        | Cron schedule for automated backups                                         | `0 2 * * *`                                            |
| `backup.cleanupStrategy` | Retention strategy for cleaning up old backups                              | `--keep-last=3 --keep-daily=3 --keep-within-weekly=1m` |
| `backup.s3AccessKey`     | Access key for S3, used for authentication                                  | `oobaiRus9pah8PhohL1ThaeTa4UVa7gu`                     |
| `backup.s3SecretKey`     | Secret key for S3, used for authentication                                  | `ju3eum4dekeich9ahM1te8waeGai0oog`                     |
| `backup.resticPassword`  | Password for Restic backup encryption                                       | `ChaXoveekoh6eigh4siesheeda2quai0`                     |
| `resources`              | Explicit CPU/memory resource requests and limits for the Clickhouse service | `{}`                                                   |
| `resourcesPreset`        | Use a common resources preset when `resources` is not set explicitly.       | `nano`                                                 |


In production environments, it's recommended to set `resources` explicitly.
Example of `resources`:

```yaml
resources:
  limits:
    cpu: 4000m
    memory: 4Gi
  requests:
    cpu: 100m
    memory: 512Mi
```

Allowed values for `resourcesPreset` are `none`, `nano`, `micro`, `small`, `medium`, `large`, `xlarge`, `2xlarge`.
This value is ignored if `resources` value is set. 
