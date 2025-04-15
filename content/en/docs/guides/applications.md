---
title: "Cozystack-managed Applications"
linkTitle: "Managed Apps"
description: "Learn about the applications that Cozystack can deploy and manage"
weight: 20
aliases:
  - /docs/components
---

## Managed PostgreSQL

Nowadays PostgreSQL is the most popular relational database. Its platform-side implementation involves a self-healing replicated cluster, managed with the increasingly popular CloudNativePG operator within the community.

## Managed MySQL

MySQL is an equally well-known and also widely used relational database. The implementation in the platform provides the ability to create a replicated MariaDB cluster, which is managed using the increasingly popular mariadb-operator.

> For each database, there is an interface for configuring users, their permissions, as well the schedules for creating backups using the currently most efficient tool - Restic.

## Managed Redis

Redis is the most commonly used key-value in-memory data store. It is most often used as a cache, as storage for user sessions, or as a message broker. The platform-side implementation involves a replicated failover Redis cluster with Sentinel, which is managed by the spotahome redis-operator.

## Managed FerretDB

FerretDB is an open source MongoDB alternative, that translates MongoDB wire protocol queries to SQL and can be used as a direct replacement for MongoDB 5.0+. In the Cozystack it is backed by PostgreSQL.

## Managed Clickhouse

ClickHouse is an open source high-performance and column-oriented SQL database management system (DBMS). It is used for online analytical processing (OLAP). In the Cozystack platform we use Altinity operator to provide Clickhouse.

## Managed RabbitMQ

Widely known message broker. Platform-side implementation allows you to create failover clusters managed by the official RabbitMQ operator.

## Managed Kafka

Apache Kafka is an open-source distributed event streaming platform that aims to provide a unified, high-throughput, low-latency platform for handling real-time data feeds. In the Cozystack we use Strimzi to run an Apache Kafka cluster on Kubernetes in various deployment configurations.

## Managed HTTP Cache

Nginx-based HTTP caching service - with its help you can always protect your application from overload using the powerful Nginx, which is traditionally used to build CDNs and caching servers.

The platform-side implementation features efficient caching without using a clustered file system and horizontal scaling without duplicating data on multiple servers.

## Managed NATS Messaging
NATS is an open-source, simple, secure and high performance messaging system. It provides data layer for cloud native applications, IoT messaging, and microservices architectures.

## Managed Kubernetes

Managed Kubernetes is a service that allows you to create full-featured Kubernetes clusters on demand, right out of the box, with just the click of a button. For each cluster, a separate managed control-plane and virtual compute nodes are created.

In the future, there will be added functionality for automatically collecting metrics and logs from users clusters into a common Monitoring Stack. To implement this service, the development of the Kubefarm project will be used.

> This set of services is enough to run almost any modern application.

## Managed VPN Service

The VPN Service is powered by the Outline Server, an advanced and user-friendly VPN solution. Internally known as "Shadowbox", which simplifies the process of setting up and sharing Shadowsocks servers. It operates by launching Shadowsocks instances on demand.

The Shadowsocks protocol implies the use of symmetric encryption algorithms, enabling a fast way to access the internet while complicating traffic analysis and blocking through DPI (Deep Packet Inspection).
