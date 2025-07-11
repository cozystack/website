---
title: Key Concepts
linkTitle: Key Concepts
description: "Learn about the core principles behind Cozystack and its key concepts"
weight: 10
aliases:
  - /docs/concepts
---

## Core Principles

The core principle of the platform is that the end-user never has direct access to the API management cluster. Instead, the platform facilitates easy integration with the provider’s system, which in turn creates all the necessary services for the user. Then, it provides the credentials for user access to these services.

Besides managed services, the platform allows to bootstrap tenant Kubernetes clusters. The users have full access to their tenant Kubernetes clusters but have no access to the management cluster.

All controllers serving the user’s cluster are run externally from it, which allows to fully isolate the management cluster API from tenants and minimizes the potential for attacks on the management cluster.

Once access is granted to the tenant Kubernetes, the user can order physical volumes, load balancers, and eventually other services using tenant Kubernetes API.


