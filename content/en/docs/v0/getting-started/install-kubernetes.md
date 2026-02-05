---
title: "2. Install and Bootstrap a Kubernetes cluster"
linkTitle: "2. Install Kubernetes"
description: "Use Talm CLI to bootstrap a Kubernetes cluster, ready for Cozystack."
weight: 15
---

## Objectives

We start this step of the tutorial, having [three nodes with Talos Linux installed on them]({{% ref "/docs/getting-started/install-talos" %}}).

As a result of this step, we will have a Kubernetes cluster installed, configured, and ready to install Cozystack.
We will also have a `kubeconfgig` for this cluster, and will have performed basic checks on the cluster.

## Installing Kubernetes

Install and bootstrap a Kubernetes cluster using [Talm]({{% ref "/docs/install/kubernetes/talm" %}}), a declarative CLI configuration tool with ready configuration presets for Cozystack.

{{% alert color="info" %}}
This part of the tutorial is being reworked.
It will include simplified instructions for Talm installation, without all the extra options and corner cases, included in the main Talm guide.
{{% /alert %}}


## Next Step

Continue the Cozystack tutorial by [installing and configuring Cozystack]({{% ref "/docs/getting-started/install-cozystack" %}}).

Extra tasks:

-   Check out [github.com/cozystack/talm](https://github.com/cozystack/talm) and give it a star!
