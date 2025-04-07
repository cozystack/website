---
title: "The distro-hosted bundle"
linkTitle: "distro-hosted"
description: "Kubernetes distribution, hosted version"
weight: 20
---

This is a Cozystack platform configuration intended for use as a Kubernetes distribution, designed for installation on existing Kubernetes clusters.

This configuration can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.
It does not include CNI plugins, virtualization, storage, or multitenancy.

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
| `bundle-disable` | Comma-separated list of disabled components from the bundle. Refer to [FAQ](/docs/faq/#how-to-disable-some-components-from-bundle) page to learn how to use this option. |
| `values-<component>` | JSON or YAML formated values passed to specific component installation. Refer to [FAQ](/docs/faq/#how-to-overwrite-parameters-for-specific-components) page to learn how to use this option. |
| `root-host` | the main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc. |
| `api-server-endpoint` | used for generating kubeconfig files for your users. It is recommended to use globally accessible IP addresses instead of local ones. |
| `telemetry-enabled` | used to enable [telemetry](/docs/telemetry/) feature in Cozystack (default: `true`) |

Refer to [FAQ](/docs/faq/#bundles) page to learn how to use generic bundle options.
