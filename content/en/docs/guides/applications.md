---
title: "Cozystack-managed Applications"
linkTitle: "Managed Apps"
description: "Learn about the applications that Cozystack can deploy and manage"
weight: 20
aliases:
  - /docs/components
---

## Managed Kubernetes

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

-    Managed application reference: [Kubernetes](https://github.com/cozystack/cozystack/tree/main/packages/apps/kubernetes#readme)


## Managed PostgreSQL

Nowadays PostgreSQL is the most popular relational database. Its platform-side implementation involves a self-healing replicated cluster, managed with the increasingly popular CloudNativePG operator within the community.

-    Website: [cloudnative-pg.io](https://cloudnative-pg.io/)
-    Managed application reference: [PostgreSQL](https://github.com/cozystack/cozystack/tree/main/packages/apps/postgres#readme)

## Managed MySQL

MySQL is an equally well-known and also widely used relational database. The implementation in the platform provides the ability to create a replicated MariaDB cluster, which is managed using the increasingly popular mariadb-operator.

> For each database, there is an interface for configuring users, their permissions, as well the schedules for creating backups using the currently most efficient tool - Restic.

-    Website: [mariadb.com](https://mariadb.com/)
-    Managed application reference: [MySQL](https://github.com/cozystack/cozystack/tree/main/packages/apps/mysql#readme)

## Managed Redis

Redis is the most commonly used key-value in-memory data store. It is most often used as a cache, as storage for user sessions, or as a message broker. The platform-side implementation involves a replicated failover Redis cluster with Sentinel, which is managed by the spotahome redis-operator.

-    Website: [redis.io](https://redis.io/)
-    Managed application reference: [Redis](https://github.com/cozystack/cozystack/tree/main/packages/apps/redis#readme)

## Managed FerretDB

FerretDB is an open source MongoDB alternative, that translates MongoDB wire protocol queries to SQL and can be used as a direct replacement for MongoDB 5.0+. In the Cozystack it is backed by PostgreSQL.

-    Website: [ferretdb.io](https://www.ferretdb.io/)
-    Managed application reference: [FerretDB](https://github.com/cozystack/cozystack/tree/main/packages/apps/ferretdb#readme)

## Managed Clickhouse

ClickHouse is an open source high-performance and column-oriented SQL database management system (DBMS). It is used for online analytical processing (OLAP). In the Cozystack platform we use Altinity operator to provide Clickhouse.

-    Website: [clickhouse.com](https://clickhouse.com/)
-    Managed application reference: [Clickhouse](https://github.com/cozystack/cozystack/tree/main/packages/apps/clickhouse#readme)

## Managed RabbitMQ

Widely known message broker. Platform-side implementation allows you to create failover clusters managed by the official RabbitMQ operator.

-    Website: [rabbitmq.com](https://www.rabbitmq.com/)
-    Managed application reference: [RabbitMQ](https://github.com/cozystack/cozystack/tree/main/packages/apps/rabbitmq#readme)

## Managed Kafka

Apache Kafka is an open-source distributed event streaming platform that aims to provide a unified, high-throughput, low-latency platform for handling real-time data feeds. In the Cozystack we use Strimzi to run an Apache Kafka cluster on Kubernetes in various deployment configurations.

-    Website: [kafka.apache.org](https://kafka.apache.org/)
-    Managed application reference: [Kafka](https://github.com/cozystack/cozystack/tree/main/packages/apps/kafka#readme)

## Managed HTTP Cache

Nginx-based HTTP caching service - with its help you can always protect your application from overload using the powerful Nginx, which is traditionally used to build CDNs and caching servers.

The platform-side implementation features efficient caching without using a clustered file system and horizontal scaling without duplicating data on multiple servers.

-    Website: [nginx.org](https://nginx.org/)
-    Managed application reference: [http-cache](https://github.com/cozystack/cozystack/tree/main/packages/apps/http-cache#readme)

## Managed NATS Messaging
NATS is an open-source, simple, secure and high performance messaging system. It provides data layer for cloud native applications, IoT messaging, and microservices architectures.

-    Website: [nats.io](https://nats.io/)
-    Managed application reference: [NATS](https://github.com/cozystack/cozystack/tree/main/packages/apps/nats#readme)

## Managed VPN Service

The VPN Service is powered by the Outline Server, an advanced and user-friendly VPN solution. Internally known as "Shadowbox", which simplifies the process of setting up and sharing Shadowsocks servers. It operates by launching Shadowsocks instances on demand.

The Shadowsocks protocol implies the use of symmetric encryption algorithms, enabling a fast way to access the internet while complicating traffic analysis and blocking through DPI (Deep Packet Inspection).

-    Website: [getoutline.org](https://getoutline.org/)
-    Managed application reference: [VPN](https://github.com/cozystack/cozystack/tree/main/packages/apps/vpn#readme)
