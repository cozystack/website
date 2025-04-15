---
title: Using Cozystack to build private cloud
linkTitle: Private Cloud
description: "How to use Cozystack to build private cloud"
weight: 20
aliases:
  - /docs/use-cases/private-cloud
---

You can use Cozystack as platform to build a private cloud powered by Infrastructure-as-Code

### Overview

One of the use cases is a self-portal for users within your company, where they can order the service they're interested in or a managed database.

You can implement best GitOps practices, where users will launch their own Kubernetes clusters and databases for their needs with a simple commit of configuration into your infrastructure Git repository.

Thanks to the standardization of the approach to deploying applications, you can expand the platform's capabilities using the functionality of standard Helm charts.

![Cozystack for private cloud](/img/case-private-cloud.png)

Here you can find reference repository to learn how to configure Cozystack services using GitOps approach:

- https://github.com/aenix-io/cozystack-gitops-example
