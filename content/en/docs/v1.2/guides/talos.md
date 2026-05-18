---
title: "Talos Linux in Cozystack"
linkTitle: "Talos Linux"
description: "Learn why Cozystack uses Talos Linux as the foundation for its Kubernetes clusters. Discover the benefits of Talos Linux, including reliability, scalability, and Kubernetes optimization."
weight: 30
---

## Why Cozystack is Using Talos Linux
                                       
Talos Linux is a Linux distribution made and optimized for one job: to run Kubernetes.
It is the foundation of reliability and security in Cozystack cluster.
Selecting it enables Cozystack to strictly limit the technology stack and make the system stable as a rock.

Let's see why Cozystack developers chose Talos as the foundation of a Kubernetes cluster and what it brings to Cozystack.

### Reliable and Straightforward

Talos Linux is an immutable OS that's managed through an API.
It has no moving parts, no traditional package manager, no file structure, and no ability to run anything except Kubernetes containers.

The base layer of the platform includes the latest version of the kernel, all the necessary kernel modules, 
container runtime and a Kubernetes-like API for interacting with the system.
Updating the system is done by rewriting the Talos image "as is" entirely onto the hard drive.


### Scalable and Reproducible

Talos Linux implements the infrastructure-as-code principle.
Talos is configured via an external, declarative manifest that can be version‑controlled in Git and
reused for all operations such as re-deploying the same cluster, adding extra nodes, and such.

When you discover an optimal configuration or solve an operational problem,
you apply it once in the manifest and instantly propagate the change to any number of nodes, making scale‑out trivial.
All nodes automatically converge to exactly the same configuration, eliminating configuration drift and making troubleshooting deterministic.

### Tailored for Kubernetes

Talos contains built‑in logic to bootstrap and maintain a Kubernetes cluster, reducing the cognitive load of the first cluster installation.
It provides full lifecycle management of both the operating system and Kubernetes itself through a single `talosctl` command set, 
covering upgrades, node replacement, and disaster recovery.

### Fine‑tuned for Cozystack

Cozystack ships a curated Talos build that already includes the extensions and kernel modules required by its storage,
networking, and observability stack, so clusters come up production‑ready out of the box.