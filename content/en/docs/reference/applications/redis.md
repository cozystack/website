---
title: "Managed Redis Service"
linkTitle: "Redis"
---


Redis is a highly versatile and blazing-fast in-memory data store and cache that can significantly boost the performance of your applications. Managed Redis Service offers a hassle-free solution for deploying and managing Redis clusters, ensuring that your data is always available and responsive.

## Deployment Details

Service utilizes the Spotahome Redis Operator for efficient management and orchestration of Redis clusters. 

- Docs: https://redis.io/docs/
- GitHub: https://github.com/spotahome/redis-operator

## Parameters

### Common parameters

| Name              | Description                                                                                                                        | Value   |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `external`        | Enable external access from outside the cluster                                                                                    | `false` |
| `size`            | Persistent Volume size                                                                                                             | `1Gi`   |
| `replicas`        | Number of Redis replicas                                                                                                           | `2`     |
| `storageClass`    | StorageClass used to store the data                                                                                                | `""`    |
| `authEnabled`     | Enable password generation                                                                                                         | `true`  |
| `resources`       | Explicit CPU and memory configuration for each Redis replica. When left empty, the preset defined in `resourcesPreset` is applied. | `{}`    |
| `resourcesPreset` | Default sizing preset used when `resources` is omitted. Allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge.  | `nano`  |

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
| `nano`      | `100m` | `128Mi` |
| `micro`     | `250m` | `256Mi` |
| `small`     | `500m` | `512Mi` |
| `medium`    | `500m` | `1Gi`   |
| `large`     | `1`    | `2Gi`   |
| `xlarge`    | `2`    | `4Gi`   |
| `2xlarge`   | `4`    | `8Gi`   |

