---
title: "The paas-hosted bundle"
linkTitle: "paas-hosted"
description: "PaaS platform, hosted version"
weight: 10
aliases:
  - /docs/bundles/paas-hosted
---

This is a Cozystack platform configuration intended for use as a PaaS platform, designed for installation on existing Kubernetes clusters.

This configuration can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.
It does not include CNI plugins, virtualization, or storage.

The Kubernetes cluster used to deploy Cozystack must conform to the following requirements:

* All CNI plugins must be disabled, as Cozystack will install its own plugin.
* Kubernetes cluster DNS domain must be set to `cozy.local`.
* Listening address of some Kubernetes components must be changed from `localhost` to a routeable address.
* Kubernetes API server must be reachable on `localhost`.


### Example configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-hosted"
  root-host: example.org
  api-server-endpoint: https://192.168.100.10:6443
  expose-services: "api,dashboard"
```

### Configuration parameters

| option | description |
|--------|-------------|
| `bundle-name` | Name of bundle to use for installation |
| `bundle-disable` | Comma-separated list of disabled components from the bundle. Read more about this option in ["how to disable some components from bundle"][disable-components].                     |
| `values-<component>` | JSON or YAML formated values passed to specific component installation. Read more about this option in ["how to overwrite parameters for specific components"][overwrite-parameters]. |
| `ipv4-pod-cidr` | The pod subnet used by Pods to assign IPs |
| `ipv4-svc-cidr` | The pod subnet used by Services to assign IPs |
| `root-host` | the main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc. |
| `api-server-endpoint` | used for generating kubeconfig files for your users. It is recommended to use globally accessible IP addresses instead of local ones. |
| `oidc-enabled` | used to enable [oidc](/docs/operations/oidc/) feature in Cozystack (default: `false`) |
| `telemetry-enabled` | used to enable [telemetry](/docs/operations/telemetry/) feature in Cozystack (default: `true`) |
| `expose-services` | Comma-separated list of services to expose to the internet. Possible values: `api,dashboard,cdi-uploadproxy,vm-exportproxy` |
| `expose-ingress` | Ingress controller to use for exposing services. (default: `tenant-root`) |
| `expose-external-ips` | Comma-separated list of external IPs used for specified ingress controller. If not specified it will use LoadBalancer service by default |

[disable-components]: {{% ref "docs/operations/bundles#how-to-disable-some-components-from-bundle" %}}
[overwrite-parameters]: {{% ref "docs/operations/bundles#how-to-overwrite-parameters-for-specific-components" %}}

Refer to the [Bundles reference]({{% ref "docs/operations/bundles" %}}) page to learn how to use generic bundle options.

### Installing Cozystack on Provided Kuberentes Clusters

Cozystack can also be installed on top of a provided managed Kubernetes cluster.
Bundles `paas-hosted` and `distro-hosted` are made specifically for this scenario.

If you bootstrap your Talos cluster in your own way, or use a different Kubernetes distribution, make sure
to apply the following mandatory settings:

* All CNI plugins must be disabled, as Cozystack will install its own plugin.
* Kubernetes cluster DNS domain must be set to `cozy.local`.
* Listening address of some Kubernetes components must be changed from `localhost` to a routeable address.
* Kubernetes API server must be reachable on `localhost`.
