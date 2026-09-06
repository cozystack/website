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
Removing one that is already installed takes two steps. Add its name to `disabledPackages` in the Platform Package above, then wait for the operator to carry that edit across. The name appears in this output once it has:

```bash
kubectl get helmrelease cozystack-platform --namespace cozy-system \
  --output jsonpath='{.spec.values.bundles.disabledPackages}'
```

Then delete the Package object. `kubectl get packages` lists the names.

{{% alert title="Warning" color="warning" %}}
Deleting the Package uninstalls the component's Helm release, and that destroys more than the workloads. Anything the chart rendered as an ordinary template without `helm.sh/resource-policy: keep` goes with the release, CRDs and namespaces included, and Kubernetes deletes every custom resource of those CRD kinds along with them. Removing `cozystack.metallb` takes the MetalLB CRDs and with them every IPAddressPool, L2Advertisement, BGPPeer and the rest of those kinds cluster-wide; removing `cozystack.cozystack-basics` takes the `cozy-public` namespace and everything stored in it. Back up anything you still need first.
{{% /alert %}}

The namespace a component installs into is the exception: the operator applies that one itself, outside the component's release and with no ownerReference, so the uninstall never had it to remove.

```bash
kubectl delete package.cozystack.io <package-name>
```

Deleting the Package while the platform values still render it means the next platform upgrade brings it back, undoing the removal one level up. Nothing reports this at the time: the delete succeeds either way and the Package reappears whenever that upgrade happens to run.

`kubectl delete hr` is not a lighter-weight version of this. Flux uninstalls the release when the HelmRelease goes away, so it destroys the same CRDs and custom resources, and then the Package recreates the HelmRelease and the chart reinstalls. The workloads come back, the custom resources do not. If you have run it before, those custom resources are already gone and have to be recreated from your own manifests or a backup.
