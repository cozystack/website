---
title: "Cozystack Bundles: Overview and Comparison"
linkTitle: "Cozystack Bundles"
description: "Cozystack bundles reference: composition, configuration, and troubleshooting."
weight: 17
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
| [Managed Kubernetes][k8s]     | ✔                      | ✔                       | ❌             | ❌                    | ❌                    |
| [Managed Applications][apps]  | ✔                      | ❌                      | ✔              | ❌                    | ❌                    |
| [Virtual Machines][vm]        | ✔                      | ✔                       | ❌             | ❌                    | ❌                    |
| Cozystack Dashboard (UI)      | ✔                      | ✔                       | ✔              | ❌                    | ❌                    |
| [Cozystack API][api]          | ✔                      | ✔                       | ✔              | ❌                    | ❌                    |
| [Kubernetes Operators]        | ✔                      | ❌                      | ✔              | ✔ (optional)          | ✔ (optional)          |
| [Monitoring subsystem]        | ✔                      | ✔                       | ✔              | ✔ (optional)          | ✔ (optional)          |
| Storage subsystem             | [LINSTOR]              | [LINSTOR]               | ❌             | [LINSTOR]             | ❌                    |
| Networking subsystem          | [Kube-OVN] + [Cilium]  | [Kube-OVN] + [Cilium]   | ❌             | [Cilium]              | ❌                    |
| Virtualization subsystem      | [KubeVirt]             | [KubeVirt]              | ❌             | [KubeVirt] (optional) | [KubeVirt] (optional) |
| OS and [Kubernetes] subsystem | [Talos Linux]          | [Talos Linux]           | ❌             | [Talos Linux]         | ❌                    |


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
[kubernetes operators]: https://github.com/cozystack/cozystack/blob/29b49496f25958d57628072d0edd102922e883f0/packages/core/platform/bundles/distro-full.yaml#L104-L158

[paas-full-gh]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/bundles/paas-full.yaml
[iaas-full-gh]: https://github.com/cozystack/cozystack/issues/730
[paas-hosted-gh]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/bundles/paas-hosted.yaml
[distro-full-gh]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/bundles/distro-full.yaml
[distro-hosted-gh]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/bundles/distro-hosted.yaml

[paas-full]: {{% ref "/docs/operations/bundles/paas-full" %}}
[iaas-full]: https://github.com/cozystack/cozystack/issues/730
[paas-hosted]: {{% ref "/docs/operations/bundles/paas-hosted" %}}
[distro-full]: {{% ref "/docs/operations/bundles/distro-full" %}}
[distro-hosted]: {{% ref "/docs/operations/bundles/distro-hosted" %}}


## Choosing the Right Bundle

Bundles combine components from different layers to match particular needs.
Some are designed for full platform scenarios, others for cloud-hosted workloads or Kubernetes distributions.

### `paas-full`

`paas-full` is a full-featured PaaS and IaaS bundle.
It includes all four layers and provides the full set of Cozystack components.
Some higher-layer components are optional and can be excluded during installation.

`paas-full` is intended for installation on bare-metal servers.

Read more:

- Bundle [configuration reference][paas-full].
- Bundle source: [paas-full.yaml][paas-full-gh].

### `iaas-full`

This planned bundle offers a complete infrastructure-as-a-service setup.
It provides all Cozystack components except for Kubernetes operators
and preset managed applications.

Bundle `iaas-full` is yet to be implemented in Cozystack.
See [cozystack/cozystack#730][iaas-full-gh].

### `paas-hosted`

Cozystack can be installed as platform-as-a-service (PaaS) on top of an existing managed Kubernetes cluster,
typically provisioned from a cloud provider.
Bundle `paas-hosted` is made for this use case.
It includes layers 3 and 4, providing Cozystack API and UI, managed applications, VMs, and tenant Kubernetes clusters.

Read more:

- Bundle [configuration reference][paas-hosted].
- Bundle source: [paas-hosted.yaml][paas-hosted-gh].

### `distro-full`

Cozystack can be used as a pure Kubernetes distribution for installing on bare metal.
Bundle `distro-full` includes everything needed to make a ready-to-work Kubernetes cluster:
Talos as the operating system, a Kubernetes distribution, plus ready-to-use networking, virtualization, and storage subsystems.
As optional components, it also provides monitoring and a set of Kubernetes operators.

Read more:

- Bundle [configuration reference][distro-full].
- Bundle source: [distro-full.yaml][distro-full-gh].

### `distro-hosted`

This minimal Cozystack bundle adds extra functionality on top of a hosted Kubernetes cluster.
It includes three optional components:

- Virtualization subsystem (as KubeVirt).
- Monitoring subsystem.
- Kubernetes operators.

- Bundle [configuration reference][distro-hosted].
- Bundle source: [distro-hosted.yaml][distro-hosted-gh].

## Learn More

To see the full list of components and configuration options for each bundle, refer to the
[bundle reference documentation]({{% ref "/docs/operations/bundles" %}}).

To deploy a selected bundle, follow the [Cozystack tutorial]({{% ref "/docs/getting-started/install-cozystack" %}}) or platform installation documentation.


