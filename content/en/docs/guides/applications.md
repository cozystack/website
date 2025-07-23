---
title: "Managed Applications in Cozystack"
linkTitle: "Managed Applications"
description: "Learn about the applications that Cozystack can deploy and manage"
weight: 20
aliases:
  - /docs/components
---


## Application Management Strategies

Cozystack deploys applications in two complementary ways:

-   **Operator‑managed applications** – Cozystack bundles a specific version of a Kubernetes Operator that installs and continuously reconciles the application.
    As a rule, the operator chooses one of the most recent stable versions of the application by default.

-   **Chart‑managed applications** – When no mature operator exists, Cozystack packages an upstream (or in‑house) Helm chart.
    The chart’s `appVersion` pin tracks the latest stable upstream release, keeping deployments secure and up‑to‑date.

## Tenants

Tenants in Cozystack are implemented as managed applications.
Learn more about tenants in [Tenant System]({{% ref "/docs/guides/tenants" %}}).


## Tenant Kubernetes Cluster

Cozystack deploys and manages Kubernetes clusters as standalone applications within each tenant’s isolated environment.
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
-   Kubernetes operator: [aenix-io/etcd-operator](https://github.com/aenix-io/etcd-operator) v0.4.2
-   Managed application reference: [Kubernetes]({{% ref "/docs/reference/applications/kubernetes" %}})


## Managed PostgreSQL

Nowadays, PostgreSQL is the most popular relational database.
Its platform-side implementation involves a self-healing replicated cluster.
This is managed with the increasingly popular CloudNativePG operator within the community.


-   Supported version: PostgreSQL 17
-   Kubernetes operator: [cloudnative-pg/cloudnative-pg](https://github.com/cloudnative-pg/cloudnative-pg) v1.24.0
-   Website: [cloudnative-pg.io](https://cloudnative-pg.io/)
-   Managed application reference: [PostgreSQL]({{% ref "/docs/reference/applications/postgres" %}})


## Managed MySQL (MariaDB)

MySQL is a widely used and well-known relational database.
The implementation in the platform provides the ability to create a replicated MariaDB cluster.
This cluster is managed using the increasingly popular mariadb-operator.

For each database, there is an interface for configuring users, their permissions,
as well as schedules for creating backups using [Restic](https://restic.net/) currently the most efficient tool.

-   Supported version: MariaDB 11.4.3
-   Kubernetes operator: [mariadb-operator/mariadb-operator](https://github.com/mariadb-operator/mariadb-operator) v0.18.0
-   Website: [mariadb.com](https://mariadb.com/)
-   Managed application reference: [MySQL]({{% ref "/docs/reference/applications/mysql" %}})


## Managed Redis

Redis is the most commonly used key-value in-memory data store.
It is most often used as a cache, as storage for user sessions, or as a message broker.
The platform-side implementation involves a replicated failover Redis cluster with Sentinel.
This is managed by the spotahome/redis-operator.

-   Supported version: Redis 6.2.6+ (based on `alpine`)
-   Kubernetes operator: [spotahome/redis-operator](https://github.com/spotahome/redis-operator) v1.3.0-rc1
-   Website: [redis.io](https://redis.io/)
-   Managed application reference: [Redis]({{% ref "/docs/reference/applications/redis" %}})


## Managed FerretDB

FerretDB is an open source MongoDB alternative.
It translates MongoDB wire protocol queries to SQL and can be used as a direct replacement for MongoDB 5.0+.
In Cozystack, it is backed by PostgreSQL.

-   Supported version: FerretDB 1.24.0.
-   Website: [ferretdb.io](https://www.ferretdb.io/)
-   Managed application reference: [FerretDB]({{% ref "/docs/reference/applications/ferretdb" %}})


## Managed ClickHouse

ClickHouse is an open source high-performance and column-oriented SQL database management system (DBMS).
It is used for online analytical processing (OLAP).
In the Cozystack platform, we use the Altinity operator to provide ClickHouse.

-   Supported version: 24.9.2.42
-   Kubernetes operator: [Altinity/clickhouse-operator](https://github.com/Altinity/clickhouse-operator) v0.25.0
-   Website: [clickhouse.com](https://clickhouse.com/)
-   Managed application reference: [Clickhouse]({{% ref "/docs/reference/applications/clickhouse" %}})


## Managed RabbitMQ

RabbitMQ is a widely known message broker.
The platform-side implementation allows you to create failover clusters managed by the official RabbitMQ operator.

-   Supported version: RabbitMQ 4.1.0+ (latest stable version)
-   Kubernetes operator: [rabbitmq/cluster-operator](https://github.com/rabbitmq/cluster-operator) v1.10.0
-   Website: [rabbitmq.com](https://www.rabbitmq.com/)
-   Managed application reference: [RabbitMQ]({{% ref "/docs/reference/applications/rabbitmq" %}})


## Managed Kafka

Apache Kafka is an open-source distributed event streaming platform.
It aims to provide a unified, high-throughput, low-latency platform for handling real-time data feeds.
In Cozystack, we use [Strimzi](https://github.com/cozystack/cozystack/blob/main/packages/system/kafka-operator/charts/strimzi-kafka-operator/README.md)
to run an Apache Kafka cluster on Kubernetes in various deployment configurations.

-   Supported version: Apache Kafka, 3.9.0
-   Kubernetes operator: [strimzi/strimzi-kafka-operator](https://github.com/strimzi/strimzi-kafka-operator) v0.45.0
-   Website: [kafka.apache.org](https://kafka.apache.org/)
-   Managed application reference: [Kafka]({{% ref "/docs/reference/applications/kafka" %}})


## Managed HTTP Cache

Nginx-based HTTP caching service helps protect your application from overload using the powerful Nginx.
Nginx is traditionally used to build CDNs and caching servers.

The platform-side implementation features efficient caching without using a clustered file system.
It also supports horizontal scaling without duplicating data on multiple servers.

-   Included versions: Nginx 1.25.3, HAProxy latest stable.
-   Website: [nginx.org](https://nginx.org/)
-   Managed application reference: [HTTP Cache]({{% ref "/docs/networking/http-cache" %}})


## Managed NATS Messaging

NATS is an open-source, simple, secure, and high performance messaging system.
It provides a data layer for cloud native applications, IoT messaging, and microservices architectures.

-   Supported version: NATS 2.10.17
-   Website: [nats.io](https://nats.io/)
-   Managed application reference: [NATS]({{% ref "/docs/reference/applications/nats" %}})


## Managed VPN Service

The VPN Service is powered by the Outline Server, an advanced and user-friendly VPN solution.
It is internally known as "Shadowbox," which simplifies the process of setting up and sharing Shadowsocks servers.
It operates by launching Shadowsocks instances on demand.

The Shadowsocks protocol uses symmetric encryption algorithms.
This enables fast internet access while complicating traffic analysis and blocking through DPI (Deep Packet Inspection).

-   Supported version: Outline Server, v1.12.3+ (stable)
-   Website: [getoutline.org](https://getoutline.org/)
-   Managed application reference: [VPN]({{% ref "/docs/networking/vpn" %}})


## Managed TCP Balancer

The Managed TCP Load Balancer Service simplifies the deployment and management of load balancers.
It efficiently distributes incoming TCP traffic across multiple backend servers, ensuring high availability and optimal resource utilization.

Managed TCP Load Balancer Service efficiently utilizes HAProxy for load balancing purposes.
HAProxy is a well-established and reliable solution for distributing incoming TCP traffic across multiple backend servers, ensuring high availability and efficient resource utilization. This deployment choice guarantees the seamless and dependable operation of your load balancing infrastructure.

-   Managed application reference: [TCP balancer]({{% ref "/docs/networking/tcp-balancer" %}})
-   Docs: https://www.haproxy.com/documentation/
