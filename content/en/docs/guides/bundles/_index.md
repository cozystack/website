---
title: "Cozystack Bundles: Overview and Comparison"
linkTitle: "Cozystack Bundles"
description: "Cozystack bundles reference: composition, configuration, and troubleshooting."
weight: 15
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
| Cozystack Dashboard           | ✔                      | ✔                       | ✔              | ❌                    | ❌                    |
| [Cozystack API][api]          | ✔                      | ✔                       | ✔              | ❌                    | ❌                    |
| [Managed Applications][apps]  | ✔                      | ❌                      | ✔              | ❌                    | ❌                    |
| [Virtual Machines][vm]        | ✔                      | ✔                       | ❌             | ❌                    | ❌                    |
| [Managed Kubernetes][k8s]     | ✔                      | ✔                       | ❌             | ❌                    | ❌                    |
| Operators                     | ✔                      | ❌                      | ✔              | ✔ (optional)          | ✔ (optional)          |
| [Monitoring subsystem]        | ✔                      | ✔                       | ✔              | ✔ (optional)          | ✔ (optional)          |
| Storage subsystem             | [LINSTOR]              | [LINSTOR]               | ❌             | [LINSTOR]             | ❌                    |
| Networking subsystem          | [Kube-OVN] + [Cilium]  | [Kube-OVN] + [Cilium]   | ❌             | [Cilium]              | ❌                    |
| Virtualization subsystem      | [KubeVirt]             | [KubeVirt]              | ❌             | [KubeVirt] (optional) | [KubeVirt] (optional) |
| OS and [Kubernetes] subsystem | [Talos Linux]          | [Talos Linux]           | ❌             | [Talos Linux]         | ❌                    |


<sup>*</sup> Bundle `iaas-full` is currently on the roadmap, see [cozystack/cozystack#730][iaas-full-gh].

[apps]: {{% ref "/docs/guides/applications" %}}
[vm]: {{% ref "/docs/operations/virtualization/virtual-machines" %}}
[k8s]: {{% ref "/docs/guides/applications#managed-kubernetes" %}}
[api]: {{% ref "/docs/development/cozystack-api" %}}
[monitoring subsystem]: {{% ref "/docs/guides/platform-stack#victoria-metrics" %}}
[linstor]: {{% ref "/docs/guides/platform-stack#drbd" %}}
[kube-ovn]: {{% ref "/docs/guides/platform-stack#kube-ovn" %}}
[cilium]: {{% ref "/docs/guides/platform-stack#cilium" %}}
[kubevirt]: {{% ref "/docs/guides/platform-stack#kubevirt" %}}
[talos linux]: {{% ref "/docs/guides/platform-stack#talos-linux" %}}
[kubernetes]: {{% ref "/docs/guides/platform-stack#kubernetes" %}}

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

## What's Next

To see the full list of components and configuration options for each bundle, refer to the 
[bundle reference documentation]({{% ref "/docs/operations/bundles" %}}).

To deploy a selected bundle, follow the [Cozystack quickstart guide]({{% ref "/docs/getting-started/first-deployment" %}}) or platform installation documentation.


