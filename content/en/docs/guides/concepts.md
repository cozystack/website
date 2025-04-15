---
title: Core Concepts
description: "Learn about the core concepts in Cozystack: platform architecture, tenants and installation bundles."
weight: 10
aliases:
  - /docs/concepts
---

These are some core concepts in Cozystack.

## Platform Architecture

The core principle of the platform is that the end-user never has direct access to the API management cluster. Instead, the platform facilitates easy integration with the provider’s system, which in turn creates all the necessary services for the user. Then, it provides the credentials for user access to these services.

Besides managed services, the platform allows to bootstrap tenant Kubernetes clusters. The users have full access to their tenant Kubernetes clusters but have no access to the management cluster.

All controllers serving the user’s cluster are run externally from it, which allows to fully isolate the management cluster API from tenants and minimizes the potential for attacks on the management cluster.

Once access is granted to the tenant Kubernetes, the user can order physical volumes, load balancers, and eventually other services using tenant Kubernetes API.

![Cozystack for public cloud](/img/case-public-cloud.png)

All use cases are presented here:

* [**Using Cozystack to build public cloud**](/docs/guides/use-cases/public-cloud/)  
  How to use Cozystack to build public cloud

* [**Using Cozystack to build private cloud**](/docs/guides/use-cases/private-cloud/)  
  How to use Cozystack to build private cloud

* [**Using Cozystack as Kubernetes distribution**](/docs/guides/use-cases/kubernetes-distribution/)
  How to use Cozystack as Kubernetes distribution


## Tenant system

A tenant is the main unit of security on the platform. The closest analogy would be Linux kernel namespaces.

Tenants can be created recursively and are subject to the following rules:

#### Higher-level tenants can access lower-level ones.

Higher-level tenants can view and manage the applications of all their children.

#### Each tenant has its own domain

By default (unless otherwise specified), it inherits the domain of its parent with a prefix of its name, for example, if the parent had the domain `example.org`, then `tenant-foo` would get the domain `foo.example.org` by default.

Kubernetes clusters created in this tenant namespace would get domains like: `kubernetes-cluster.foo.example.org`

![tenant hierarchy](/img/tenants1.png)

#### Lower-level tenants can access the cluster services of their parent (in case they do not run their own)

By default there is `tenant-root` with a set of services like `etcd`, `ingress`, `monitoring`.
You can create create another tenant namespace `tenant-foo` inside of `tenant-root` and even more `tenant-bar` inside of `tenant-foo`.

Let's see what will happen when you run Kubernetes and Postgres under `tenant-bar` namespace.

Since `tenant-bar` does not have its own cluster services like `ingress`, and `monitoring`, the applications will use the cluster services of the parent tenant.  
This in turn means:

- The Kubernetes cluster data will be stored in etcd for `tenant-bar`.
- All metrics will be collected in the monitoring from `tenant-foo`.
- Access to the cluster will be through the common ingress of `tenant-root`.

![tenant services](/img/tenants2.png)

## Bundles

The Cozystack platform supports various deployment scenarios through a system of bundles.
Each bundle is tailored for specific use cases and environments.

Below are the example bundles:

#### `paas-full`

This is a Cozystack platform configuration intended for use as a PaaS platform, designed for installation on Talos Linux.
It includes all available features, enabling a comprehensive PaaS experience.

#### `paas-hosted`

This is a Cozystack platform configuration intended for use as a PaaS platform, designed for installation on existing Kubernetes clusters.

This configuration can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.
It does not include CNI plugins, virtualization, or storage.

#### `distro-full`

This is a Cozystack platform configuration intended for use as a Kubernetes distribution, designed for installation on Talos Linux.

This allows you to use Cozystack as a reliable Kubernetes distribution for bare metal.
It includes storage but excludes virtualization and multitenancy features.

#### `distro-hosted`

This is a Cozystack platform configuration intended for use as a Kubernetes distribution, designed for installation on existing Kubernetes clusters.

This configuration can be used with [kind](https://kind.sigs.k8s.io/) and any cloud-based Kubernetes clusters.
It does not include CNI plugins, virtualization, storage, or multitenancy.
