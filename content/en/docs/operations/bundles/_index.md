---
title: "Bundles Configuration and Troubleshooting"
linkTitle: "Bundles"
description: "Cozystack bundles reference: composition, configuration, and troubleshooting."
weight: 20
aliases:
  - /docs/bundles
---

This section provides practical guidance for working with Cozystack bundles.
You’ll also find detailed reference pages for each bundle, outlining their structure, included components, and expected environment.

* [paas-full]
* [paas-hosted]
* [distro-full]
* [distro-hosted]

[paas-full]: {{% ref "/docs/operations/bundles/paas-full" %}}
[iaas-full]: https://github.com/cozystack/cozystack/issues/730
[paas-hosted]: {{% ref "/docs/operations/bundles/paas-hosted" %}}
[distro-full]: {{% ref "/docs/operations/bundles/distro-full" %}}
[distro-hosted]: {{% ref "/docs/operations/bundles/distro-hosted" %}}

### How to overwrite parameters for specific components

You might want to overwrite specific options for the components.
To achieve this, you must specify values in JSON or YAML format using the values-<component> option.

For example, if you want to overwrite `k8sServiceHost` and `k8sServicePort` for cilium,
take a look at its [values.yaml](https://github.com/cozystack/cozystack/blob/238061efbc0da61d60068f5de31d6eaa35c4d994/packages/system/cilium/values.yaml#L18-L19) file.

Then specify these options in the `values-cilium` section of your Cozystack configuration, as shown below:

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
  values-cilium: |
    cilium:
      k8sServiceHost: 11.22.33.44
      k8sServicePort: 6443
```

### How to disable some components from bundle

Sometimes you may need to disable specific components within a bundle.
To do this, use the `bundle-disable` option and provide a comma-separated list of the components you want to disable. For example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-full"
  bundle-disable: "linstor,dashboard"
  ipv4-pod-cidr: "10.244.0.0/16"
  ipv4-svc-cidr: "10.96.0.0/16"
```

{{% alert color="warning" %}}
:warning: Disabling components using this option will not remove them if they are already installed. To remove them, you must delete the Helm release manually using the `kubectl delete hr -n <namespace> <component>` command.
{{% /alert %}}
