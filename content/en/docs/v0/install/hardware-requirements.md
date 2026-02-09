---
title: "Hardware requirements"
linkTitle: "Hardware Requirements"
description: "Define the hardware requirements for your Cozystack use case."
weight: 5
aliases:
  - /docs/v0/getting-started/hardware-requirements
  - /docs/v0/talos/hardware-requirements
---

Cozystack utilizes [Talos Linux]({{% ref "/docs/v0/guides/talos" %}}), a minimalistic Linux distribution designed solely to run Kubernetes.
Usually, this means you cannot share a server with any services other than those run by Cozystack.
The good news is that whichever service you need, Cozystack will run it perfectly: securely, efficiently, and
in a fully containerized or virtualized environment.

Hardware requirements depend on your usage scenario.
Below are several common deployment options; review them to determine which setup fits your needs best.

{{< include "docs/v0/install/_include/hardware-config-tabs.md" >}}

**Compute:**

- Three or more physical or virtual servers with amd64/x86_64 architecture, with the specifications shown in the table above.
- Virtualized servers need nested virtualization enabled and the CPU model set to `host` (without emulation).
- PXE installation requires an extra management instance connected to the same network, with any Linux system able to run a Docker container.
  It should also have `x86-64-v2` architecture, which most probably may be achieved by setting CPU model to `host` in case of a VM.

**Storage:**

Storage in a Cozystack cluster is used both by the system and by the user workloads.
There are two options: having a dedicated disk for each role or allocating space on system disk for user storage.
Low latency is critical for control-plane nodes storage, local SSDs are recommended. 

**Using two disks**

Separating disks by role is the primary and more reliable option.

- **Primary Disk**: This disk contains the Talos Linux operating system, essential system kernel modules and
  Cozystack system base pods, logs, and base container images. Also an etcd cluster will be running on top of it, so a low-latency volume should be used, preferably a local SSD.

  Minimum sizes vary by configuration (see table above). Talos installation expects `/dev/sda` as the system disk (virtio drives usually appear as `/dev/vda`).

- **Secondary Disk**: Dedicated to workload data and can be increased based on workload requirements.
  Used for provisioning volumes via PersistentVolumeClaims (PVCs).

  Minimum sizes vary by configuration (see table above). Disk path (usually `/dev/sdb`) will be defined in the storage configuration.
  It does not affect the Talos installation.

  Learn more about configuring Linstor StorageClass from the
  [Deploy Cozystack tutorial](https://cozystack.io/docs/getting-started/install-cozystack/#configure-storage)

**Using a single disk**

It's possible to use a single disk with space allocated for user storage.
See [How to install Talos on a single-disk machine]({{% ref "/docs/v0/install/how-to/single-disk" %}})
Using a local SSD disk is recommended.

**Networking:**

- Machines must be allowed to use additional IPs, or an external load balancer must be available.
  Using additional IPs is disabled by default and must be enabled explicitly in most public clouds.
- Additional public IPs for ingress and virtual machines may be needed. Check if your public cloud provider supports floating IPs.
- Routable FQDN domain (or use [nip.io](https://nip.io/) with dash notation)
- Located in the same L2 network segment
- Anti-spoofing disabled (required for MetalLB)
- Minimum 1 Gbps (10 Gbps recommended for production)
- Low latency between cluster nodes

## Production Cluster

For a production environment, consider the following:

**Compute:**

- Having at least **three worker nodes** is mandatory for running highly available applications.
  If one of the three nodes becomes unavailable due to hardware failure or maintenance, you’ll be operating in a degraded state.
  While database clusters and replicated storage will continue functioning, starting new database instances or creating replicated volumes won’t be possible.
- Having separate servers for Kubernetes master nodes is highly recommended, although not required.
  It’s much easier to take a pure worker node offline for maintenance or upgrades, than if it also serves as a management node.

**Networking:**

- In a setup with multiple data centers, it’s ideal to have direct, dedicated optical links between them.
- Servers must support out-of-band management (IPMI, iLO, iDRAC, etc.) to allow remote monitoring, recovery, and management.

## Distributed Cluster

You can build a [distributed cluster]({{% ref "/docs/v0/operations/stretched/" %}}) with Cozystack.

**Networking:**

- Distributed cluster requires both a fast and reliable network, and it **must** have low RTT (Round Trip Time), as
  Kubernetes is not designed to operate efficiently over high-latency networks.

  Data centers in the same city typically have less than 1 ms latency, which is ideal.
  The *maximum acceptable* RTT is 10 ms.
  Running Kubernetes or replicated storage over a network with RTT above 20 ms is strongly discouraged.
  To measure actual RTT, you can use the `ping` command.

- It's also recommended to have at least 2–3 nodes per data center in a distributed cluster.
  This ensures that the cluster would be able to survive one data center loss without major disruption.

- If it's hard to keep a single address space between data centers, instead of using some external VPN,
  you can enable **KubeSpan**, a Talos Linux feature that creates a WireGuard-backed full-mesh VPN between nodes.

## Highly Available Applications

Achieving high availability adds to the basic production environment requirements.

**Networking:**

- It is recommended to have multiple 10 Gbps (or faster) network cards.
  You can separate storage and application traffic by assigning them to different network interfaces.

- Expect a significant amount of horizontal, inter-node traffic inside clusters.
  It is usually caused by multiple replicas of services and databases deployed across different nodes exchanging data.
  Also, virtual machines with live migration require replicated volumes, which further increases the amount of traffic.

## System Resource Planning

For detailed recommendations on system resource allocation (CPU and memory) per node, based on cluster scale and number of tenants, refer to [System Resource Planning Recommendations]({{% ref "/docs/v0/install/resource-planning" %}}).
