---
title: "System Resource Planning Recommendations"
linkTitle: "Resource Planning"
description: "How much system resources to allocate per node depending on cluster scale."
weight: 6
---

This guide helps you plan system resource allocation per node based on cluster size and tenant count. Recommendations are based on production deployments and provide reasonably accurate estimates for planning purposes.

{{% alert color="warning" %}}
**Important:** Values shown are only for system components. Add your tenant workload requirements (applications, databases, Kubernetes clusters, VMs, etc.) on top of these.
{{% /alert %}}

**Quick start**: Allocate at least **2 CPU cores** and **6 GB RAM** per node for system components. For precise requirements based on your cluster size and tenant count, use the table or calculator below.

**Note on allocation**: These values represent expected consumption during normal operation, not hard resource reservations. Kubernetes dynamically schedules workloads, and system components will consume approximately these amounts while remaining capacity stays available for tenant workloads.

## Resource Requirements

Requirements depend on both cluster size (number of nodes) and number of tenants. With many active services per tenant (5+), consider using values from the next tenant category.

| Cluster Size | Nodes | Up to 5 tenants | 6-14 tenants | 15-30 tenants | 31+ tenants |
|--------------|-------|-----------------|---------------|---------------|-------------|
| **Small** | 3-5 | CPU: 2 cores<br>RAM: 6 GB | CPU: 2 cores<br>RAM: 6 GB | CPU: 3 cores<br>RAM: 10 GB | CPU: 3 cores<br>RAM: 15 GB |
| **Medium** | 6-10 | CPU: 3 cores<br>RAM: 7 GB | CPU: 3 cores<br>RAM: 7 GB | CPU: 3 cores<br>RAM: 12 GB | CPU: 4 cores<br>RAM: 18 GB |
| **Large** | 11+ | CPU: 3 cores<br>RAM: 9 GB | CPU: 3 cores<br>RAM: 10 GB | CPU: 4 cores<br>RAM: 15 GB | CPU: 4 cores<br>RAM: 22 GB |

**Planning tips:**
- Monitor actual resource consumption and adjust as needed
- Plan for 20-30% growth buffer
- With high tenant activity, consider increasing CPU by 50-100% and memory by 100-300%

### Calculate Your Requirements

Use the calculator below to find requirements for your specific configuration:

{{< system-resource-calculator >}}

### Why Resource Requirements Scale

System resource consumption increases with cluster size and tenant count because system components must handle more Kubernetes objects to monitor, more network policies to enforce, and more logs to collect and process.
