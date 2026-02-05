---
title: "Cluster Services Reference"
linkTitle: "Cluster Services"
description: "Learn about middleware system packages, deployed to tenants and providing major functionality to user apps."
weight: 35
menu:
  docs:
    weight: 35
---

## Monitoring

The monitoring system in Cozystack provides comprehensive observability for both system-level and tenant-level resources. It operates at two primary levels: system-wide monitoring for infrastructure components and tenant-specific monitoring for user applications and services.

### Architecture Overview

- **System Level**: Monitors core Cozystack components, Kubernetes clusters, and underlying infrastructure.
- **Tenant Level**: Provides isolated monitoring stacks for each tenant, allowing them to monitor their own applications without interference.

### Key Components

- **VMAgent**: Collects metrics from various sources and forwards them to VictoriaMetrics.
- **VMCluster**: VictoriaMetrics cluster for storing and querying metrics.
- **Grafana**: Visualization and dashboarding tool for metrics and logs.
- **Alerta**: Alerting system for notifications based on metrics thresholds.

### Data Flows

Metrics flow from exporters (e.g., node-exporters, kube-state-metrics) to VMAgent, which then writes to VMCluster. Grafana queries VMCluster for visualization, and Alerta processes alerts from VMCluster or other sources.

For detailed configuration, see [Monitoring Hub Reference]({{{{% ref "/docs/v0/operations/services/monitoring" %}}).

Cozystack includes a number of cluster services.
They are deployed through tenant settings, and not through the application catalog.

Each tenant can have its own copy of cluster service or use the parent tenant's services.
Read more about the services sharing mechanism in [Tenant System]({{{{% ref "/docs/v0/guides/tenants#sharing-cluster-services" %}})
