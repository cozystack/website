---
title: Use Talm to bootstrap a Cozystack cluster
linkTitle: Talm
description: "`talm` is a declarative CLI tool made by Cozystack devs and optimized for deploying Cozystack.<br> Recommended for infrastructure-as-code and GitOps."
weight: 5
aliases:
  - /docs/operations/talos/configuration/talm
  - /docs/talos/bootstrap/talm
  - /docs/talos/configuration/talm
---

This guide explains how to install and configure Kubernetes on a Talos Linux cluster using Talm.
As a result of completing this guide you will have a Kubernetes cluster ready to install Cozystack.

[Talm](https://github.com/cozystack/talm) is a Helm-like utility for declarative configuration management of Talos Linux.
Talm was created by Ænix to allow more declarative and customizable configurations for cluster management.
Talm comes with pre-built presets for Cozystack.

## Prerequisites

By the start of this guide you should have [Talos Linux installed]({{% ref "/docs/install/talos" %}}), but not initialized (bootstrapped), on several nodes.
These nodes should belong to one subnet or have public IPs.

This guide uses an example where the nodes of a cluster are located in the subnet `192.168.123.0/24`, having the following IP addresses:

- `node1`: private `192.168.123.11` or public `12.34.56.101`.
- `node2`: private `192.168.123.12` or public `12.34.56.102`.
- `node3`: private `192.168.123.13` or public `12.34.56.103`.

Public IPs are optional.
All you need for an installation with Talm is to have access to the nodes: directly, through VPN, bastion host, or other means.
This guide will use private IPs as a default option in examples, and public IPs in instructions and examples which are specific for the public IP setup.

If you are using DHCP, you might not be aware of the IP addresses assigned to your nodes in the private subnet.
Nodes with Talos Linux [expose Talos API on port `50000`](https://www.talos.dev/v1.10/learn-more/talos-network-connectivity/).
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


## 1. Install Dependencies

For this guide, you need a couple of tools installed:

-   **Talm**.
    To install the latest build for your platform, download and run the installer script:
    
    ```bash
    curl -sSL https://github.com/cozystack/talm/raw/refs/heads/main/hack/install.sh | sh -s
    ```
    Talm has binaries built for Linux, macOS, and Windows, both AMD and ARM.
    You can also [download a binary from GitHub](https://github.com/cozystack/talm/releases) 
    or [build Talm from the source](https://github.com/cozystack/talm).
    

-   **talosctl** is distributed as a brew package:

    ```bash
    brew install siderolabs/tap/talosctl
    ```

    For more installation options, see the [`talosctl` installation guide](https://www.talos.dev/v1.9/talos-guides/install/talosctl/)

## 2. Initialize Cluster Configuration

The first step is to initialize configuration templates and provide configuration values for templating.


### 2.1 Initialize Configuration

Start by initializing configuration for a new cluster, using the `cozystack` preset:

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


### 2.2. Edit Configuration Values and Templates

The power of Talm is in templating.
There are several files with source values and templates which you can edit: `Chart.yaml`, `values.yaml`, and `templates/*`.
Talm uses these values and templates to generate Talos configuration for all nodes in the cluster, both control plane and workers.

All configuration values that are often changed, are placed in `values.yaml`:

```yaml
## Used to access the cluster's control plane
endpoint: "https://192.168.100.10:6443"
## Cozystack API cluster domain — used by services and tenant K8s clusters to access the management cluster
clusterDomain: cozy.local
## Floating IP — should be an unused IP in the same subnet as nodes
floatingIP: 192.168.100.10
## Talos source image: use the latest available version
## https://github.com/cozystack/cozystack/pkgs/container/cozystack%2Ftalos
image: "ghcr.io/cozystack/cozystack/talos:v1.10.5"
## Pod subnet — used to assign IPs to pods
podSubnets:
- 10.244.0.0/16
## Service subnet — used to assign IPs to services
serviceSubnets:
- 10.96.0.0/16
## Subnet with node IPs
advertisedSubnets:
- 192.168.100.0/24
## Add OIDC issuer URL to enable OIDC — see comments below.
oidcIssuerUrl: ""
certSANs: []
```

You don't need to fill in the node IPs at this step.
Instead, you will provide them later, when you generate node configurations.


### 2.3 Add Keycloak Configuration

By default, the cluster will be accessible only by authentication with a token.
However, you can configure an OIDC provider to use account-based authentication.
This configuration starts at this step and continues later, after installing Cozystack.

To configure Keycloak as an OIDC provider, apply the following changes to the templates:

-   For Talm v0.6.6 or later: in `./templates/_helpers.tpl` replace `keycloak.example.com` with `keycloak.<your-domain.tld>`.

-   For Talm earlier than v0.6.6, update `./templates/_helpers.tpl` in the following way:

    ```yaml
     cluster:
       apiServer:
         extraArgs:
           oidc-issuer-url: "https://keycloak.example.com/realms/cozy"
           oidc-client-id: "kubernetes"
           oidc-username-claim: "preferred_username"
           oidc-groups-claim: "groups"
    ```


## 3. Generate Node Configuration Files

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


## 4. Apply Configuration and Bootstrap a Cluster

At this point, the configuration files in `node/*.yaml` are ready for applying to nodes.


### 4.1 Apply Configuration Files

Use `talm apply` to apply the configuration files to the corresponding nodes:

```bash
talm apply -f nodes/node1.yaml -i
talm apply -f nodes/node2.yaml -i
talm apply -f nodes/node3.yaml -i
```

This command initializes nodes, setting up authenticated connection, so that `-i` (`--insecure`) won't be required further on.
If the command succeeded, it will return the node's IP:

```console
$ talm apply -f nodes/node1.yaml -i
- talm: file=nodes/node1.yaml, nodes=[192.168.123.11], endpoints=[192.168.123.11]
```

Later on, you can also use the following options with `talm apply`:

- `--dry-run` - dry run mode will show a diff with the existing configuration without making changes.
- `-m try` - try mode will roll back the configuration in 1 minute.


### 4.2 Wait for Reboot

Wait until all nodes have rebooted.
If an installation media was used, such as a USB stick, remove it to ensure that the nodes boot from the internal disk.

When nodes are ready, they will expose port `50000`, which is a sign that the node has completed Talos configuration and rebooted.
If you need to automate the node readiness check, consider this example:

```bash
timeout 60 sh -c 'until \
  nc -nzv 192.168.123.11 50000 && \
  nc -nzv 192.168.123.12 50000 && \
  nc -nzv 192.168.123.13 50000; \
  do sleep 1; done'
```


### 4.3. Bootstrap Kubernetes

Bootstrap the Kubernetes cluster by running `talm bootstrap` against one of the control plane nodes:

```bash
talm bootstrap -f nodes/node1.yaml
```


## 5. Access the Kubernetes Cluster

At this point, the Kubernetes cluster is ready to install Cozystack.

Before this step, you were interacting with the cluster using Talos API and `talosctl`.
Further steps require Kubernetes API and `kubectl`, which require a `kubeconfig`.


### 5.1. Get a kubeconfig

Use Talm to generate an administrative `kubeconfig`:

```bash
talm kubeconfig kubeconfig -f nodes/node1.yaml
```

This command will produce a `kubeconfig` file in the current directory.


### 5.2. Change Cluster API URL

The `kubeconfig` now has the Cluster API URL set to the floating IP (VIP) in the private subnet.

If you’re using a public IP instead of floatingIP, update the endpoint accordingly.
Edit the `kubeconfig` — change the cluster URL to a public IP of one of the nodes:

```diff
  apiVersion: v1                                                                                                          
  clusters:                                                                                                               
  - cluster:     
      certificate-authority-data: ...                                                                                                         
-     server: https://10.0.1.101:6443   
+     server: https://12.34.56.101:6443   
```


### 5.3. Activate kubeconfig

Finally, set up the `KUBECONFIG` variable or use other tools to make this kubeconfig
accessible to your `kubectl` client:

```bash
export KUBECONFIG=$PWD/kubeconfig
```

{{% alert color="info" %}}
To make this `kubeconfig` permanently available, you can make it the default one (`~/.kube/config`),
use `kubectl config use-context`, or employ a variety of other methods.
Check out the [Kubernetes documentation on cluster access](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/).
{{% /alert %}}


### 5.4. Check Cluster Availability

Check that the cluster is available:

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

### 5.5. Check Node State

Check the state of cluster nodes:

```bash
kubectl get nodes    
```

Output shows node status and Kubernetes version:

```console
NAME    STATUS     ROLES           AGE     VERSION
node1   NotReady   control-plane   7m56s   v1.33.1
node2   NotReady   control-plane   7m56s   v1.33.1
node3   NotReady   control-plane   7m56s   v1.33.1
```

Note that all nodes show `STATUS: NotReady`, which is normal at this step.
This happens because the default [Kubernetes CNI plugin](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
was disabled in the Talos configuration to enable Cozystack installing its own CNI plugin.


## Further Steps

Now you have a Kubernetes cluster bootstrapped and ready for installing Cozystack.
To complete the installation, follow the deployment guide, starting with the
[Install Cozystack]({{% ref "/docs/getting-started/install-cozystack" %}}) section.
