---
title: "The Open Source Platform Cozystack Version 0.16.0"
slug: the-open-source-platform-cozystack-version-0-16-0
date: 2024-10-03
author: "Timur Tukaev"
description: "Key Highlights Cozystack now features an alert system based on the open-source tool Alerta, with the ability to configure notifications…"
---

### The Open Source Platform Cozystack Version 0.16.0 Released: Alert System with Telegram Notifications and More Improvements

Key Highlights Cozystack now features an alert system based on the open-source tool [Alerta](https://alerta.io/), with the ability to configure notifications directly to Telegram. Additionally, you can receive alerts from k8s-prometheus stack, all Grafana dashboards have been updated, as well as Grafana itself and the grafana-operator.

![](https://cdn-images-1.medium.com/max/800/1*jOAv-G1LLJy84HwQHpI0Pw.png)
Alerta interface

> Cozystack is an Open Source platform designed for building cloud infrastructure on bare metal, enabling rapid deployment of managed Kubernetes, database as a service, applications as a service, and virtual machines based on KubeVirt. Within the platform, you can deploy services like Kafka, FerretDB, PostgreSQL, Cilium, Grafana, Victoria Metrics, and others with just a single click.

Other changes:

- Nginx-ingress updated to version v1.11.2 and issue with accessing nginx-ingress from inside the cluster was resolved
- Flux and flux-operator updated to the latest versions
- Updated Kamaji to the latest version and fixed issue with controller restarts
- Added endpointslice controller to CCM; ordered services now send traffic only to nodes that serve them
- Talos Linux updated to version v1.8.0
- Cilium updated to the latest patch version (v1.16.2)

![](https://cdn-images-1.medium.com/max/800/1*AfwiLHWi-5tqeanoAfTr0A.jpeg)
New dashboards

![](https://cdn-images-1.medium.com/max/800/1*Lop2OD3KPS0Zw21Hn4oaDw.jpeg)
New dashboards

![](https://cdn-images-1.medium.com/max/800/1*-iZWlbUb3RZH1wfNxdhRhw.jpeg)
New dashboards

*For more details, visit the* [GitHub page](https://github.com/aenix-io/cozystack/releases/tag/v0.16.0)*.*