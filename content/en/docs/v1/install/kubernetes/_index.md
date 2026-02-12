---
title: "Installing and Configuring Kubernetes Cluster"
linkTitle: "2. Install Kubernetes"
description: "Step 2: Installing and configuring a Kubernetes cluster ready for Cozystack installation."
weight: 20
aliases:
  - /docs/v1/operations/talos/configuration
  - /docs/v1/talos/bootstrap
  - /docs/v1/talos/configuration
---


**The second step** in deploying a Cozystack cluster is to install and configure a Kubernetes cluster.
The result is a Kubernetes cluster installed, configured, and ready to install Cozystack.

If this is your first time installing Cozystack, [start with the Cozystack tutorial]({{% ref "/docs/v1/getting-started" %}}).

## Installation Options

### Talos Linux (Recommended)

For production deployments, Cozystack recommends [Talos Linux]({{% ref "/docs/v1/guides/talos" %}}) as the underlying operating system.
A prerequisite to using these methods is having [installed Talos Linux]({{% ref "/docs/v1/install/talos" %}}).

There are several methods to configure Talos nodes and bootstrap a Kubernetes cluster:

-   **Recommended**: [using Talm]({{% ref "./talm" %}}), a declarative CLI tool, which has ready presets for Cozystack and uses the power of Talos API under the hood.
-   [Using `talos-bootstrap`]({{% ref "./talos-bootstrap" %}}), an interactive script for bootstrapping Kubernetes clusters on Talos OS.
-   [Using talosctl]({{% ref "./talosctl" %}}), a specialized command-line tool for managing Talos.
-   [Air-gapped installation]({{% ref "./air-gapped" %}}) is possible with Talm or talosctl.

### Generic Kubernetes

Cozystack can also be deployed on other Kubernetes distributions:

-   [Generic Kubernetes]({{% ref "./generic" %}}) — deploy Cozystack on k3s, kubeadm, RKE2, or other distributions.

If you encounter problems with installation, refer to the [Troubleshooting section]({{% ref "./troubleshooting" %}}).

## Further Steps

-   After installing and configuring a Kubernetes cluster, you will have it ready to
    [install and configure Cozystack]({{% ref "/docs/v1/install/cozystack" %}}).
