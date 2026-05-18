---
title: "Cozystack Components Reference"
linkTitle: "Components"
description: "Full reference for Cozystack components."
weight: 30
aliases:
  - /docs/v1.3/install/cozystack/components
---

### Overwriting Component Parameters

You might want to override specific options for the components.
To achieve this, modify the corresponding Package resource and specify values
in the `spec.components` section. The values structure follows the
[values.yaml](https://github.com/cozystack/cozystack/tree/main/packages/system)
of the respective system chart in the Cozystack repository.

For example, if you want to enable FRR-K8s mode for MetalLB, look at its
[values.yaml](https://github.com/cozystack/cozystack/blob/main/packages/system/metallb/values.yaml)
to understand the available parameters, then modify the `cozystack.metallb` Package:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.metallb
  namespace: cozy-system
spec:
  variant: default
  components:
    metallb:
      values:
        metallb:
          frrk8s:
            enabled: true
```

### Enabling and Disabling Components

Bundles have optional components that need to be explicitly enabled (included) in the installation.
Regular bundle components can, on the other hand, be disabled (excluded) from the installation, when you don't need them.

Use `bundles.enabledPackages` and `bundles.disabledPackages` in the Platform Package values.
Every entry in those lists is a fully-qualified Package name — the same name you see with
`kubectl get package`. All platform packages live under the `cozystack.` prefix (for example,
`cozystack.metallb`, `cozystack.hetzner-robotlb`, `cozystack.nfs-driver`). Run
`kubectl get package` to see the exact names available on your cluster before editing
the Platform Package.

For example, [installing Cozystack in Hetzner]({{% ref "/docs/v1.3/install/providers/hetzner" %}})
requires swapping the default load balancer, MetalLB, with one made specifically for Hetzner, called RobotLB:

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
            - cozystack.metallb
          enabledPackages:
            - cozystack.hetzner-robotlb
        # rest of the config
```

Disabling components must be done before installing Cozystack.
Applying updated configuration with `disabledPackages` will not remove components that are already installed.
To remove already installed components, delete the Helm release manually using this command:

```bash
kubectl delete hr -n <namespace> <component>
```
