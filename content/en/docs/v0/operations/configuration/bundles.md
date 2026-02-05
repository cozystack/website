---
title: "Cozystack Bundles: Overview and Comparison"
linkTitle: "Bundles"
description: "Cozystack bundles reference: composition, configuration, and troubleshooting."
weight: 20
aliases:
  - /docs/guides/bundles
  - /docs/operations/bundles/
  - /docs/operations/bundles/paas-full
  - /docs/operations/bundles/paas-hosted
  - /docs/operations/bundles/distro-full
  - /docs/operations/bundles/distro-hosted
  - /docs/install/cozystack/bundles
---

## Introduction

**Bundles** are pre-defined combinations of Cozystack components.
Each bundle is tested, versioned, and guaranteed to work as a unit.
They simplify installation, reduce the risk of misconfiguration, and make it easier to choose the right set of features for your deployment.

This guide is for infrastructure engineers, DevOps teams, and platform architects planning to deploy Cozystack in different environments.
It explains how Cozystack bundles help tailor the installation to specific needs—whether you're building a fully featured platform-as-a-service
or just need a minimal Kubernetes cluster.


## Bundles Overview

| Component                     | [paas-full]            | [iaas-full]<sup>*</sup> | [paas-hosted]  | [distro-full]         | [distro-hosted]       |
|:------------------------------|:-----------------------|:------------------------|:---------------|:----------------------|:----------------------|
| [Managed Kubernetes][k8s]     | ✔                      | ✔                       |                |                       |                       |
| [Managed Applications][apps]  | ✔                      |                         | ✔              |                       |                       |
| [Virtual Machines][vm]        | ✔                      | ✔                       |                |                       |                       |
| Cozystack Dashboard (UI)      | ✔                      | ✔                       | ✔              |                       |                       |
| [Cozystack API][api]          | ✔                      | ✔                       | ✔              |                       |                       |
| [Kubernetes Operators]        | ✔                      |                         | ✔              | ✔ (optional)          | ✔ (optional)          |
| [Monitoring subsystem]        | ✔                      | ✔                       | ✔              | ✔ (optional)          | ✔ (optional)          |
| Storage subsystem             | [LINSTOR]              | [LINSTOR]               |                | [LINSTOR]             |                       |
| Networking subsystem          | [Kube-OVN] + [Cilium]  | [Kube-OVN] + [Cilium]   |                | [Cilium]              |                       |
| Virtualization subsystem      | [KubeVirt]             | [KubeVirt]              |                | [KubeVirt] (optional) | [KubeVirt] (optional) |
| OS and [Kubernetes] subsystem | [Talos Linux]          | [Talos Linux]           |                | [Talos Linux]         |                       |

<sup>*</sup> Bundle `iaas-full` is currently on the roadmap, see [cozystack/cozystack#730][iaas-full-gh].

[apps]: {{% ref "/docs/applications" %}}
[vm]: {{% ref "/docs/virtualization" %}}
[k8s]: {{% ref "/docs/kubernetes" %}}
[api]: {{% ref "/docs/cozystack-api" %}}
[monitoring subsystem]: {{% ref "/docs/guides/platform-stack#victoria-metrics" %}}
[linstor]: {{% ref "/docs/guides/platform-stack#drbd" %}}
[kube-ovn]: {{% ref "/docs/guides/platform-stack#kube-ovn" %}}
[cilium]: {{% ref "/docs/guides/platform-stack#cilium" %}}
[kubevirt]: {{% ref "/docs/guides/platform-stack#kubevirt" %}}
[talos linux]: {{% ref "/docs/guides/platform-stack#talos-linux" %}}
[kubernetes]: {{% ref "/docs/guides/platform-stack#kubernetes" %}}
[kubernetes operators]: https://github.com/cozystack/cozystack/blob/c0f742595f1e942a9bf4921e9655142cc9040551/packages/core/platform/bundles/paas-full.yaml#L185-L243

[paas-full-gh]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/bundles/paas-full.yaml
[iaas-full-gh]: https://github.com/cozystack/cozystack/issues/730
[paas-hosted-gh]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/bundles/paas-hosted.yaml
[distro-full-gh]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/bundles/distro-full.yaml
[distro-hosted-gh]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/bundles/distro-hosted.yaml

[paas-full]: {{% ref "/docs/operations/configuration/bundles#paas-full" %}}
[iaas-full]: https://github.com/cozystack/cozystack/issues/730
[paas-hosted]: {{% ref "/docs/operations/configuration/bundles#paas-hosted" %}}
[distro-full]: {{% ref "/docs/operations/configuration/bundles#distro-full" %}}
[distro-hosted]: {{% ref "/docs/operations/configuration/bundles#distro-hosted" %}}


## Choosing the Right Bundle

Bundles combine components from different layers to match particular needs.
Some are designed for full platform scenarios, others for cloud-hosted workloads or Kubernetes distributions.

### `paas-full`

`paas-full` is a full-featured PaaS and IaaS bundle, designed for installation on Talos Linux.
It includes all four layers and provides the full set of Cozystack components, enabling a comprehensive PaaS experience.
Some higher-layer components are optional and can be excluded during installation.

`paas-full` is intended for installation on bare-metal servers or VMs.

Bundle source: [paas-full.yaml][paas-full-gh].

Example configuration:

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
  root-host: "example.org"
  api-server-endpoint: "https://192.168.100.10:6443"
  expose-services: "api,dashboard,cdi-uploadproxy,vm-exportproxy"
```

### `paas-hosted`

Cozystack can be installed as platform-as-a-service (PaaS) on top of an existing managed Kubernetes cluster,
typically provisioned from a cloud provider.
Bundle `paas-hosted` is made for this use case.
It can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.

Bundle `paas-hosted` includes layers 3 and 4, providing Cozystack API and UI, managed applications, and tenant Kubernetes clusters.
It does not include CNI plugins, virtualization, or storage.

The Kubernetes cluster used to deploy Cozystack must conform to the following requirements:

-   Listening address of some Kubernetes components must be changed from `localhost` to a routable address.
-   Kubernetes API server must be reachable on `localhost`.

Bundle source: [paas-hosted.yaml][paas-hosted-gh].

Example configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-hosted"
  root-host: "example.org"
  api-server-endpoint: "https://192.168.100.10:6443"
  expose-services: "api,dashboard"
```

### `distro-full`

Cozystack can be used as a pure Kubernetes distribution for installing on Talos Linux over bare metal.
Bundle `distro-full` includes everything needed to make a ready-to-work Kubernetes cluster:

- Talos as the operating system,
- Kubernetes distribution,
- Ready-to-use subsystems: networking, virtualization, and storage,
- Optional components: Monitoring and a set of Kubernetes operators.

Bundle source: [distro-full.yaml][distro-full-gh].

Example configuration:

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
  root-host: "example.org"
  api-server-endpoint: "https://192.168.100.10:6443"
```

### `distro-hosted`

This minimal Cozystack bundle adds extra functionality on top of a hosted Kubernetes cluster.
It includes three optional components:

- Virtualization subsystem (as KubeVirt).
- Monitoring subsystem.
- Kubernetes operators.

Bundle `distro-hosted` can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.
It does not include CNI plugins, virtualization, storage, or multitenancy.

The Kubernetes cluster used to deploy Cozystack must conform to the following requirements:

* Kubernetes cluster DNS domain must be set to `cozy.local`.
* Listening address of some Kubernetes components must be changed from `localhost` to a routable address.
* Kubernetes API server must be reachable on `localhost`.

Bundle source: [distro-hosted.yaml][distro-hosted-gh].

### `iaas-full`

This planned bundle offers a complete infrastructure-as-a-service setup.
It provides all Cozystack components except for Kubernetes operators
and preset managed applications.

Bundle `iaas-full` is yet to be implemented in Cozystack.
See [cozystack/cozystack#730][iaas-full-gh].

## Learn More

For a full list of configuration options for each bundle, refer to the
[ConfigMap reference]({{% ref "/docs/operations/configuration/configmap" %}}).

To see the full list of components, how to enable and disable them, refer to the
[Components reference]({{% ref "/docs/operations/configuration/components" %}}).

To deploy a selected bundle, follow the [Cozystack installation guide]({{% ref "/docs/install/cozystack" %}}) 
or [provider-specific guides]({{% ref "/docs/install/providers" %}}).
However, if this your first time installing Cozystack, it's best to use the complete bundle `paas-full` and
go through the [Cozystack tutorial]({{% ref "/docs/getting-started" %}}).
