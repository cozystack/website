---
title: "Cozystack 1.6: Talos Workers, Tenant SSO, Security Groups, Hierarchical Quotas, and Safer etcd Upgrades"
slug: "cozystack-1-6-talos-workers-tenant-sso-security-groups-hierarchical-quotas"
date: 2026-08-04
author: "Cozystack Team"
description: "Cozystack v1.6.0 moves tenant Kubernetes workers to Talos Linux, adds tenant-controlled OIDC, a SecurityGroup firewall API, hierarchical quotas, and in-place etcd-operator adoption."
images:
  - "cozystack-1-6-banner.png"
article_types:
  - "release"
topics:
  - "platform"
  - "kubernetes"
  - "talos"
  - "security"
  - "storage"
---

{{< figure src="cozystack-1-6-banner.png" alt="Cozystack v1.6.0 release banner — Talos workers, tenant SSO, security groups, hierarchical quotas" width="720" >}}

Cozystack v1.6.0 is now available. The release was published on July 22, 2026, and includes all fixes previously shipped in the v1.5.1, v1.5.2, and v1.5.3 patch releases.

This release changes several important parts of the platform. Tenant Kubernetes workers now run Talos Linux instead of Ubuntu, tenants can enable OIDC authentication for Kubernetes and Grafana, and a new SecurityGroup API provides a safer interface for managing application network policies.

Cozystack 1.6 also introduces hierarchical resource quotas, completes the etcd-operator v1alpha2 migration, expands Keycloak security and backup options, and makes application deletion consistently reclaim its storage.

The upgrade surface is larger than usual. Operators should review the upgrade section before applying the release.

## Talos Linux for tenant Kubernetes workers

Tenant Kubernetes worker nodes no longer use Ubuntu and kubeadm. Cozystack now provisions them with Talos Linux through Cluster API Bootstrap Provider Talos. Workers boot from a Talos image delivered through CDI and use a single system disk managed by Talos instead of separate system and kubelet disks.

Existing tenant clusters are migrated automatically. On the first reconciliation after the platform upgrade, the old worker machines are gradually replaced with Talos-based workers.

This does not require tenants to recreate their clusters, but operators should expect a complete worker-pool rollout. Worker disks are reprovisioned, and container images must be downloaded again.

MachineHealthCheck remediation is also enabled by default. Cluster API can now replace unhealthy workers automatically, with `maxUnhealthy` set to 50%. Operators who prefer the previous behaviour can temporarily set it to 0% while their fleets move to Talos.

## OIDC single sign-on for tenant Kubernetes and Grafana

Cozystack 1.6 introduces tenant-controlled OIDC authentication for managed Kubernetes clusters and individual Grafana instances.

Each Kubernetes resource now supports three authentication modes:

- `System` uses the platform Keycloak instance.
- `CustomConfig` accepts a tenant-provided Kubernetes authentication configuration.
- `None` keeps OIDC disabled.

In `System` mode, tenants can assign admin or view access to individual users. Cozystack creates the required role bindings and exposes a ready-to-use kubeconfig containing the `kubectl oidc-login` configuration through the dashboard.

Grafana uses the same model. Tenants can connect an instance to the platform Keycloak realm and assign Admin, Editor, or Viewer roles to users without requiring platform-level configuration. The local Grafana administrator credentials remain available as a break-glass access method.

## SecurityGroup: a tenant-facing firewall API

Cozystack now includes the namespace-scoped SecurityGroup resource under the `sdn.cozystack.io/v1alpha1` API. It lets tenants manage network access between their applications without direct access to Cilium resources.

A SecurityGroup can include several managed applications. Cozystack labels their pods and generates the corresponding CiliumNetworkPolicy. Rules can reference other SecurityGroups, making it possible to describe access at the application-group level instead of working with individual pod selectors.

For example, a tenant can allow a frontend group to connect to an API group while allowing only the API group to reach the database group.

In v1.6, SecurityGroup rules add permitted traffic. An empty rule list does not create a default-deny policy, because connectivity is still calculated from all policies selecting the pods. Default-deny behaviour is planned separately.

## Hierarchical resource quotas

Resource quotas now follow the tenant hierarchy.

Previously, every tenant quota was enforced only inside its own namespace. A tenant administrator could create a sub-tenant with a larger quota, or with no quota, and consume more resources than the parent tenant had been allocated.

In Cozystack 1.6, a tenant quota represents the budget of the entire subtree below that tenant. A child tenant with its own quota reserves part of the parent's remaining budget. A child without a separate quota shares the parent's resource pool. A quota that exceeds the parent's available budget is rejected during admission.

The controller also tracks aggregate usage across the subtree and maintains additional ResourceQuota objects to enforce the shared limit at runtime.

Existing multi-level tenant structures should be reviewed before upgrading. Overcommitted tenant trees generate a `QuotaOvercommitted` event, and operators can configure a temporary rollout buffer for workloads already above the newly enforced limit.

## etcd-operator v1alpha2 with in-place adoption

Cozystack completes its migration to the new `etcd-operator.cozystack.io/v1alpha2` API.

The new operator uses a membership-based lifecycle instead of managing etcd as a conventional StatefulSet. Its CRDs are now delivered through a separate `etcd-operator-crds` package so they can be installed before the controller.

Existing etcd clusters are adopted in place. The migration rewrites the required ownership information and resources before the new operator starts managing the cluster. No etcd data move or pod restart is required.

Before adoption, Cozystack takes a mandatory snapshot of every legacy cluster using the platform-managed backup infrastructure. The upgrade stops if the snapshot destination cannot be reached. This protects both standalone tenant etcd instances and the etcd clusters backing tenant Kubernetes control planes.

The old per-application `backup.*` settings have been removed from the etcd module. Backups should now be configured through a BackupClass and the platform Etcd backup strategy.

## More secure and manageable Keycloak deployments

Keycloak receives several independent, opt-in improvements.

An optional database proxy can encrypt selected database fields at the application level. Encryption keys can be provided directly or managed through Vault Transit, with Kubernetes and AppRole authentication supported for Vault connections.

Operators can also expose the Keycloak administration console and Administration REST API through a separate hostname. This makes it possible to keep the public authentication endpoint accessible while placing administrative access behind a private ingress class or Gateway.

The Keycloak PostgreSQL database can now be backed up to S3 through Barman. The platform login theme is also configurable through branding values, including a custom theme image.

## Wildcard certificates across the tenant tree

Cozystack 1.5 allowed operators to provide an existing wildcard certificate for platform services and the root tenant. Version 1.6 extends this model to child tenants.

The platform controller replicates the certificate into every tenant namespace where TLS terminates. Tenant ingress controllers and Gateways can then use it automatically without cross-namespace Secret access or additional operator configuration.

Operators can also let Cozystack request and manage a wildcard certificate through DNS-01. Using one wildcard certificate instead of issuing a separate certificate for every hostname helps avoid ACME rate limits on larger installations.

## Stable releases now contain the exact tested artifacts

The release pipeline has been redesigned around immutable image tags and explicit release-candidate promotion.

A stable release is no longer rebuilt independently. The images tested as `vX.Y.Z-rc.N` are promoted by digest to `vX.Y.Z`, making the stable release byte-identical to the release candidate that passed end-to-end testing.

Release tags are no longer force-moved, and the scheduled workflow that automatically created patch releases has been removed. Stable versions are now created only through an explicit RC-to-stable promotion process.

## Application deletion now reclaims storage

Deleting a managed application previously left some PVCs and generated Secrets behind.

Cozystack 1.6 adds cleanup handling across the application catalog. Storage used by ClickHouse, Qdrant, OpenBao, monitoring, SeaweedFS, etcd, Harbor, and several other managed services is now reclaimed when the application is deleted.

This fixes resource leaks, but it also changes deletion semantics. Deleting an application is now destructive. Operators and tenants should create backups or snapshots before removing workloads whose data may still be needed.

## Also in v1.6.0

The dashboard now displays the external IP assigned to LoadBalancer services directly on the application Services tab.

Kamaji now runs two controller replicas with soft anti-affinity. The release also removes its telemetry admission webhook, reducing admission latency for TenantControlPlane resources on multi-tenant installations.

Velero moves to version 1.18.1. Multiple backups can now be processed concurrently, and restore data movers can use cache volumes instead of relying entirely on node ephemeral storage.

The release also includes fixes for SeaweedFS upgrade naming, KubeVirt memory and connection leaks, Cilium networking and Gateway API behaviour, LINSTOR scheduler admission, and COSI BucketClaim reconciliation.

## Platform components

Several core components are updated in this release.

Talos Linux moves from v1.13.0 to v1.13.6, including kernel updates that address the CVE-2026-53359 and CVE-2026-46113 KVM guest-to-host escape vulnerabilities.

Other major updates include:

- etcd-operator v0.5.2 with the new v1alpha2 API
- Cilium 1.19.5
- KubeVirt 1.8.4
- Velero 1.18.1
- Vertical Pod Autoscaler 1.5.0
- Harbor 2.15.1
- Keycloak 26.6.3
- LINSTOR 1.33.3 and linstor-csi v1.11.2
- FoundationDB operator 2.30.0
- HAMi 2.9.0
- Percona MongoDB operator 1.22.0
- OpenBao 2.5.1
- csi-driver-nfs 4.13.3

Managed Kubernetes patch versions are updated to v1.32.13, v1.33.13, v1.34.9, and v1.35.6. Kubernetes v1.30 is no longer supported for tenant clusters.

## Upgrade notes

Cozystack 1.6 has the largest upgrade surface since v1.0. Several preconditions can stop the upgrade, so operators should review the complete release notes and run the provided checks before applying the new Platform Package.

The most important items are:

1. **Verify the etcd backup destination.** Legacy etcd clusters require a working platform backup target before they can be adopted by the new operator.
2. **Audit SeaweedFS installations.** Some clusters that were installed or upgraded through v1.5.x may require recovery of their workload naming before the chart can be rendered safely.
3. **Move tenant Kubernetes clusters away from v1.30.** Live resources are migrated to v1.31 automatically, but GitOps-managed resources must also be updated in Git.
4. **Check tenant StorageClasses.** A manually created StorageClass that has the same name as a propagated LINSTOR class can block the tenant CSI deployment.
5. **Plan for worker replacement.** Existing tenant worker pools will roll from Ubuntu to Talos Linux. Worker disks are recreated, and images are downloaded again.
6. **Review MachineHealthCheck settings.** Automated worker remediation is now enabled with a default `maxUnhealthy` value of 50%.
7. **Back up applications before deleting them.** Application deletion now removes associated storage instead of leaving PVCs behind.

Clusters upgrading directly from v1.4.x must also meet the v1.5 requirement: Kubernetes 1.33 or newer is required for the management cluster and for tenant clusters using the Flux addon.

## Thank you to all contributors

Cozystack v1.6.0 was made possible by @androndo, @IvanHunters, @kvaps, @lexfrei, @lllamnyp, @mattia-eleuteri, @matthieu-robin, @myasnikovdaniil, @scooby87, @shreyaabaranwal, @sircthulhu, and @tym83.

We are especially glad to welcome our first-time contributor, @shreyaabaranwal.

## Release links

- [Cozystack v1.6.0 release notes on GitHub](https://github.com/cozystack/cozystack/releases/tag/v1.6.0)
- [Full changelog from v1.5.0 to v1.6.0](https://github.com/cozystack/cozystack/compare/v1.5.0...v1.6.0)

## Join the community

- [Cozystack on GitHub](https://github.com/cozystack/cozystack)
- Telegram [group](https://t.me/cozystack)
- Slack [group](https://kubernetes.slack.com/archives/C06L3CPRVN1) (Get invite at [https://slack.kubernetes.io](https://slack.kubernetes.io))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
