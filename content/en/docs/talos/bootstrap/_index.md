---
title: "Configuring Kubernetes Cluster on Talos Linux"
linkTitle: "2. Configuring Kubernetes"
description: "Configuring Kubernetes Cluster on Talos Linux"
weight: 20
aliases:
  - /docs/talos/configuration
  - /docs/operations/talos/configuration
---


**The second step** in deploying a Cozystack cluster is to install and configure a Kubernetes cluster on Talos Linux nodes.
A prerequisite to this step is having [installed Talos Linux]({{% ref "/docs/talos/install" %}}).
The result is a Kubernetes cluster installed, configured, and ready to install Cozystack.

If this is your first time installing Cozystack, [start with the Cozystack tutorial]({{% ref "/docs/getting-started" %}}).

The recommended option is to [use Talm]({{% ref "./talm" %}}), a declarative CLI tool, which has ready presets for Cozystack and uses the power of Talos API under the hood.