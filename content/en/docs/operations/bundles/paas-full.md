---
title: "The paas-full bundle"
linkTitle: "paas-full"
description: "PaaS platform, full stack version"
weight: 10
aliases:
  - /docs/bundles/pass-full
---

This is a Cozystack platform configuration intended for use as a PaaS platform, designed for installation on Talos Linux.

It includes all available features, enabling a comprehensive PaaS experience.

### Example configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-full"
  ipv4-pod-cidr: "10.244.0.0/16"
  ipv4-pod-gateway: "10.244.0.1"
  ipv4-svc-cidr: "10.96.0.0/16"
  ipv4-join-cidr: "100.64.0.0/16"
  root-host: example.org
  api-server-endpoint: https://192.168.100.10:6443
  expose-services: "api,dashboard,cdi-uploadproxy,vm-exportproxy"
```

### Configuration parameters

| option                 | description                                                                                                                                                                                                                |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `bundle-name`          | Name of bundle to use for installation                                                                                                                                                                                     |
| `bundle-enable`        | Optional bundle components included in the installation. Read more about this option in ["How to enable and disable bundle components"][enable-disable].                                                                   |
| `bundle-disable`       | Bundle components excluded (disabled) from the installation. Read more about this option in ["How to enable and disable bundle components"][enable-disable].                                                               |
| `values-<component>`   | JSON or YAML formatted values passed to specific component installation. Read more about this option in ["how to overwrite parameters for specific components"][overwrite-parameters].                                      |
| `ipv4-pod-cidr`        | The pod subnet used by Pods to assign IPs                                                                                                                                                                                  |
| `ipv4-pod-gateway`     | The gateway address for the pod subnet                                                                                                                                                                                     |
| `ipv4-svc-cidr`        | The pod subnet used by Services to assign IPs                                                                                                                                                                              |
| `ipv4-join-cidr`       | The `join` subnet, as a special subnet for network communication between the Node and Pod. Follow [kube-ovn](https://kubeovn.github.io/docs/en/guide/subnet/#join-subnet) documentation to learn more about these options. |
| `root-host`            | the main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc.                                                                                                                   |
| `api-server-endpoint`  | used for generating kubeconfig files for your users. It is recommended to use globally accessible IP addresses instead of local ones.                                                                                      |
| `oidc-enabled`         | used to enable [oidc](/docs/operations/oidc/) feature in Cozystack (default: `false`)                                                                                                                                      |
| `telemetry-enabled`    | used to enable [telemetry](/docs/operations/telemetry/) feature in Cozystack (default: `true`)                                                                                                                             |
| `expose-services`      | Comma-separated list of services to expose to the internet. Possible values: `api,dashboard,cdi-uploadproxy,vm-exportproxy`                                                                                                |
| `expose-ingress`       | Ingress controller to use for exposing services. (default: `tenant-root`)                                                                                                                                                  |
| `expose-external-ips`  | Comma-separated list of external IPs used for specified ingress controller. If not specified it will use LoadBalancer service by default                                                                                   |
| `cpu-allocation-ratio` | CPU allocation ratio: `1/cpu-allocation-ratio` CPU requested per 1 vCPU. Defaults to 10 if unset.                                                                                                                          |


[enable-disable]: {{% ref "docs/operations/bundles#how-to-enable-and-disable-bundle-components" %}}
[overwrite-parameters]: {{% ref "docs/operations/bundles#how-to-overwrite-parameters-for-specific-components" %}}

Refer to the [Bundles reference]({{% ref "docs/operations/bundles" %}}) page to learn how to use generic bundle options.
