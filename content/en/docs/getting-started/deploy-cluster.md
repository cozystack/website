---
title: "1. Deploy Talos Linux and bootstrap a Kubernetes cluster"
linkTitle: "1. Deploy Talos and Kubernetes"
description: "Install our distribution of Talos Linux on a set of virtual machines. Use Talm CLI to bootstrap a Kubernetes cluster, ready for Cozystack."
weight: 10
aliases:
  - first-deployment
---


## Before you begin

This tutorial assumes that you deploy a Cozystack cluster on virtual machines,
which is the most universal and simple way.
Make sure you have VMs and a management host that match the [requirements]({{% ref "/docs/getting-started/requirements" %}}).

## Objectives

This tutorial shows how to bootstrap Cozystack.
It will guide you through the following steps:

1.  Install Talos Linux on virtual machines
1.  Bootstrap Talos to run a Kubernetes cluster
1.  Get a kubeconfig, check cluster status, and prepare to install Cozystack


### 1 Install Talos Linux

Boot your machines with Talos Linux image in one of these ways:

- [Install using temporary DHCP and PXE servers](/docs/talos/install/pxe/) running in Docker containers.
- [Install using ISO](/docs/talos/install/iso/).
- [Install on Hetzner servers](/docs/talos/install/hetzner/).


### 2 Bootstrap Talos Cluster

Bootstrap your Talos Linux cluster using one of the following tools:

- [**Talm**]({{% ref "/docs/talos/bootstrap/talm" %}}), for a declarative way of cluster management.
- [**talosctl**]({{% ref "/docs/talos/bootstrap/talosctl" %}}), for using native `talosctl` tool.
- [**talos-bootstrap**]({{% ref "/docs/talos/bootstrap/talos-bootstrap" %}}), for an interactive walkthrough.

{{< tabs name="Bootstrapping tools" >}}
{{% tab name="Talm" %}}
Talm is a utility tool for bootstrapping and managing Talos clusters in a declarative way.

Visit the [releases page](https://github.com/cozystack/talm/releases) for the latest Talm binaries
or use the universal installation script:

```bash
curl -sSL https://github.com/cozystack/talm/raw/refs/heads/main/hack/install.sh | sh -s
talm --help
```
{{% /tab %}}

{{% tab name="talos-bootstrap" %}}
[talos-bootstrap](https://github.com/cozystack/talos-bootstrap/) is an interactive script for bootstrapping Kubernetes clusters on Talos OS.

```bash
sudo curl -fsSL -o /usr/local/bin/talos-bootstrap \
    https://github.com/cozystack/talos-bootstrap/raw/master/talos-bootstrap
sudo chmod +x /usr/local/bin/talos-bootstrap
talos-bootstrap --help
```
{{% /tab %}}
{{< /tabs >}}

### Existing cluster or other Kubernetes distributions

For a first tutorial run, it's strongly recommended to install Cozystack on bare metal.
However, Cozystack can also be installed in other ways, including on top of a provided managed Kubernetes cluster.

If you bootstrap your Talos cluster in your own way, or use a different Kubernetes distribution, make sure
to apply all settings from the guides above.
These settings are mandatory:

* All CNI plugins must be disabled, as Cozystack will install its own plugin.
* Kubernetes cluster DNS domain must be set to `cozy.local`.
* Listening address of some Kubernetes components must be changed from `localhost` to a routeable address.
* Kubernetes API server must be reachable on `localhost`.
