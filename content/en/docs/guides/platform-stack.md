---
title: "Cozystack Components"
linkTitle: "Components"
description: "Cozystack Components"
weight: 15
---

## Basic Platform Stack

### Kubernetes

Kubernetes has already become a kind of de facto standard for managing server workloads.

One of the key features of Kubernetes is a convenient and unified API that is understandable to everyone (everything is YAML). Also, the best software design patterns that provide continuous recovery in any situation (reconciliation method) and efficient scaling to a large number of servers.

This fully solves the integration problem, since all existing virtualization platforms have an outdated and rather complex APIs that cannot be extended without modifying the source code. As a result, there is always a need to create your own custom solutions, which requires additional effort.

### Flux CD

We use FluxCD as the core element of our platform, believing it sets a new industry standard for platform engineering. FluxCD provides a simple and uniform interface for both installing and managing the lifecycle of all platform components.

### Talos Linux

Using Talos Linux as the base layer for the platform allows to strictly limit the technology stack and make the system stable as a rock. 

Talos Linux has no moving parts, no traditional package manager, no file structure, and no ability to run anything except Kubernetes containers. 
The base layer of the platform includes the latest version of the kernel, all the necessary kernel modules, container runtime and a Kubernetes-like API for interacting with the system.

Updating the system is done by rewriting the image "as is" entirely onto the hard drive.

### KubeVirt

KubeVirt is a project started by global industry leaders with a common vision to unify Kubernetes and a desire to introduce it to the world of virtualization. KubeVirt extends the capabilities of Kubernetes by providing convenient abstractions for launching and managing virtual machines, as well the all related entities such as snapshots, presets, virtual volumes, and more.

At the moment, the KubeVirt project is being jointly developed by such world-famous companies as RedHat, NVIDIA, ARM.

### Kamaji

We use Kamaji to deploy user Kubernetes clusters. Kamaji provides a straightforward and convenient method for launching all the necessary Kubernetes control-plane in containers. Worker nodes are then connected to these control planes and handle user workloads.

The approach developed by the Kamaji project is modeled after the design of modern clouds and ensures security by design where end users do not have any control plane nodes for their clusters.

### DRBD

DRBD is the fastest replication block storage running right in the Linux kernel. When DRBD only deals with data replication, time-tested technologies such as LVM or ZFS are used for securely store the data.
The DRBD kernel module is included in the mainline Linux kernel and has been used to build fault-tolerant systems for over a decade.

DRBD is managed using LINSTOR, a system integrated with Kubernetes and which is a management layer for creating virtual volumes based on DRBD. It allows you to easily manage hundreds or thousands of virtual volumes in a cluster.

### Kube-OVN

OVN is a free implementation of virtual network fabric for Kubernetes and OpenStack based on Open vSwitch technology. With Kube-OVN, you get a robust and functional virtual network that ensures reliable isolation between tenants and provides floating addresses for virtual machines.

In the future, this will enable seamless integration with other clusters and customer network services.

### Cilium

Utilizing Cilium in conjunction with OVN enables the most efficient and flexible network policies, along with a productive services network in Kubernetes, leveraging an offloaded Linux network stack featuring the cutting-edge eBPF technology.

Cilium is a highly promising project, widely adopted and supported by numerous cloud providers worldwide.

### Grafana

Grafana with Grafana Loki and the OnCall extension provides a single interface to Observability. It allows you to conveniently view charts, logs and manage alerts for your infrastructure and applications.

### Victoria Metrics

Victoria Metrics allows you to most efficiently collect, store and process metrics in the Open Metrics format, doing it more efficiently than Prometheus in the same setup.

### MetalLB

MetalLB is the default load balancer for Kubernetes; with its help, your services can obtain public addresses that are accessible not only from inside, but also from outside your cluster network.

### Haproxy

HAProxy is an advanced and widely known TCP balancer. It continuously checks the availability of services and carefully balance production traffic between them in real time.

### SeaweedFS

SeaweedFS is a simple and highly scalable distributed file system designed for two main objectives: to store billions of files and to serve the files faster. It allows access O(1), usually just one disk read operation.


## Application stack


### Managed PostgreSQL

Nowadays PostgreSQL is the most popular relational database. Its platform-side implementation involves a self-healing replicated cluster, managed with the increasingly popular CloudNativePG operator within the community.

### Managed MySQL

MySQL is an equally well-known and also widely used relational database. The implementation in the platform provides the ability to create a replicated MariaDB cluster, which is managed using the increasingly popular mariadb-operator.

> For each database, there is an interface for configuring users, their permissions, as well the schedules for creating backups using the currently most efficient tool - Restic.

### Managed Redis

Redis is the most commonly used key-value in-memory data store. It is most often used as a cache, as storage for user sessions, or as a message broker. The platform-side implementation involves a replicated failover Redis cluster with Sentinel, which is managed by the spotahome redis-operator.

### Managed FerretDB

FerretDB is an open source MongoDB alternative, that translates MongoDB wire protocol queries to SQL and can be used as a direct replacement for MongoDB 5.0+. In the Cozystack it is backed by PostgreSQL.

### Managed Clickhouse

ClickHouse is an open source high-performance and column-oriented SQL database management system (DBMS). It is used for online analytical processing (OLAP). In the Cozystack platform we use Altinity operator to provide Clickhouse.

### Managed RabbitMQ

Widely known message broker. Platform-side implementation allows you to create failover clusters managed by the official RabbitMQ operator.

### Managed Kafka

Apache Kafka is an open-source distributed event streaming platform that aims to provide a unified, high-throughput, low-latency platform for handling real-time data feeds. In the Cozystack we use Strimzi to run an Apache Kafka cluster on Kubernetes in various deployment configurations.

### Managed HTTP Cache

Nginx-based HTTP caching service - with its help you can always protect your application from overload using the powerful Nginx, which is traditionally used to build CDNs and caching servers.

The platform-side implementation features efficient caching without using a clustered file system and horizontal scaling without duplicating data on multiple servers.

### Managed NATS Messaging
NATS is an open-source, simple, secure and high performance messaging system. It provides data layer for cloud native applications, IoT messaging, and microservices architectures.

### Managed Kubernetes

Managed Kubernetes is a service that allows you to create full-featured Kubernetes clusters on demand, right out of the box, with just the click of a button. For each cluster, a separate managed control-plane and virtual compute nodes are created.

In the future, there will be added functionality for automatically collecting metrics and logs from users clusters into a common Monitoring Stack. To implement this service, the development of the Kubefarm project will be used.

> This set of services is enough to run almost any modern application.

### Managed VPN Service

The VPN Service is powered by the Outline Server, an advanced and user-friendly VPN solution. Internally known as "Shadowbox", which simplifies the process of setting up and sharing Shadowsocks servers. It operates by launching Shadowsocks instances on demand.

The Shadowsocks protocol implies the use of symmetric encryption algorithms, enabling a fast way to access the internet while complicating traffic analysis and blocking through DPI (Deep Packet Inspection).
