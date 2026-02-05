---
title: "Introduction to Cozystack"
linkTitle: "Introduction"
description: "Learn what Cozystack is and what you can build with it."
weight: 9
---

## What is Cozystack

Cozystack is a Kubernetes-based framework for building a private cloud environment.
It can be used by a single company to run its own [private cloud]({{% ref "/docs/guides/use-cases/private-cloud" %}}) or by a service provider to offer a
[platform-as-a-service]({{% ref "/docs/guides/use-cases/public-cloud" %}}) to multiple customers.

Cozystack covers the most critical needs of a development team:

-   [Kubernetes clusters]({{% ref "/docs/cozystack-api" %}}) for running applications in development and production
-   Standard [managed applications]({{% ref "/docs/applications" %}}): databases, queue managers, caches, and more
-   [Virtual machines]({{% ref "/docs/virtualization" %}})
-   Reliable distributed storage

[Cozystack platform stack]({{% ref "/docs/guides/platform-stack" %}}) includes reliable components that are typically installed
in Kubernetes clusters separately.
Here they're bundled and tested to work together seamlessly.
The virtualization platform is also built-in and does not require additional hardware.
Instead, virtual machines run directly inside Kubernetes.

Another powerful feature is the [tenant system]({{% ref "/docs/guides/concepts#tenant-system" %}}).
It allows you to isolate individual developers, teams, or even entire companies in their own fully functional spaces—all on the same hardware.

## Key features

### Multi-User, Multi-Tenant, with SSO included

Cozystack is designed for use by multiple teams, departments, or even companies.
The traditional approach of assigning each team a dedicated namespace can be too limiting.
Teams may need multiple environments with identical namespace names,
or they may lack the root permissions required to manage their own access models.

Cozystack's [tenant system]({{% ref "/docs/guides/concepts#tenant-system" %}}) solves these issues
by allowing users to deploy a Kubernetes-in-Kubernetes environment with a single app.
Users of nested Kubernetes clusters have full access and control.
The quota system ensures optimal hardware utilization while isolating resources to prevent the “noisy neighbor” problem.
Platform users can also generate detailed usage reports for each tenant.

The [single sign-on system]({{% ref "/docs/operations/oidc" %}}) in Cozystack is powered by Keycloak.
The Kubernetes API—both in the root tenant and in nested tenants—supports SSO out of the box.

### Replicated Storage System

Not all businesses can afford dedicated hardware SAN or NAS devices.
Cozystack includes a reliable distributed storage system that enables the creation of disaster-resilient, replicated volumes.
It's even possible to replicate volumes across multiple data centers.

### Virtualization System

Typically, you must choose between virtualization and containerization.
Cozystack combines both in a single platform.
There's no need to maintain a separate virtualization infrastructure.
In Cozystack, [virtual machines]({{% ref "/docs/virtualization" %}})
run directly in Kubernetes and consume CPU, memory, GPU, and storage from the same Kubernetes resource pool.

### Managed Databases Without Overhead

Even though Linux-on-Linux virtualization is highly efficient, it still introduces some overhead.
Cozystack avoids this by running [managed databases]({{% ref "/docs/applications" %}})
directly in containers on the host hardware.
You can spin up multiple high-availability databases with dedicated IP addresses,
all on limited hardware—yet each runs with direct access to CPU and storage.

### Kubernetes ecosystem

We’re not aware of any other Kubernetes distribution with more built-in infrastructure components.
(Seriously—send us a link if you find one!)
Rather than manually installing components and controllers, you simply choose
a [Cozystack bundle]({{% ref "/docs/operations/configuration/bundles" %}}) that fits your needs.
All components are pre-configured, tested for compatibility, and updated alongside the Cozystack framework.

