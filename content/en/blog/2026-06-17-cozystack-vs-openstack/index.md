---
title: "Cozystack vs OpenStack: An Honest Comparison for 2026"
slug: cozystack-vs-openstack
date: 2026-06-17
author: "Timur Tukaev"
description: "An honest, practical comparison of Cozystack and OpenStack across architecture, compute, networking, storage, managed services, operations, and multi-tenancy — and why a Kubernetes-native platform is a compelling OpenStack alternative for building a private cloud."
images:
  - "social-card.png"
article_types:
  - tech-article
topics:
  - platform
  - kubernetes
---

![Cozystack vs OpenStack — an honest comparison for 2026](social-card.png)

OpenStack has been the default answer to "how do we build a private cloud?" for over a decade — broad feature set, massive vendor ecosystem, first-mover gravity. But a growing number of teams are discovering that operating OpenStack is a full-time job in itself. Configuration drift across dozens of interacting services, painful upgrades that block entire sprints, and a hiring pool that shrinks as engineers gravitate toward Kubernetes-native tooling.

Cozystack takes a different approach. Instead of a purpose-built cloud control plane, it composes one from Kubernetes primitives: KubeVirt for VMs, Cilium and Kube-OVN for networking, LINSTOR/DRBD for storage, Flux for reconciliation. The result is a free, open-source PaaS — a CNCF Sandbox project — delivering VMs, managed Kubernetes clusters, VPCs, and managed services on bare metal, all through a single Kubernetes API. In other words, a Kubernetes-native alternative to OpenStack.

This article compares the two across seven dimensions to help you decide which fits your team and your workloads.

## Architecture

OpenStack is a collection of projects — Nova, Neutron, Cinder, Keystone, Glance, Heat, Horizon — each with its own release cadence, API schema, database, and message-queue consumers. A minimal production deployment involves at least five core services in HA mode with MariaDB/Galera, RabbitMQ, and agent fleets on every node. The upside is modularity: swap the ML2 driver in Neutron without touching Nova, run Cinder with dozens of backends. The downside is surface area — every service is another thing to monitor, upgrade, and debug at 3 AM, and cross-service failures are hard to trace.

Cozystack starts from a different premise: Kubernetes already provides scheduling, health checking, service discovery, RBAC, and a declarative API. Every component — KubeVirt, Kube-OVN, LINSTOR, Keycloak — runs as Kubernetes workloads managed by Flux HelmReleases. No separate message queue, no per-service database, no extra agent fleet. Anyone who understands Kubernetes can inspect, debug, and extend the platform. The trade-off: Cozystack is younger, has a smaller third-party ecosystem, and inherits its components' limitations.

## Compute

| Capability | OpenStack | Cozystack |
|---|---|---|
| Virtual machines | Nova + libvirt/KVM | KubeVirt + libvirt/KVM |
| Containers | Zun (rarely deployed) | Native Kubernetes pods |
| Managed Kubernetes | Magnum | Kamaji + Cluster API |
| GPU passthrough | Supported | Supported |
| Live migration | Supported | Supported |

Nova is battle-tested, handling thousands of VMs in production with deep hypervisor support — NUMA pinning, SR-IOV, the full libvirt matrix. KubeVirt, the compute engine behind Cozystack, runs VMs as Kubernetes pods with an inner libvirt domain. VMs and containers share the same scheduler, networking, and storage, so a team running legacy Windows alongside containerized microservices manages everything through one API. KubeVirt supports live migration, CPU/memory hotplug, and GPU passthrough (with the usual caveat — shared by Nova — that VMs holding passthrough devices cannot be live-migrated). It does not match every niche Nova feature (bare-metal provisioning via Ironic has no equivalent), but for most VM workloads the gap is negligible.

For managed Kubernetes the difference is sharper. Magnum provisions clusters on Nova VMs using Heat templates, but monitoring, upgrades, and etcd backup are largely your problem. Cozystack uses Kamaji with Cluster API to run tenant control planes as pods on the management cluster, eliminating dedicated control-plane VMs and enabling hundreds of lightweight clusters.

## Networking

Neutron is powerful but operationally complex. A typical deployment involves OVS or OVN agents on every compute node, L3 agents, DHCP agents, and metadata agents. Each has its own failure modes — L3-agent failover can strand floating IPs, DHCP restarts cause lease storms. Debugging means correlating logs across agents on multiple nodes.

Cozystack splits networking into two concerns. Cilium handles pod-to-pod traffic on the management network using eBPF, with native network policies and optional observability via Hubble. Kube-OVN handles tenant VPC networking using the same OVN/OVS data plane that powers many OpenStack clouds — but integrated directly with the Kubernetes API. VPCs, subnets, and routing rules are custom resources. Inspecting a tenant's network is `kubectl get vpc`, not sourcing an OpenRC file and navigating Neutron's abstraction layers.

| Capability | OpenStack Neutron | Cozystack |
|---|---|---|
| Data plane | OVS or OVN | Cilium (eBPF) + Kube-OVN (OVN) |
| VPC isolation | Neutron routers + security groups | Kube-OVN logical routers + switches |
| Load balancing | Octavia | Cilium L4 LB, Ingress controllers |
| Floating IPs | Native | Supported via Kube-OVN |
| Debugging interface | Neutron API + agent logs | kubectl + Grafana/VictoriaLogs (Hubble UI optional) |

## Storage

Cinder is a thick abstraction over dozens of backends — Ceph, NetApp, Pure Storage, Dell PowerStore. If your organization already owns a SAN, Cinder almost certainly has a driver for it. Snapshots, volume replication, and multi-attach are available depending on the backend.

Cozystack takes a zero-external-dependency approach. Block storage is LINSTOR with DRBD, synchronously replicating volumes across nodes at the kernel level. Object storage is SeaweedFS. There is no separate storage cluster or proprietary hardware to maintain. The trade-off is clear: fewer options, but nothing to buy, license, or manage outside the cluster. Teams with existing Ceph or NetApp investments benefit from Cinder's ecosystem. Teams starting from bare metal get replicated block storage from LINSTOR/DRBD with zero external dependencies.

## Managed Services

This is where the gap is widest. OpenStack offers Trove for database-as-a-service, but Trove supports a limited set of databases and has seen low adoption. Heat provides orchestration but is a template engine, not a managed-service platform.

Cozystack ships a full catalog out of the box: PostgreSQL, MariaDB, MongoDB, Redis, Kafka, RabbitMQ, NATS, ClickHouse, Qdrant, FoundationDB, OpenBao, and Harbor. Each service is a Helm chart managed by Flux with sensible defaults for replication, backup, and monitoring. Deploying a three-replica PostgreSQL cluster with automated backups is a single HelmRelease or a few dashboard clicks.

In OpenStack, the same outcome requires a separate ops team per data service or a third-party platform like Aiven. Cozystack bundles this into the platform — a significant advantage for teams offering self-service data infrastructure.

## Operations and Upgrades

OpenStack upgrades are widely considered the platform's most painful aspect. Each service has its own release cycle within the six-month cadence. Upgrading means database migrations per service, configuration updates, coordinated agent restarts, and API compatibility checks. Skip a release and the work doubles. Major upgrades routinely consume multi-day maintenance windows.

Cozystack uses Flux for continuous reconciliation. Each component is a HelmRelease. An upgrade is a version bump — Flux renders new manifests and applies rolling updates with health checks. Three parallel release branches ship weekly patches. Rollback is a version pin away. A bad chart can still break a component, but the blast radius is smaller — each component upgrades independently, and the feedback loop is minutes, not days.

## Multi-Tenancy

OpenStack provides multi-tenancy through Keystone projects and domains, with network isolation from Neutron security groups and quotas set per project. This model works but requires careful policy configuration to prevent privilege escalation.

Cozystack implements nested tenants as Kubernetes namespaces with layered RBAC. Each tenant gets its own VPC with L2/L3 isolation via Kube-OVN, resource quotas via Kubernetes ResourceQuota, and a dedicated monitoring stack. Tenants can create sub-tenants, naturally modeling organizational hierarchies. Per-tenant monitoring ensures developers in Tenant A see only their own metrics and logs.

| Capability | OpenStack | Cozystack |
|---|---|---|
| Tenant model | Keystone projects/domains | Nested Kubernetes namespaces |
| Network isolation | Neutron tenant networks | Kube-OVN VPCs per tenant |
| Resource quotas | Nova/Cinder/Neutron quotas | ResourceQuota per tenant |
| Per-tenant monitoring | Manual setup | Built-in per-tenant stack |
| Sub-tenants | Hierarchical projects (limited) | Native nested tenants |

## When to Choose OpenStack

OpenStack remains right if your organization has a mature ops team that already handles upgrades and cross-service troubleshooting — the switching cost may not be justified. If you depend on a specific Cinder backend with no Kubernetes CSI equivalent, OpenStack gives you the driver ecosystem. If you need bare-metal provisioning at scale via Ironic, OpenStack has a mature solution. And if compliance mandates OpenStack-specific certifications already audited, re-certifying is a real cost.

## When to Choose Cozystack

Cozystack is the stronger choice if you are building a new cloud from bare metal and want to minimize operational complexity. If your team thinks in Kubernetes terms, Cozystack will feel native. If you need managed services without a separate DBaaS platform, they ship out of the box. If you want managed Kubernetes without dedicated control-plane VMs, Kamaji plus Cluster API is more efficient than Magnum. And if your upgrade strategy is "weekly without a maintenance window," Flux-based reconciliation is built for that.

## Further Reading

- [Cozystack documentation](https://cozystack.io/docs/) — installation, architecture, and service catalog
- [OpenStack documentation](https://docs.openstack.org/) — project guides for each service
- [KubeVirt user guide](https://kubevirt.io/user-guide/) — VM lifecycle on Kubernetes
- [Kube-OVN documentation](https://kubeovn.github.io/docs/) — VPC and network policy configuration
- [LINSTOR user guide](https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/) — storage replication internals
- [Kamaji project](https://kamaji.clastix.io/) — hosted Kubernetes control planes

## Community and Resources

Cozystack development happens in the open on [GitHub](https://github.com/cozystack/cozystack), with an active community on Telegram and Slack and regular public roadmap meetings. OpenStack has one of the largest open-source communities in infrastructure, governed by the OpenInfra Foundation, with biannual summits and commercial support from Canonical, Red Hat, and Mirantis.

Both projects are genuinely open source. Your choice should be driven by your operational model, your team's skills, and your workloads. Deploy a proof of concept on hardware that resembles production and let the results speak.

## Join the community

* GitHub: [cozystack/cozystack](https://github.com/cozystack/cozystack)
* Telegram: [@cozystack](https://t.me/cozystack)
* Slack: [#cozystack](https://kubernetes.slack.com/archives/C06L3CPRVN1) on the Kubernetes workspace ([invite](https://slack.kubernetes.io))
* [Subscribe to our community meetings calendar](https://zoom-lfx.platform.linuxfoundation.org/meetings/cozystack)
* [Add meetings to your calendar](https://webcal.prod.itx.linuxfoundation.org/lfx/lfsixxnFWxbvsyEuC2)
