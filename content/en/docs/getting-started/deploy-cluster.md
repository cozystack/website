---
title: "1. Deploy Talos Linux and bootstrap a Kubernetes cluster"
linkTitle: "1. Deploy Talos and Kubernetes"
description: "Install our distribution of Talos Linux on a set of virtual machines. Use Talm CLI to bootstrap a Kubernetes cluster, ready for Cozystack."
weight: 10
aliases:
  - first-deployment
---

## Before you begin

Make sure that you have nodes (bare metal servers or VMs) that fit the
[hardware requirements]({{% ref "/docs/getting-started/requirements" %}}).

## Objectives

On this step of the tutorial you will bootstrap a Kubernetes cluster on Talos Linux,
and make sure that it is ready to install Cozystack.

The tutorial will guide you through the following steps:

1.  Install Talos Linux on your nodes or start it from another OS using `kexec`.
1.  Bootstrap Talos to run a Kubernetes cluster.
1.  Get a kubeconfig, check cluster status, and prepare to install Cozystack.


### 1 Install Talos Linux

Boot your machines with Talos Linux image in one of these ways:

- [Quick-start Talos from another running Linux OS]({{% ref "/docs/talos/install/kexec" %}}).
- [Install using temporary DHCP and PXE servers]({{% ref "/docs/talos/install/pxe" %}}) running in Docker containers.
- [Install using ISO]({{% ref "/docs/talos/install/iso" %}}).

### 2 Bootstrap Talos Cluster

Bootstrap your Talos Linux cluster using one of the following tools:

- [Talm]({{% ref "/docs/talos/bootstrap/talm" %}}), for a declarative way of cluster management.
- [talosctl]({{% ref "/docs/talos/bootstrap/talosctl" %}}), for using native `talosctl` tool.
- [talos-bootstrap]({{% ref "/docs/talos/bootstrap/talos-bootstrap" %}}), for an interactive walkthrough.

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

