---
title: "Cozystack Platform Stack"
linkTitle: "Platform Stack"
description: "All open-source components in the Cozystack platform stack: networking, storage, observability, databases, and managed services with licenses and technical descriptions."
weight: 15
---

Cozystack is composed entirely of open-source components, layered from the operating system up to user-facing managed services.
This page describes each component, its role in the platform, and its upstream license.

## Overview

![Cozystack Architecture Layers](cozystack-layers.png)

Components are organized by their role in the platform stack.
Cozystack-maintained charts, CRDs, controllers, and application APIs are licensed under **Apache-2.0** and are not listed individually below.

## Operating system and Kubernetes runtime

{{< oss-cards >}}
{{< oss-card name="Talos Linux" logo="talos" license="MPL-2.0" source="https://github.com/siderolabs/talos/blob/main/LICENSE" description="Immutable Linux distribution built for Kubernetes nodes. Removes shell, SSH, and mutable filesystem layers to minimize the attack surface." >}}
{{< oss-card name="Kubernetes" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes/kubernetes/blob/master/LICENSE" description="Container orchestration platform managing all Cozystack workloads. Both the management cluster and tenant clusters run on Kubernetes." >}}
{{< /oss-cards >}}

## Cluster provisioning and virtualization

{{< oss-cards >}}
{{< oss-card name="Kamaji" logo="kamaji" license="Apache-2.0" source="https://github.com/clastix/kamaji/blob/master/LICENSE" description="Deploys tenant Kubernetes control planes as pods in the management cluster. Enables multi-tenancy without dedicated control-plane VMs." >}}
{{< oss-card name="Cluster API" logo="clusterapi" license="Apache-2.0" source="https://github.com/kubernetes-sigs/cluster-api/blob/main/LICENSE" description="Declarative cluster lifecycle management via Kamaji and KubeVirt providers. Enables consistent, reproducible tenant cluster provisioning and upgrades." >}}
{{< oss-card name="KubeVirt" logo="kubevirt" license="Apache-2.0" source="https://github.com/kubevirt/kubevirt/blob/main/LICENSE" description="Virtual machine management as native Kubernetes workloads. Powers Cozystack's VM service and tenant cluster worker nodes via CDI disk management." >}}
{{< /oss-cards >}}

## Networking

{{< oss-cards >}}
{{< oss-card name="Cilium" logo="cilium" license="Apache-2.0" source="https://github.com/cilium/cilium/blob/main/LICENSE" description="eBPF-based CNI for pod networking and NetworkPolicy enforcement. Works alongside Kube-OVN for high-throughput, low-latency packet processing." >}}
{{< oss-card name="Kube-OVN" logo="kubeovn" license="Apache-2.0" source="https://github.com/cozystack/kubeovn-chart/blob/main/LICENSE" description="OVN-based virtual networking providing VPC isolation, floating IPs, and tenant network segmentation. Built on Open vSwitch technology." >}}
{{< oss-card name="Multus CNI" logo="multus" license="Apache-2.0" source="https://github.com/k8snetworkplumbingwg/multus-cni/blob/master/LICENSE" description="Meta-CNI enabling pods to attach multiple network interfaces simultaneously. Used to connect KubeVirt VMs to secondary physical or VLAN-backed interfaces." >}}
{{< oss-card name="MetalLB" logo="metallb" license="Apache-2.0" source="https://github.com/metallb/metallb/blob/main/LICENSE" description="Bare-metal load balancer assigning external IPs to Kubernetes Services via ARP/NDP or BGP. Default load balancer for all platform and tenant services." >}}
{{< oss-card name="ingress-nginx" logo="nginx" license="Apache-2.0" source="https://github.com/kubernetes/ingress-nginx/blob/main/LICENSE" description="NGINX-based ingress controller for HTTP/HTTPS routing with TLS termination. Deployed as the default ingress controller across management and tenant clusters." >}}
{{< oss-card name="Gateway API CRDs" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-sigs/gateway-api/blob/main/LICENSE" description="Standard Kubernetes Gateway API CRDs for role-oriented L4/L7 routing. Enables modern traffic management with compatible gateway controllers." >}}
{{< oss-card name="CoreDNS" logo="coredns" license="Apache-2.0" source="https://github.com/coredns/coredns/blob/master/LICENSE" description="Cluster DNS server for service discovery and internal name resolution. Resolves cluster.local service names for all pod-to-service lookups." >}}
{{< oss-card name="ExternalDNS" logo="externaldns" license="Apache-2.0" source="https://github.com/kubernetes-sigs/external-dns/blob/master/LICENSE.md" description="Syncs Kubernetes Service and Ingress resources to external DNS providers automatically. Eliminates manual DNS record management for platform and tenant endpoints." >}}
{{< oss-card name="Kilo" logo="kilo" license="Apache-2.0" source="https://github.com/squat/kilo/blob/main/LICENSE" description="WireGuard-based mesh networking for clusters spanning multiple geographic locations. Creates encrypted tunnels for seamless cross-site pod-to-pod communication." >}}
{{< oss-card name="Hetzner RobotLB" logo="hetzner" license="MIT" source="https://github.com/Intreecom/robotlb/blob/master/LICENSE" description="Load balancer controller for Hetzner dedicated hardware via the Robot API. Enables LoadBalancer-type Services on Hetzner bare-metal without Hetzner Cloud." >}}
{{< /oss-cards >}}

## Storage and backup

{{< oss-cards >}}
{{< oss-card name="LINSTOR / Piraeus" logo="linstor" license="GPL-3.0; Apache-2.0" source="https://github.com/piraeusdatastore/piraeus-operator/blob/v2/LICENSE" description="DRBD-based replicated block storage managed by LINSTOR. Provisions persistent volumes with synchronous replication for VM disks and databases." >}}
{{< oss-card name="SeaweedFS" logo="seaweedfs" license="Apache-2.0" source="https://github.com/seaweedfs/seaweedfs/blob/master/LICENSE" description="Distributed object storage backing the managed Bucket service. S3-compatible with O(1) disk read performance and no clustered filesystem dependency." >}}
{{< oss-card name="Velero" logo="velero" license="Apache-2.0" source="https://github.com/velero-io/velero/blob/main/LICENSE" description="Backup and restore for Kubernetes clusters and persistent volumes. Stores backups in S3-compatible object storage for off-cluster retention." >}}
{{< oss-card name="CSI Driver NFS" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-csi/csi-driver-nfs/blob/master/LICENSE" description="CSI driver for mounting NFS shares as persistent volumes. Supports ReadWriteMany access mode required for multi-pod shared storage scenarios." >}}
{{< oss-card name="CSI Snapshot Controller" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-csi/external-snapshotter/blob/master/LICENSE" description="Manages the VolumeSnapshot lifecycle across all CSI drivers. Provides a consistent API for point-in-time storage snapshots and clone workflows." >}}
{{< oss-card name="Container Object Storage Interface" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-sigs/container-object-storage-interface/blob/main/LICENSE" description="Kubernetes-native API for provisioning S3-compatible object storage buckets. Used to provision SeaweedFS buckets for the managed Bucket service." >}}
{{< oss-card name="S3 Manager" license="Apache-2.0" source="https://github.com/cloudlena/s3manager/blob/main/LICENSE" description="Lightweight web UI for S3-compatible object storage. Bundled with the managed Bucket service for bucket browsing and file management." >}}
{{< /oss-cards >}}

## GitOps and platform automation

{{< oss-cards >}}
{{< oss-card name="Flux" logo="fluxcd" license="Apache-2.0; AGPL-3.0" source="https://github.com/fluxcd/flux2/blob/main/LICENSE" description="GitOps engine reconciling cluster state from Helm releases and Kustomizations. ControlPlane Flux Operator is AGPL-3.0; upstream controllers are Apache-2.0." >}}
{{< oss-card name="Aenix etcd Operator" logo="etcd" license="Apache-2.0" source="https://github.com/aenix-io/etcd-operator/blob/main/LICENSE" description="Manages dedicated etcd clusters for tenant Kubernetes control planes. Handles member lifecycle, scaling, and backup-restore as Kubernetes reconciliation loops." >}}
{{< oss-card name="cert-manager" logo="cert-manager" license="Apache-2.0" source="https://github.com/cert-manager/cert-manager/blob/master/LICENSE" description="Automates TLS certificate issuance, renewal, and rotation. Integrates with ACME, internal PKI (OpenBao), and self-signed issuers." >}}
{{< oss-card name="External Secrets Operator" logo="external-secrets" license="Apache-2.0" source="https://github.com/external-secrets/external-secrets/blob/main/LICENSE" description="Syncs secrets from external KMS (Vault, OpenBao, AWS, GCP) into Kubernetes Secrets. Enables GitOps secret management without storing values in Git." >}}
{{< oss-card name="SAP ClusterSecret Operator" logo="sap" license="Apache-2.0" source="https://github.com/SAP/clustersecret-operator/blob/main/LICENSE" description="Replicates Kubernetes Secrets across namespaces, keeping copies in sync. Used to propagate platform-level credentials to tenant namespaces." >}}
{{< oss-card name="Stakater Reloader" logo="reloader" license="Apache-2.0" source="https://github.com/stakater/Reloader/blob/master/LICENSE" description="Triggers rolling restarts when ConfigMaps or Secrets change. Ensures Deployments and StatefulSets pick up configuration updates without manual intervention." >}}
{{< oss-card name="Tinkerbell Smee" logo="tinkerbell" license="Apache-2.0" source="https://github.com/tinkerbell/smee/blob/main/LICENSE" description="iPXE boot and DHCP server for bare-metal node provisioning. Serves boot scripts enabling automated Talos Linux deployment on physical hardware." >}}
{{< oss-card name="Telepresence" logo="telepresence" license="Apache-2.0" source="https://github.com/telepresenceio/telepresence/blob/release/v2/LICENSE" description="Proxies traffic between a local dev machine and a remote Kubernetes cluster. Enables local debugging while accessing live remote cluster services." >}}
{{< /oss-cards >}}

## Observability

{{< oss-cards >}}
{{< oss-card name="VictoriaMetrics Operator" logo="victoriametrics" license="Apache-2.0" source="https://github.com/VictoriaMetrics/operator/blob/master/LICENSE" description="Prometheus-compatible metrics storage and query engine. More memory-efficient than Prometheus at scale; exposes a PromQL-compatible API for Grafana." >}}
{{< oss-card name="Grafana Operator" logo="grafana" license="Apache-2.0" source="https://github.com/grafana/grafana-operator/blob/master/LICENSE" description="Manages Grafana instances, dashboards, and data sources as Kubernetes CRDs. Provides a unified observability UI for platform operators and tenants." >}}
{{< oss-card name="Fluent Bit" logo="fluent-bit" license="Apache-2.0" source="https://github.com/fluent/fluent-bit/blob/master/LICENSE" description="Lightweight log forwarder running as a DaemonSet on every node. Collects platform and tenant workload logs with minimal CPU and memory overhead." >}}
{{< oss-card name="kube-state-metrics" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes/kube-state-metrics/blob/main/LICENSE" description="Generates Prometheus-format metrics about Kubernetes object state (deployments, pods, nodes, PVCs). Feeds cluster health data into VictoriaMetrics." >}}
{{< oss-card name="node-exporter" logo="prometheus" license="Apache-2.0" source="https://github.com/prometheus/node_exporter/blob/master/LICENSE" description="Exports system and hardware metrics (CPU, memory, disk, network) from each node as a DaemonSet. Feeds host telemetry into VictoriaMetrics." >}}
{{< oss-card name="Prometheus Operator CRDs" logo="prometheus" license="Apache-2.0" source="https://github.com/prometheus-community/helm-charts/blob/main/LICENSE" description="CRDs for ServiceMonitor, PodMonitor, and PrometheusRule resources consumed by VictoriaMetrics. Provides a vendor-neutral monitoring target API." >}}
{{< oss-card name="Metrics Server" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes-sigs/metrics-server/blob/master/LICENSE" description="Provides the Resource Metrics API for HPA and kubectl top. Aggregates kubelet-reported CPU and memory usage across cluster nodes." >}}
{{< oss-card name="Goldpinger" logo="goldpinger" license="Apache-2.0" source="https://github.com/bloomberg/goldpinger/blob/master/LICENSE" description="Pod-to-pod connectivity checker deployed as a DaemonSet. Surfaces node-to-node network partition failures with metrics and a real-time visualization UI." >}}
{{< /oss-cards >}}

## Autoscaling and resource management

{{< oss-cards >}}
{{< oss-card name="Vertical Pod Autoscaler" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes/autoscaler/blob/master/LICENSE" description="Automatically right-sizes CPU and memory requests for pods based on observed usage. Eliminates manual resource tuning for platform and tenant workloads (chart: MIT)." >}}
{{< oss-card name="Cluster Autoscaler" logo="kubernetes" license="Apache-2.0" source="https://github.com/kubernetes/autoscaler/blob/master/LICENSE" description="Scales node pools based on pending pods or underutilized nodes. Enables cost-efficient elastic scaling of tenant Kubernetes clusters." >}}
{{< /oss-cards >}}

## GPU and accelerators

{{< oss-cards >}}
{{< oss-card name="NVIDIA GPU Operator" logo="nvidia" license="Apache-2.0" source="https://github.com/NVIDIA/gpu-operator/blob/main/LICENSE" description="Manages the full lifecycle of NVIDIA GPU drivers, device plugins, and runtimes on Kubernetes nodes. Enables AI/ML and LLM inference workloads without per-node manual setup." >}}
{{< oss-card name="HAMi" logo="hami" license="Apache-2.0" source="https://github.com/Project-HAMi/HAMi/blob/master/LICENSE" description="GPU sharing and fractional scheduling for Kubernetes. Allows multiple workloads to share a single GPU, maximizing utilization for LLM inference platforms." >}}
{{< /oss-cards >}}

## Identity, registry, and secrets

{{< oss-cards >}}
{{< oss-card name="Keycloak" logo="keycloak" license="Apache-2.0" source="https://github.com/keycloak/keycloak/blob/main/LICENSE.txt" description="OIDC and SAML identity provider for platform SSO. Secures the platform API, Grafana, Harbor, and tenant services with role-based access control." >}}
{{< oss-card name="Harbor" logo="harbor" license="Apache-2.0" source="https://github.com/goharbor/harbor/blob/main/LICENSE" description="CNCF-graduated OCI registry for container images and Helm charts. Provides RBAC, vulnerability scanning, content trust signing, and registry replication." >}}
{{< oss-card name="OpenBao" logo="openbao" license="MPL-2.0" source="https://github.com/openbao/openbao/blob/main/LICENSE" description="Open-source Vault fork for dynamic secrets, PKI management, and encrypted secret storage. Supports Kubernetes and OIDC authentication backends." >}}
{{< /oss-cards >}}

## Managed database runtimes

{{< oss-cards >}}
{{< oss-card name="PostgreSQL" logo="postgresql" license="PostgreSQL License" source="https://www.postgresql.org/about/licence/" description="Replicated relational database managed via CloudNativePG. Features automated failover, Barman-based backup scheduling, and connection pooling." >}}
{{< oss-card name="MariaDB Server" logo="mariadb" license="GPL-2.0" source="https://github.com/MariaDB/server/blob/main/COPYING" description="MySQL-compatible replicated database managed via mariadb-operator. Supports Galera multi-primary replication and Restic-based backup scheduling." >}}
{{< oss-card name="MongoDB (Percona Server)" logo="mongodb" license="SSPL-1.0" source="https://github.com/percona/percona-server-mongodb/blob/master/LICENSE-Community.txt" description="Document-oriented NoSQL database deployed via Percona Operator. Supports replica sets, sharded clusters, and automated Percona backup." >}}
{{< oss-card name="ClickHouse" logo="clickhouse" license="Apache-2.0" source="https://github.com/ClickHouse/ClickHouse/blob/master/LICENSE" description="Column-oriented DBMS optimized for real-time analytics. Deployed via Altinity ClickHouse Operator with multi-shard distributed clusters." >}}
{{< oss-card name="OpenSearch" logo="opensearch" license="Apache-2.0" source="https://github.com/opensearch-project/OpenSearch/blob/main/LICENSE.txt" description="Search and analytics engine managed via opensearch-k8s-operator. Full-text search, log aggregation, and Elasticsearch-compatible query API." >}}
{{< oss-card name="Qdrant" logo="qdrant" license="Apache-2.0" source="https://github.com/qdrant/qdrant/blob/master/LICENSE" description="High-performance vector database for similarity search and AI workloads. Supports dense and sparse vector embeddings for recommendation and semantic search." >}}
{{< oss-card name="FoundationDB" logo="foundationdb" license="Apache-2.0" source="https://github.com/apple/foundationdb/blob/main/LICENSE" description="Distributed database with strong ACID guarantees across the cluster, managed via FoundationDB Kubernetes Operator. Designed for extreme reliability at scale." >}}
{{< oss-card name="Redis" logo="redis" license="RSALv2 or SSPLv1 (7.x) / AGPLv3 (8.x)" source="https://redis.io/legal/licenses/" description="In-memory key-value store deployed as a replicated Sentinel cluster via Spotahome Redis Operator. Supports Redis 7.4 and Redis 8 for caching and pub/sub." >}}
{{< /oss-cards >}}

## Managed messaging and caching runtimes

{{< oss-cards >}}
{{< oss-card name="Apache Kafka" logo="kafka" license="Apache-2.0" source="https://github.com/apache/kafka/blob/trunk/LICENSE" description="Distributed event streaming platform managed via Strimzi Kafka Operator. Multi-broker clusters with configurable replication for event-driven architectures." >}}
{{< oss-card name="NATS" logo="nats" license="Apache-2.0" source="https://github.com/nats-io/nats-server/blob/main/LICENSE" description="Lightweight pub-sub and request-reply messaging deployed via the official Helm chart. Low-latency, minimal-overhead messaging for microservices and IoT." >}}
{{< oss-card name="RabbitMQ" logo="rabbitmq" license="MPL-2.0; Apache-2.0 for some files" source="https://github.com/rabbitmq/rabbitmq-server/blob/main/LICENSE" description="AMQP message broker managed via RabbitMQ Cluster Operator. Highly available clusters with quorum queues and fanout, topic, and direct exchange routing." >}}
{{< /oss-cards >}}

## Managed networking services

{{< oss-cards >}}
{{< oss-card name="NGINX" logo="nginx" license="BSD-2-Clause" source="https://github.com/nginx/nginx/blob/master/LICENSE" description="Powers the managed HTTP Cache service with reverse-proxy caching and GeoIP filtering. Scales horizontally without a shared filesystem." >}}
{{< oss-card name="HAProxy" logo="haproxy" license="GPL-2.0 with exceptions" source="https://github.com/haproxy/haproxy/blob/master/LICENSE" description="Enterprise TCP/HTTP load balancer powering the managed TCP Balancer and HTTP Cache. Provides active health checks and high-throughput connection handling." >}}
{{< oss-card name="IP2Location modules" license="MIT" source="https://github.com/ip2location/ip2location-nginx/blob/master/LICENSE" description="GeoIP modules (IP2Location and IP2Proxy) bundled into the HTTP Cache. Enables country-based traffic filtering and proxy/VPN detection." >}}
{{< oss-card name="Outline Server (Shadowsocks)" logo="outline" license="Apache-2.0" source="https://github.com/OutlineFoundation/outline-server/blob/master/LICENSE" description="Shadowsocks-based VPN backend developed by Google's Jigsaw team. Manages Shadowsocks instances with symmetric encryption to resist DPI traffic analysis." >}}
{{< /oss-cards >}}
