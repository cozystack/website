---
title: "0. Requirements and Toolchain"
linkTitle: "0. Requirements"
description: "Prepare VMs and install required CLI tools on your machine before running this tutorial."
weight: 1
---

## Requirements

To run this tutorial, you will need the following setup:

-   A **management host**, which can be your workstation or a virtual machine:
    -   [Docker](https://docs.docker.com/engine/install/) and [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed
    -   Network access to the cluster nodes

-   **Cluster nodes:** three virtual machines in the following minimal configuration:

    -   CPU: 4 cores, `x86` architecture.
    -   RAM: 16 GiB
    -   HDD1: 32GiB (primary disk used for Talos Linux)
    -   HDD2: 100GiB (secondary disk used for images and user application data)
    -   Located in the same L2 network segment
    -   Nested virtualization enabled
    -   Anti-spoofing disabled
    -   CPU passthrough enabled
    -   CPU model set to `host` in the hypervisor settings
    
---

![Cozystack deployment](/img/cozystack-deployment.png)
