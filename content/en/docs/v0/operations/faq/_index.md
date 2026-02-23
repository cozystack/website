---
title: "Frequently asked questions and How-to guides"
linkTitle: "FAQ / How-tos"
description: "Knowledge base with FAQ and advanced configurations"
weight: 100
aliases:
  - /docs/v0/faq
  - /docs/v0/guides/faq
  - /docs/operations/faq
  - /docs/faq
  - /docs/guides/faq
---

{{% alert title="Troubleshooting" %}}
Troubleshooting advice can be found on our [Troubleshooting Cheatsheet](/docs/v0/operations/troubleshooting/).
{{% /alert %}}


## Deploying Cozystack

<details>
<summary>How to allocate space on system disk for user storage</summary>

Deploying Cozystack, [How to install Talos on a single-disk machine]({{% ref "/docs/v0/install/how-to/single-disk" %}})

</details>
<br>

<details>
<summary>How to Enable KubeSpan</summary>

Deploying Cozystack, [How to Enable KubeSpan]({{% ref "/docs/v0/install/how-to/kubespan" %}})

</details>
<br>

<details>
<summary>How to enable Hugepages</summary>

Deploying Cozystack, [How to enable Hugepages]({{% ref "/docs/v0/install/how-to/hugepages" %}}).

</details>
<br>

<details>
<summary>What if my cloud provider does not support MetalLB</summary>

Most cloud providers don't support MetalLB.
Instead of using it, you can expose the main ingress controller using the external IPs method.

For deploying on Hetzner, follow the specialized [Hetzner installation guide]({{% ref "/docs/v0/install/providers/hetzner" %}}).
For other providers, follow the [Cozystack installation guide, Public IP Setup]({{% ref "/docs/v0/install/cozystack#4b-public-ip-setup" %}}).

</details>
<br>

<details>
<summary>Public-network Kubernetes deployment</summary>

Deploying Cozystack, [Deploy with public networks]({{% ref "/docs/v0/install/how-to/public-ip" %}}).

</details>

## Operations

<details>
<summary>How to enable access to dashboard via ingress-controller</summary>

Update your `ingress` application and enable `dashboard: true` option in it.
Dashboard will become available under: `https://dashboard.<your_domain>`

</details>
<br>

<details>
<summary>How to configure Cozystack using FluxCD or ArgoCD</summary>

Here you can find reference repository to learn how to configure Cozystack services using GitOps approach:

- https://github.com/aenix-io/cozystack-gitops-example

</details>
<br>

<details>
<summary>How to generate kubeconfig for tenant users</summary>

Moved to [How to generate kubeconfig for tenant users]({{% ref "/docs/v0/operations/faq/generate-kubeconfig" %}}).

</details>
<br>

<details>
<summary>How to use ServiceAccount tokens for API access</summary>

See [ServiceAccount Tokens for API Access]({{% ref "/docs/v0/operations/faq/serviceaccount-api-access" %}}).

</details>
<br>

<details>
<summary>How to Rotate Certificate Authority</summary>

Moved to Cluster Maintenance, [How to Rotate Certificate Authority]({{% ref "/docs/v0/operations/cluster/rotate-ca" %}}).

</details>
<br>

<details>
<summary>How to cleanup etcd state</summary>

Moved to Troubleshooting: [How to clean up etcd state]({{% ref "/docs/v0/operations/troubleshooting/etcd#how-to-clean-up-etcd-state" %}}).

</details>

## Bundles

<details>
<summary>How to overwrite parameters for specific components</summary>

Moved to Cluster configuration, [Components reference]({{% ref "/docs/v0/operations/configuration/components#overwriting-component-parameters" %}}).

</details>
<br>

<details>
<summary>How to disable some components from bundle</summary>

Moved to Cluster configuration, [Components reference]({{% ref "/docs/v0/operations/configuration/components#enabling-and-disabling-components" %}}).

</details>
