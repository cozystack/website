---
title: "Managed TCP Load Balancer Service"
linkTitle: "TCP Load Balancer"
---


The Managed TCP Load Balancer Service simplifies the deployment and management of load balancers. It efficiently distributes incoming TCP traffic across multiple backend servers, ensuring high availability and optimal resource utilization.

## Deployment Details

Managed TCP Load Balancer Service efficiently utilizes HAProxy for load balancing purposes. HAProxy is a well-established and reliable solution for distributing incoming TCP traffic across multiple backend servers, ensuring high availability and efficient resource utilization. This deployment choice guarantees the seamless and dependable operation of your load balancing infrastructure.

- Docs: https://www.haproxy.com/documentation/

## Parameters

### Common parameters

| Name       | Description                                     | Value   |
| ---------- | ----------------------------------------------- | ------- |
| `external` | Enable external access from outside the cluster | `false` |
| `replicas` | Number of HAProxy replicas                      | `2`     |

### Configuration parameters

| Name                             | Description                                                                                                                               | Value   |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `httpAndHttps.mode`              | Mode for balancer. Allowed values: `tcp` and `tcp-with-proxy`                                                                             | `tcp`   |
| `httpAndHttps.targetPorts.http`  | HTTP port number.                                                                                                                         | `80`    |
| `httpAndHttps.targetPorts.https` | HTTPS port number.                                                                                                                        | `443`   |
| `httpAndHttps.endpoints`         | Endpoint addresses list                                                                                                                   | `[]`    |
| `whitelistHTTP`                  | Secure HTTP by enabling  client networks whitelisting                                                                                     | `false` |
| `whitelist`                      | List of client networks                                                                                                                   | `[]`    |
| `resources`                      | Explicit CPU and memory configuration for each TCP Balancer replica. When left empty, the preset defined in `resourcesPreset` is applied. | `{}`    |
| `resourcesPreset`                | Default sizing preset used when `resources` is omitted. Allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge.         | `nano`  |

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

