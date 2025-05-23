---
title: Bootstrap a Talos Linux cluster for Cozystack using Talm
linkTitle: Talm
description: "Bootstrap a Talos Linux cluster for Cozystack using Talm"
weight: 5
aliases:
  - /docs/talos/configuration/talm
---

[Talm](https://github.com/cozystack/talm) is a Helm-like utility for declarative configuration management of Talos Linux.
It was created by Ænix to allow more declarative and custom configurations for cluster management.

Talm comes with pre-built presets for Cozystack.

## 1. Initialize Cluster Configuration

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

You're free to edit `Chart.yaml`, `values.yaml`, and `templates/*` to meet your environment requirements.

Be aware that your nodes are booted Talos Linux image and awaiting in maintenance mode.

{{% alert color="info" %}}
To configure your cluster for using Keycloak, apply the following change:

-   For Talm v0.6.6 or later: in `cluster1/templates/_helpers.tpl` replace  `keycloak.example.com` with your domain.
    
-   For Talm earlier than v0.6.6, update template args manually:

    ```yaml
     cluster:
       apiServer:
         extraArgs:
           oidc-issuer-url: "https://keycloak.example.com/realms/cozy"
           oidc-client-id: "kubernetes"
           oidc-username-claim: "preferred_username"
           oidc-groups-claim: "groups"
    ```
{{% /alert %}}

## 2. Make Node Configuration Files

Next step is to make node configuration files from templates.
You will need to know the nodes' IP addresses.

{{% alert color="info" %}}
If you are using DHCP, you might not be aware of the IP addresses assigned to your nodes.
You can use `nmap` to find them, providing your network mask (`192.168.100.0/24` in the example):

```bash
nmap -Pn -n -p 50000 192.168.100.0/24 -vv | grep 'Discovered'
```

Example output:

```
Discovered open port 50000/tcp on 192.168.100.63
Discovered open port 50000/tcp on 192.168.100.159
Discovered open port 50000/tcp on 192.168.100.192
```
{{% /alert %}}

Now, create a `nodes` directory and collect the information from your nodes into a node-specific file for each node:

```bash
mkdir nodes
talm template -e 192.168.100.63 -n 192.168.100.63 -t templates/controlplane.yaml -i > nodes/node1.yaml
talm template -e 192.168.100.159 -n 192.168.100.159 -t templates/controlplane.yaml -i > nodes/node2.yaml
talm template -e 192.168.100.192 -n 192.168.100.192 -t templates/controlplane.yaml -i > nodes/node3.yaml
```

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

In future operations, you can also use the following options:

- `--dry-run` - dry run mode will show a diff with the existing configuration.
- `-m try` - try mode will roll back the configuration in 1 minute.

## 4. Bootstrap and Access Cluster

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

Check connection:
```bash
kubectl get ns
```

example output:
```console
NAME              STATUS   AGE
default           Active   7m56s
kube-node-lease   Active   7m56s
kube-public       Active   7m56s
kube-system       Active   7m56s
```

{{% alert color="warning" %}}
:warning: All nodes should currently show as `READY: False`, which is normal.
This happens because in the previous step you have disabled the default CNI plugin .
Cozystack will install its own CNI-plugin on the next step.
{{% /alert %}}


Now you have a Kubernetes cluster prepared for installing Cozystack.
To complete the installation, follow the deployment guide, starting with the
[Install Cozystack]({{% ref "/docs/getting-started/first-deployment#install-cozystack" %}}) section.
