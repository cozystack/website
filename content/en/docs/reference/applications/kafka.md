---
title: "Managed Kafka Service"
linkTitle: "Kafka"
---


## Parameters

### Common parameters

| Name                        | Description                                                                                                                                      | Value   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------- |
| `external`                  | Enable external access from outside the cluster                                                                                                  | `false` |
| `kafka.size`                | Persistent Volume size for Kafka                                                                                                                 | `10Gi`  |
| `kafka.replicas`            | Number of Kafka replicas                                                                                                                         | `3`     |
| `kafka.storageClass`        | StorageClass used to store the Kafka data                                                                                                        | `""`    |
| `zookeeper.size`            | Persistent Volume size for ZooKeeper                                                                                                             | `5Gi`   |
| `zookeeper.replicas`        | Number of ZooKeeper replicas                                                                                                                     | `3`     |
| `zookeeper.storageClass`    | StorageClass used to store the ZooKeeper data                                                                                                    | `""`    |
| `kafka.resources`           | Resources                                                                                                                                        | `{}`    |
| `kafka.resourcesPreset`     | Use a common resources preset when `resources` is not set explicitly. (allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge) | `small` |
| `zookeeper.resources`       | Resources                                                                                                                                        | `{}`    |
| `zookeeper.resourcesPreset` | Use a common resources preset when `resources` is not set explicitly. (allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge) | `small` |

### Configuration parameters

| Name     | Description          | Value |
| -------- | -------------------- | ----- |
| `topics` | Topics configuration | `[]`  |
