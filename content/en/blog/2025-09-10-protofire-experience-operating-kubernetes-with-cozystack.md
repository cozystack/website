---
title: "Protofire Experience Operating Kubernetes with Cozystack"
slug: protofire-experience-operating-kubernetes-with-cozystack
date: 2025-09-10
author: "Timur Tukaev"
description: "In a recent infrastructure transition that spanned several months, our team explored alternative container orchestration platforms to…"
---

### [Protofire](https://www.linkedin.com/company/protofire-io/) Experience Operating Kubernetes with Cozystack

In a recent infrastructure transition that spanned several months, our team explored alternative container orchestration platforms to simplify operations and optimize costs. At the time, our environment consisted of nearly a hundred AWS accounts running multiple ECS services, along with managed PostgreSQL, Redis, RabbitMQ, and ALBs.

One of the goals was to consolidate our deployment architecture under Kubernetes while maintaining support for stateful services, without introducing significant operational complexity. After evaluating different options, we decided to adopt [Cozystack](http://cozystack.io), primarily due to its all-in-one approach and compatibility with bare-metal infrastructure.

![](https://cdn-images-1.medium.com/max/800/1*ZaReZmQFCRYbv7yM1zoq-g.png)

Cozystack is built on Talos Linux, which provides immutable and secure nodes, and includes a set of pre-packaged Helm-ready applications such as PostgreSQL, Redis, RabbitMQ, and Ingress-NGINX. These built-in components allowed us to accelerate the initial setup while maintaining flexibility for customization.

Currently, we manage two Kubernetes clusters — each composed of three control-plane and three worker nodes, with capacity planned for scaling. Based on our infrastructure modeling and cost tracking, we expect a 7× to 10× reduction in spend compared to our previous AWS setup.

During the initial phase, migrating and tuning each environment, including adapting Helm charts, took more than a day. Through iteration and process improvements, we’ve since reduced this time: today, standard environments can be provisioned and configured in roughly one day.

We also restructured our observability tooling during this process. We adopted Loki for centralized log collection, complementing the existing metrics and Grafana dashboards already available through the platform.

Cozystack’s recent joining CNCF Sandbox gave us additional reassurance regarding its long-term support and technical maturity. From our perspective, this migration has provided meaningful operational and financial benefits, and helped us simplify and standardize how we deliver and maintain services internally.

*👉 Got a use case? Share it with our maintainers! We’ll showcase it to the community.*