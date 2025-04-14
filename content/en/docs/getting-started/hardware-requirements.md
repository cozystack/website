---
title: "Hardware requirements"
linkTitle: "Hardware Requirements"
description: "Define the hardware requirements for your Cozystack use case."
weight: 5
---

The Cozystack platform runs on top of Talos Linux, a minimalistic operating system designed solely to run Kubernetes.
It is **not** possible to "share" a bare server with other services.

The good news is that whatever other services you need to run, Cozystack can be the perfect platform to host them—securely,
efficiently, and in a fully containerized or virtualized environment.

Hardware requirements depend on your usage scenario.
Below are several common deployment options—review them to determine what setup best fits your needs.

## Proof-of-Concept Lab

Here are the baseline requirements for running a proof-of-concept installation.

**Compute:**

- Three physical or virtual servers with amd64/x86_64 architecture, each having at least 16 GB RAM and 4 CPU cores.
- If the servers are virtualized, ensure that nested virtualization is enabled and the CPU model is set to `host` (without emulation).
- A PXE installation requires an extra management VM or physical server connected to the same network,
  with any Linux system installed on it (for example, Ubuntu should be enough).
  This VM should support the `x86-64-v2` architecture, which most probably can be achieved by setting CPU model to `host`.

Storage:

- The primary disk should be at least 32 GB. Talos Linux uses it for the OS, images, and logs. It's better to have more space.  
- A secondary disk is required for the replicated storage system. 100 GB is a good starting point, but the actual size depends entirely on your workload.

**Networking:**

- Machines must be allowed to use additional IPs (this is typically disabled by default and must be enabled explicitly in most public clouds), 
  or an external load balancer must be available.
- Additional public IPs for ingress and virtual machines may be needed. Not all public cloud providers support floating IPs.


## Production Clusters

For a production environment, consider the following recommendations:

**Compute:**

- A minimum of **three worker nodes** is the bare minimum to run HA applications.
  If one of the three nodes becomes unavailable—due to hardware failure or maintenance—you’ll be operating in a degraded state.
  While database clusters and replicated storage will continue functioning, it won’t be possible to start new database instances or create new replicated volumes.
- Having separate servers for the Kubernetes control plane is highly recommended, although not required.
  It’s much easier to take a pure worker node offline for maintenance or upgrades, than if it also serves as a management node.

**Networking:**

- In a multi-datacenter setup, it’s ideal to have direct, dedicated optical links between datacenters.
- Servers must support out-of-band management (IPMI, iLO, iDRAC, etc.) to allow remote monitoring, recovery, and management.

## Distributed Cluster

You can build a [distributed cluster]({{% ref "/docs/operations/stretched/" %}}) with Cozystack.

**Networking:**

- Distributed cluster requires both a fast and reliable network **and** low RTT (Round Trip Time), because
  Kubernetes is not designed to operate efficiently over high-latency networks.

  Two datacenters in the same city typically have less than 1 ms latency, which is ideal.
  The *maximum acceptable* RTT is 10 ms.
  Running Kubernetes or replicated storage over a network with RTT above 20 ms is strongly discouraged.
  Use the `ping` command between locations to measure actual RTT.

- It's also recommended to have at least 2–3 nodes per datacenter in a distributed cluster.
  This ensures that if one datacenter loses connectivity, the cluster can survive the outage without major disruption.

- If it's impossible to keep an internal network addressing scheme (such as VPN between datacenters),
  you can enable **KubeSpan**—a Talos Linux feature that creates a WireGuard-backed full-mesh VPN between nodes.

## High-Availability applications

**Networking:**

- For production environments, it is recommended to have multiple 10 Gbps (or faster) network cards.
  You can separate storage and application traffic by assigning them to different network interfaces.

  In production environments, high availability typically requires running multiple replicas of services across different nodes.
  These services often generate significant inter-node traffic.
  Database replicas also exchange data, and virtual machines with live migration require replicated volumes, which further increase traffic.
 