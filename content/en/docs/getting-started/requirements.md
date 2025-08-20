---
title: "Requirements and Toolchain"
linkTitle: "Requirements"
description: "Prepare infrastructure and install the toolchain."
weight: 1
---

## Toolchain

You will need the following tools installed on your workstation:

-   [talosctl](https://www.talos.dev/v1.10/talos-guides/install/talosctl/), the command line client for Talos Linux.
-   [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl), the command line client for Kubernetes.
-   [Talm](https://github.com/cozystack/talm?tab=readme-ov-file#installation), Cozystack's own configuration manager for Talos Linux:<br>
    
    ```bash
    curl -sSL https://github.com/cozystack/talm/raw/refs/heads/main/hack/install.sh | sh -s
    ```

## Hardware Requirements

To run this tutorial, you will need the following setup:

**Cluster nodes:** three bare-metal servers or virtual machines in the following minimal configuration:

-   CPU: 4 cores, `x86` architecture.
-   RAM: 16 GiB.
-   Hard disks:
    -   HDD1: 32GiB<br>Primary disk, used for Talos Linux, etcd storage, and downloaded images.
    -   HDD2: 100GiB<br>Secondary disk, used for user application data.
-   OS:
    -   Any Linux distribution, for example, Ubuntu.<br>
    -   There are [other installation methods]({{% ref "/docs/install/talos" %}}) which require either any Linux or no OS at all to start. 
-   Networking:
    -   Routable FQDN domain.<br>If you don't have one, you can use [nip.io](https://nip.io/) with dash notation
    -   Located in the same L2 network segment.
-   Anti-spoofing disabled.<br>
    It is required for MetalLB, the load balancer used in Cozystack.
-   If using virtual machines, there are extra requirements:
    -   CPU passthrough enabled and CPU model set to `host` in the hypervisor settings.
    -   Nested virtualization enabled.<br>
        Required for virtual machines and tenant kubernetes clusters.

For a more detailed explanation of hardware requirements for different setups, refer to the [Hardware Requirements]({{% ref "/docs/install/hardware-requirements" %}})
    
