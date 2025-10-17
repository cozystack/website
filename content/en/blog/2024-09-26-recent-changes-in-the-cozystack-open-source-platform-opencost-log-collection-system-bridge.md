---
title: "Recent Changes in the Cozystack Open Source Platform: Opencost, Log Collection System, Bridge…"
slug: recent-changes-in-the-cozystack-open-source-platform-opencost-log-collection-system-bridge-
date: 2024-09-26
author: "Andrei Kvapil"
description: "Over the past couple of months, we have been actively developing our Cozystack Open Source platform, and today we’re presenting the…"
---

### **Recent Changes in the Cozystack Open Source Platform: Opencost, Log Collection System, Bridge Binding in Virtual Machines**

### Over the past couple of months, we have been actively developing our Cozystack Open Source platform, and today we’re presenting the improvements introduced from v0.12 to v0.15.

![](https://cdn-images-1.medium.com/max/800/1*ZE25TSWfLE46qz7vy5xQGQ.jpeg)

> *Cozystack is an Open Source platform that enables building a cloud on bare metal for rapid deployment of managed Kubernetes, database as a service, applications as a service, and virtual machines based on KubeVirt. Within the platform, you can deploy Kafka, FerretDB, PostgreSQL, Cilium, Grafana, Victoria Metrics, and* [other services](https://cozystack.io/docs/components/) *with a single click.*

### [v0.15](https://github.com/aenix-io/cozystack/releases/tag/v0.15.0)

- **Opencost Integration**: We have added Opencost to the platform — an Open Source project from the Cloud Native ecosystem for monitoring and allocating costs of cloud infrastructure and containers.
- **Strimzi Operator Update**: Updated the Strimzi Operator responsible for managed Kafka and disabled its network policy generation (we use our own solution for this).
- **Talos Linux Profile**: Introduced a profile in Talos Linux for installation on AMD64 architectures.

### [v0.14](https://github.com/aenix-io/cozystack/releases/tag/v0.14.0)

- **Password Generation**: Added password generation for FerretDB, PostgreSQL, and Clickhouse.
- **Component Updates**: CNPG updated to version 1.24.0, RabbitMQ updated to version 3.13.2.

### [v0.13](https://github.com/aenix-io/cozystack/releases/tag/v0.13.0)

- **Log Collection System**: Introduced a log collection system based on [VictoriaLogs](https://docs.victoriametrics.com/victorialogs/) and [Fluentbit](https://fluentbit.io/). You can view logs directly in Grafana using [LogsQL](https://docs.victoriametrics.com/victorialogs/logsql/) queries.
- **Virtual Machine Enhancements**: Reworked virtual machines to be created with bridge binding and on block devices without an additional file system layer. This significantly improves performance and enables live migration.
- **New VM Options**: Added support for running Talos Linux and Alpine Linux within VMs.
- **Disk Resizing Support**: Enabled support for expandDisks for automatic resizing of a virtual machine’s disk after resizing the PVC.
- **Updates**: FerretDB updated to version v1.24, KubeVirt and CDI updated to the latest versions.

### [v0.12](https://github.com/aenix-io/cozystack/releases/tag/v0.12.0)

- **Developer Experience Improvements**: Added numerous enhancements to improve the developer experience.
- **Cilium Update**: Cilium updated to version 1.16.1.

> Join our [cozy community](https://t.me/cozystack): ask questions, receive support from the community and maintainers, and participate in the development of the Open Source platform!