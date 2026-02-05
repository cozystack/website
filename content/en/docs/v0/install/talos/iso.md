---
title: Install Talos Linux using ISO
linkTitle: ISO
description: "How to install Talos Linux using ISO"
weight: 20
aliases:
  - /docs/talos/installation/iso
  - /docs/talos/install/iso
  - /docs/operations/talos/installation/iso
---

This guide explains how to install Talos Linux on bare metal servers or virtual machines.
Note that Cozystack provides its own Talos builds, which are tested and optimized for running a Cozystack cluster.

## Installation

1.  Download Talos Linux asset from the Cozystack's [releases page](https://github.com/cozystack/cozystack/releases).

    ```bash
    wget https://github.com/cozystack/cozystack/releases/latest/download/metal-amd64.iso
    ```

1.  Boot your machine with ISO attached.

1.  Click **<F3>** and fill your network settings:

    ![Cozystack for private cloud](/img/talos-network-configuration.png)

## Next steps

Once you have installed Talos, proceed by [installing and bootstrapping a Kubernetes cluster]({{% ref "/docs/install/kubernetes" %}}).
