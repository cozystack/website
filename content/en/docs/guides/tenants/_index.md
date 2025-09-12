---
title: Tenant System
description: "Learn about tenants, the way Cozystack helps manage resources and improve security."
weight: 17
---

## Introduction

A **tenant** in Cozystack is the primary unit of isolation and security, analogous to a Kubernetes namespace but with enhanced scope.
Each tenant represents an isolated environment with its own resources, networking, and RBAC (role-based access control).
Some cloud providers use the term "projects" for a similar entity.

Cozystack administrators and users create tenants using the [Tenant application]({{% ref "/docs/applications/tenant" %}})
from the application catalog.
Tenants can be created via the Cozystack dashboard (UI), `kubectl`, or directly via Cozystack API.


### Tenant Nesting

All user tenants belong to the base `root` tenant.
This `root` tenant is used only to deploy user tenants and system components.
All user-side applications are deployed in their respective tenants.

Tenants can be nested further: an administrator of a tenant can create sub-tenants as applications in the Cozystack catalog.
Parent tenants can share their resources with their children and oversee their applications.
In turn, children can use their parent's services.

![tenant hierarchy diagram](./tenants1.png)


### Sharing Cluster Services

Tenants may have [cluster services]({{% ref "/docs/operations/services" %}}) deployed in them.
Cluster services are middleware services providing core functionality to the tenants and user-facing applications.

The `root` tenant has a set of services like `etcd`, `ingress`, and `monitoring` by default.
Lower-level tenants can run their own cluster services or access ones of their parent.

For example, a Cozystack user creates the following tenants and services:

- Tenant `foo` inside of tenant `root`, having its own instances of `etcd` and `monitoring` running.
- Tenant `bar` inside of tenant `foo`, having its own instance of `etcd`.
- [Tenant Kubernetes cluster]({{% ref "/docs/kubernetes" %}}) and a
  [Postgres database]({{% ref "/docs/applications/postgres" %}}) in the tenant `bar`.

All applications need services like `ingress` and `monitoring`. 
Since tenant `bar` does not have these services, the applications will use the parent tenant's services.

Here's how this configuration will be resolved:

-   The tenant Kubernetes cluster will store its data in the `bar` tenant's own `etcd` service.
-   All metrics will be collected in the monitoring stack of the parent tenant `foo`.
-   Access to the applications will be through the common `ingress` deployed in the tenant `root`.

![tenant services](./tenants2.png)


### Unique Domain Names

Each tenant has its own domain.
By default, (unless otherwise specified), it inherits the domain of its parent with a prefix of its name.
For example, if the `root` tenant has domain `example.org`, then tenant `foo` gets the domain `foo.example.org` by default.
However, it can be redefined to have another domain, such as `example.com`.

Kubernetes clusters created in this tenant namespace would get domains like: `kubernetes-cluster.foo.example.org`


### Tenant Naming Limitations

Tenant names must be alphanumeric.
Using dashes (`-`) in tenant names is not allowed, unlike with other services.
This limitation exists to keep consistent naming in tenants, nested tenants, and services deployed in them.

For example:

-   The root tenant is named `root`, but internally it's referenced as `tenant-root`.
-   A user tenant is named `foo`, which results in `tenant-foo`.
-   However, a tenant cannot be named `foo-bar`, because parsing names like `tenant-foo-bar` can be ambiguous.


### Reference

See the reference for the application implementing tenant management: [`tenant`]({{% ref "/docs/applications/tenant#parameters" %}})

