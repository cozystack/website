---
title: Bootstrap a Talos Linux cluster for Cozystack using Talm
linkTitle: Talm
description: "Bootstrap a Talos Linux cluster for Cozystack using Talm"
weight: 20
---

[Talm](https://github.com/cozystack/talm) is a Helm-like utility for declarative configuration management of Talos Linux.

It was created by Ænix to allow more declarative and custom configurations for cluster management.

Talm comes with pre-built presets for Cozystack.

Initialize the new project:

```
mkdir -p cluster1
cd cluster1
talm init --preset cozystack
```

{{% alert color="warning" %}}
If you use keycloak.

From v0.6.6 Talm:
- in `cluster1/templates/_helpers.tpl` replace  `keycloak.example.com` to your domain.

Before v0.6.6 Talm:
- Add in template args manualy:
```
  cluster:
    apiServer:
      extraArgs:
        oidc-issuer-url: "https://keycloak.example.com/realms/cozy"
        oidc-client-id: "kubernetes"
        oidc-username-claim: "preferred_username"
        oidc-groups-claim: "groups"

{{% /alert %}}

The structure of the project mostly mirrors an ordinary Helm chart:

- `charts` - a directory that includes a common library chart with functions used for querying information from Talos Linux.
- `Chart.yaml` - a file containing the common information about your project; the name of the chart is used as the name for the newly created cluster.
- `templates` - a directory used to describe templates for the configuration generation.
- `secrets.yaml` - a file containing secrets for your cluster.
- `values.yaml` - a common values file used to provide parameters for the templating.
- `nodes` - an optional directory used to describe and store generated configuration for nodes.

You're free to edit the files: `Chart.yaml`, `values.yaml`, and `templates/*` to meet your environment requirements.

Be aware that your nodes are booted Talos Linux image and awaiting in maintenance mode

{{% alert color="info" %}}
If you are using DHCP, you might not be aware of the IP addresses assigned to your nodes.\
You can use nmap to find them all:

```bash
nmap -Pn -n -p 50000 192.168.100.0/24 -vv | grep 'Discovered'
```

Where `192.168.100.0/24` is your network.

Example output:

```
Discovered open port 50000/tcp on 192.168.100.63
Discovered open port 50000/tcp on 192.168.100.159
Discovered open port 50000/tcp on 192.168.100.192
```
{{% /alert %}}

Now, create a nodes directory and collect the information from your nodes into a node-specific file for each node:

```bash
mkdir nodes
talm template -e 192.168.100.63 -n 192.168.100.63 -t templates/controlplane.yaml -i > nodes/srv1.yaml
talm template -e 192.168.100.159 -n 192.168.100.159 -t templates/controlplane.yaml -i > nodes/srv2.yaml
talm template -e 192.168.100.192 -n 192.168.100.192 -t templates/controlplane.yaml -i > nodes/srv3.yaml
```

Check the generated files, and if everything is okay, apply it:

```bash
talm apply -f nodes/srv1.yaml -i
talm apply -f nodes/srv2.yaml -i
talm apply -f nodes/srv3.yaml -i
```

Wait until all nodes have rebooted. Remove the installation media (e.g., USB stick) to ensure that the nodes boot from the internal disk.

In future operations, you can also use the following options:

- `--dry-run` - dry run mode will show a diff with the existing configuration.
- `-m try` - try mode will rollback the configuration in 1 minute.

Now, bootstrap the cluster by running this command against the first node (only for first node!):

```bash
talm bootstrap -f nodes/srv1.yaml
```

To access the cluster, generate the admin kubeconfig (only for first node!):

```bash
talm kubeconfig kubeconfig -f nodes/srv1.yaml
```

Export your `KUBECONFIG` variable:
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
:warning: All nodes should currently show as `READY: False`, don't worry about that, this is because you disabled the default CNI plugin in the previous step. Cozystack will install it's own CNI-plugin on the next step.
{{% /alert %}}

Now follow **Get Started** guide starting from the [**Install Cozystack**](/docs/get-started/#install-cozystack) section, to continue the installation.
