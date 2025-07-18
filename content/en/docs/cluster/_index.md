---
title: "Bootstrapping a Cozystack Cluster on Talos Linux Nodes"
linkTitle: "Cluster Bootstrap"
description: "Configuring Talos Linux for Cozystack"
weight: 40
aliases:
  - /docs/talos/configuration
  - /docs/operations/talos/configuration
---

If this is your first time installing Cozystack, [start with the Cozystack tutorial]({{% ref "/docs/getting-started" %}}).

The second step in deploying a Cozystack cluster after [installing Talos Linux]({{% ref "/docs/talos" %}}) is to bootstrap Talos Linux nodes by applying configuration,
which results in a Kubernetes cluster with Cozystack installed and ready to work.

The recommended option is to [use Talm]({{% ref "./talm" %}}), a declarative CLI tool, which has ready presets for Cozystack and uses the power of Talos API under the hood.