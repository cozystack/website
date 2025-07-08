---
title: "Managed PostgreSQL Service"
linkTitle: "PostgreSQL"
---


PostgreSQL is currently the leading choice among relational databases, known for its robust features and performance.
The Managed PostgreSQL Service takes advantage of platform-side implementation to provide a self-healing replicated cluster.
This cluster is efficiently managed using the highly acclaimed CloudNativePG operator, which has gained popularity within the community.

## Deployment Details

This managed service is controlled by the CloudNativePG operator, ensuring efficient management and seamless operation.

- Docs: <https://cloudnative-pg.io/docs/>
- Github: <https://github.com/cloudnative-pg/cloudnative-pg>

## HowTos

### How to switch primary/secondary replica

See:

- <https://cloudnative-pg.io/documentation/1.15/rolling_update/#manual-updates-supervised>

### How to restore backup

find snapshot:

```bash
restic -r s3:s3.example.org/postgres-backups/database_name snapshots
```

restore:

```bash
restic -r s3:s3.example.org/postgres-backups/database_name restore latest --target /tmp/
```

more details:

- <https://blog.aenix.io/restic-effective-backup-from-stdin-4bc1e8f083c1>

## Parameters

### Common parameters

| Name                                    | Description                                                                                                              | Value   |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------- |
| `external`                              | Enable external access from outside the cluster                                                                          | `false` |
| `size`                                  | Persistent Volume size                                                                                                   | `10Gi`  |
| `replicas`                              | Number of Postgres replicas                                                                                              | `2`     |
| `storageClass`                          | StorageClass used to store the data                                                                                      | `""`    |
| `postgresql.parameters.max_connections` | Determines the maximum number of concurrent connections to the database server. The default is typically 100 connections | `100`   |
| `quorum.minSyncReplicas`                | Minimum number of synchronous replicas that must acknowledge a transaction before it is considered committed.            | `0`     |
| `quorum.maxSyncReplicas`                | Maximum number of synchronous replicas that can acknowledge a transaction (must be lower than the number of instances).  | `0`     |

### Configuration parameters

| Name        | Description             | Value |
| ----------- | ----------------------- | ----- |
| `users`     | Users configuration     | `{}`  |
| `databases` | Databases configuration | `{}`  |

### Backup parameters

| Name                     | Description                                                          | Value                               |
| ------------------------ | -------------------------------------------------------------------- | ----------------------------------- |
| `backup.enabled`         | Enable pereiodic backups                                             | `false`                             |
| `backup.schedule`        | Cron schedule for automated backups                                  | `0 2 * * * *`                       |
| `backup.retentionPolicy` | The retention policy                                                 | `30d`                               |
| `backup.destinationPath` | The path where to store the backup (i.e. s3://bucket/path/to/folder) | `s3://BUCKET_NAME/`                 |
| `backup.endpointURL`     | Endpoint to be used to upload data to the cloud                      | `http://minio-gateway-service:9000` |
| `backup.s3AccessKey`     | The access key for S3, used for authentication                       | `oobaiRus9pah8PhohL1ThaeTa4UVa7gu`  |
| `backup.s3SecretKey`     | The secret key for S3, used for authentication                       | `ju3eum4dekeich9ahM1te8waeGai0oog`  |

### Bootstrap parameters

| Name                     | Description                                                                                                                             | Value   |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `bootstrap.enabled`      | Restore cluster from backup                                                                                                             | `false` |
| `bootstrap.recoveryTime` | Time stamp up to which recovery will proceed, expressed in RFC 3339 format, if empty, will restore latest                               | `""`    |
| `bootstrap.oldName`      | Name of cluster before deleting                                                                                                         | `""`    |
| `resources`              | Explicit CPU and memory configuration for each PostgreSQL replica. When left empty, the preset defined in `resourcesPreset` is applied. | `{}`    |
| `resourcesPreset`        | Default sizing preset used when `resources` is omitted. Allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge.       | `micro` |


## Parameter examples and reference

### resources and resourcesPreset

`resources` sets explicit CPU and memory configurations for each replica.
When left empty, the preset defined in `resourcesPreset` is applied.

```yaml
resources:
  cpu: 4000m
  memory: 4Gi
```

`resourcesPreset` sets named CPU and memory configurations for each replica.
This setting is ignored if the corresponding `resources` value is set.

| Preset name | CPU    | memory  |
|-------------|--------|---------|
| `nano`      | `250m` | `128Mi` |
| `micro`     | `500m` | `256Mi` |
| `small`     | `1`    | `512Mi` |
| `medium`    | `1`    | `1Gi`   |
| `large`     | `3`    | `2Gi`   |
| `xlarge`    | `4`    | `4Gi`   |
| `2xlarge`   | `8`    | `8Gi`   |

### users

```yaml
users:
  user1:
    password: strongpassword
  user2:
    password: hackme
  airflow:
    password: qwerty123
  debezium:
    replication: true
```

### databases

```yaml
databases:          
  myapp:            
    roles:          
      admin:        
      - user1       
      - debezium    
      readonly:     
      - user2       
  airflow:          
    roles:          
      admin:        
      - airflow     
    extensions:     
    - hstore        
```
