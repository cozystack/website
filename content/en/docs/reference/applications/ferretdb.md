---
title: "Managed FerretDB Service"
linkTitle: "FerretDB"
---


FerretDB is an open source MongoDB alternative.
It translates MongoDB wire protocol queries to SQL and can be used as a direct replacement for MongoDB 5.0+.
Internally, FerretDB service is backed by Postgres.

## Parameters

### Common parameters

| Name                     | Description                                                                                                                 | Value   |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ------- |
| `external`               | Enable external access from outside the cluster                                                                             | `false` |
| `size`                   | Persistent Volume size                                                                                                      | `10Gi`  |
| `replicas`               | Number of replicas                                                                                                          | `2`     |
| `storageClass`           | StorageClass used to store the data                                                                                         | `""`    |
| `quorum.minSyncReplicas` | Minimum number of synchronous replicas that must acknowledge a transaction before it is considered committed                | `0`     |
| `quorum.maxSyncReplicas` | Maximum number of synchronous replicas that can acknowledge a transaction (must be lower than the total number of replicas) | `0`     |

### Configuration parameters

| Name    | Description         | Value |
| ------- | ------------------- | ----- |
| `users` | Users configuration | `{}`  |

### Backup parameters

| Name                     | Description                                                                                                                           | Value                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `backup.enabled`         | Enable periodic backups                                                                                                               | `false`                                                |
| `backup.s3Region`        | The AWS S3 region where backups are stored                                                                                            | `us-east-1`                                            |
| `backup.s3Bucket`        | The S3 bucket used for storing backups                                                                                                | `s3.example.org/postgres-backups`                      |
| `backup.schedule`        | Cron schedule for automated backups                                                                                                   | `0 2 * * *`                                            |
| `backup.cleanupStrategy` | The strategy for cleaning up old backups                                                                                              | `--keep-last=3 --keep-daily=3 --keep-within-weekly=1m` |
| `backup.s3AccessKey`     | The access key for S3, used for authentication                                                                                        | `oobaiRus9pah8PhohL1ThaeTa4UVa7gu`                     |
| `backup.s3SecretKey`     | The secret key for S3, used for authentication                                                                                        | `ju3eum4dekeich9ahM1te8waeGai0oog`                     |
| `backup.resticPassword`  | The password for Restic backup encryption                                                                                             | `ChaXoveekoh6eigh4siesheeda2quai0`                     |
| `resources`              | Explicit CPU and memory configuration for each FerretDB replica. When left empty, the preset defined in `resourcesPreset` is applied. | `{}`                                                   |
| `resourcesPreset`        | Default sizing preset used when `resources` is omitted. Allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge.     | `nano`                                                 |



## Parameter examples and reference

### resources and resourcesPreset

`resources` sets explicit CPU and memory configurations for each replica.
When left empty, the preset defined in `resourcesPreset` is applied.

```yaml
resources:
  cpu: 4000m
  memory: 4Gi
```

`resourcePreset` sets named CPU and memory configurations for each replica.
This setting is ignored if the corresponding `resources` value is set.

| Preset name | CPU    | memory  |
|-------------|--------|---------|
| `nano`      | `100m` | `128Mi` |
| `micro`     | `250m` | `256Mi` |
| `small`     | `500m` | `512Mi` |
| `medium`    | `500m` | `1Gi`   |
| `large`     | `1`    | `2Gi`   |
| `xlarge`    | `2`    | `4Gi`   |
| `2xlarge`   | `4`    | `8Gi`   |
