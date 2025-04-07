---
title: "The paas-full bundle"
linkTitle: "paas-full"
description: "PaaS platform, full stack version"
weight: 10
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
```

### Configuration parameters

| option | description |
|--------|-------------|
| `bundle-name` | Name of bundle to use for installation |
| `bundle-disable` | Comma-separated list of disabled components from the bundle. Refer to [FAQ](/docs/faq/#how-to-disable-some-components-from-bundle) page to learn how to use this option. |
| `values-<component>` | JSON or YAML formated values passed to specific component installation. Refer to [FAQ](/docs/faq/#how-to-overwrite-parameters-for-specific-components) page to learn how to use this option. |
| `ipv4-pod-cidr` | The pod subnet used by Pods to assign IPs |
| `ipv4-pod-gateway` | The gateway address for the pod subnet |
| `ipv4-svc-cidr` | The pod subnet used by Services to assign IPs |
| `ipv4-join-cidr` | The `join` subnet, as a special subnet for network communication between the Node and Pod. Follow [kube-ovn](https://kubeovn.github.io/docs/en/guide/subnet/#join-subnet) documentation to learn more about these options. |
| `root-host` | the main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc. |
| `api-server-endpoint` | used for generating kubeconfig files for your users. It is recommended to use globally accessible IP addresses instead of local ones. |
| `oidc-enabled` | used to enable [oidc](/docs/oidc/) feature in Cozystack (default: `false`) |
| `telemetry-enabled` | used to enable [telemetry](/docs/telemetry/) feature in Cozystack (default: `true`) |
