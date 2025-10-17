---
title: "Updates to the Open-Source Platform Cozystack 0.24–0.29:"
slug: updates-to-the-open-source-platform-cozystack-0-24-0-29-
date: 2025-04-10
author: "Timur Tukaev"
description: "We haven’t shared much about Cozystack’s new features lately, even though we’ve released six new versions over the past month and a half…"
---

### Updates to the Open-Source Platform Cozystack 0.24–0.29: PXE Machine Provisioning, Inter-Datacenter RTT Monitoring, and Dedicated IP Addresses for VMs

We haven’t shared much about Cozystack’s new features lately, even though we’ve released six new versions over the past month and a half: 0.24, 0.25, 0.26, 0.27, 0.28, and 0.29. Let’s take a closer look at the changes, starting from the latest release and going back to version 0.24.

> What is Cozystack?

> Cozystack is an open-source platform that enables building a bare-metal cloud for rapid deployment of managed Kubernetes, Database as a Service, Applications as a Service, and KubeVirt-based virtual machines. With just a click, users can deploy services like Kafka, FerretDB, PostgreSQL, Cilium, Grafana, VictoriaMetrics, and more.

### Key Changes

- Platform Stabilization for Multi-Datacenter Configurations: Significant improvements were made to etcd, Cilium, Kube-OVN, Linstor, and other components.
- Enhanced Observability Stack: New dashboards were added for several components, and Grafana settings were optimized for better performance.
- Release of the cozy-proxy Utility: This tool allows assigning dedicated IP addresses to VMs in Kubernetes (instead of just exposing individual ports).
- Introduction of Vertical Pod Autoscaler (VPA): VPA automatically sets resource limits for applications based on historical metrics.
- Documentation Refactoring and Expansion: New sections were added to improve clarity and usability.
- Repository Migration: The platform and its utilities were moved from the [aenix-io](https://github.com/aenix-io) organization to [cozystack](https://github.com/cozystack) after the project was accepted into the CNCF Sandbox.

### Cozystack v0.29

In v0.29.0, the development team focused on improving platform stability and reliability, including patching [CVE-2025–1974](https://github.com/advisories/GHSA-mgvx-rpfc-9mpv) in ingress-nginx. New features include:

- A set of presets to limit resource consumption for applications.
- Automated certificate renewal.
- Expanded VPA integration with additional platform components.

Other Changes:

- Added Cilium host firewall for improved out-of-the-box cluster security.
- Implemented a process for running e2e tests in GitHub CI.
- Published the [first version](https://github.com/cozystack/cozystack/blob/main/GOVERNANCE.md) of the project governance structure as part of the CNCF Sandbox transition.
- Updated Flux Operator to v0.18.0 and Talos Linux to v1.9.5.

Details: [v0.29.0](https://github.com/cozystack/cozystack/releases/tag/v0.29.0), [v0.29.1](https://github.com/cozystack/cozystack/releases/tag/v0.29.1).

### Cozystack v0.28

The highlight of this release was the introduction of Vertical Pod Autoscaler (VPA) to automatically set resource limits for applications. The repository was also moved from aenix-io to the cozystack GitHub organization.

**Other Changes:**

- Tenant isolation is now enabled by default.
- Source-IP validation responsibility shifted from Cilium to Kube-OVN.
- Minor bug fixes in LINSTOR, Kube-OVN, and KubeVirt.
- Updated Cilium to v1.17.1 and Kube-OVN to v1.13.3.

Details: [v0.28.0](https://github.com/cozystack/cozystack/releases/tag/v0.28.0), [v0.28.2](https://github.com/cozystack/cozystack/releases/tag/v0.28.2).

### Cozystack v0.27

This release focused on platform stabilization and introduced linstor-plunger scripts to automatically fix issues in LINSTOR (e.g., DRBD lost connection, stuck loop devices). It also added support for distributing PostgreSQL replicas across different nodes.

![](https://cdn-images-1.medium.com/max/800/0*XPWNsEtGmcIiY6zs)

**Other Changes:**

- Added [convenient dashboards](https://github.com/cozystack/cozystack/pull/661) for ClickHouse and Piraeus monitoring.
- Updated etcd-operator to v0.4.1.
- Increased maxLabelsTimeseries from 30 to 60.
- Fixed the Goldfinger dashboard for tracking network latency in multi-datacenter clusters.

**Details:** [v0.27.0](https://github.com/cozystack/cozystack/releases/tag/v0.27.0).

### Cozystack v0.26

This release improved stability for multi-datacenter configurations and added network connectivity monitoring. These metrics help fine-tune platform components.

**Other Changes:**

- Added resource limits for individual tenants within a cluster.
- Integrated Goldpinger to monitor latency between datacenters, with data displayed in Grafana.
- Live VM migration is now enabled by default.
- Introduced LINSTOR volume snapshots (a step toward a full backup system).
- Fixed TLS handling in etcd helm chart to prevent issues with expired root certificates (previously valid for 90 days).

**Details:** [v0.26.0](https://github.com/cozystack/cozystack/releases/tag/v0.26.0), [v0.26.1](https://github.com/cozystack/cozystack/releases/tag/v0.26.1).

### Cozystack v0.25

This release introduced cozy-proxy, a standalone tool for assigning dedicated IP addresses to VMs (instead of just ports). This is crucial for service providers running VM-based applications requiring unique IPs.

**Other Changes:**

- Enhanced monitoring for etcd, Flux, and Kafka with new dashboards.
- Updated Talos Linux to v1.9.3.
- Tenant-specific users can now download kubeconfig.

**Details:** [v0.25.0](https://github.com/cozystack/cozystack/releases/tag/v0.25.0), [v0.25.1](https://github.com/cozystack/cozystack/releases/tag/v0.25.1), [v0.25.2](https://github.com/cozystack/cozystack/releases/tag/v0.25.2), [v0.25.3](https://github.com/cozystack/cozystack/releases/tag/v0.25.3).

![](https://cdn-images-1.medium.com/max/800/0*CIY_xKXLnyUjRk4U)

### Cozystack v0.24

This release added PXE provisioning for nodes to automatically deploy Talos Linux. The [smee](https://github.com/tinkerbell/smee) (DHCP/PXE server) from [Tinkerbell](https://tinkerbell.org/) was integrated for this purpose.

**Other Changes:**

- Updated cert-manager to v16.
- Replaced darkhttp with the custom cozystack-assets-server.
- Pre-installed Grafana plugins for faster startup.

**Details:** [v0.24.0](https://github.com/cozystack/cozystack/releases/tag/v0.24.0), [v0.24.1](https://github.com/cozystack/cozystack/releases/tag/v0.24.1).

![](https://cdn-images-1.medium.com/max/800/0*PNjPPNo9algUKb7J)

### What’s Next

We’re finalizing GPU support for VMs to enable AI/ML workloads on the platform.

### Join Our Community

- [Telegram](https://t.me/cozystack)
- [Slack](https://kubernetes.slack.com/archives/C06L3CPRVN1) (in [Kubernetes Slack workspace](https://communityinviter.com/apps/kubernetes/community))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)