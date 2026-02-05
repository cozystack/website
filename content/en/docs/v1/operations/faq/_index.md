---
title: "Frequently asked questions and How-to guides"
linkTitle: "FAQ / How-tos"
description: "Knowledge base with FAQ and advanced configurations"
weight: 100
aliases:
  - /docs/faq
  - /docs/guides/faq
---

{{% alert title="Troubleshooting" %}}
Troubleshooting advice can be found on our [Troubleshooting Cheatsheet](/docs/operations/troubleshooting/).
{{% /alert %}}


## Deploying Cozystack

### How to allocate space on system disk for user storage

Deploying Cozystack, [How to install Talos on a single-disk machine]({{% ref "/docs/install/how-to/single-disk" %}})

### How to Enable KubeSpan

Deploying Cozystack, [How to Enable KubeSpan]({{% ref "/docs/install/how-to/kubespan" %}})

### How to enable Hugepages

Deploying Cozystack, [How to enable Hugepages]({{% ref "/docs/install/how-to/hugepages" %}}).


### What if my cloud provider does not support MetalLB

Most cloud providers don't support MetalLB.
Instead of using it, you can expose the main ingress controller using the external IPs method.

For deploying on Hetzner, follow the specialized [Hetzner installation guide]({{% ref "/docs/install/providers/hetzner" %}}).
For other providers, follow the [Cozystack installation guide, Public IP Setup]({{% ref "/docs/install/cozystack#4b-public-ip-setup" %}}).

### Public-network Kubernetes deployment

Deploying Cozystack, [Deploy with public networks]({{% ref "/docs/install/how-to/public-ip" %}}).

## Operations

### How to enable access to dashboard via ingress-controller

Update your `ingress` application and enable `dashboard: true` option in it.
Dashboard will become available under: `https://dashboard.<your_domain>`


### How to configure Cozystack using FluxCD or ArgoCD

Here you can find reference repository to learn how to configure Cozystack services using GitOps approach:

- https://github.com/aenix-io/cozystack-gitops-example

### How to generate kubeconfig for tenant users

Moved to [How to generate kubeconfig for tenant users]({{% ref "/docs/operations/faq/generate-kubeconfig" %}}).

### How to Rotate Certificate Authority

Moved to Cluster Maintenance, [How to Rotate Certificate Authority]({{% ref "/docs/operations/cluster/rotate-ca" %}}).

### How to cleanup etcd state

Moved to Troubleshooting: [How to clean up etcd state]({{% ref "/docs/operations/troubleshooting/etcd#how-to-clean-up-etcd-state" %}}).

## Bundles

### How to overwrite parameters for specific components

Moved to Cluster configuration, [Components reference]({{% ref "/docs/operations/configuration/components#overwriting-component-parameters" %}}).

### How to disable some components from bundle

Moved to Cluster configuration, [Components reference]({{% ref "/docs/operations/configuration/components#enabling-and-disabling-components" %}}).
