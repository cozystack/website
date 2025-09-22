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

### How to Enable KubeSpan

Installing Talos, [How to Enable KubeSpan]({{% ref "/docs/install/talos/kubespan" %}})

### What if my cloud provider does not support MetalLB

Most cloud providers don't support MetalLB.
Instead of using it, you can expose the main ingress controller using the external IPs method.

For deploying on Hetzner, follow the specialized [Hetzner installation guide]({{% ref "/docs/install/providers/hetzner" %}}).
For other providers, follow the [Cozystack installation guide, Public IP Setup]({{% ref "/docs/install/cozystack#4b-public-ip-setup" %}}).


## Operations

### How to enable access to dashboard via ingress-controller

Update your `ingress` application and enable `dashboard: true` option in it.
Dashboard will become available under: `https://dashboard.<your_domain>`


### How to configure Cozystack using FluxCD or ArgoCD

Here you can find reference repository to learn how to configure Cozystack services using GitOps approach:

- https://github.com/aenix-io/cozystack-gitops-example


### Public-network Kubernetes deployment

A Kubernetes/Cozystack cluster can be deployed using only public networks:

-   Both management and worker nodes have public IP addresses.
-   Worker nodes connect to the management nodes over the public Internet, without a private internal network or VPN.

Such a setup is not recommended for production, but can be used for research and testing,
when hosting limitations prevent provisioning a private network.

To enable this setup when deploying with `talosctl`, add the following data in the node configuration files:

```yaml
cluster:
  controlPlane:
    endpoint: https://<MANAGEMENT_NODE_IP>:6443
```

For `talm`, append the same lines at end of the first node's configuration file, such as `nodes/node1.yaml`.

### How to allocate space on system disk for user storage

Moved to [How to install Talos on a single-disk machine]({{% ref "/docs/operations/faq/single-disk-installation" %}})

### How to generate kubeconfig for tenant users

Moved to [How to generate kubeconfig for tenant users]({{% ref "/docs/operations/faq/generate-kubeconfig" %}}).

### How to enable Hugepages

Moved to Cluster Configuration, [How to enable Hugepages]({{% ref "/docs/operations/configuration/hugepages" %}}).

### How to Rotate Certificate Authority

Moved to Cluster Maintenance, [How to Rotate Certificate Authority]({{% ref "/docs/operations/cluster/rotate-ca" %}}).

### How to cleanup etcd state

Moved to Troubleshooting: [How to clean up etcd state]({{% ref "/docs/operations/troubleshooting/etcd#how-to-clean-up-etcd-state" %}}).

## Bundles

### How to overwrite parameters for specific components

Moved to Cluster configuration, [Components reference]({{% ref "/docs/operations/configuration/components#overwriting-component-parameters" %}}).

### How to disable some components from bundle

Moved to Cluster configuration, [Components reference]({{% ref "/docs/operations/configuration/components#enabling-and-disabling-components" %}}).
