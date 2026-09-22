---
title: "Cozystack Components Reference"
linkTitle: "Components"
description: "Full reference for Cozystack components."
weight: 30
aliases:
  - /docs/v1.2/install/cozystack/components
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
Every entry in those lists is a fully-qualified name under the `cozystack.` prefix (for example, `cozystack.metallb`, `cozystack.hetzner-robotlb`, `cozystack.nfs-driver`). Run `kubectl get packagesource` to see the exact names available on your cluster before editing the Platform Package. `kubectl get package` answers only for `disabledPackages`, because an optional component has no Package object until its name is already in `enabledPackages`.

For example, [installing Cozystack in Hetzner]({{% ref "/docs/v1.2/install/providers/hetzner" %}})
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
From v1.2.1 onward, applying updated configuration with `disabledPackages` will not remove components that are already installed.
On v1.2.0 the platform does not annotate the Package with `helm.sh/resource-policy: keep`, so adding the name to `disabledPackages` does remove an installed component: the destruction described below happens at that point, and there is no second command to run. Back up anything you still need before making that edit. Take the listing below before making the edit and wait on the same releases afterwards: the Package its selector needs goes away with the component.

From v1.2.1 onward, removing an installed component takes two steps. Add its name to `disabledPackages` in the Platform Package above, then wait for the operator to carry that edit across. The name appears in this output once it has:

```bash
kubectl get helmrelease cozystack-platform --namespace cozy-system \
  --output jsonpath='{.spec.values.bundles.disabledPackages}'
```

Then delete the Package object.

{{% alert title="Warning" color="warning" %}}
Deleting the Package uninstalls the component's Helm release, and that destroys more than the workloads. Anything the chart rendered as an ordinary template without `helm.sh/resource-policy: keep` goes with the release, CRDs and namespaces included, and Kubernetes deletes every custom resource of those CRD kinds along with them. Removing `cozystack.metallb` takes every CRD the MetalLB chart bundles, subcharts included, and with them every custom resource of those kinds cluster-wide; removing `cozystack.cozystack-basics` takes the `cozy-public` and `tenant-root` namespaces and everything stored in them, which is every application in the root tenant. Back up anything you still need first.
{{% /alert %}}

The namespace a component installs into is the exception: the operator applies that one itself, outside the component's release and with no ownerReference, so the uninstall never had it to remove.

List the releases the Package owns before deleting it. The operator labels every HelmRelease it renders with the name of the Package that produced it, and one Package can own several:

```bash
kubectl get helmrelease --all-namespaces --selector cozystack.io/package=<package-name> \
  --output custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,SUSPENDED:.spec.suspend'
```

Clear `spec.suspend` on any release that shows `true` before going on. Flux skips the uninstall for a suspended HelmRelease and only drops its own finalizer, so that release disappears with everything it installed left behind and nothing left managing it.

```bash
kubectl delete package.cozystack.io <package-name>
```

Nothing holds a finalizer on the Package, so this command returns as soon as the object is gone and the uninstall it triggers runs afterwards. Wait on each release from the listing to know the destructive part has finished:

```bash
kubectl wait --for=delete helmrelease/<name> --namespace <namespace> --timeout=10m
```

`kubectl wait --for=delete` exits 0 for a name that was never there, silently and with nothing to tell it apart from a deletion it watched, so take both values from the listing rather than guessing them. A returned wait says the HelmRelease is gone, not that the uninstall ran.

Deleting the Package while the platform values still render it means the next platform upgrade brings it back, undoing the removal one level up. Nothing reports this at the time: the delete succeeds either way and the Package reappears whenever that upgrade happens to run.

`kubectl delete hr` is not a lighter-weight version of this. Flux uninstalls the release when an unsuspended HelmRelease goes away, so it destroys the same CRDs and custom resources, and then the Package recreates the HelmRelease and the chart reinstalls. The workloads come back, the custom resources do not. If you have run it before, those custom resources are already gone and have to be recreated from your own manifests or a backup.
