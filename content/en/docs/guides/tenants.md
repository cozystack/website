---
title: Tenant System
description: "Learn about tenants, the way Cozystack helps manage resources and improve security."
weight: 15
aliases:
---

## Introduction

A **tenant** is the main unit of security on the platform. The closest analogy would be Linux kernel namespaces.

Tenants can be created recursively and are subject to the following rules:

### Tenant naming

Tenant names must be alphanumeric.
Using dashes (`-`) in tenant names is not allowed, unlike with other services.
This limitation exists to keep consistent naming in tenants, nested tenants, and services deployed in them.

For example:

-   The root tenant is named `root`, but internally it's referenced as `tenant-root`.
-   A nested tenant could be named `foo`, which would result in `tenant-foo` in service names and URLs.
-   However, a tenant can not be named `foo-bar`, because parsing names such as `tenant-foo-bar` would be ambiguous.

### Nested tenants

Tenants can be nested: an administrator of a tenant can create sub-tenants as applications in the Cozystack catalog.
Parent tenants can share their resources with their children and oversee their applications.
In turn, children can use their parent's services.

![tenant hierarchy diagram](/img/tenants1.png)

### Unique domains

Each tenant has its own domain.
By default, (unless otherwise specified), it inherits the domain of its parent with a prefix of its name.
For example, if the parent had the domain `example.org`, then `tenant-foo` would get the domain `foo.example.org` by default.

Kubernetes clusters created in this tenant namespace would get domains like: `kubernetes-cluster.foo.example.org`

### Lower-level tenants can access the cluster services of their parent (in case they do not run their own)

By default there is `tenant-root` with a set of services like `etcd`, `ingress`, `monitoring`.
You can create create another tenant namespace `tenant-foo` inside of `tenant-root` and even more `tenant-bar` inside of `tenant-foo`.

Let's see what will happen when you run Kubernetes and Postgres under `tenant-bar` namespace.

Since `tenant-bar` does not have its own cluster services like `ingress`, and `monitoring`, the applications will use the cluster services of the parent tenant.
This in turn means:

- The Kubernetes cluster data will be stored in etcd for `tenant-bar`.
- All metrics will be collected in the monitoring from `tenant-foo`.
- Access to the cluster will be through the common ingress of `tenant-root`.

![tenant services](/img/tenants2.png)

See the reference for the application implementing tenant management: [`tenant`]({{% ref "/docs/reference/applications/tenant#parameters" %}})

