---
title: "Cozystack Architecture and Platform Stack"
linkTitle: "Platform Stack"
description: "Learn of the core components that power the functionality and flexibility of Cozystack"
weight: 15
---

This article explains Cozystack composition through its four layers, and shows the role and value of each component in the platform stack.

## Overview

To understand Cozystack composition, it's helpful to view it as sub-systems, layered from hardware to user-facing:

![Cozystack Architecture Layers](cozystack-layers.png)

## Layer 1: OS and Hardware

This is a foundation layer, providing cluster functionality on bare metal.
It consists of Talos Linux and a Kubernetes cluster installed on Talos.

### Talos Linux
                                       
Talos Linux is a Linux distribution made and optimized for one job: to run Kubernetes.
It is the foundation of reliability and security in Cozystack cluster.
Selecting it enables Cozystack to strictly limit the technology stack and make the system stable as a rock.

Let's see why Cozystack developers chose Talos and what it brings to Cozystack.

#### Reliable and Straightforward

Talos Linux is an immutable OS that's managed through an API.
It has no moving parts, no traditional package manager, no file structure, and no ability to run anything except Kubernetes containers.

The base layer of the platform includes the latest version of the kernel, all the necessary kernel modules, 
container runtime and a Kubernetes-like API for interacting with the system.
Updating the system is done by rewriting the Talos image "as is" entirely onto the hard drive.


#### Scalable and Reproducible

Talos Linux implements the infrastructure-as-code principle.
Talos is configured via an external, declarative manifest that can be version‑controlled in Git and
reused for all operations such as re-deploying the same cluster, adding extra nodes, and such.

When you discover an optimal configuration or solve an operational problem,
you apply it once in the manifest and instantly propagate the change to any number of nodes, making scale‑out trivial.
All nodes automatically converge to exactly the same configuration, eliminating configuration drift and making troubleshooting deterministic.

#### Tailored for Kubernetes

Talos contains built‑in logic to bootstrap and maintain a Kubernetes cluster, reducing the cognitive load of the first cluster installation.
It provides full lifecycle management of both the operating system and Kubernetes itself through a single `talosctl` command set, 
covering upgrades, node replacement, and disaster recovery.

#### Fine‑tuned for Cozystack

Cozystack ships a curated Talos build that already includes the extensions and kernel modules required by its storage,
networking, and observability stack, so clusters come up production‑ready out of the box.


### Kubernetes

Kubernetes has already become a kind of de facto standard for managing server workloads.

One of the key features of Kubernetes is a convenient and unified API that is understandable to everyone (everything is YAML). Also, the best software design patterns that provide continuous recovery in any situation (reconciliation method) and efficient scaling to a large number of servers.

This fully solves the integration problem, since all existing virtualization platforms have an outdated and rather complex APIs that cannot be extended without modifying the source code. As a result, there is always a need to create your own custom solutions, which requires additional effort.

## Layer 2: Infrastructure Services

Second layer contains the key components which perform major roles such as storage, networking, and virtualization.
Adding these components to the base Kubernetes cluster makes it much more functional.

### Flux CD

FluxCD provides a simple and uniform interface for both installing all platform components and managing their lifecycle.
Cozystack developers have adopted FluxCD as the core element of the platform, believing it sets a new industry standard for platform engineering. 

### KubeVirt

KubeVirt brings virtualization capability to Cozystack.
It enables creating virtual machines and worker nodes for tenant Kubernetes clusters.

KubeVirt is a project started by global industry leaders with a common vision to unify Kubernetes and a desire to introduce it to the world of virtualization.
It extends the capabilities of Kubernetes by providing convenient abstractions for launching and managing virtual machines,
as well the all related entities such as snapshots, presets, virtual volumes, and more.

At the moment, the KubeVirt project is being jointly developed by such world-famous companies as RedHat, NVIDIA, ARM.

### DRBD and LINSTOR

DRBD and LINSTOR are the foundation of replicated storage in Cozystack.

DRBD is the fastest replication block storage running right in the Linux kernel.
When DRBD only deals with data replication, time-tested technologies such as LVM or ZFS are used to securely store the data.
The DRBD kernel module is included in the mainline Linux kernel and has been used to build fault-tolerant systems for over a decade.

DRBD is managed using LINSTOR, a system integrated with Kubernetes.
LINSTOR is a management layer for creating virtual volumes based on DRBD.
It enables managing hundreds or thousands of virtual volumes in the Cozystack cluster.

### Kube-OVN

The networking functionality in Cozystack is based on Kube-OVN and Cilium.

OVN is a free implementation of virtual network fabric for Kubernetes and OpenStack based on the Open vSwitch technology.
With Kube-OVN, you get a robust and functional virtual network that ensures reliable isolation between tenants and provides floating addresses for virtual machines.

In the future, this will enable seamless integration with other clusters and customer network services.

### Cilium

Utilizing Cilium in conjunction with OVN enables the most efficient and flexible network policies,
along with a productive services network in Kubernetes, leveraging an offloaded Linux network stack featuring the cutting-edge eBPF technology.

Cilium is a highly promising project, widely adopted and supported by numerous cloud providers worldwide.

## Layer 3: Platform Services

These are components that provide the user-side functionality to Cozystack and its managed applications.

### Kamaji

Cozystack uses Kamaji Control Plane to deploy tenant Kubernetes clusters.
Kamaji provides a straightforward and convenient method for launching all the necessary Kubernetes control-plane in containers.
Worker nodes are then connected to these control planes and handle user workloads.

The approach developed by the Kamaji project is modeled after the design of modern clouds and ensures security by design
where end users do not have any control plane nodes for their clusters.

### Grafana

Grafana with Grafana Loki and the OnCall extension provides a single interface to Observability.
It allows you to conveniently view charts, logs and manage alerts for your infrastructure and applications.

### Victoria Metrics

Victoria Metrics allows you to most efficiently collect, store and process metrics in the Open Metrics format,
doing it more efficiently than Prometheus in the same setup.

### MetalLB

MetalLB is the default load balancer for Kubernetes;
with its help, your services can obtain public addresses that are accessible not only from inside,
but also from outside your cluster network.

### HAProxy

HAProxy is an advanced and widely known TCP balancer.
It continuously checks service availability and carefully balances production traffic between them in real time.

See the application reference: [`tcp-balancer`]({{% ref "/docs/reference/applications/tcp-balancer" %}})

### SeaweedFS

SeaweedFS is a simple and highly scalable distributed file system designed for two main objectives:
to store billions of files and to serve the files faster. It allows access O(1), usually just one disk read operation.

### Kubernetes Operators

Cozystack includes a set of Kubernetes operators, used for managing system services and managed applications.

## Layer 4: User-side services

Cozystack is shipped with a number of user-side applications, pre-configured for reliability and resource efficiency,
coming with monitoring and observability included:

-   [Managed applications]({{% ref "../applications" %}}), such as databases and queues.
-   [Tenant Kubernetes clusters]({{% ref "../applications#tenant-kubernetes-cluster" %}}), fully-functional managed Kubernetes clusters for development and production workloads.
-   [Virtual machines]({{% ref "/docs/operations/virtualization/virtual-machines" %}}), supporting Linux and Windows OS.
