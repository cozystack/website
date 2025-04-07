---
title: Using Cozystack to build public cloud
linkTitle: Public Cloud
description: "How to use Cozystack to build public cloud"
weight: 10
---

You can use Cozystack as backend for a public cloud

### Overview

Cozystack positions itself as a kind of framework for building public clouds. The key word here is framework. In this case, it's important to understand that Cozystack is made for cloud providers, not for end users.

Despite having a graphical interface, the current security model does not imply public user access to your management cluster.

Instead, end users get access to their own Kubernetes clusters, can order LoadBalancers and additional services from it, but they have no access and know nothing about your management cluster powered by Cozystack.

Thus, to integrate with your billing system, it's enough to teach your system to go to the management Kubernetes and place a YAML file signifying the service you're interested in. Cozystack will do the rest of the work for you.

![Cozystack for public cloud](/img/case-public-cloud.png)
