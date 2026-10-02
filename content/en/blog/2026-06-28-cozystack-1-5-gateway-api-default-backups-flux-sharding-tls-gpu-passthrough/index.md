---
title: "Cozystack 1.5: Gateway API, Default Backups, Flux Sharding, TLS for Managed Services, and GPU Passthrough"
slug: cozystack-1-5-gateway-api-default-backups-flux-sharding-tls-gpu-passthrough
date: 2026-06-28
author: "Cozystack Team"
description: "Cozystack v1.5.0 adds opt-in Gateway API ingress via Cilium, TLS for managed databases, out-of-the-box backups, Flux v2.8, GPU passthrough, and dashboard improvements."
images:
  - "cozystack-1-5-banner.jpg"
article_types:
  - release
topics:
  - platform
---

{{< figure src="cozystack-1-5-banner.jpg" alt="Cozystack v1.5.0 release banner — Gateway API, default backups, Flux sharding, TLS, and GPU passthrough" width="720" >}}

Cozystack v1.5.0 is now available. The release was published on June 22, 2026, and rolls up every fix shipped in the v1.4.1 to v1.4.4 patch line.

This release is focused on the next layer of production maturity. It makes traffic publishing more flexible, backups easier to adopt, tenant reconciliation safer, managed services more secure by default, and GPU workloads less manual to operate.

## Main highlights

### Gateway API support via Cilium

Cozystack 1.5 adds Gateway API support backed by Cilium.

This is an opt-in ingress path that can run alongside the existing per-tenant ingress-nginx controllers. Existing clusters keep their current behavior by default. The feature is materialized per tenant through a new `gateway.cozystack.io/v1alpha1 TenantGateway` CRD reconciled by `cozystack-controller`.

Operators can enable the new path at the platform level with `publishing.gateway.enabled=true`. After that, a tenant can get its own Gateway, LoadBalancer IP, and certificate through `tenant.spec.gateway=true`. If the value is not set, the tenant can inherit the nearest ancestor Gateway through the same label-based model already used for ingress inheritance.

Two certificate solver modes are supported.

HTTP-01 is the default mode. It gives each app its own certificate with no extra platform setup for new apps.

DNS-01 is opt-in. It uses one wildcard certificate for an apex domain and supports Cloudflare, Route 53, DigitalOcean, and RFC 2136 providers.

There are two upgrade details to know.

Cilium Envoy and Gateway API support are now always enabled, which adds a `cilium-envoy` DaemonSet (roughly 100 MB RAM per node at idle). Also, `cozystack-api` now invokes admission on Create and Delete for `apps.cozystack.io/*`, so custom admission policies or webhooks on these kinds will now run on all three verbs.

### TLS for managed databases and messaging

Cozystack 1.5 adds TLS support for Kafka, NATS, Qdrant, and PostgreSQL external endpoints.

The model is consistent across these services. Each chart gets a `tls.enabled` value with tri-state behavior.

When unset, it inherits from `external`. This means TLS turns on automatically when the service is published externally and stays off for internal-only deployments. An explicit `true` or `false` always wins.

The trust anchor is chart-managed or operator-managed. Clients retrieve and pin the self-signed CA. There is no public CA involved.

Kafka now serves TLS on its external LoadBalancer listener on port 9094, with certificates managed by Strimzi.

NATS and Qdrant use a self-contained cert-manager chain inside the tenant namespace. NATS covers client connections and cluster routes. Qdrant covers REST and gRPC.

PostgreSQL already serves TLS through CloudNativePG. In 1.5, `tls.enabled` injects the external hostname into the server certificate SANs when `external: true`, so `sslmode=verify-full` works against the external endpoint.

One change needs planning. Existing instances with `external: true` will switch to TLS-on after upgrade. Internal instances are not affected.

### Backups that work out of the box

Previous releases gave Cozystack the backup machinery. Version 1.5 makes the default path practical.

A platform-managed `BackupClass` named `cozy-default` is now shipped by default. It is backed by a shared system bucket named `cozy-backups`.

Apps can opt in with `useSystemBucket`. After that, Cozystack projects shared backup credentials into the tenant namespace with RBAC isolation and projection metrics. This removes the need to configure per-app S3 credentials for the normal path.

Default strategies are now provided for every backup-capable app: Velero for VMDisk and VMInstance, CNPG for PostgreSQL, Altinity for ClickHouse, and dedicated strategies for MariaDB, FoundationDB, and etcd.

Velero is now a default system package. This fixes a real install and upgrade problem where the default backup strategy controller depended on Velero, while Velero itself was optional. Existing clusters will get Velero in the `cozy-velero` namespace on upgrade. Operators who do not back up VMs can opt out with `bundles.disabledPackages`.

Two new backup strategies also land in this release.

The new etcd strategy is cluster-scoped and S3-only. It supports snapshot BackupJobs and destructive in-place RestoreJobs.

The new generic Job strategy gives operators an application-agnostic way to define backup and restore logic. The operator supplies a Kubernetes Job template. Cozystack renders it for backup and re-renders it with restore mode for recovery.

### Flux v2.8 with stricter reconciliation

Cozystack 1.5 upgrades Flux from v2.7.3 to v2.8.0.

This affects both the embedded management-cluster Flux and the optional tenant Flux addon. The flux-operator and flux-instance charts move from v0.33.0 to v0.50.0.

Flux v2.8 brings helm-controller v1.5 with Server-Side Apply, `--force-conflicts`, and kstatus-based health checking by default.

This is a stricter model. Misplaced chart fields that Flux v2.7 silently ignored now become hard errors. Parent HelmReleases now wait for every child resource to become Ready before reporting Ready themselves.

This is better for correctness, but it also changes upgrade behavior.

Kubernetes 1.33 or newer is now required for the management cluster. The same requirement applies to tenant clusters that enable the Flux addon.

The old `upgrade.force: true` knob is removed. Immutable-field changes no longer self-heal through force replacement. If an upgrade changes an immutable field, such as StatefulSet `volumeClaimTemplates` or `serviceName`, the object must be recreated manually (for example, `kubectl delete sts <name> --cascade=orphan`) and reconciled again by Flux.

### flux-shard-operator for tenant HelmRelease sharding

Cozystack now includes `flux-shard-operator`.

This operator spreads tenant HelmReleases across multiple helm-controller shards. The goal is simple: one noisy tenant should not slow down reconciliation for everyone else.

A typical bad case is a HelmRelease stuck in infinite remediation. Before sharding, that could degrade reconciliation across the tenant controller path. With 1.5, placement is assigned per tenant. All HelmReleases for one tenant share the same shard.

The default setting is `shardCount: auto`. Small clusters keep the current single-shard behavior. Larger fleets shard out automatically based on the tenant HelmRelease count. Operators can also pin the shard count explicitly.

The old hand-rolled `flux-tenants` deployment is drained and retired automatically by migration 44.

### Operator-provided wildcard certificates

Operators can now serve platform services and the root tenant ingress through a pre-existing wildcard TLS certificate.

Set `publishing.certificates.wildcardSecretName` to the name of a TLS Secret in the publishing namespace. By default, that namespace is `tenant-root`.

Only the Secret name travels over the Cozystack values channel. The key material does not.

This works for both ingress paths.

With ingress-nginx, the controller serves the Secret as the default SSL certificate and platform Ingresses drop their cert-manager annotations.

With Gateway API, a new `existingSecret` TenantGateway certificate mode references the Secret directly and does not create an Issuer or Certificate.

The current scope is the root tenant. Extending wildcard mode to child tenants is a follow-up.

### GPU passthrough without manual KubeVirt patching

GPU support gets a major operational cleanup in 1.5.

For tenant Kubernetes, node groups that declare `gpus` now get the `gpu=on` kubelet label automatically. This lets HAMi's device plugin schedule and advertise `nvidia.com/gpu`.

The tenant GPU operator also loads the NVIDIA driver with `NVreg_NvLinkDisable=1`, which fixes a single-SXM-GPU passthrough case that could previously hang during initialization.

For KubeVirt VMs, enabling `cozystack.gpu-operator` now auto-populates the KubeVirt CR. It injects the `HostDevices` feature gate and fills `permittedHostDevices` from shipped NVIDIA default tables. vGPU configuration is also covered through `mediatedDevicesConfiguration`.

In practice, GPU VMs can now schedule without a manual `kubectl patch`.

There is one important upgrade note. The bundle now owns `spec.configuration.permittedHostDevices`. If you have custom hand-edited device entries, move them into `.gpu.permittedHostDevices` before upgrading and verify that each `resourceName` matches what your nodes advertise.

A third GPU operator variant is also added. The new `container` variant is for hosts where the NVIDIA driver and container toolkit are already installed by the OS. It exposes GPUs to regular containerized pods through the device plugin only.

### Deletion protection for critical platform objects

Cozystack 1.5 adds a deletion-protection guardrail for critical platform objects.

Objects labeled `platform.cozystack.io/no-delete=true` cannot be deleted directly. The check runs in-process through Kubernetes ValidatingAdmissionPolicy. There is no webhook, DaemonSet, TLS setup, or extra image.

Protected objects include the `cozy-system` and `tenant-root` namespaces, the root tenant HelmRelease, the `cozystack-version` ConfigMap, the `cozystack-packages` package source, cert-manager ClusterIssuers, the LinstorCluster, and the packages CRDs.

If an operator really needs to delete a protected object, they can remove the label first.

This feature requires Kubernetes 1.30 or newer.

### Runtime-populated dashboard dropdowns

The dashboard gets a cleaner way to show live options in create and edit forms.

A new read-only `Option` resource powers dropdowns that depend on cluster state. This covers GPU devices, KubeVirt instancetypes and preferences, Multus networks, VM images, storage pools, storage classes, backup classes, and backup plans.

App charts declare option sources through the new `x-cozystack-options` schema keyword. Tenants get read-only access to options in their own namespace.

The result is simple but important. Forms no longer need to rely on free text or stale static enums when the correct value already exists in the cluster.

## Also in v1.5.0

Cozystack 1.5 also includes a broad set of platform improvements and fixes.

Tenant users can now start, stop, and restart their VMs from the dashboard. The missing KubeVirt subresource RBAC has been added at the tenant base-use level.

Platform admins get a new Tenant Overview Grafana dashboard. It shows a cross-tenant fleet summary, top consumers, usage trends, and health signals. It is deployed only to the root monitoring stack, not to per-tenant Grafanas.

A new Cluster Usage page in the dashboard is backed by dedicated RBAC. It shows cluster-wide and per-node utilization, including GPUs.

Stateful app `storageClass` fields are now marked as immutable in the chart schema and rendered as read-only in dashboard edit forms. This covers 16 stateful apps, including PostgreSQL, Kafka, Redis, OpenSearch, ClickHouse, MongoDB, NATS, Qdrant, RabbitMQ, Harbor, FoundationDB, MariaDB, VMDisk, and others. The reason is practical: changing `storageClass` does not migrate existing data.

The enforcement is UI-only in this release. Direct `kubectl patch` is still accepted until API-level CEL enforcement lands.

The release also fixes a long list of install, upgrade, and runtime issues. Highlights include safer OpenAPI schema publishing in `cozystack-api`, full upstream prometheus-operator CRDs, fixed OIDC issuer URLs in tenant kubeconfigs, containerd 2.x registry config support, KubeVirt CSI hotplug detach fixes, startup probes for slow controllers, OpenSearch availability in the PaaS bundle, and several SeaweedFS fixes after the 4.31 bump.

## Platform components

Several core components are updated in this release.

Flux moves from v2.7.3 to v2.8.0.

MetalLB moves from v0.15.2 to v0.16.1. FRR-K8s is now the default BGP backend. Metrics endpoints are HTTPS-only.

SeaweedFS moves from 4.05 to 4.31. This clears the upstream 4.23 erasure-coding and multi-disk hazard and brings many S3 API correctness fixes.

etcd-operator moves from v0.4.3 to v0.4.5. The update includes restore-path fixes and backup status improvements.

ouroboros moves from v0.7.2 to v0.8.0. It now logs clearer reasons when TCP backend readiness checks fail.

seaweedfs-cosi-driver moves to v0.3.1 and can recover from stale UNIX sockets after non-graceful exits.

Cozystack also adds kuberture as a new optional system package. It watches the Kubernetes API server EndpointSlice and emits headless Services for external-dns, which helps publish Kubernetes API endpoints to DNS.

## Upgrade notes

Most operators can take v1.5.0 with no manual action, but several changes need attention.

First, Kubernetes 1.33 or newer is required for the management cluster. It is also required for tenant clusters that enable the Flux addon.

Second, `upgrade.force` is gone. Immutable-field changes no longer self-heal through force replacement. Operators may need to recreate affected objects manually (for example, `kubectl delete sts <name> --cascade=orphan`) and let Flux reconcile them again.

Third, GPU VM operators must move custom host device entries before upgrading. Cozystack now owns `KubeVirt.spec.configuration.permittedHostDevices` when `cozystack.gpu-operator` is enabled.

Fourth, MetalLB now uses the FRR-K8s BGP backend by default. Metrics are HTTPS-only, so scrape configs using old HTTP endpoints must be updated.

Fifth, externally published databases and messaging services gain TLS automatically. Clients must retrieve and pin the self-signed CA. Internal services are not affected.

## Documentation

This release ships with new and updated documentation for several production paths.

* [Gateway API guide](https://cozystack.io/docs/v1.5/networking/gateway-api/) — the Cilium-backed publishing model, certificate modes, and migration details
* [Application backup and recovery](https://cozystack.io/docs/v1.5/applications/backup-and-recovery/)
* [Managed app backup configuration](https://cozystack.io/docs/v1.5/operations/services/managed-app-backup-configuration/)
* [Managed Kubernetes operations](https://cozystack.io/docs/v1.5/kubernetes/)
* [GPU sharing and operator variants](https://cozystack.io/docs/v1.5/kubernetes/gpu-sharing/)
* [Upgrade guide](https://cozystack.io/docs/v1.5/operations/cluster/upgrade/)
* [Cozystack v1.5 documentation](https://cozystack.io/docs/v1.5/)

## Thank you to all contributors

Cozystack v1.5.0 was made possible by [@androndo](https://github.com/androndo), [@Arsolitt](https://github.com/Arsolitt), [@elaugaste](https://github.com/elaugaste), [@IvanHunters](https://github.com/IvanHunters), [@kvaps](https://github.com/kvaps), [@kvapsova](https://github.com/kvapsova), [@lexfrei](https://github.com/lexfrei), [@lllamnyp](https://github.com/lllamnyp), [@myasnikovdaniil](https://github.com/myasnikovdaniil), [@sunib](https://github.com/sunib), and [@tym83](https://github.com/tym83).

A special welcome to [@elaugaste](https://github.com/elaugaste), our first-time contributor in this release. Thank you all.

## Release links

* [Cozystack v1.5.0 on GitHub](https://github.com/cozystack/cozystack/releases/tag/v1.5.0)
* [Full changelog v1.4.0 to v1.5.0](https://github.com/cozystack/cozystack/compare/v1.4.0...v1.5.0)

## Join the community

* GitHub: [cozystack/cozystack](https://github.com/cozystack/cozystack)
* Telegram: [@cozystack](https://t.me/cozystack)
* Slack: [#cozystack](https://kubernetes.slack.com/archives/C06L3CPRVN1) on the Kubernetes workspace ([invite](https://slack.kubernetes.io))
* [Subscribe to our community meetings calendar](https://zoom-lfx.platform.linuxfoundation.org/meetings/cozystack)
* [Add meetings to your calendar](https://webcal.prod.itx.linuxfoundation.org/lfx/lfsixxnFWxbvsyEuC2)
