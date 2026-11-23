---
title: "Multi-Location Clusters"
linkTitle: "Multi-Location"
description: "Extend Cozystack management clusters across multiple locations using Kilo WireGuard mesh, cloud autoscaling, and local cloud controller manager."
weight: 40
---

This section covers extending a Cozystack management cluster across multiple physical locations
(on-premises + cloud, multi-cloud, etc.) using WireGuard mesh networking.

The setup consists of three components:

- [Networking Mesh]({{% ref "networking-mesh" %}}) -- Kilo WireGuard mesh with Cilium IPIP encapsulation
- [Local CCM]({{% ref "local-ccm" %}}) -- cloud controller manager for node IP detection and lifecycle
- [Cluster Autoscaling]({{% ref "autoscaling" %}}) -- automatic node provisioning in cloud providers
