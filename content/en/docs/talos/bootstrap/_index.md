---
title: "Bootstrapping a Kubernetes Cluster on Talos Linux Nodes"
linkTitle: "Cluster Bootstrap"
description: "Configuring Talos Linux for Cozystack"
weight: 20
aliases:
  - /docs/talos/configuration
  - /docs/operations/talos/configuration
---

If this is your first time installing Cozystack, [start with the Cozystack tutorial]({{% ref "/docs/getting-started" %}}).

Bootstrapping a Kubernetes cluster on Talos linux nodes is the second step in deploying a Cozystack cluster
after [installing Talos Linux]({{% ref "/docs/talos/install" %}}).
It results in a Kubernetes cluster installed, configured, and ready to install Cozystack.

The recommended option is to [use Talm]({{% ref "./talm" %}}), a declarative CLI tool, which has ready presets for Cozystack and uses the power of Talos API under the hood.