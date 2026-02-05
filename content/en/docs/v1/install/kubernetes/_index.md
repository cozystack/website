---
title: "Installing and Configuring Kubernetes Cluster on Talos Linux"
linkTitle: "2. Install Kubernetes"
description: "Step 2: Installing and configuring a Kubernetes cluster on Talos Linux nodes, ready for Cozystack installation."
weight: 20
aliases:
  - /docs/operations/talos/configuration
  - /docs/talos/bootstrap
  - /docs/talos/configuration
---


**The second step** in deploying a Cozystack cluster is to install and configure a Kubernetes cluster on Talos Linux nodes.
A prerequisite to this step is having [installed Talos Linux]({{% ref "/docs/install/talos" %}}).
The result is a Kubernetes cluster installed, configured, and ready to install Cozystack.

If this is your first time installing Cozystack, [start with the Cozystack tutorial]({{% ref "/docs/getting-started" %}}).

## Installation Options

There are several methods to configure Talos nodes and bootstrap a Kubernetes cluster:

-   **Recommended**: [using Talm]({{% ref "./talm" %}}), a declarative CLI tool, which has ready presets for Cozystack and uses the power of Talos API under the hood.
-   [Using `talos-bootstrap`]({{% ref "./talos-bootstrap" %}}), an interactive script for bootstrapping Kubernetes clusters on Talos OS.
-   [Using talosctl]({{% ref "./talosctl" %}}), a specialized command line tool for managing Talos.
-   [Air-gapped installation]({{% ref "./air-gapped" %}}) is possible with Talm or talosctl.

If you encounter problems with installation, refer to the [Troubleshooting section]({{% ref "./troubleshooting" %}}).

## Further Steps

-   After installing and configuring Kubernetes on top of Talos Linux nodes, you will have a Kubernetes cluster ready to
    [install and configure Cozystack]({{% ref "/docs/install/cozystack" %}}).
