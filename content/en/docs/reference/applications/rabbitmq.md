---
title: "Managed RabbitMQ Service"
linkTitle: "RabbitMQ"
---


RabbitMQ is a robust message broker that plays a crucial role in modern distributed systems. Our Managed RabbitMQ Service simplifies the deployment and management of RabbitMQ clusters, ensuring reliability and scalability for your messaging needs.

## Deployment Details

The service utilizes official RabbitMQ operator. This ensures the reliability and seamless operation of your RabbitMQ instances.

- Github: https://github.com/rabbitmq/cluster-operator/
- Docs: https://www.rabbitmq.com/kubernetes/operator/operator-overview.html

## Parameters

### Common parameters

| Name           | Description                                     | Value   |
| -------------- | ----------------------------------------------- | ------- |
| `external`     | Enable external access from outside the cluster | `false` |
| `size`         | Persistent Volume size                          | `10Gi`  |
| `replicas`     | Number of RabbitMQ replicas                     | `3`     |
| `storageClass` | StorageClass used to store the data             | `""`    |

### Configuration parameters

| Name              | Description                                                                                                                           | Value  |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| `users`           | Users configuration                                                                                                                   | `{}`   |
| `vhosts`          | Virtual Hosts configuration                                                                                                           | `{}`   |
| `resources`       | Explicit CPU and memory configuration for each RabbitMQ replica. When left empty, the preset defined in `resourcesPreset` is applied. | `{}`   |
| `resourcesPreset` | Default sizing preset used when `resources` is omitted. Allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge.     | `nano` |

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

