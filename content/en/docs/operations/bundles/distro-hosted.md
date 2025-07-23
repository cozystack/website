---
title: "The distro-hosted bundle"
linkTitle: "distro-hosted"
description: "Kubernetes distribution, hosted version"
weight: 20
aliases:
  - /docs/bundles/distro-hosted
---

This is a Cozystack platform configuration intended for use as a Kubernetes distribution, designed for installation on existing Kubernetes clusters.

This configuration can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.
It does not include CNI plugins, virtualization, storage, or multitenancy.

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
  bundle-name: "distro-hosted"
  root-host: example.org
  api-server-endpoint: https://192.168.100.10:6443
```

### Configuration parameters

| option | description |
|--------|-------------|
| `bundle-name` | Name of bundle to use for installation |
| `bundle-disable` | Comma-separated list of disabled components from the bundle. Read more about this option in ["how to disable some components from bundle"][disable-components].                     |
| `values-<component>` | JSON or YAML formated values passed to specific component installation. Read more about this option in ["how to overwrite parameters for specific components"][overwrite-parameters]. |
| `root-host` | the main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc. |
| `api-server-endpoint` | used for generating kubeconfig files for your users. It is recommended to use globally accessible IP addresses instead of local ones. |
| `telemetry-enabled` | used to enable [telemetry](/docs/operations/telemetry/) feature in Cozystack (default: `true`) |

[disable-components]: {{% ref "docs/operations/bundles#how-to-disable-some-components-from-bundle" %}}
[overwrite-parameters]: {{% ref "docs/operations/bundles#how-to-overwrite-parameters-for-specific-components" %}}

Refer to the [Bundles reference]({{% ref "docs/operations/bundles" %}}) page to learn how to use generic bundle options.

