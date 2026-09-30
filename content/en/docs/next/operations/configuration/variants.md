---
title: "Cozystack Variants: Overview and Comparison"
linkTitle: "Variants"
description: "Cozystack variants reference: composition, configuration, and comparison."
weight: 20
aliases:
  - /docs/next/guides/bundles
  - /docs/next/operations/bundles/
  - /docs/next/operations/bundles/isp-full
  - /docs/next/operations/bundles/isp-hosted
  - /docs/next/operations/bundles/paas-full
  - /docs/next/operations/bundles/paas-hosted
  - /docs/next/operations/bundles/distro-full
  - /docs/next/operations/bundles/distro-hosted
  - /docs/next/install/cozystack/bundles
  - /docs/next/operations/configuration/bundles
---

## Introduction

**Variants** are pre-defined configurations of Cozystack that determine which bundles and components are enabled.
Each variant is tested, versioned, and guaranteed to work as a unit.
They simplify installation, reduce the risk of misconfiguration, and make it easier to choose the right set of features for your deployment.

This guide is for infrastructure engineers, DevOps teams, and platform architects planning to deploy Cozystack in different environments.
It explains how Cozystack variants help tailor the installation to specific needs—whether you're building a fully featured platform-as-a-service
or need full manual control over installed packages.


## Variants Overview

| Component                     | [default]              | [isp-full]             | [isp-full-generic]     | [isp-hosted]           | [isp-slim]             | [isp-slim-generic]     | [isp-hosted-slim]      |
|:------------------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------|
| [Managed Kubernetes][k8s]     |                        | ✔                      | ✔                      |                        |                        |                        |                        |
| [Managed Applications][apps]  |                        | ✔                      | ✔                      | ✔                      | opt-in                 | opt-in                 | opt-in                 |
| [Virtual Machines][vm]        |                        | ✔                      | ✔                      |                        |                        |                        |                        |
| Cozystack Dashboard (UI)      |                        | ✔                      | ✔                      | ✔                      | ✔                      | ✔                      | ✔                      |
| [Cozystack API][api]          |                        | ✔                      | ✔                      | ✔                      | ✔                      | ✔                      | ✔                      |
| [Kubernetes Operators]        |                        | ✔                      | ✔                      | ✔                      | opt-in                 | opt-in                 | opt-in                 |
| [Monitoring subsystem]        |                        | ✔                      | ✔                      | ✔                      | opt-in                 | opt-in                 | opt-in                 |
| Backups                       |                        | ✔                      | ✔                      | ✔                      | opt-in                 | opt-in                 | opt-in                 |
| Storage subsystem             |                        | [LINSTOR]              | [LINSTOR]              |                        | [LINSTOR]              | [LINSTOR]              |                        |
| Networking subsystem          |                        | [Kube-OVN] + [Cilium]  | [Kube-OVN] + [Cilium]  |                        | [Cilium]               | [Cilium]               |                        |
| Virtualization subsystem      |                        | [KubeVirt]             | [KubeVirt]             |                        |                        |                        |                        |
| OS and [Kubernetes] subsystem |                        | [Talos Linux]          |                        |                        | [Talos Linux]          |                        |                        |

[apps]: {{% ref "/docs/next/applications" %}}
[vm]: {{% ref "/docs/next/virtualization" %}}
[k8s]: {{% ref "/docs/next/kubernetes" %}}
[api]: {{% ref "/docs/next/cozystack-api" %}}
[monitoring subsystem]: {{% ref "/docs/next/guides/platform-stack#victoria-metrics" %}}
[linstor]: {{% ref "/docs/next/guides/platform-stack#drbd" %}}
[kube-ovn]: {{% ref "/docs/next/guides/platform-stack#kube-ovn" %}}
[cilium]: {{% ref "/docs/next/guides/platform-stack#cilium" %}}
[kubevirt]: {{% ref "/docs/next/guides/platform-stack#kubevirt" %}}
[talos linux]: {{% ref "/docs/next/guides/platform-stack#talos-linux" %}}
[kubernetes]: {{% ref "/docs/next/guides/platform-stack#kubernetes" %}}
[kubernetes operators]: https://github.com/cozystack/cozystack/blob/main/packages/core/platform/templates/bundles/paas.yaml

[default]: {{% ref "/docs/next/operations/configuration/variants#default" %}}
[isp-full]: {{% ref "/docs/next/operations/configuration/variants#isp-full" %}}
[isp-full-generic]: {{% ref "/docs/next/operations/configuration/variants#isp-full-generic" %}}
[isp-hosted]: {{% ref "/docs/next/operations/configuration/variants#isp-hosted" %}}
[isp-slim]: {{% ref "/docs/next/operations/configuration/variants#isp-slim" %}}
[isp-slim-generic]: {{% ref "/docs/next/operations/configuration/variants#isp-slim-generic" %}}
[isp-hosted-slim]: {{% ref "/docs/next/operations/configuration/variants#isp-hosted-slim" %}}


## Choosing the Right Variant

Variants combine bundles from different layers to match particular needs.
Some are designed for full platform scenarios, others for cloud-hosted workloads or fully manual package management.

### `default`

`default` is a minimal variant that only provides the set of PackageSources (package registry references).
No bundles or components are pre-configured—all packages are managed manually through [cozypkg](https://github.com/cozystack/cozystack/tree/main/cmd/cozypkg).
Use this variant when you need full control over which packages are installed and configured.
This is the variant used in the [Build Your Own Platform (BYOP)]({{% ref "/docs/next/install/cozystack/kubernetes-distribution" %}}) workflow.

Example configuration:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: default
```

### `isp-full`

`isp-full` is a full-featured PaaS and IaaS variant, designed for installation on Talos Linux.
It includes all bundles and provides the full set of Cozystack components, enabling a comprehensive PaaS experience.
Some higher-layer components are optional and can be excluded during installation.

`isp-full` is intended for installation on bare-metal servers or VMs.

Example configuration:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full
  components:
    platform:
      values:
        networking:
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://192.168.100.10:6443"
          exposedServices:
            - api
            - dashboard
            - cdi-uploadproxy
            - vm-exportproxy
```

### `isp-full-generic`

`isp-full-generic` provides the same full-featured PaaS and IaaS experience as `isp-full`, but is designed for generic Kubernetes distributions such as k3s, kubeadm, or RKE2.
Use this variant when you want the full Cozystack feature set without requiring Talos Linux.

For detailed installation instructions, see the [Generic Kubernetes guide]({{% ref "/docs/next/install/kubernetes/generic" %}}).

Example configuration:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full-generic
  components:
    platform:
      values:
        networking:
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://192.168.100.10:6443"
          exposedServices:
            - api
            - dashboard
            - cdi-uploadproxy
            - vm-exportproxy
```

### `isp-hosted`

Cozystack can be installed as platform-as-a-service (PaaS) on top of an existing managed Kubernetes cluster,
typically provisioned from a cloud provider.
Variant `isp-hosted` is made for this use case.
It can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.

`isp-hosted` includes the PaaS and NaaS bundles, providing Cozystack API and UI, managed applications, and tenant Kubernetes clusters.
It does not include CNI plugins, virtualization, or storage.

The Kubernetes cluster used to deploy Cozystack must conform to the following requirements:

-   Listening address of some Kubernetes components must be changed from `localhost` to a routable address.
-   Kubernetes API server must be reachable on `localhost`.

Example configuration:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-hosted
  components:
    platform:
      values:
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://192.168.100.10:6443"
          exposedServices:
            - api
            - dashboard
```

### `isp-slim`

`isp-slim` is the minimal counterpart of `isp-full` for Talos Linux, meant for small installations such as arm64 clusters, labs and edge sites. It installs the base platform only: Cilium networking, LINSTOR storage, the Cozystack API and dashboard, tenants, ingress and Gateway API. Everything else, including managed applications, their operators, monitoring and backups, is opt-in (with `authentication.oidc.enabled`, Keycloak, `cozystack.keycloak-operator` and `cozystack.postgres-operator` are installed as well): add the packages you need to `bundles.enabledPackages` (see [Enabling components on slim variants](#enabling-components-on-slim-variants)).

Virtualization and managed Kubernetes are not available on slim variants: enabling the `iaas` bundle fails the render. Use `isp-full` or `isp-full-generic` if you need them.

Networking runs on Cilium alone, without Kube-OVN, so `networking.podCIDR`, `networking.podGateway`, `networking.serviceCIDR` and `networking.joinCIDR` are not used: pods get addresses from the pod CIDR Kubernetes assigns to each node. `networking.encryption.enabled` is not supported on `isp-slim` and `isp-slim-generic` and fails the render.

MetalLB is not installed. `LoadBalancer` Services get their addresses from Cilium: create a pool and an L2 announcement policy, for example:

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: default
spec:
  blocks:
    - start: 192.0.2.10
      stop: 192.0.2.20
---
apiVersion: cilium.io/v2alpha1
kind: CiliumL2AnnouncementPolicy
metadata:
  name: default
spec:
  loadBalancerIPs: true
```

With `publishing.externalIPs` set, the host ingress needs no load balancer at all, but a Gateway still creates a `LoadBalancer` Service and needs the pool. MetalLB is still available as an opt-in package, `cozystack.metallb`.

Example configuration:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-slim
  components:
    platform:
      values:
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://192.168.100.10:6443"
          exposedServices:
            - api
            - dashboard
```

### `isp-slim-generic`

`isp-slim-generic` is the same minimal platform as `isp-slim`, with the same Cilium-only networking, for generic Kubernetes distributions such as k3s, kubeadm or RKE2. Node requirements are those of `isp-full-generic`; see the [Generic Kubernetes guide]({{% ref "/docs/next/install/kubernetes/generic" %}}) and set `variant: isp-slim-generic` in the Platform Package.

### `isp-hosted-slim`

`isp-hosted-slim` is the minimal counterpart of `isp-hosted`: the host cluster provides CNI and storage, and Cozystack installs only the API, dashboard, tenants, ingress and Gateway API. Cluster requirements are those of `isp-hosted`. Managed applications are opt-in, as on the other slim variants.

### Enabling components on slim variants

On a slim variant, a package is installed only when it is listed in `bundles.enabledPackages` of the Platform Package. A package does not pull in its dependencies: list every package from its row below, otherwise the Package stays in `DependenciesNotReady`.

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-slim
  components:
    platform:
      values:
        bundles:
          enabledPackages:
            - cozystack.postgres-operator
            - cozystack.postgres-application
```

| Component | Packages to add to `bundles.enabledPackages` |
| --- | --- |
| A managed application, for example PostgreSQL | The application and its operator: `cozystack.postgres-application`, `cozystack.postgres-operator`. The same pattern applies to MariaDB, Kafka, ClickHouse, FoundationDB, RabbitMQ, Redis, MongoDB and OpenSearch. Valkey uses `cozystack.redis-operator`; Harbor also needs `cozystack.postgres-operator`, `cozystack.redis-operator` and `cozystack.seaweedfs-application`, and its tenant needs SeaweedFS enabled for the registry bucket. NATS, OpenBao, Qdrant, `cozystack.tcp-balancer-application` and `cozystack.vpn-application` need no operator. |
| Monitoring | `cozystack.monitoring-application`, `cozystack.grafana-operator`, `cozystack.postgres-operator`, `cozystack.monitoring-agents`, `cozystack.metrics-server`, `cozystack.vertical-pod-autoscaler`. Also set `monitoring.rootEnabled: true` in the platform values and `spec.monitoring: true` on the root Tenant. |
| etcd for tenants | `cozystack.etcd-application`, `cozystack.etcd-operator`, `cozystack.vertical-pod-autoscaler` |
| SeaweedFS and buckets | `cozystack.seaweedfs-application`, `cozystack.bucket-application` |
| Backups | `cozystack.backupstrategy-controller`, `cozystack.backup-controller`, `cozystack.velero`, `cozystack.bucket-application`, `cozystack.monitoring-agents`, `cozystack.metrics-server`, `cozystack.vertical-pod-autoscaler`. The default backup bucket lives in the root Tenant, so also add `cozystack.seaweedfs-application` and set `spec.seaweedfs: true` on the root Tenant. |
| Metrics API (`kubectl top`, HPA) | `cozystack.metrics-server` |
| Multus | `cozystack.multus`. Not available on `isp-hosted-slim`. |
| MetalLB | `cozystack.metallb`. Not available on `isp-hosted-slim`. |

Slim variants are meant for new installations. Do not switch a running `isp-full` or `isp-full-generic` cluster to a slim variant: the networking Package moves from Kube-OVN with Cilium to Cilium alone, Kube-OVN is removed, and running pods lose networking. The other platform components stay installed (their Packages carry `helm.sh/resource-policy: keep`), so the switch does not make the cluster smaller.

## Learn More

For a full list of configuration options for each variant, refer to the
[configuration reference]({{% ref "/docs/next/operations/configuration" %}}).

To see the full list of components, how to enable and disable them, refer to the
[Components reference]({{% ref "/docs/next/operations/configuration/components" %}}).

To deploy a selected variant, follow the [Cozystack installation guide]({{% ref "/docs/next/install/cozystack" %}})
or [provider-specific guides]({{% ref "/docs/next/install/providers" %}}).
However, if this your first time installing Cozystack, it's best to use the variant `isp-full` and
go through the [Cozystack tutorial]({{% ref "/docs/next/getting-started" %}}).
