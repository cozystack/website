---
title: "The distro-full bundle"
linkTitle: "distro-full"
description: "Kubernetes distribution, full stack version"
weight: 20
---

This is a Cozystack platform configuration intended for use as a Kubernetes distribution, designed for installation on Talos Linux.

This allows you to use Cozystack as a reliable Kubernetes distribution, primarily sharpened for bare metal, although it can also be installed on virtual machines.
It includes storage but excludes virtualization and multitenancy features.

### Example configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "distro-full"
  ipv4-pod-cidr: "10.244.0.0/16"
  ipv4-svc-cidr: "10.96.0.0/16"
  root-host: example.org
  api-server-endpoint: https://192.168.100.10:6443
```

### Configuration parameters

| option | description |
|--------|-------------|
| `bundle-name` | Name of bundle to use for installation |
| `bundle-disable` | Comma-separated list of disabled components from the bundle. Refer to [FAQ](/docs/faq/#how-to-disable-some-components-from-bundle) page to learn how to use this option. |
| `values-<component>` | JSON or YAML formated values passed to specific component installation. Refer to [FAQ](/docs/faq/#how-to-overwrite-parameters-for-specific-components) page to learn how to use this option. |
| `ipv4-pod-cidr` | The pod subnet used by Pods to assign IPs |
| `ipv4-svc-cidr` | The pod subnet used by Services to assign IPs |
| `root-host` | the main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc. |
| `api-server-endpoint` | used for generating kubeconfig files for your users. It is recommended to use globally accessible IP addresses instead of local ones. |
| `telemetry-enabled` | used to enable [telemetry](/docs/telemetry/) feature in Cozystack (default: `true`) |

Refer to [FAQ](/docs/faq/#bundles) page to learn how to use generic bundle options.
