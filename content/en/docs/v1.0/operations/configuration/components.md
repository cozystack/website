---
title: "Cozystack Components Reference"
linkTitle: "Components"
description: "Full reference for Cozystack components."
weight: 30
aliases:
  - /docs/v1.0/install/cozystack/components
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
For example, [installing Cozystack in Hetzner]({{% ref "/docs/v1.0/install/providers/hetzner" %}})
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
            - cozystack.metallb
          enabledPackages:
            - cozystack.hetzner-robotlb
        # rest of the config
```

Disabling components must be done before installing Cozystack.

On v1.0 the platform does not annotate the Packages it renders with `helm.sh/resource-policy: keep`, so adding a name to `disabledPackages` also removes the component when it is already installed. The next platform reconcile drops the Package, the operator's ownerReference takes the component's HelmRelease with it, and Flux uninstalls the release. There is no second command and no confirmation step, so back up anything you still need before making that edit.

{{% alert title="Warning" color="warning" %}}
Uninstalling the component's Helm release destroys more than the workloads. Anything the chart rendered as an ordinary template without `helm.sh/resource-policy: keep` goes with the release, CRDs and namespaces included, and Kubernetes deletes every custom resource of those CRD kinds along with them. Removing `cozystack.metallb` takes every CRD the MetalLB chart bundles, subcharts included, and with them every custom resource of those kinds cluster-wide; removing `cozystack.cozystack-basics` takes the `cozy-public` namespace and everything stored in it. Back up anything you still need first.
{{% /alert %}}

The namespace a component installs into is the exception: the operator applies that one itself, outside the component's release and with no ownerReference, so the uninstall never had it to remove.

`kubectl delete hr` is not a lighter-weight way to do the same thing. Flux uninstalls the release when the HelmRelease goes away, so it destroys the same CRDs and custom resources, and then the Package recreates the HelmRelease and the chart reinstalls. The workloads come back, the custom resources do not. If you have run it before, those custom resources are already gone and have to be recreated from your own manifests or a backup.
