---
title: "Cozystack Deployment Guide: from Infrastructure to a Ready Cluster"
linkTitle: "Deploying Cozystack"
description: "Learn how to deploy a Cozystack cluster using Talos Linux and Kubernetes. This guide covers installation, configuration, and best practices for a reliable and secure Cozystack deployment."
weight: 30
aliases:
  - /docs/talos
  - /docs/operations/talos
---

## Cozystack Tutorial

If this is your first time installing Cozystack, consider [going through the Cozystack tutorial]({{% ref "/docs/getting-started" %}}).
It shows the shortest way to getting a proof-of-concept Cozystack cluster.

## Generic Installation Path

Installing Cozystack on bare-metal servers or VMs involves three consecutive steps.
Each of them has a variety of options, and while there is a recommended option, we provide alternatives to make the installation process flexible:

1.  [Install Talos Linux]({{% ref "./talos" %}}) on bare metal or VMs running Linux or having no OS at all.
1.  [Install and bootstrap a Kubernetes cluster]({{% ref "./kubernetes" %}}) on top of Talos Linux.
1.  [Install and configure Cozystack]({{% ref "./cozystack" %}}) on the Kubernetes cluster.

## Air-gapped Environment

Cozystack can be installed in an isolated environment without direct Internet access.
The key difference of such installation is in using proxy registries for images:

1.  [Install Talos Linux]({{% ref "./talos" %}}) on bare metal or VMs running Linux or having no OS at all.
1.  [Configure Talos nodes for air-gap and bootstrap a Kubernetes cluster]({{% ref "./kubernetes/air-gapped" %}}).
1.  [Install and configure Cozystack]({{% ref "./cozystack" %}}) on the Kubernetes cluster.

## Provider-specific Installation

There are specific guides for cloud providers, covering all the steps from preparing infrastructure to installing and configuring Cozystack.
If that's your case, we recommend using the guides below:

- [Hetzner]({{% ref "/docs/install/providers/hetzner" %}})
- [Oracle Cloud Infrastructure (OCI)]({{% ref "/docs/install/providers/oracle-cloud" %}})
- [Servers.com]({{% ref "/docs/install/providers/servers-com" %}})


## Upgrading and Post-deployment Configuration

After you've deployed a cluster, proceed to the [Cluster Administration]({{% ref "/docs/operations" %}}) section for
the next actions:

- [Configure OIDC]({{% ref "/docs/operations/oidc" %}})
- [Deploy Cozystack in a Multi-Datacenter Setup]({{% ref "/docs/operations/stretched" %}})
- [Upgrading Cozystack]({{% ref "/docs/operations/cluster/upgrade" %}})
