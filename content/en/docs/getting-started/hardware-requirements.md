---
title: "Hardware requirements"
linkTitle: "Hardware requirements"
description: "Plan your installation."
weight: 20
---

To estimate the hardware requirements for your Cozystack installation, first decide what you want to do with it.

The Cozystack platform runs on top of Talos Linux, which is a minimalistic operating system designed to run Kubernetes
only. It's not possible to "share" a server with other services.

## Proof-of-concept lab

Here are the baseline requirements for running a proof-of-concept installation:

* Three physical or virtual servers of amd64/x86_64 architecture, 16 GB RAM each
* We recommend having at least 4 CPU cores per server
* If servers are virtualized, ensure that nested virtualization is enabled, and the CPU model is set to `host` without
  emulation.
* The primary disk should be at least 32GB. Talos Linux will use it for the operating system, images and logs. Having
  more space is recommended.
* A secondary disk is required for the replicated storage system. 100GB is a good starting point, but the required size
  completely depends on what you are planning to run.
* Machines must be allowed to use additional IPs (this is disallowed by default and needs to be enabled explicitly in
  most public clouds), or an external load balancer must be available.
* If needed, additional public IPs for ingress and virtual machines must be available from the provider. Not all public
  cloud providers allow floating IPs.

## HA applications

For production environments, it's usually required to have several replicas of your services distributed across nodes.
These services usually create a significant amount of traffic between nodes. Database replicas also send traffic between
nodes. Virtual machines with the live migration option require replicated volumes which create a lot of traffic.

Therefore, for production environments, it's recommended to have several network cards of 10Gbps or more. It's possible
to split storage and other traffic across different sets of network cards.

## Distributed cluster

With some tuning, it's possible to create a [distributed cluster]({{% ref "/docs/operations/stretched/" %}}) with
Cozystack. The common requirements are a fast and reliable network **AND** low RTT (run the `ping` command between
locations to check what the actual RTT is). The *acceptable* RTT value is 10ms at most. Kubernetes is not designed to
run in a network with high latency. Two datacenters in a single city usually have less than 1ms latency, which is fine.
It's absolutely unacceptable to run Kubernetes and replicated storage over a network with RTT higher than 20ms.

It's also recommended to have at least 2-3 nodes per datacenter in a distributed cluster. So if an entire datacenter
loses connectivity, the cluster will survive the outage without much pain.

If there is no possibility to keep an internal network addressing scheme (VPN between datacenters), it's possible to use
KubeSpan: a Talos Linux feature that creates WireGuard-backed full mesh VPN between nodes.

## Production clusters

For a production environment, consider these options:

* It's recommended but not required to have separate servers for the Kubernetes control plane. It's possible to run the
  control plane on the same servers as workloads, but it's easier to shut down a pure worker node for maintenance or
  upgrade than a combined node.
* A minimum of three worker nodes is the BARE minimum to run HA applications. If you only have three nodes and any one
  of them goes down due to hardware failure, or for maintenance, it's an emergency. Database clusters and replicated
  storage will continue to run, but it will not be possible to start new database instances or create new replicated
  volumes.
* In a multi-datacenter setup, it's better to have direct dedicated optical lines between datacenters.
* Servers must have out-of-band management capabilities (IPMI, iLO, iDRAC, etc.) to allow remote management and
  recovery.
