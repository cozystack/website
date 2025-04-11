---
title: "Introduction to Cozystack"
linkTitle: "Introduction"
description: "Target audience, key features and benefits of Cozystack framework."
weight: 9
---

Cozystack is a Kubernetes-based framework for building a complete cloud environment on your (or rented) hardware.
Numerous components that are usually installed in Kubernetes clusters are already included in the Cozystack framework
and tuned to work seamlessly with each other. The virtualization platform is also included and does not require extra
hardware servers. You get your virtual machines right in Kubernetes. Another powerful feature is
the [tenant]({{% ref "/docs/guides/concepts#tenant-system" %}}) system that allows you to isolate teams, individual
developers or even companies in their own fully-functional space, all on the same hardware.

The Cozystack framework can be used by a single company to run its own cloud, or by a service provider to provide the
platform as a service to multiple customers. The gentle learning curve also allows individual developers to learn
Kubernetes by using their own instance of the Cozystack platform.

Key features
------------

### Multi-user, multi-tenant, SSO included

Cozystack is designed to be used by multiple teams, departments or even companies. The "usual" approach of giving out
a dedicated namespace to each team could be too restrictive. Users may need to have multiple environments with the same
fixed namespace name. Or, users can suffer from not having root permission to the cluster to tune their own permission
model. The Cozystack tenant system allows users to create Kubernetes-in-Kubernetes with a single app deployment. The
users of nested Kubernetes can have full access to it. The quota system allows platform users to get the maximum from
the hardware, while keeping the resources isolated and preventing the "noisy neighbor" problem.

It's possible for platform users to get a detailed usage report for each tenant.

The SSO subsystem is based on Keycloak and allows platform users to create a single sign-on system. The Kubernetes API
in the root tenant as well as in downward tenants supports SSO out of the box.

### Storage system included

Not all businesses can afford a dedicated hardware SAN or NAS. Cozystack includes a reliable distributed storage
system that enables creating disaster-proof replicated volumes. It's even possible to replicate volumes across multiple
data centers.

### Virtualization system included

Usually, you either have a Virtualization or a Containerization system. Cozystack combines both of them in one. You
don't have to build another system on another set of servers to run virtual machines. Virtual machines consume
resources (CPU, memory, GPU, storage) directly from the Kubernetes resource pool.

### Managed databases do not have virtualization overhead

While Linux-on-Linux virtualization is extremely efficient, it can still have some overhead. In Cozystack, managed
databases run in the containers, but directly on the hardware. You may create multiple HA databases, each with its own
address on limited hardware, but all databases are running with direct access to CPU and storage.

### Kubernetes ecosystem

We do not know another Kubernetes distribution that has more infrastructure components included (seriously, send us
a link if you find one!). Instead of installing all the components and controllers, you just choose
a [bundle]({{% ref "/docs/operations/bundles/" %}}) that fits your needs. All the components are pre-configured and
tested to work with each other. Components get updates along with the Cozystack framework.
