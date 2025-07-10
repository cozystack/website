---
title: "Managed NATS Service"
linkTitle: "NATS"
---


NATS is an open-source, simple, secure, and high performance messaging system.
It provides a data layer for cloud native applications, IoT messaging, and microservices architectures.

## Parameters

### Common parameters

| Name                | Description                                                                                                                       | Value   |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `external`          | Enable external access from outside the cluster                                                                                   | `false` |
| `replicas`          | Persistent Volume size for NATS                                                                                                   | `2`     |
| `storageClass`      | StorageClass used to store the data                                                                                               | `""`    |
| `users`             | Users configuration                                                                                                               | `{}`    |
| `jetstream.size`    | Jetstream persistent storage size                                                                                                 | `10Gi`  |
| `jetstream.enabled` | Enable or disable Jetstream                                                                                                       | `true`  |
| `config.merge`      | Additional configuration to merge into NATS config                                                                                | `{}`    |
| `config.resolver`   | Additional configuration to merge into NATS config                                                                                | `{}`    |
| `resources`         | Explicit CPU and memory configuration for each NATS replica. When left empty, the preset defined in `resourcesPreset` is applied. | `{}`    |
| `resourcesPreset`   | Default sizing preset used when `resources` is omitted. Allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge. | `nano`  |

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
| `large`     | `2`    | `2Gi`   |
| `xlarge`    | `4`    | `4Gi`   |
| `2xlarge`   | `8`    | `8Gi`   |

