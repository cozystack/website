---
title: "Licenses"
linkTitle: "Licenses"
description: "Licenses of open-source components packaged with Cozystack."
weight: 35
---

This page lists the open-source components Cozystack ships, grouped by their role in the platform.
Cozystack-maintained charts, CRDs, controllers, and application APIs are licensed under **Apache-2.0** and are not listed individually below.
For each upstream component, the card links to the upstream license file.

{{% alert color="info" %}}
This reference is hand-curated against the current `next` set of components.
Container images can include additional operating-system packages and library dependencies with their own licenses.
Pinned upstream versions of managed runtimes (PostgreSQL, MariaDB, Kafka, etc.) may change between Cozystack minor releases — check the version of Cozystack you run.
{{% /alert %}}

## Operating system and Kubernetes runtime

{{< oss-cards >}}
{{< oss-card name="Talos Linux" logo="talos" license="MPL-2.0" source="https://github.com/siderolabs/talos/blob/main/LICENSE" description="Immutable Linux distribution built for Kubernetes nodes." >}}
{{< oss-card name="Kubernetes" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes/kubernetes/blob/master/LICENSE" description="Container orchestration kernel used for both the management cluster and tenant clusters." >}}
{{< oss-card name="Kamaji" logo="kamaji" license="Apache-2.0" source="https://github.com/clastix/kamaji/blob/master/LICENSE" description="Hosted control planes for tenant Kubernetes clusters." >}}
{{< oss-card name="Cluster API" logo="clusterapi" license="Apache-2.0" source="https://github.com/kubernetes-sigs/cluster-api/blob/main/LICENSE" description="Declarative provisioning of tenant Kubernetes clusters (core, operator, and Kamaji/KubeVirt providers)." >}}
{{< oss-card name="KubeVirt" logo="kubevirt" license="Apache-2.0" source="https://github.com/kubevirt/kubevirt/blob/main/LICENSE" description="Virtual machines as Kubernetes-native workloads (core, CDI, CSI, and instancetypes)." >}}
{{< /oss-cards >}}

## Networking

{{< oss-cards >}}
{{< oss-card name="Cilium" logo="cilium" license="Apache-2.0" source="https://github.com/cilium/cilium/blob/main/LICENSE" description="eBPF-based CNI for pod networking and NetworkPolicy." >}}
{{< oss-card name="Kube-OVN" logo="kubeovn" license="Apache-2.0" source="https://github.com/cozystack/kubeovn-chart/blob/main/LICENSE" description="OVN-based virtual networking, used for VPC and floating IPs." >}}
{{< oss-card name="Multus CNI" logo="multus" license="Apache-2.0" source="https://github.com/k8snetworkplumbingwg/multus-cni/blob/master/LICENSE" description="Multiple network interfaces per pod." >}}
{{< oss-card name="MetalLB" logo="metallb" license="Apache-2.0" source="https://github.com/metallb/metallb/blob/main/LICENSE" description="Bare-metal load balancer for Kubernetes Services." >}}
{{< oss-card name="ingress-nginx" logo="nginx" license="Apache-2.0" source="https://github.com/kubernetes/ingress-nginx/blob/main/LICENSE" description="HTTP ingress controller." >}}
{{< oss-card name="Gateway API CRDs" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-sigs/gateway-api/blob/main/LICENSE" description="Standard Kubernetes Gateway API definitions." >}}
{{< oss-card name="CoreDNS" logo="coredns" license="Apache-2.0" source="https://github.com/coredns/coredns/blob/master/LICENSE" description="Cluster DNS server." >}}
{{< oss-card name="ExternalDNS" logo="externaldns" license="Apache-2.0" source="https://github.com/kubernetes-sigs/external-dns/blob/master/LICENSE.md" description="Sync Kubernetes resources to external DNS providers." >}}
{{< oss-card name="Kilo" logo="kilo" license="Apache-2.0" source="https://github.com/squat/kilo/blob/main/LICENSE" description="Mesh networking across geographically distributed nodes." >}}
{{< oss-card name="Hetzner RobotLB" logo="hetzner" license="MIT" source="https://github.com/Intreecom/robotlb/blob/master/LICENSE" description="Load balancer integration for Hetzner dedicated hardware." >}}
{{< /oss-cards >}}

## Storage

{{< oss-cards >}}
{{< oss-card name="LINSTOR / Piraeus" logo="linstor" license="GPL-3.0; Apache-2.0" source="https://github.com/piraeusdatastore/piraeus-operator/blob/v2/LICENSE" description="DRBD-based replicated block storage (LINSTOR server, CSI, scheduler extender, GUI, Piraeus operator)." >}}
{{< oss-card name="SeaweedFS" logo="seaweedfs" license="Apache-2.0" source="https://github.com/seaweedfs/seaweedfs/blob/master/LICENSE" description="Distributed object storage; backs the managed Bucket service." >}}
{{< oss-card name="CSI Driver NFS" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-csi/csi-driver-nfs/blob/master/LICENSE" description="NFS CSI driver." >}}
{{< oss-card name="CSI Snapshot Controller" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-csi/external-snapshotter/blob/master/LICENSE" description="External snapshotter and VolumeSnapshot CRDs." >}}
{{< oss-card name="Velero" logo="velero" license="Apache-2.0" source="https://github.com/velero-io/velero/blob/main/LICENSE" description="Cluster and persistent volume backups." >}}
{{< oss-card name="Container Object Storage Interface" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-sigs/container-object-storage-interface/blob/main/LICENSE" description="COSI controller for managed object storage." >}}
{{< oss-card name="S3 Manager" license="Apache-2.0" source="https://github.com/cloudlena/s3manager/blob/main/LICENSE" description="Web UI for S3-compatible buckets." >}}
{{< /oss-cards >}}

## Observability

{{< oss-cards >}}
{{< oss-card name="VictoriaMetrics Operator" logo="victoriametrics" license="Apache-2.0" source="https://github.com/VictoriaMetrics/operator/blob/master/LICENSE" description="Metrics storage, ingestion, and Prometheus-compatible query layer." >}}
{{< oss-card name="Grafana Operator" logo="grafana" license="Apache-2.0" source="https://github.com/grafana/grafana-operator/blob/master/LICENSE" description="Manages Grafana instances, dashboards, and datasources." >}}
{{< oss-card name="Fluent Bit" logo="fluent-bit" license="Apache-2.0" source="https://github.com/fluent/fluent-bit/blob/master/LICENSE" description="Log forwarder running on every node." >}}
{{< oss-card name="kube-state-metrics" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes/kube-state-metrics/blob/main/LICENSE" description="Exposes Kubernetes object state as metrics." >}}
{{< oss-card name="node-exporter" logo="prometheus" license="Apache-2.0" source="https://github.com/prometheus/node_exporter/blob/master/LICENSE" description="System and hardware metrics from each node." >}}
{{< oss-card name="Prometheus Operator CRDs" logo="prometheus" license="Apache-2.0" source="https://github.com/prometheus-community/helm-charts/blob/main/LICENSE" description="CRDs for Prometheus-style monitoring resources, consumed by VictoriaMetrics." >}}
{{< oss-card name="Metrics Server" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-sigs/metrics-server/blob/master/LICENSE" description="Kubelet metrics for HPA and `kubectl top`." >}}
{{< oss-card name="Goldpinger" logo="goldpinger" license="Apache-2.0" source="https://github.com/bloomberg/goldpinger/blob/master/LICENSE" description="Pod-to-pod connectivity checks across the cluster." >}}
{{< /oss-cards >}}

## Autoscaling and resource management

{{< oss-cards >}}
{{< oss-card name="Vertical Pod Autoscaler" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes/autoscaler/blob/master/LICENSE" description="Vertical resource right-sizing for pods (chart: MIT)." >}}
{{< oss-card name="Cluster Autoscaler" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes/autoscaler/blob/master/LICENSE" description="Horizontal scaling of node pools." >}}
{{< oss-card name="Stakater Reloader" logo="reloader" license="Apache-2.0" source="https://github.com/stakater/Reloader/blob/master/LICENSE" description="Restarts pods when their ConfigMaps or Secrets change." >}}
{{< /oss-cards >}}

## GPU and accelerators

{{< oss-cards >}}
{{< oss-card name="NVIDIA GPU Operator" logo="nvidia" license="Apache-2.0" source="https://github.com/NVIDIA/gpu-operator/blob/main/LICENSE" description="Driver, container runtime, and device-plugin lifecycle for NVIDIA GPUs." >}}
{{< oss-card name="HAMi" logo="hami" license="Apache-2.0" source="https://github.com/Project-HAMi/HAMi/blob/master/LICENSE" description="GPU sharing and fractional GPU scheduling." >}}
{{< /oss-cards >}}

## GitOps and platform automation

{{< oss-cards >}}
{{< oss-card name="Flux" logo="fluxcd" license="Apache-2.0; AGPL-3.0" source="https://github.com/fluxcd/flux2/blob/main/LICENSE" description="GitOps engine. ControlPlane Flux Operator and instance chart are AGPL-3.0; upstream Flux controllers are Apache-2.0." >}}
{{< oss-card name="Aenix etcd Operator" logo="etcd" license="Apache-2.0" source="https://github.com/aenix-io/etcd-operator/blob/main/LICENSE" description="Manages etcd clusters used by tenant Kamaji control planes." >}}
{{< oss-card name="cert-manager" logo="cert-manager" license="Apache-2.0" source="https://github.com/cert-manager/cert-manager/blob/master/LICENSE" description="Automated TLS certificate issuance and rotation." >}}
{{< oss-card name="External Secrets Operator" logo="external-secrets" license="Apache-2.0" source="https://github.com/external-secrets/external-secrets/blob/main/LICENSE" description="Sync secrets from external KMS into Kubernetes." >}}
{{< oss-card name="SAP ClusterSecret Operator" logo="sap" license="Apache-2.0" source="https://github.com/SAP/clustersecret-operator/blob/main/LICENSE" description="Replicate secrets across namespaces." >}}
{{< oss-card name="Tinkerbell Smee" logo="tinkerbell" license="Apache-2.0" source="https://github.com/tinkerbell/smee/blob/main/LICENSE" description="iPXE / DHCP boot server for bare-metal provisioning." >}}
{{< oss-card name="Telepresence" logo="telepresence" license="Apache-2.0" source="https://github.com/telepresenceio/telepresence/blob/release/v2/LICENSE" description="Local development against a remote cluster (Traffic Manager)." >}}
{{< /oss-cards >}}

## Identity, registry, and admin UI

{{< oss-cards >}}
{{< oss-card name="Keycloak" logo="keycloak" license="Apache-2.0" source="https://github.com/keycloak/keycloak/blob/main/LICENSE.txt" description="OIDC provider for platform and tenant SSO; deployed with the KubeRocketCI Keycloak Operator." >}}
{{< oss-card name="Harbor" logo="harbor" license="Apache-2.0" source="https://github.com/goharbor/harbor/blob/main/LICENSE" description="OCI registry for container images and Helm charts." >}}
{{< /oss-cards >}}

## Managed database runtimes

{{< oss-cards >}}
{{< oss-card name="PostgreSQL" logo="postgresql" license="PostgreSQL License" source="https://www.postgresql.org/about/licence/" description="Managed via CloudNativePG operator (Apache-2.0)." >}}
{{< oss-card name="MariaDB Server" logo="mariadb" license="GPL-2.0" source="https://github.com/MariaDB/server/blob/main/COPYING" description="Managed via mariadb-operator (MIT)." >}}
{{< oss-card name="MongoDB (Percona Server)" logo="mongodb" license="SSPL-1.0" source="https://github.com/percona/percona-server-mongodb/blob/master/LICENSE-Community.txt" description="Managed via Percona Operator for MongoDB (Apache-2.0)." >}}
{{< oss-card name="ClickHouse" logo="clickhouse" license="Apache-2.0" source="https://github.com/ClickHouse/ClickHouse/blob/master/LICENSE" description="Server and Keeper, managed via Altinity ClickHouse Operator (Apache-2.0)." >}}
{{< oss-card name="OpenSearch" logo="opensearch" license="Apache-2.0" source="https://github.com/opensearch-project/OpenSearch/blob/main/LICENSE.txt" description="Managed via opensearch-k8s-operator (Apache-2.0)." >}}
{{< oss-card name="Qdrant" logo="qdrant" license="Apache-2.0" source="https://github.com/qdrant/qdrant/blob/master/LICENSE" description="Vector database, deployed via the upstream Qdrant Helm chart." >}}
{{< oss-card name="FoundationDB" logo="foundationdb" license="Apache-2.0" source="https://github.com/apple/foundationdb/blob/main/LICENSE" description="Managed via FoundationDB Kubernetes Operator (Apache-2.0)." >}}
{{< oss-card name="Redis" logo="redis" license="RSALv2 or SSPLv1 (7.x) / AGPLv3 (8.x)" source="https://redis.io/legal/licenses/" description="Managed via Spotahome Redis Operator (Apache-2.0). Cozystack supports Redis 7.4 and Redis 8." >}}
{{< /oss-cards >}}

## Managed messaging and caching runtimes

{{< oss-cards >}}
{{< oss-card name="Apache Kafka" logo="kafka" license="Apache-2.0" source="https://github.com/apache/kafka/blob/trunk/LICENSE" description="Managed via Strimzi Kafka Operator (Apache-2.0)." >}}
{{< oss-card name="NATS" logo="nats" license="Apache-2.0" source="https://github.com/nats-io/nats-server/blob/main/LICENSE" description="Lightweight messaging server, deployed via the upstream NATS Helm chart." >}}
{{< oss-card name="RabbitMQ" logo="rabbitmq" license="MPL-2.0; Apache-2.0 for some files" source="https://github.com/rabbitmq/rabbitmq-server/blob/main/LICENSE" description="Managed via RabbitMQ Cluster Operator (MPL-2.0)." >}}
{{< oss-card name="OpenBao" logo="openbao" license="MPL-2.0" source="https://github.com/openbao/openbao/blob/main/LICENSE" description="Secrets management fork of HashiCorp Vault, deployed via the upstream OpenBao Helm chart." >}}
{{< /oss-cards >}}

## Managed networking services

{{< oss-cards >}}
{{< oss-card name="NGINX" logo="nginx" license="BSD-2-Clause" source="https://github.com/nginx/nginx/blob/master/LICENSE" description="Used by the managed HTTP Cache service." >}}
{{< oss-card name="HAProxy" logo="haproxy" license="GPL-2.0 with exceptions" source="https://github.com/haproxy/haproxy/blob/master/LICENSE" description="Used by the managed TCP Balancer and HTTP Cache services." >}}
{{< oss-card name="IP2Location modules" license="MIT" source="https://github.com/ip2location/ip2location-nginx/blob/master/LICENSE" description="GeoIP modules bundled into the HTTP Cache (IP2Location and IP2Proxy)." >}}
{{< oss-card name="Outline Server (Shadowsocks)" logo="outline" license="Apache-2.0" source="https://github.com/OutlineFoundation/outline-server/blob/master/LICENSE" description="Backs the managed VPN service." >}}
{{< /oss-cards >}}
