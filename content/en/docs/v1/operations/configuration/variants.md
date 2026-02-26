---
title: "Cozystack Variants: Overview and Comparison"
linkTitle: "Variants"
description: "Cozystack variants reference: composition, configuration, and comparison."
weight: 20
aliases:
  - /docs/v1/guides/bundles
  - /docs/v1/operations/bundles/
  - /docs/v1/operations/bundles/isp-full
  - /docs/v1/operations/bundles/isp-hosted
  - /docs/v1/operations/bundles/paas-full
  - /docs/v1/operations/bundles/paas-hosted
  - /docs/v1/operations/bundles/distro-full
  - /docs/v1/operations/bundles/distro-hosted
  - /docs/v1/install/cozystack/bundles
  - /docs/v1/operations/configuration/bundles
---

## Introduction

**Variants** are pre-defined configurations of Cozystack that determine which bundles and components are enabled.
Each variant is tested, versioned, and guaranteed to work as a unit.
They simplify installation, reduce the risk of misconfiguration, and make it easier to choose the right set of features for your deployment.

This guide is for infrastructure engineers, DevOps teams, and platform architects planning to deploy Cozystack in different environments.
It explains how Cozystack variants help tailor the installation to specific needs—whether you're building a fully featured platform-as-a-service
or need full manual control over installed packages.


## Variants Overview

| Component                     | [default]              | [isp-full]             | [isp-full-generic]     | [isp-hosted]           |
|:------------------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------|
| [Managed Kubernetes][k8s]     |                        | ✔                      | ✔                      |                        |
| [Managed Applications][apps]  |                        | ✔                      | ✔                      | ✔                      |
| [Virtual Machines][vm]        |                        | ✔                      | ✔                      |                        |
| Cozystack Dashboard (UI)      |                        | ✔                      | ✔                      | ✔                      |
| [Cozystack API][api]          |                        | ✔                      | ✔                      | ✔                      |
| [Kubernetes Operators]        |                        | ✔                      | ✔                      | ✔                      |
| [Monitoring subsystem]        |                        | ✔                      | ✔                      | ✔                      |
| Storage subsystem             |                        | [LINSTOR]              | [LINSTOR]              |                        |
| Networking subsystem          |                        | [Kube-OVN] + [Cilium]  | [Kube-OVN] + [Cilium]  |                        |
| Virtualization subsystem      |                        | [KubeVirt]             | [KubeVirt]             |                        |
| OS and [Kubernetes] subsystem |                        | [Talos Linux]          |                        |                        |

[apps]: {{% ref "/docs/v1/applications" %}}
[vm]: {{% ref "/docs/v1/virtualization" %}}
[k8s]: {{% ref "/docs/v1/kubernetes" %}}
[api]: {{% ref "/docs/v1/cozystack-api" %}}
[monitoring subsystem]: {{% ref "/docs/v1/guides/platform-stack#victoria-metrics" %}}
[linstor]: {{% ref "/docs/v1/guides/platform-stack#drbd" %}}
[kube-ovn]: {{% ref "/docs/v1/guides/platform-stack#kube-ovn" %}}
[cilium]: {{% ref "/docs/v1/guides/platform-stack#cilium" %}}
[kubevirt]: {{% ref "/docs/v1/guides/platform-stack#kubevirt" %}}
[talos linux]: {{% ref "/docs/v1/guides/platform-stack#talos-linux" %}}
[kubernetes]: {{% ref "/docs/v1/guides/platform-stack#kubernetes" %}}
[kubernetes operators]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/templates/bundles/paas.yaml

[default]: {{% ref "/docs/v1/operations/configuration/variants#default" %}}
[isp-full]: {{% ref "/docs/v1/operations/configuration/variants#isp-full" %}}
[isp-full-generic]: {{% ref "/docs/v1/operations/configuration/variants#isp-full-generic" %}}
[isp-hosted]: {{% ref "/docs/v1/operations/configuration/variants#isp-hosted" %}}


## Choosing the Right Variant

Variants combine bundles from different layers to match particular needs.
Some are designed for full platform scenarios, others for cloud-hosted workloads or fully manual package management.

### `default`

`default` is a minimal variant that only provides the set of PackageSources (package registry references).
No bundles or components are pre-configured—all packages are managed manually through [cozypkg](https://github.com/cozystack/cozystack/tree/main/cmd/cozypkg).
Use this variant when you need full control over which packages are installed and configured.

Example configuration:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: default
```

### `isp-full`

`isp-full` is a full-featured PaaS and IaaS variant, designed for installation on Talos Linux.
It includes all bundles and provides the full set of Cozystack components, enabling a comprehensive PaaS experience.
Some higher-layer components are optional and can be excluded during installation.

`isp-full` is intended for installation on bare-metal servers or VMs.

Example configuration:

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
        networking:
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://192.168.100.10:6443"
          exposedServices:
            - api
            - dashboard
            - cdi-uploadproxy
            - vm-exportproxy
```

### `isp-full-generic`

`isp-full-generic` provides the same full-featured PaaS and IaaS experience as `isp-full`, but is designed for generic Kubernetes distributions such as k3s, kubeadm, or RKE2.
Use this variant when you want the full Cozystack feature set without requiring Talos Linux.

For detailed installation instructions, see the [Generic Kubernetes guide]({{% ref "/docs/v1/install/kubernetes/generic" %}}).

Example configuration:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full-generic
  components:
    platform:
      values:
        networking:
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://192.168.100.10:6443"
          exposedServices:
            - api
            - dashboard
            - cdi-uploadproxy
            - vm-exportproxy
```

### `isp-hosted`

Cozystack can be installed as platform-as-a-service (PaaS) on top of an existing managed Kubernetes cluster,
typically provisioned from a cloud provider.
Variant `isp-hosted` is made for this use case.
It can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.

`isp-hosted` includes the PaaS and NaaS bundles, providing Cozystack API and UI, managed applications, and tenant Kubernetes clusters.
It does not include CNI plugins, virtualization, or storage.

The Kubernetes cluster used to deploy Cozystack must conform to the following requirements:

-   Listening address of some Kubernetes components must be changed from `localhost` to a routable address.
-   Kubernetes API server must be reachable on `localhost`.

Example configuration:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-hosted
  components:
    platform:
      values:
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://192.168.100.10:6443"
          exposedServices:
            - api
            - dashboard
```

## Learn More

For a full list of configuration options for each variant, refer to the
[configuration reference]({{% ref "/docs/v1/operations/configuration" %}}).

To see the full list of components, how to enable and disable them, refer to the
[Components reference]({{% ref "/docs/v1/operations/configuration/components" %}}).

To deploy a selected variant, follow the [Cozystack installation guide]({{% ref "/docs/v1/install/cozystack" %}})
or [provider-specific guides]({{% ref "/docs/v1/install/providers" %}}).
However, if this your first time installing Cozystack, it's best to use the variant `isp-full` and
go through the [Cozystack tutorial]({{% ref "/docs/v1/getting-started" %}}).
