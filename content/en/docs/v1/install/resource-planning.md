---
title: "System Resource Planning Recommendations"
linkTitle: "Resource Planning"
description: "How much system resources to allocate per node depending on cluster scale."
weight: 6
---

## System Resource Planning Recommendations

How much system resources to allocate per node depending on cluster scale.

These recommendations are based on real-world usage cases from production deployments. While workloads vary across different environments, these calculations should provide reasonably accurate estimates for planning purposes.

{{% alert color="warning" %}}
**Important:** All values on this page show only the resources that need to be reserved for system components. They do not include resources for running tenant workloads (applications, databases, Kubernetes clusters, VMs, etc.). When planning your infrastructure, add the resources required for tenant workloads on top of these system resource requirements.
{{% /alert %}}

### Simple Recommendations

**Basic recommendation**: Allocate at least **2 CPU cores** and **5 GB memory** per node for system components.

Scale Dependency:

**By number of nodes:**
- Small cluster (3-5 nodes): ~2 CPU cores, ~6 GB memory per node
- Medium cluster (6-10 nodes): ~3 CPU cores, ~7 GB memory per node  
- Large cluster (10+ nodes): ~3 CPU cores, ~9 GB memory per node

**Important considerations:**
- System resource consumption may increase as the number of tenants and services within them grows. Each tenant adds load to system components (monitoring, logging, network policies, etc.).
- With a large number of tenants, increase the basic recommendation by **50-100% for CPU** and **100-300% for memory** depending on usage intensity.
- While operators managing these services run in a single instance, the overall system load increases with the number of tenants and workloads. More tenants mean more objects to monitor, more network policies to enforce, and more logs to collect and process.

**Dependency on number of tenants:**

The requirements vary based on the number of tenants in your cluster. Use the table below to find the exact values for your specific cluster size and tenant count combination.

**Note:** The values provided are baseline. Actual consumption may vary depending on the number of services within tenants and their usage intensity. With a large number of active services in tenants (e.g., 5+ services per tenant), use the next category by number of tenants.

#### What to do:

1. **Usage**: Monitor actual resource usage and adjust as needed
2. **Reserve**: Plan for 20-30% growth when planning
3. **Monitoring**: Regularly check actual system resource consumption
4. **Tenant consideration**: Use the table above to select appropriate values based on the number of tenants

### Resource Requirements Table

The table below shows CPU cores and memory (RAM) requirements per node. Rows represent cluster size (number of nodes), columns represent number of tenants. Each cell shows the recommended values on separate lines.

| Cluster Size | Number of Nodes | Up to 5 tenants | 6-14 tenants | 15-30 tenants | 30+ tenants |
|--------------|-----------------|-----------------|---------------|---------------|-------------|
| Small | 3-5 | CPU: 2 cores<br>RAM: 6 GB | CPU: 2 cores<br>RAM: 6 GB | CPU: 3 cores<br>RAM: 10 GB | CPU: 3 cores<br>RAM: 15 GB |
| Medium | 6-10 | CPU: 3 cores<br>RAM: 7 GB | CPU: 3 cores<br>RAM: 7 GB | CPU: 3 cores<br>RAM: 12 GB | CPU: 4 cores<br>RAM: 18 GB |
| Large | 10+ | CPU: 3 cores<br>RAM: 9 GB | CPU: 3 cores<br>RAM: 10 GB | CPU: 4 cores<br>RAM: 15 GB | CPU: 4 cores<br>RAM: 22 GB |

**Calculation examples:**
- Cluster with 5 nodes and 3 tenants: **2 CPU cores**, **6 GB memory** per node (Small cluster, Up to 5 tenants)
- Cluster with 5 nodes and 10 tenants: **2 CPU cores**, **6 GB memory** per node (Small cluster, 6-14 tenants)
- Cluster with 6 nodes and 25 tenants: **3 CPU cores**, **12 GB memory** per node (Medium cluster, 15-30 tenants)
- Cluster with 6 nodes and 40 tenants: **4 CPU cores**, **18 GB memory** per node (Medium cluster, 30+ tenants)

