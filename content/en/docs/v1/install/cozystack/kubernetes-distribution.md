---
title: "Build Your Own Platform (BYOP)"
linkTitle: "Build Your Own Platform"
description: "Build your own platform with Cozystack by installing only the components you need using the cozypkg CLI tool."
weight: 20
---

## Overview

Cozystack can be used in BYOP (Build Your Own Platform) mode — similar to how Linux distributions let you install only the packages you need.
Instead of deploying the full platform with all components, you selectively install only what you need from the Cozystack package repository.

This approach is useful when:

-   You have an existing Kubernetes cluster and only need specific components (e.g., a Postgres operator or monitoring).
-   Your cluster already has networking (CNI) and storage configured, and you don't want Cozystack to manage them.
-   You want full control over which components are installed and how they are configured.

The workflow relies on two Kubernetes resources managed by the Cozystack Operator:

-   **PackageSource** — describes a package repository and the available variants for each package.
-   **Package** — declares that a specific package should be installed in a chosen variant, optionally with custom values.

The `cozypkg` CLI tool provides a convenient interface for working with these resources: listing available packages, resolving dependencies, and installing packages interactively.


## 1. Install the Cozystack Operator

Install the Cozystack operator using Helm from the OCI registry:

```bash
helm upgrade --install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version X.Y.Z \
  --namespace cozy-system \
  --create-namespace
```

Replace `X.Y.Z` with the desired Cozystack version.
You can find available versions on the [Cozystack releases page](https://github.com/cozystack/cozystack/releases).

If you're installing on a non-Talos Kubernetes distribution (k3s, kubeadm, RKE2, etc.), set the operator variant:

```bash
helm upgrade --install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version X.Y.Z \
  --namespace cozy-system \
  --create-namespace \
  --set cozystackOperator.variant=generic \
  --set cozystack.apiServerHost=<YOUR_API_SERVER_IP> \
  --set cozystack.apiServerPort=6443
```

The operator installs FluxCD (in all-in-one mode, working without CNI) and creates the initial `cozystack.cozystack-platform` PackageSource.

At this point, only one PackageSource exists:

```bash
kubectl get packagesource
```

```console
NAME                           VARIANTS                      READY   STATUS
cozystack.cozystack-platform   default,isp-full,isp-full...  True    ...
```


## 2. Install cozypkg

Install the `cozypkg` CLI tool using Homebrew:

```bash
brew tap cozystack/tap
brew install cozypkg
```

Pre-built binaries for other platforms are available on the [GitHub releases page](https://github.com/cozystack/cozystack/releases).


## 3. Install the Platform Package

The first step is to install the `cozystack-platform` package with the `default` variant.
This variant does not install any components — it only registers PackageSources for all packages available in the Cozystack repository.

```bash
cozypkg add cozystack.cozystack-platform
```

The tool will prompt you to select a variant. Choose `default`:

```console
PackageSource: cozystack.cozystack-platform
Available variants:
  1. default
  2. isp-full
  3. isp-full-generic
  4. isp-hosted
Select variant (1-4): 1
```

After the platform package is installed, all other PackageSources become available:

```bash
cozypkg list
```

```console
NAME                                VARIANTS                      READY   STATUS
cozystack.cert-manager              default                       True    ...
cozystack.cozystack-platform        default,isp-full,isp-full...  True    ...
cozystack.ingress-nginx             default                       True    ...
cozystack.linstor                   default                       True    ...
cozystack.metallb                   default                       True    ...
cozystack.monitoring                default                       True    ...
cozystack.networking                noop,cilium,cilium-kilo,...   True    ...
cozystack.postgres-operator         default                       True    ...
...
```


## 4. Install Packages

Use `cozypkg add` to install any available package. The tool automatically resolves dependencies and prompts you to select a variant for each package that needs to be installed.

```bash
cozypkg add <package-name>
```

For example, when installing a package that depends on networking, `cozypkg` will detect the dependency, show which packages are already installed, and ask you to choose a variant for each missing dependency.

### Networking Variants

The `cozystack.networking` package has several variants to accommodate different environments:

| Variant | Description |
|:--------|:------------|
| `noop` | Installs nothing. Use when networking is already configured in your cluster (e.g., existing CNI and kube-proxy). |
| `cilium` | Cilium CNI for Talos Linux clusters. |
| `cilium-generic` | Cilium CNI for generic Kubernetes distributions (k3s, kubeadm, RKE2). |
| `kubeovn-cilium` | Cilium + KubeOVN for Talos Linux. Required for full virtualization features (live migration). |
| `kubeovn-cilium-generic` | Cilium + KubeOVN for generic Kubernetes distributions. |
| `cilium-kilo` | Cilium + Kilo for WireGuard-based cluster mesh. |

If your cluster already has a CNI plugin configured, choose `noop`.
Since networking is a dependency of most other packages, the `noop` variant satisfies the dependency without installing anything.

### Viewing Installed Packages

To see which packages are currently installed and their variants:

```bash
cozypkg list --installed
```

```console
NAME                           VARIANT   READY   STATUS
cozystack.cozystack-platform   default   True    ...
cozystack.networking           noop      True    ...
cozystack.cert-manager         default   True    ...
```


## 5. Override Component Values

Each package consists of one or more components (Helm charts). You can override values for specific components by editing the Package resource directly.

The Package spec supports a `components` map where you can specify values for each component:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.metallb
spec:
  variant: default
  components:
    metallb:
      values:
        metallb:
          frrk8s:
            enabled: true
```

Apply the resource:

```bash
kubectl apply -f metallb-package.yaml
```

To find available values for a component, refer to the corresponding `values.yaml` in the [Cozystack repository](https://github.com/cozystack/cozystack/tree/main/packages/system).

You can also enable or disable individual components within a package:

```yaml
spec:
  components:
    some-component:
      enabled: false
```


## 6. Remove Packages

To remove an installed package:

```bash
cozypkg del <package-name>
```

The tool checks for reverse dependencies — if other installed packages depend on the one you're removing, it will list them and ask for confirmation before deleting all affected packages.


## Next Steps

-   Learn about [Cozystack variants]({{% ref "/docs/v1/operations/configuration/variants" %}}) and how they define package composition.
-   See the [Components reference]({{% ref "/docs/v1/operations/configuration/components" %}}) for details on overriding component parameters.
-   For a full platform installation, see the [Platform installation guide]({{% ref "./platform" %}}).
