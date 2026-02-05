---
title: "Cozystack ConfigMap Reference"
linkTitle: "ConfigMap"
description: "Reference for the Cozystack ConfigMap, which defines key configuration values for a Cozystack installation and operations."
weight: 10
aliases:
  - /docs/install/cozystack/configmap
---

This page explains the role of Cozystack's main ConfigMap and provides a full reference for its values.

Cozystack's main configuration is defined by a single [Kubernetes ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/).
This ConfigMap includes [Cozystack bundle]({{% ref "/docs/operations/configuration/bundles" %}}) and [components setup]({{% ref "/docs/operations/configuration/components" %}}),
key network settings, exposed services, and other options.


## Example

Here's an example of configuration for installing Cozystack with bundle `paas-full`, with root host "example.org",
and Cozystack Dashboard and API exposed and available to users:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-full"
  root-host: "example.org"
  api-server-endpoint: "https://api.example.org:443"
  expose-services: "dashboard,api"
  ipv4-pod-cidr: "10.244.0.0/16"
  ipv4-pod-gateway: "10.244.0.1"
  ipv4-svc-cidr: "10.96.0.0/16"
  ipv4-join-cidr: "100.64.0.0/16"
```


## Reference

| Value (`data.*`)       | Bundles                    | Description                                                                                                                                                                            |
|------------------------|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `bundle-name`          | all                        | Name of bundle to use for installation.                                                                                                                                                |
| `bundle-enable`        | all                        | Optional bundle components included in the installation. Read more about this option in ["How to enable and disable bundle components"][enable-disable].                               |
| `bundle-disable`       | all                        | Bundle components excluded (disabled) from the installation. Read more about this option in ["How to enable and disable bundle components"][enable-disable].                           |
| `values-<component>`   | all                        | JSON or YAML formatted values passed to specific component installation. Read more about this option in ["how to overwrite parameters for specific components"][overwrite-parameters]. |
| `root-host`            | all                        | The main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc.                                                                               |
| `api-server-endpoint`  | all                        | Used for generating kubeconfig files for your users. It is recommended to use a routable FQDN or IP address instead of local-only addresses.                                           |
| `telemetry-enabled`    | all                        | Enable [telemetry] feature in Cozystack (default: `true`).                                                                                                                             |
| `expose-services`      | all                        | Comma-separated list of services to expose to the internet. Possible values: `api,dashboard,cdi-uploadproxy,vm-exportproxy`.                                                           |
| `expose-ingress`       | all                        | Ingress controller to use for exposing services. (default: `tenant-root`)                                                                                                              |
| `expose-external-ips`  | all                        | Comma-separated list of external IPs used for the specified ingress controller. If not specified, a LoadBalancer service is used by default.                                           |
| `ipv4-pod-cidr`        | `paas-full`, `distro-full` | The pod subnet used by Pods to assign IPs                                                                                                                                              |
| `ipv4-pod-gateway`     | `paas-full`                | The gateway address for the pod subnet                                                                                                                                                 |
| `ipv4-svc-cidr`        | `paas-full`, `distro-full` | The pod subnet used by Services to assign IPs                                                                                                                                          |
| `ipv4-join-cidr`       | `paas-full`                | The `join` subnet, as a special subnet for network communication between the Node and Pod. Follow the [kube-ovn] documentation to learn more about these options.                      |
| `oidc-enabled`         | `paas-full`, `paas-hosted` | Enable [oidc] feature in Cozystack (default: `false`)                                                                                                                                  |
| `cpu-allocation-ratio` | `paas-full`, `paas-hosted` | CPU allocation ratio: `1/cpu-allocation-ratio` CPU requested per 1 vCPU. Defaults to 10. See [Resource Management] for detailed explanation and examples.                              |

[enable-disable]: {{% ref "/docs/operations/configuration/components#enabling-and-disabling-components" %}}
[overwrite-parameters]: {{% ref "/docs/operations/configuration/components#overwriting-component-parameters" %}}
[Resource Management]: {{% ref "/docs/guides/resource-management#cpu-allocation-ratio" %}}
[oidc]: {{% ref "/docs/operations/oidc" %}}
[telemetry]: {{% ref "/docs/operations/configuration/telemetry" %}}
[kube-ovn]: https://kubeovn.github.io/docs/en/guide/subnet/#join-subnet
