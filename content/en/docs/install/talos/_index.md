---
title: "Installing Talos Linux on Bare Metal or Virtual Machines"
linkTitle: "1. Install Talos"
description: "Step 1: Installing Talos Linux on virtual machines or bare metal, ready to bootstrap Cozystack cluster."
weight: 10
aliases:
  - /docs/talos/installation
  - /docs/talos/install
  - /docs/operations/talos/installation
  - /docs/operations/talos
---

**The first step** in deploying a Cozystack cluster is to install Talos Linux on your bare-metal servers or virtual machines.
Ensure the VMs or bare-metal servers are provisioned before you begin.
To plan the installation, see the [hardware requirements]({{% ref "/docs/install/hardware-requirements" %}}).

If this is your first time installing Cozystack, consider [starting with the Cozystack tutorial]({{% ref "/docs/getting-started" %}}).

## Installation Options

There are several methods to install Talos on any bare metal server or virtual machine.
They have various limitations and optimal use cases:

-   **Recommended:** [Boot to Talos Linux from another Linux OS using `boot-to-talos`]({{% ref "/docs/install/talos/boot-to-talos" %}}) —
    a simple installation method, which can be used completely from userspace, and with no external dependencies except the Talos image.

    Choose this option if you are new to Talos or if you have VMs with pre-installed OS from a cloud provider.
-   [Boot to Talos Linux from another Linux OS using `kexec`]({{% ref "/docs/install/talos/kexec" %}}) — another simple installation method,
    but with some extra requirements. 
-   [Install using temporary DHCP and PXE servers running in Docker containers]({{% ref "/docs/install/talos/pxe" %}}) — 
    requires an extra management machine, but allows for installing on multiple hosts at once.
-   [Install using ISO image]({{% ref "/docs/install/talos/iso" %}}) — optimal for systems which can automate ISO installation.

## Further Steps

-   After installing Talos Linux, you will have a number of nodes ready for the next step, which is to
    [install and bootstrap a Kubernetes cluster]({{% ref "/docs/install/kubernetes" %}}).
    
-   Read the [Talos Linux overview]({{% ref "/docs/guides/talos" %}}) to learn why Talos Linux is the optimal OS choice for Cozystack
    and what it brings to the platform.
