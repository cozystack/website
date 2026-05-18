---
title: "Cozystack 1.2: OpenSearch, VPC Peering, and Smarter Tenant Scheduling"
slug: cozystack-1-2-opensearch-vpc-peering-and-smarter-tenant-scheduling
date: 2026-03-31
author: "Timur Tukaev"
description: "Cozystack 1.2 brings managed OpenSearch, VPC peering, SchedulingClass, and a stabilization follow-up in v1.2.1."
article_types:
  - release
topics:
  - platform
  - opensearch
  - networking

---

### Cozystack 1.2: OpenSearch, VPC Peering, and Smarter Tenant Scheduling

The Cozystack 1.2 release line is now available. [v1.2.0](https://github.com/cozystack/cozystack/releases/tag/v1.2.0) was published on March 27, 2026, and [v1.2.1](https://github.com/cozystack/cozystack/releases/tag/v1.2.1) followed on March 31, 2026.

This cycle expands the platform in three important directions: managed search and analytics, secure networking between tenant environments, and better control over where tenant workloads run. The follow-up `v1.2.1` release focuses on safety and operational stability.

### Main highlights

#### Managed OpenSearch in the application catalog

Cozystack 1.2 adds **OpenSearch** as a fully managed service. It supports OpenSearch v1, v2, and v3, can run in a multi-role topology, enables TLS by default, ships with built-in HTTP Basic authentication, and can optionally deploy OpenSearch Dashboards alongside the engine.

This makes OpenSearch a first-class PaaS component inside Cozystack, rather than something operators need to integrate manually.

#### VPC peering for tenant-to-tenant connectivity

The `vpc` application now supports **VPC peering**, allowing tenants to connect private networks directly without sending traffic through public endpoints. For multi-tenant environments, this is a substantial step forward: operators can build cleaner internal topologies and expose only the traffic that actually needs to leave the platform.

The release also adds deterministic peering IP allocation and support for static routes, which makes the feature much more usable in real production layouts.

#### SchedulingClass for workload placement

The new **SchedulingClass** system gives operators cluster-wide control over where tenant workloads land. In practice, this means workloads can be pinned to particular data centers, hardware classes, or node groups without forcing tenants to manage scheduler details themselves.

For operators running multiple sites or mixed hardware pools, this is one of the most important platform additions in 1.2. It also becomes self-service through the Cozystack dashboard.

### Also in Cozystack v1.2.0

Beyond the headline features, `v1.2.0` also includes several substantial platform improvements:

- **VictoriaLogs moves to clustered mode** with `VLCluster`, bringing higher availability and better scalability for the logging stack.
- **LINSTOR volume relocation after clone and restore** improves storage placement for snapshot restore and PVC clone workflows.
- **cozystack-scheduler is enabled by default**, making SchedulingClass part of the default platform behavior.
- **external-dns is now available as a standalone extra package**.

### Cozystack v1.2.1: stabilization update

While `v1.2.0` introduced the major new capabilities, `v1.2.1` is the release that hardens them for production use.

The most important fixes in `v1.2.1` are:

- **Preventing accidental deletion of installed packages** when packages are moved between `enabledPackages` and `disabledPackages`.
- **Restoring propagation of CPU, memory, and ephemeral storage allocation ratios** to managed packages.
- **Fixing critical LINSTOR and DRBD behavior**, including TCP port preservation and a safer `verify-alg` setting for newer kernels.
- **Fixing Multus/CNI failure modes** that could otherwise leave nodes unable to create new pods after failed CNI setup or boot-time CNI race conditions.
- **Pinning monitoring databases to PostgreSQL 17**, avoiding breakage in Grafana and Alerta monitoring queries.

Taken together, these changes make `v1.2.1` much more than a routine patch release.

### Release links

- [Cozystack v1.2.0 on GitHub](https://github.com/cozystack/cozystack/releases/tag/v1.2.0)
- [Cozystack v1.2.1 on GitHub](https://github.com/cozystack/cozystack/releases/tag/v1.2.1)
- [Full changelog for v1.2.0](https://github.com/cozystack/cozystack/compare/v1.1.0...v1.2.0)
- [Full changelog for v1.2.1](https://github.com/cozystack/cozystack/compare/v1.2.0...v1.2.1)

### Join the community

- Telegram [group](https://t.me/cozystack)
- Slack [group](https://kubernetes.slack.com/archives/C06L3CPRVN1) (Get invite at [https://slack.kubernetes.io](https://slack.kubernetes.io))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
- [Cozysummit Virtual 2026](https://community.cncf.io/events/details/cncf-virtual-project-events-hosted-by-cncf-presents-cozysummit-virtual-2026/)
