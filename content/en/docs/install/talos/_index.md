---
title: "Installing Talos Linux on Bare Metal or Virtual Machines"
linkTitle: "1. Installing Talos"
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

After installing Talos Linux, you will have a number of nodes ready to be 
[bootstrapped with Cozystack configuration]({{% ref "/docs/install/kubernetes" %}}).

If this is your first time installing Cozystack, [start with the Cozystack tutorial]({{% ref "/docs/getting-started" %}}).

There are several methods to install Talos:

- [Quick-start Talos from another running Linux OS]({{% ref "/docs/install/talos/kexec" %}}).
- [Install using temporary DHCP and PXE servers]({{% ref "/docs/install/talos/pxe" %}}) running in Docker containers.
- [Install using ISO]({{% ref "/docs/install/talos/iso" %}}).

There are also specific guides for cloud providers, covering all the steps from preparing infrastructure to installing and configuring Cozystack.
If that's your case, we recommend using the guides below:

- [Hetzner]({{% ref "/docs/install/providers/hetzner" %}})
- [Oracle Cloud Infrastructure (OCI)]({{% ref "/docs/install/providers/oracle-cloud" %}})
- [Servers.com]({{% ref "/docs/install/providers/servers-com" %}})

Finally, if you want to learn why we use Talos Linux, check out the [Talos Linux overview]({{% ref "/docs/guides/talos" %}}).
