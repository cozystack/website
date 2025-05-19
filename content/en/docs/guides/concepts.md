---
title: Platform Architecture
linkTitle: Platform Architecture
description: "Learn about the core concepts in Cozystack: platform architecture, tenants and installation bundles."
weight: 10
aliases:
  - /docs/concepts
---

The core principle of the platform is that the end-user never has direct access to the API management cluster. Instead, the platform facilitates easy integration with the provider’s system, which in turn creates all the necessary services for the user. Then, it provides the credentials for user access to these services.

Besides managed services, the platform allows to bootstrap tenant Kubernetes clusters. The users have full access to their tenant Kubernetes clusters but have no access to the management cluster.

All controllers serving the user’s cluster are run externally from it, which allows to fully isolate the management cluster API from tenants and minimizes the potential for attacks on the management cluster.

Once access is granted to the tenant Kubernetes, the user can order physical volumes, load balancers, and eventually other services using tenant Kubernetes API.

![Cozystack for public cloud](/img/case-public-cloud.png)

## Cozystack Use Cases

All use cases are presented here:

* [**Using Cozystack to build public cloud**](/docs/guides/use-cases/public-cloud/)  
  How to use Cozystack to build public cloud

* [**Using Cozystack to build private cloud**](/docs/guides/use-cases/private-cloud/)  
  How to use Cozystack to build private cloud

* [**Using Cozystack as Kubernetes distribution**](/docs/guides/use-cases/kubernetes-distribution/)
  How to use Cozystack as Kubernetes distribution


## Tenant system

> Moved to [Tenant System]({{% ref "/docs/guides/tenants" %}})

## Bundles

> Moved to [Bundles]({{% ref "/docs/guides/bundles" %}})
