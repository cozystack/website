---
title: "Cozystack Architecture and Platform Stack"
linkTitle: "Platform Stack"
description: "Learn of the core components that power the functionality and flexibility of Cozystack"
weight: 15
---

This article explains Cozystack composition through its four layers, and shows the role and value of each component in the platform stack.

## Overview

To understand Cozystack composition, it's helpful to view it as sub-systems, layered from hardware to user-facing:

![Cozystack Architecture Layers](cozystack-layers.png)

## Layer 1: OS and Hardware

This is a foundation layer, providing cluster functionality on bare metal.
It consists of Talos Linux and a Kubernetes cluster installed on Talos.

### Talos Linux
                                       
Talos Linux is a Linux distribution made and optimized for a single purpose: to run Kubernetes.
It provides the foundation for reliability and security in a Cozystack cluster.
Its use allows Cozystack to limit the technology stack, improving stability and security.

Read more about it in the [Talos Linux]({{%ref "/docs/guides/talos" %}}) section.

### Kubernetes

Kubernetes has already become a kind of de facto standard for managing server workloads.

One of the key features of Kubernetes is a convenient and unified API that is understandable to everyone (everything is YAML). Also, the best software design patterns that provide continuous recovery in any situation (reconciliation method) and efficient scaling to a large number of servers.

This fully solves the integration problem, since all existing virtualization platforms have an outdated and rather complex APIs that cannot be extended without modifying the source code. As a result, there is always a need to create your own custom solutions, which requires additional effort.

## Layer 2: Infrastructure Services

Second layer contains the key components which perform major roles such as storage, networking, and virtualization.
Adding these components to the base Kubernetes cluster makes it much more functional.

### Flux CD

FluxCD provides a simple and uniform interface for both installing all platform components and managing their lifecycle.
Cozystack developers have adopted FluxCD as the core element of the platform, believing it sets a new industry standard for platform engineering. 

### KubeVirt

KubeVirt brings virtualization capability to Cozystack.
It enables creating virtual machines and worker nodes for tenant Kubernetes clusters.

KubeVirt is a project started by global industry leaders with a common vision to unify Kubernetes and a desire to introduce it to the world of virtualization.
It extends the capabilities of Kubernetes by providing convenient abstractions for launching and managing virtual machines,
as well the all related entities such as snapshots, presets, virtual volumes, and more.

At the moment, the KubeVirt project is being jointly developed by such world-famous companies as RedHat, NVIDIA, ARM.

### DRBD and LINSTOR

DRBD and LINSTOR are the foundation of replicated storage in Cozystack.

DRBD is the fastest replication block storage running right in the Linux kernel.
When DRBD only deals with data replication, time-tested technologies such as LVM or ZFS are used to securely store the data.
The DRBD kernel module is included in the mainline Linux kernel and has been used to build fault-tolerant systems for over a decade.

DRBD is managed using LINSTOR, a system integrated with Kubernetes.
LINSTOR is a management layer for creating virtual volumes based on DRBD.
It enables managing hundreds or thousands of virtual volumes in the Cozystack cluster.

### Kube-OVN

The networking functionality in Cozystack is based on Kube-OVN and Cilium.

OVN is a free implementation of virtual network fabric for Kubernetes and OpenStack based on the Open vSwitch technology.
With Kube-OVN, you get a robust and functional virtual network that ensures reliable isolation between tenants and provides floating addresses for virtual machines.

In the future, this will enable seamless integration with other clusters and customer network services.

### Cilium

Utilizing Cilium in conjunction with OVN enables the most efficient and flexible network policies,
along with a productive services network in Kubernetes, leveraging an offloaded Linux network stack featuring the cutting-edge eBPF technology.

Cilium is a highly promising project, widely adopted and supported by numerous cloud providers worldwide.

## Layer 3: Platform Services

These are components that provide the user-side functionality to Cozystack and its managed applications.

### Kamaji

Cozystack uses Kamaji Control Plane to deploy tenant Kubernetes clusters.
Kamaji provides a straightforward and convenient method for launching all the necessary Kubernetes control-plane in containers.
Worker nodes are then connected to these control planes and handle user workloads.

The approach developed by the Kamaji project is modeled after the design of modern clouds and ensures security by design
where end users do not have any control plane nodes for their clusters.

### Grafana

Grafana with Grafana Loki and the OnCall extension provides a single interface to Observability.
It allows you to conveniently view charts, logs and manage alerts for your infrastructure and applications.

### Victoria Metrics

Victoria Metrics allows you to most efficiently collect, store and process metrics in the Open Metrics format,
doing it more efficiently than Prometheus in the same setup.

### MetalLB

MetalLB is the default load balancer for Kubernetes;
with its help, your services can obtain public addresses that are accessible not only from inside,
but also from outside your cluster network.

### HAProxy

HAProxy is an advanced and widely known TCP balancer.
It continuously checks service availability and carefully balances production traffic between them in real time.

See the application reference: [TCP Balancer]({{% ref "/docs/networking/tcp-balancer" %}})

### SeaweedFS

SeaweedFS is a simple and highly scalable distributed file system designed for two main objectives:
to store billions of files and to serve the files faster. It allows access O(1), usually just one disk read operation.

### Kubernetes Operators

Cozystack includes a set of Kubernetes operators, used for managing system services and managed applications.

## Layer 4: User-side services

Cozystack is shipped with a number of user-side applications, pre-configured for reliability and resource efficiency,
coming with monitoring and observability included:

-   [Tenant Kubernetes clusters]({{% ref "/docs/kubernetes" %}}), fully-functional managed Kubernetes clusters for development and production workloads.
-   [Managed applications]({{% ref "/docs/applications" %}}), such as databases and queues.
-   [Virtual machines]({{% ref "/docs/virtualization" %}}), supporting Linux and Windows OS.
-   [Networking appliances]({{% ref "/docs/networking" %}}), including VPN, HTTP cache, TCP load balancer, and virtual routers.

### Managed Kubernetes

Cozystack deploys and manages tenant Kubernetes clusters as standalone applications within each tenant’s isolated environment.
These clusters are fully separate from the root management cluster and are intended for deploying tenant-specific or customer-developed applications.

Deployment involves the following components:

-   **Kamaji Control Plane**: [Kamaji](https://kamaji.clastix.io/) is an open-source project that facilitates the deployment
    of Kubernetes control planes as pods within a root cluster.
    Each control plane pod includes essential components like `kube-apiserver`, `controller-manager`, and `scheduler`,
    allowing for efficient multi-tenancy and resource utilization.

-   **Etcd Cluster**: A dedicated etcd cluster is deployed using Ænix's [aenix-io/etcd-operator](https://github.com/aenix-io/etcd-operator).
    It provides reliable and scalable key-value storage for the Kubernetes control plane.

-   **Worker Nodes**: Virtual Machines are provisioned to serve as worker nodes.
    These nodes are configured to join the tenant Kubernetes cluster, enabling the deployment and management of workloads.

This architecture ensures isolated, scalable, and efficient Kubernetes environments tailored for each tenant.

-   Supported version: Kubernetes v1.32.4
-   Operator: [aenix-io/etcd-operator](https://github.com/aenix-io/etcd-operator) v0.4.2
-   Managed application reference: [Kubernetes]({{% ref "/docs/kubernetes" %}})


### Virtual Machines

In Cozystack, virtualization features are powered by [KubeVirt]({{% ref "/docs/guides/platform-stack#kubevirt" %}}).
Cozystack has a number of applications providing virtualization functionality:

-   [Simple virtual machine]({{% ref "/docs/virtualization/virtual-machine" %}}).
-   [Virtual machine instance]({{% ref "/docs/virtualization/vm-instance" %}}) with more advanced configuration.
-   [Virtual machine disk]({{% ref "/docs/virtualization/vm-disk" %}}), offering a choice of image sources.
-   [VM image (Golden Disk)]({{% ref "/docs/virtualization/vm-image" %}}), which makes OS images locally available, improving VM creation time and saving network traffic.


### ClickHouse

ClickHouse is an open source high-performance and column-oriented SQL database management system (DBMS).
It is used for online analytical processing (OLAP).
In the Cozystack platform, we use the Altinity operator to provide ClickHouse.

-   Supported version: 24.9.2.42
-   Kubernetes operator: [Altinity/clickhouse-operator](https://github.com/Altinity/clickhouse-operator) v0.25.0
-   Website: [clickhouse.com](https://clickhouse.com/)
-   Managed application reference: [ClickHouse]({{% ref "/docs/applications/clickhouse" %}})


### FerretDB

FerretDB is an open source MongoDB alternative.
It translates MongoDB wire protocol queries to SQL and can be used as a direct replacement for MongoDB 5.0+.
In Cozystack, it is backed by PostgreSQL.

-   Supported version: FerretDB 1.24.0.
-   Website: [ferretdb.io](https://www.ferretdb.io/)
-   Managed application reference: [FerretDB]({{% ref "/docs/applications/ferretdb" %}})


### Kafka

Apache Kafka is an open-source distributed event streaming platform.
It aims to provide a unified, high-throughput, low-latency platform for handling real-time data feeds.
Cozystack is using [Strimzi](https://github.com/cozystack/cozystack/blob/main/packages/system/kafka-operator/charts/strimzi-kafka-operator/README.md)
to run an Apache Kafka cluster on Kubernetes in various deployment configurations.

-   Supported version: Apache Kafka 3.9.0
-   Kubernetes operator: [strimzi/strimzi-kafka-operator](https://github.com/strimzi/strimzi-kafka-operator) v0.45.0
-   Website: [kafka.apache.org](https://kafka.apache.org/)
-   Managed application reference: [Kafka]({{% ref "/docs/applications/kafka" %}})


### MySQL (MariaDB)

MySQL is a widely used and well-known relational database.
The implementation in the platform provides the ability to create a replicated MariaDB cluster.
This cluster is managed using the increasingly popular mariadb-operator.

For each database, there is an interface for configuring users, their permissions,
as well as schedules for creating backups using [Restic](https://restic.net/), one of the most efficient tools currently available.

-   Supported version: MariaDB 11.4.3
-   Kubernetes operator: [mariadb-operator/mariadb-operator](https://github.com/mariadb-operator/mariadb-operator) v0.18.0
-   Website: [mariadb.com](https://mariadb.com/)
-   Managed application reference: [MySQL]({{% ref "/docs/applications/mysql" %}})


### NATS Messaging

NATS is an open-source, simple, secure, and high performance messaging system.
It provides a data layer for cloud native applications, IoT messaging, and microservices architectures.

-   Supported version: NATS 2.10.17
-   Website: [nats.io](https://nats.io/)
-   Managed application reference: [NATS]({{% ref "/docs/applications/nats" %}})


### PostgreSQL

Nowadays, PostgreSQL is the most popular relational database.
Its platform-side implementation involves a self-healing replicated cluster.
This is managed with the increasingly popular CloudNativePG operator within the community.


-   Supported version: PostgreSQL 17
-   Kubernetes operator: [cloudnative-pg/cloudnative-pg](https://github.com/cloudnative-pg/cloudnative-pg) v1.24.0
-   Website: [cloudnative-pg.io](https://cloudnative-pg.io/)
-   Managed application reference: [PostgreSQL]({{% ref "/docs/applications/postgres" %}})


### RabbitMQ

RabbitMQ is a widely known message broker.
The platform-side implementation allows you to create failover clusters managed by the official RabbitMQ operator.

-   Supported version: RabbitMQ 4.1.0+ (latest stable version)
-   Kubernetes operator: [rabbitmq/cluster-operator](https://github.com/rabbitmq/cluster-operator) v1.10.0
-   Website: [rabbitmq.com](https://www.rabbitmq.com/)
-   Managed application reference: [RabbitMQ]({{% ref "/docs/applications/rabbitmq" %}})


### Redis

Redis is the most commonly used key-value in-memory data store.
It is most often used as a cache, as storage for user sessions, or as a message broker.
The platform-side implementation involves a replicated failover Redis cluster with Sentinel.
This is managed by the spotahome/redis-operator.

-   Supported version: Redis 6.2.6+ (based on `alpine`)
-   Kubernetes operator: [spotahome/redis-operator](https://github.com/spotahome/redis-operator) v1.3.0-rc1
-   Website: [redis.io](https://redis.io/)
-   Managed application reference: [Redis]({{% ref "/docs/applications/redis" %}})


### VPN Service

The VPN Service is powered by the Outline Server, an advanced and user-friendly VPN solution.
It is internally known as "Shadowbox," which simplifies the process of setting up and sharing Shadowsocks servers.
It operates by launching Shadowsocks instances on demand.

The Shadowsocks protocol uses symmetric encryption algorithms.
This enables fast internet access while complicating traffic analysis and blocking through DPI (Deep Packet Inspection).

-   Supported version: Outline Server, v1.12.3+ (stable)
-   Website: [getoutline.org](https://getoutline.org/)
-   Managed application reference: [VPN]({{% ref "/docs/networking/vpn" %}})

### HTTP Cache

Nginx-based HTTP caching service helps protect your application from overload using the powerful Nginx.
Nginx is traditionally used to build CDNs and caching servers.

The platform-side implementation features efficient caching without using a clustered file system.
It also supports horizontal scaling without duplicating data on multiple servers.

-   Included versions: Nginx 1.25.3, HAProxy latest stable.
-   Website: [nginx.org](https://nginx.org/)
-   Managed application reference: [HTTP Cache]({{% ref "/docs/networking/http-cache" %}})


### TCP Balancer

The Managed TCP Load Balancer service provides deployment and management of load balancers.
It efficiently distributes incoming TCP traffic across multiple backend servers, ensuring high availability and optimal resource utilization.

TCP Load Balancer service is powered by [HAProxy](https://www.haproxy.org/), a mature and reliable TCP load balancer.

-   Managed application reference: [TCP balancer]({{% ref "/docs/networking/tcp-balancer" %}})
-   Docs: [HAProxy Documentation](https://www.haproxy.com/documentation/)


### Tenants

Tenants in Cozystack are implemented as managed applications.
Learn more about tenants in [Tenant System]({{% ref "/docs/guides/tenants" %}}).
