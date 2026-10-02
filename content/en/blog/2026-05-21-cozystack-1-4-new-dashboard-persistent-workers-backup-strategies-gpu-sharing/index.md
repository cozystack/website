---
title: "Cozystack 1.4: New Dashboard UI, Persistent Tenant Workers, Backup Strategies, and Fractional GPU Sharing"
slug: cozystack-1-4-new-dashboard-persistent-workers-backup-strategies-gpu-sharing
date: 2026-05-21
author: "Cozystack Team"
description: "Cozystack v1.4.0 brings a schema-driven dashboard, persistent worker-node storage for tenant Kubernetes, cloud-style resource presets, declarative backups for managed applications, HAMi-based fractional GPU sharing, a one-switch PROXY-protocol and hairpin-NAT fix, and operational improvements for upgrades, scheduling, and observability."
images:
  - "cozystack-1-4-banner.jpg"
article_types:
  - release
topics:
  - platform
---

{{< figure src="cozystack-1-4-banner.jpg" alt="Cozystack v1.4.0 release banner" width="720" >}}

Cozystack v1.4.0 is now available. The release was published on May 19, 2026, and rolls up every fix shipped in the v1.3.1 to v1.3.3 patch line.

This cycle is focused on the operational experience of running Cozystack as a production platform: a faster dashboard architecture, more durable tenant Kubernetes workers, clearer resource sizing, backup workflows for managed applications, better GPU utilization, safer ingress publishing, and fewer race conditions during first installs and upgrades.

## Main highlights

### New schema-driven dashboard UI

Cozystack 1.4 ships a rewritten dashboard from the `cozystack/cozystack-ui` project. The old `openapi-ui` plus BFF stack has been replaced by a React 19 and TypeScript frontend that talks directly to the Kubernetes API.

The new architecture removes an extra process and proxy layer while keeping the dashboard schema-driven. It also improves several day-to-day workflows:

* VNC access for virtual machines now uses dynamic WebSocket URLs instead of deployment-specific `localhost` assumptions.
* The dashboard can read `ApplicationDefinition` resources for the application catalog and marketplace.
* Operators can inject runtime branding through a ConfigMap, including logos, names, and brand colors, without rebuilding the image.
* Existing `/openapi-ui/*` bookmarks are redirected to the new console.
* The package has been renamed consistently to `cozy-dashboard`.

{{< figure src="dashboard-marketplace-iaas.webp" alt="Cozystack 1.4 dashboard — IaaS marketplace with Bucket, Kubernetes, VirtualPrivateCloud, VMDisk and VMInstance services" width="720" caption="The new dashboard exposes the IaaS marketplace driven by ApplicationDefinition resources." >}}

{{< figure src="dashboard-marketplace-paas.webp" alt="Cozystack 1.4 dashboard — PaaS marketplace with managed PostgreSQL, MariaDB, ClickHouse, Kafka, Redis, OpenSearch, NATS, Harbor, Keycloak and more" width="720" caption="The PaaS catalog covers managed databases, messaging, object storage, secrets, search, and inference services." >}}

{{< figure src="dashboard-deploy-kubernetes.webp" alt="Cozystack 1.4 dashboard — Deploy new Kubernetes form with cluster addons (cert-manager, Cilium, Gateway API, ingress-nginx, GPU Operator)" width="720" caption="Deploying a managed Kubernetes cluster uses the same schema-driven form, with cluster addons exposed declaratively." >}}

{{< figure src="dashboard-deploy-httpcache.webp" alt="Cozystack 1.4 dashboard — Deploy new httpcache form with size, storageClass, endpoints, HAProxy replicas, and resource parameters" width="720" caption="A managed HTTP cache deployment, with PVC sizing, storage class, endpoints, and resource parameters all generated from the application schema." >}}

Documentation:

* [Deploying applications through the new dashboard](https://cozystack.io/docs/v1.4/getting-started/deploy-app/)
* [ApplicationDefinition reference](https://cozystack.io/docs/v1.4/cozystack-api/application-definitions/)
* [White-labeling and runtime branding](https://cozystack.io/docs/v1.4/operations/configuration/white-labeling/)

### Persistent worker-node storage for tenant Kubernetes

Tenant Kubernetes worker VMs now use PVC-backed persistent disks through KubeVirt `dataVolumeTemplates`. Previously, workers used ephemeral `emptyDisk` storage, which meant kubelet certificates, kubeconfig, and containerd state were lost after a VM reboot. A rebooted worker could lose its identity and require manual recovery.

In v1.4, worker state survives VM restarts. The NodeGroup field `ephemeralStorage` is renamed to `diskSize`, and a new per-nodeGroup `storageClass` option lets operators control where worker disks are provisioned. Migration 39 rewrites legacy values automatically during upgrade.

Existing tenant clusters will roll worker nodes once because the KubeVirt machine template changes. Operators should plan capacity for the rollout and choose the storage class intentionally. For many worker-node disk scenarios, the `local` StorageClass is recommended because worker disks now survive restarts and do not need DRBD replication semantics.

Documentation: [Tenant Kubernetes configuration](https://cozystack.io/docs/v1.4/kubernetes/).

### Instance-type resource presets

Resource presets now follow a cloud-style `<series>.<size>` taxonomy. The new model covers five CPU-to-memory series:

* `t1` for tiny and low-memory workloads.
* `c1` for compute-balanced workloads.
* `s1` for standard services such as proxies and caches.
* `u1` for universal workloads such as databases and messaging.
* `m1` for memory-heavy workloads such as search and analytics.

Each series includes eight sizes from `nano` to `4xlarge`, giving operators and tenants 40 presets in total.

The previous flat names such as `small`, `medium`, and `large` are still accepted as deprecated aliases. Existing deployments keep the same CPU and memory values, while Migration 39 rewrites stored values to the new names. The Cozystack API now emits deprecation warnings when app CRs still use legacy preset names.

Documentation: [Resource presets](https://cozystack.io/docs/v1.4/guides/resource-management/).

### Declarative backup strategies for managed applications

The backup strategy controller now supports PostgreSQL, MariaDB, ClickHouse, and FoundationDB. Tenants can define a strategy together with `BackupClass`, `Plan`, `BackupJob`, and `RestoreJob` resources, while the controller composes the backend-specific objects for each managed service.

The new strategies support scheduled backups, ad-hoc snapshots, in-place restores, and restore-to-copy workflows against S3-compatible object storage. Credentials are referenced through Kubernetes Secrets instead of being stored inline, and controller RBAC is constrained so it can only access explicitly referenced secrets.

This extends the existing backup flows for VMInstance and VMDisk and moves Cozystack closer to full backup coverage across the managed application catalog.

Documentation:

* [Managed app backup configuration](https://cozystack.io/docs/v1.4/operations/services/managed-app-backup-configuration/)
* [Application backup and recovery](https://cozystack.io/docs/v1.4/applications/backup-and-recovery/)

### HAMi-based fractional GPU sharing

Cozystack 1.4 adds `hami` as an optional system package. HAMi v2.8.1, a CNCF Sandbox project, provides fractional GPU sharing for tenant Kubernetes clusters.

With HAMi enabled, tenant workloads can request resources such as `nvidia.com/gpu`, `nvidia.com/gpumem`, and `nvidia.com/gpucores`, allowing multiple pods to share one physical NVIDIA GPU with explicit memory and compute slicing. The integration includes the device plugin, scheduler extender, mutating webhook, and RuntimeClass. It is exposed through an opt-in `hami.enabled` toggle and depends on the NVIDIA GPU Operator.

There is one important compatibility note: HAMi compute isolation depends on container images with glibc older than 2.34. Memory enforcement works broadly, but Alpine and musl-based images are not supported for HAMi-core compute isolation.

Documentation: [GPU sharing with HAMi](https://cozystack.io/docs/v1.4/kubernetes/gpu-sharing/).

### One switch for PROXY protocol and hairpin NAT

The new `publishing.proxyProtocol: true` option enables PROXY protocol on the host ingress-nginx and deploys Ouroboros to solve the related hairpin-NAT problem.

When PROXY protocol is enabled, in-cluster traffic to the cluster's own public hostnames can otherwise reach ingress-nginx without the required PROXY header. Ouroboros fixes that path through CoreDNS rewrite snippets. Cozystack exposes it as both a host-level system package and a per-tenant addon through `addons.ouroboros.enabled`.

The default behavior is unchanged. Clusters that do not enable PROXY protocol do not receive new resources.

Documentation: [PROXY protocol and hairpin NAT](https://cozystack.io/docs/v1.4/networking/hairpin-proxy-protocol/).

### Better HelmRelease behavior and tenant bootstrap reliability

The Cozystack operator now exposes HelmRelease generation knobs as operator flags and chart values, including interval, retry interval, install timeout, upgrade timeout, and max history.

The retry strategy now uses `RetryOnFailure`, which avoids uninstall-and-reinstall loops when a first install is slow. Applications can also set a per-Application install and upgrade timeout through the `release.cozystack.io/helm-install-timeout` annotation. Tenant Kubernetes uses this to give Kamaji enough time during cold bootstrap, fixing the recurring `wait hr/tenant-kubernetes timeout` failure mode.

Documentation:

* [Tenant Kubernetes operations](https://cozystack.io/docs/v1.4/kubernetes/)
* [Troubleshooting Flux CD](https://cozystack.io/docs/v1.4/operations/troubleshooting/flux-cd/)

### Kubelet reservations for worker nodes

Tenant Kubernetes worker nodes now receive automatically computed kubelet reservations for CPU and memory. This keeps kubelet itself from being targeted under memory pressure and makes scheduler and autoscaler decisions more accurate.

Cluster-autoscaler annotations now report allocatable CPU and memory instead of raw totals, so autoscaling decisions match what Kubernetes can actually schedule.

Documentation: [Tenant Kubernetes operations](https://cozystack.io/docs/v1.4/kubernetes/).

## Also in v1.4.0

* PostgreSQL parameters are now typed and protected by a denylist for dangerous values such as `archive_command`, `restore_command`, `ssl_passphrase_command`, `dynamic_library_path`, and `*_preload_libraries`.
* Keycloak gains `extraEnv` and user profile customization support.
* The etcd application exposes S3 backup schedules through the updated etcd-operator.
* Per-package `upgradeCRDs` policy is now configurable.
* `cozyreport` now collects Flux, cert-manager, host context, application resources, and a top-level `summary.txt`.
* SeaweedFS tenant ingress limits single PUT requests to 5 GB.
* GPU observability dashboards and recording rules were added for Grafana and VictoriaMetrics.
* VMInstance port filtering is fixed under the new cozy-proxy v0.3.0 mode.
* LINSTOR CSI is updated with fixes for dual-attach and transient demotion errors.

Documentation:

* [PostgreSQL configuration](https://cozystack.io/docs/v1.4/applications/postgres/)
* [Keycloak and OIDC](https://cozystack.io/docs/v1.4/operations/oidc/)
* [etcd service configuration](https://cozystack.io/docs/v1.4/operations/services/etcd/)
* [SeaweedFS service configuration](https://cozystack.io/docs/v1.4/operations/services/seaweedfs/)
* [Monitoring dashboards](https://cozystack.io/docs/v1.4/operations/services/monitoring/dashboards/)
* [Troubleshooting and diagnostics](https://cozystack.io/docs/v1.4/operations/troubleshooting/)

## Platform components

Cozystack 1.4 updates the platform base and several core packages:

* Talos: v1.12.7 to v1.13.0
* cert-manager: v1.19.3 to v1.20.2
* Cilium: v1.19.1 to v1.19.3
* NVIDIA GPU Operator: v25.3.0 to v26.3.1
* etcd-operator: v0.4.2 to v0.4.3
* KubeVirt: v1.6.3 to v1.8.2
* cozy-proxy: v0.2.0 to v0.3.0
* linstor-csi: v1.10.6
* HAMi: v2.8.1
* Ouroboros: v0.7.2

Documentation:

* [Platform stack overview](https://cozystack.io/docs/v1.4/guides/platform-stack/)
* [Upgrade guide](https://cozystack.io/docs/v1.4/operations/cluster/upgrade/)

## Upgrade notes

Most operators can upgrade to v1.4.0 without manual configuration changes. Cozystack keeps the same API surface for existing workloads, and in-platform migrations handle the main value rewrites.

There are several operational details to plan for:

* Tenant Kubernetes workers will roll once. The `ephemeralStorage` to `diskSize` migration is automatic, but existing worker VMs are replaced one by one because the KubeVirt machine template changes.
* KubeVirt VMs that were already running before the platform upgrade need a cold restart after upgrading. The KubeVirt jump from v1.6.3 to v1.8.2 crosses an upstream QEMU change, and live migration of pre-upgrade VMs can fail. New VMs created after the upgrade are unaffected.
* Legacy resource preset names still work as deprecated aliases, but new deployments should use the `<series>.<size>` names.
* PostgreSQL deployments that use denylisted parameters will fail to render until those parameters are removed.
* cert-manager v1.20 changes the default container UID/GID to 65532. Operators with custom PodSecurityPolicy, imagePullSecrets, or filesystem-mounted certificates pinned to the previous UID should review their configuration.

Documentation:

* [Upgrade guide](https://cozystack.io/docs/v1.4/operations/cluster/upgrade/)
* [Tenant Kubernetes operations](https://cozystack.io/docs/v1.4/kubernetes/)
* [Virtualization operations](https://cozystack.io/docs/v1.4/virtualization/)
* [Resource management](https://cozystack.io/docs/v1.4/guides/resource-management/)
* [PostgreSQL configuration](https://cozystack.io/docs/v1.4/applications/postgres/)

## Documentation worth knowing about

* [New dashboard and application catalog](https://cozystack.io/docs/v1.4/getting-started/deploy-app/)
* [ApplicationDefinition reference](https://cozystack.io/docs/v1.4/cozystack-api/application-definitions/)
* [White-labeling and runtime branding](https://cozystack.io/docs/v1.4/operations/configuration/white-labeling/)
* [Tenant Kubernetes configuration](https://cozystack.io/docs/v1.4/kubernetes/)
* [Resource presets](https://cozystack.io/docs/v1.4/guides/resource-management/)
* [Managed app backup configuration](https://cozystack.io/docs/v1.4/operations/services/managed-app-backup-configuration/)
* [Application backup and recovery](https://cozystack.io/docs/v1.4/applications/backup-and-recovery/)
* [GPU sharing with HAMi](https://cozystack.io/docs/v1.4/kubernetes/gpu-sharing/)
* [PROXY protocol and hairpin NAT](https://cozystack.io/docs/v1.4/networking/hairpin-proxy-protocol/)
* [Upgrade guide](https://cozystack.io/docs/v1.4/operations/cluster/upgrade/)
* [Cozystack v1.4 documentation](https://cozystack.io/docs/v1.4/)

## Thank you to all contributors

This release was shaped by the work of [@androndo](https://github.com/androndo), [@Arsolitt](https://github.com/Arsolitt), [@dislogical](https://github.com/dislogical), [@dvc](https://github.com/dvc), [@IvanHunters](https://github.com/IvanHunters), [@kvaps](https://github.com/kvaps), [@lexfrei](https://github.com/lexfrei), [@matthieu-robin](https://github.com/matthieu-robin), [@mattia-eleuteri](https://github.com/mattia-eleuteri), [@myasnikovdaniil](https://github.com/myasnikovdaniil), [@sircthulhu](https://github.com/sircthulhu), and [@tym83](https://github.com/tym83).

A special welcome to first-time contributors [@dvc](https://github.com/dvc) and [@dislogical](https://github.com/dislogical). Thank you all.

## Release links

* [Cozystack v1.4.0 on GitHub](https://github.com/cozystack/cozystack/releases/tag/v1.4.0)
* [Full changelog v1.3.0 to v1.4.0](https://github.com/cozystack/cozystack/compare/v1.3.0...v1.4.0)
* [Cozystack UI](https://github.com/cozystack/cozystack-ui)
* [HAMi](https://github.com/Project-HAMi/HAMi)
* [Ouroboros](https://github.com/lexfrei/ouroboros)

## Join the community

* GitHub: [cozystack/cozystack](https://github.com/cozystack/cozystack)
* Telegram: [@cozystack](https://t.me/cozystack)
* Slack: [#cozystack](https://kubernetes.slack.com/archives/C06L3CPRVN1) on the Kubernetes workspace ([invite](https://slack.kubernetes.io))
* [Subscribe to our community meetings calendar](https://zoom-lfx.platform.linuxfoundation.org/meetings/cozystack)
* [Add meetings to your calendar](https://webcal.prod.itx.linuxfoundation.org/lfx/lfsixxnFWxbvsyEuC2)
