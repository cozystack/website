{{< tabs name="hardware_config" >}}
{{% tab name="Minimal" %}}

Here are the baseline requirements for running a small installation.
The minimum recommended configuration for each node is as follows:

| Component        | Requirement  |
|------------------|--------------|
| Hosts            | 3x Physical hosts (or VMs with host CPU passthrough) |
| Architecture     | x86_64        |
| CPU              | 8 cores      |
| RAM              | 24 GB        |
| Primary Disk     | 50 GB SSD (or RAW for VMs) |
| Secondary Disk   | 256 GB SSD (raw) |

**Suitable for:**
- Dev/Test environments
- Small demonstration setups
- 1-2 Tenants
- Up to 3 Kubernetes clusters
- Few VMs or Databases

{{% /tab %}}
{{% tab name="Recommended" %}}

For small production environments, the recommended configuration for each node is as follows:

| Component        | Requirement  |
|------------------|--------------|
| Hosts            | 3x Physical hosts |
| Architecture     | x86_64        |
| CPU              | 16-32 cores  |
| RAM              | 64 GB        |
| Primary Disk     | 100 GB SSD or NVMe |
| Secondary Disk   | 1-2 TB SSD or NVMe |

**Suitable for:**
- Small to medium production environments
- 5-10 Tenants
- 5+ Kubernetes clusters
- Dozens Virtual Machines or Databases
- S3-compatible storage

{{% /tab %}}
{{% tab name="Optimal" %}}

For medium to large production environments, the optimal configuration for each node is as follows:

| Component        | Requirement  |
|------------------|--------------|
| Hosts            | 6x+ Physical hosts |
| Architecture     | x86_64        |
| CPU              | 32-64 cores  |
| RAM              | 128-256 GB   |
| Primary Disk     | 200 GB SSD or NVMe |
| Secondary Disk   | 4-10 TB NVMe |

**Suitable for:**
- Large production environments
- 20+ Tenants
- Dozens Kubernetes clusters
- Hundreds of Virtual Machines and Databases
- S3-compatible storage

{{% /tab %}}
{{< /tabs >}}

