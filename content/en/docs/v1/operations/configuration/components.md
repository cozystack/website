---
title: "Cozystack Components Reference"
linkTitle: "Components"
description: "Full reference for Cozystack components."
weight: 30
aliases:
  - /docs/v1/install/cozystack/components
---

### Overwriting Component Parameters

You might want to override specific options for the components.
To achieve this, specify values in the `spec.components` section of the Platform Package.

For example, if you want to overwrite `k8sServiceHost` and `k8sServicePort` for cilium,
take a look at its [values.yaml](https://github.com/cozystack/cozystack/blob/238061efbc0da61d60068f5de31d6eaa35c4d994/packages/system/cilium/values.yaml#L18-L19) file.

Then specify these options in the `networking` component of your Platform Package:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: distro-full
  components:
    platform:
      values:
        networking:
          podCIDR: "10.244.0.0/16"
          serviceCIDR: "10.96.0.0/16"
    networking:
      values:
        cilium:
          k8sServiceHost: 11.22.33.44
          k8sServicePort: 6443
```

### Enabling and Disabling Components

Bundles have optional components that need to be explicitly enabled (included) in the installation.
Regular bundle components can, on the other hand, be disabled (excluded) from the installation, when you don't need them.

Use `bundles.enabledPackages` and `bundles.disabledPackages` in the Platform Package values.
For example, [installing Cozystack in Hetzner]({{% ref "/docs/v1/install/providers/hetzner" %}})
requires swapping default load balancer, MetalLB, with one made specifically for Hetzner, called RobotLB:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full
  components:
    platform:
      values:
        bundles:
          disabledPackages:
            - metallb
          enabledPackages:
            - hetzner-robotlb
        # rest of the config
```

Disabling components must be done before installing Cozystack.
Applying updated configuration with `disabledPackages` will not remove components that are already installed.
To remove already installed components, delete the Helm release manually using this command:

```bash
kubectl delete hr -n <namespace> <component>
```
