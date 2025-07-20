---
title: Use Talm to bootstrap a Cozystack cluster
linkTitle: Talm
description: "`talm` is a declarative CLI tool made by Cozystack devs and optimized for deploying Cozystack.<br> Recommended for infrastructure-as-code and GitOps."
weight: 5
aliases:
  - /docs/talos/configuration/talm
  - /docs/operations/talos/configuration/talm
---

This guide explains how to prepare a Talos Linux cluster for deploying Cozystack using
[Talm](https://github.com/cozystack/talm) — a Helm-like utility for declarative configuration management of Talos Linux.

Talm was created by Ænix to allow more declarative and custom configurations for cluster management.
It comes with pre-built presets for Cozystack.

## Prerequisites

By the start of this guide you should have Talos OS installed, but not initialized (bootstrapped), on several nodes.
These nodes should belong to one subnet or have public IPs.

This guide uses an example where the nodes of a cluster are located in the subnet `192.168.123.0/24`, having the following IP addresses:

- `192.168.123.11`
- `192.168.123.12`
- `192.168.123.13`

{{% alert color="info" %}}
If you are using DHCP, you might not be aware of the IP addresses assigned to your nodes.
You can use `nmap` to find them, providing your network mask (`192.168.123.0/24` in the example):

```bash
nmap -Pn -n -p 50000 192.168.123.0/24 -vv | grep 'Discovered'
```

Example output:

```console
Discovered open port 50000/tcp on 192.168.123.11
Discovered open port 50000/tcp on 192.168.123.12
Discovered open port 50000/tcp on 192.168.123.13
```
{{% /alert %}}


## 1. Initialize Cluster Configuration

The first step is to initialize configuration templates and adjust them

Start working with Talm by initializing configuration for a new cluster:

```bash
mkdir -p cluster1
cd cluster1
talm init --preset cozystack
```

The structure of the project mostly mirrors an ordinary Helm chart:

- `charts` - a directory that includes a common library chart with functions used for querying information from Talos Linux.
- `Chart.yaml` - a file containing the common information about your project; the name of the chart is used as the name for the newly created cluster.
- `templates` - a directory used to describe templates for the configuration generation.
- `secrets.yaml` - a file containing secrets for your cluster.
- `values.yaml` - a common values file used to provide parameters for the templating.
- `nodes` - an optional directory used to describe and store generated configuration for nodes.

### 1.1. Edit Configuration Templates

You're free to edit `Chart.yaml`, `values.yaml`, and `templates/*` to meet your environment requirements.

### 1.2 Apply Keycloak Configuration

To configure Keycloak as an OIDC provider, apply the following changes:

-   For Talm v0.6.6 or later: in `cluster1/templates/_helpers.tpl` replace `keycloak.example.com` with `keycloak.<your-domain.tld>`.

-   For Talm earlier than v0.6.6, update `cluster1/templates/_helpers.tpl` in the following way:

    ```yaml
     cluster:
       apiServer:
         extraArgs:
           oidc-issuer-url: "https://keycloak.example.com/realms/cozy"
           oidc-client-id: "kubernetes"
           oidc-username-claim: "preferred_username"
           oidc-groups-claim: "groups"
    ```

## 2. Generate Node Configuration Files

Next step is to make node configuration files from templates.
Create a `nodes` directory and collect the information from each node into a node-specific file:

```bash
mkdir nodes
talm template -e 192.168.123.11 -n 192.168.123.11 -t templates/controlplane.yaml -i > nodes/node1.yaml
talm template -e 192.168.123.12 -n 192.168.123.12 -t templates/controlplane.yaml -i > nodes/node2.yaml
talm template -e 192.168.123.13 -n 192.168.123.13 -t templates/controlplane.yaml -i > nodes/node3.yaml
```

The `--insecure` (`-i`) parameter is required because Talm must retrieve configuration data
from Talos nodes that are not initialized yet, awaiting in maintenance mode, and therefore unable to accept an authenticated connection.
The nodes will be initialized only on the next step, with `talm apply`.

## 3. Apply Node Configuration

Check the files generated in the previous step.
If everything is okay, apply the configuration to each node:

```bash
talm apply -f nodes/node1.yaml -i
talm apply -f nodes/node2.yaml -i
talm apply -f nodes/node3.yaml -i
```

Wait until all nodes have rebooted.
If an installation media was used, such as a USB stick, remove it to ensure that the nodes boot from the internal disk.

Later on, you can also use the following options:

- `--dry-run` - dry run mode will show a diff with the existing configuration.
- `-m try` - try mode will roll back the configuration in 1 minute.

## 4. Bootstrap and Access the Cluster

Run `talm bootstrap` on a single control-plane node — it is enough to bootstrap the whole cluster:

```bash
talm bootstrap -f nodes/node1.yaml
```

To access the cluster, generate an administrative `kubeconfig`:

```bash
talm kubeconfig kubeconfig -f nodes/node1.yaml
```

Export the `KUBECONFIG` variable:
```bash
export KUBECONFIG=$PWD/kubeconfig
```

Check that the cluster is available with this new `kubeconfig`:

```bash
kubectl get ns
```

Example output:

```console
NAME              STATUS   AGE
default           Active   7m56s
kube-node-lease   Active   7m56s
kube-public       Active   7m56s
kube-system       Active   7m56s
```

{{% alert color="info" %}}
:warning: All nodes will show as `READY: False`, which is normal at this step.
This happens because the default CNI plugin was disabled in the previous step to enable Cozystack installing its own CNI plugin.
{{% /alert %}}

Now you have a Kubernetes cluster prepared for installing Cozystack.
To complete the installation, follow the deployment guide, starting with the
[Install Cozystack]({{% ref "/docs/getting-started/install-cozystack" %}}) section.