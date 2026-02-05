---
title: "Cozystack Components Reference"
linkTitle: "Components"
description: "Full reference for Cozystack components."
weight: 30
aliases:
  - /docs/install/cozystack/components
---

### Overwriting Component Parameters

You might want to override specific options for the components.
To achieve this, you must specify values in JSON or YAML format using the `data.values-<component>` option
in the [Cozystack ConfigMap]({{% ref "/docs/operations/configuration/configmap" %}}).

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

### Enabling and Disabling Components

Bundles have optional components that need to be explicitly enabled (included) in the installation.
Regular bundle components can, on the other hand, be disabled (excluded) from the installation, when you don't need them.

Use options `bundle-enable` and `bundle-disable`, providing comma-separated lists of the components.
For example, [installing Cozystack in Hetzner]({{% ref "/docs/install/providers/hetzner" %}})
requires swapping default load balancer, MetalLB, with one made specifically for Hetzner, called RobotLB:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-full"
  bundle-disable: "metallb"
  bundle-enable: "hetzner-robotlb"
  # rest of the config
```

Disabling components must be done before installing Cozystack.
Applying updated configuration with `bundle-disable` will not remove components that are already installed.
To remove already installed components, delete the Helm release manually using this command:

```bash
kubectl delete hr -n <namespace> <component>
```
