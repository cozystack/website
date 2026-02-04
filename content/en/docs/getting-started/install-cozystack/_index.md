---
title: "3. Install and Configure Cozystack"
linkTitle: "3. Install Cozystack"
description: "Install Cozystack, configure storage and networking, and access the dashboard."
weight: 20
---

This guide walks you through installing Cozystack on top of a Kubernetes cluster.

## Choose Your Version

Cozystack has two major versions with different configuration approaches:

### [Cozystack v1.x (Recommended)]({{% ref "./v1" %}})

The latest version using **Package-based configuration**.

- Unified configuration through a single Package resource
- New bundle variants: `isp-full`, `isp-hosted`, `distro-full`
- Managed by `cozystack-operator`
- Recommended for new installations

[→ Install Cozystack v1.x]({{% ref "./v1" %}})

### [Cozystack v0.x (Legacy)]({{% ref "./v0" %}})

Previous version using **ConfigMap-based configuration**.

- Configuration through ConfigMap in `cozy-system`
- Bundle names: `paas-full`, `paas-hosted`
- For existing v0.x installations

[→ Install Cozystack v0.x]({{% ref "./v0" %}})

---

## What You'll Learn

Both installation guides cover:

1. Preparing configuration (Package for v1.x or ConfigMap for v0.x)
2. Installing Cozystack
3. Configuring storage with LINSTOR
4. Setting up networking (MetalLB or public IPs)
5. Deploying etcd, ingress, and monitoring
6. Accessing the Cozystack dashboard

## Prerequisites

Before starting, ensure you have completed:

- [Requirements: infrastructure and tools]({{% ref "../requirements" %}})
- [1. Install Talos Linux]({{% ref "../install-talos" %}})
- [2. Install Kubernetes]({{% ref "../install-kubernetes" %}})

Choose the version that matches your needs and proceed with the appropriate installation guide.
