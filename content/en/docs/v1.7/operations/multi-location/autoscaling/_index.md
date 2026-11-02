---
title: "Cluster Autoscaling"
linkTitle: "Autoscaling"
description: "Automatic node scaling for Cozystack management clusters using Kubernetes Cluster Autoscaler."
weight: 20
---

The `cluster-autoscaler` system package enables automatic node scaling for Cozystack management clusters.
It monitors pending pods and automatically provisions or removes cloud nodes based on demand.

Before configuring autoscaling, complete the [Networking Mesh]({{% ref "../networking-mesh" %}})
and [Local CCM]({{% ref "../local-ccm" %}}) setup.

Cozystack provides pre-configured variants for different cloud providers:

- [Hetzner Cloud]({{% ref "hetzner" %}}) -- scale using Hetzner Cloud servers
- [Azure]({{% ref "azure" %}}) -- scale using Azure Virtual Machine Scale Sets

Each variant is deployed as a separate Cozystack Package with provider-specific configuration.
