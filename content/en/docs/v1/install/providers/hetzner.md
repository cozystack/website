---
title: How to install Cozystack in Hetzner
linkTitle: Hetzner.com
description: "How to install Cozystack in Hetzner"
weight: 30
aliases:
  - /docs/v1/operations/talos/installation/hetzner
  - /docs/v1/talos/installation/hetzner
  - /docs/v1/talos/install/hetzner
---

This guide will help you to install Cozystack on a dedicated server from [Hetzner](https://www.hetzner.com/).
There are several steps to follow, including preparing the infrastructure, installing Talos Linux, configuring cloud-init, and bootstrapping the cluster.


## Prepare Infrastructure and Networking

Installation on Hetzner includes the common [hardware requirements]({{% ref "/docs/v1/install/hardware-requirements" %}}) with several additions.

### Networking Options

There are two options for network connectivity between Cozystack nodes in the cluster:

-   **Creating a subnet using vSwitch.**
    This option is recommended for production environments.

    For this option, dedicated servers must be deployed on [Hetzner robot](https://robot.hetzner.com/).
    Hetzner also requires using its own load balancer, RobotLB, in place of Cozystack's default MetalLB.
    Cozystack includes RobotLB as an optional component since release v0.35.0.
    
-   **Using only dedicated servers' public IPs.**
    This option is valid for a proof-of-concept installation, but not recommended for production.


### Configure Subnet with vSwitch

Complete the following steps to prepare your servers for installing Cozystack:

1.  Make network configuration settings in Hetzner (only for the **vSwitch subnet** option).

    Complete the steps from the [Prerequisites section](https://github.com/Intreecom/robotlb/blob/master/README.md#prerequisites)
    of RobotLB's README:

    1.  Create a [vSwitch](https://docs.hetzner.com/cloud/networks/connect-dedi-vswitch/).
    2.  Use it to assign IPs to your dedicated servers on Hetzner.
    3.  Create a subnet to [connect your dedicated servers](https://docs.hetzner.com/cloud/networks/connect-dedi-vswitch/). 

    Note that you don't need to deploy RobotLB manually.
    Instead, you will configure Cozystack to install it as an optional component on the step "Installing Cozystack" of this guide.

### Disable Secure Boot

1.  Make sure that Secure Boot is disabled.

    Secure Boot is currently not supported in Talos Linux.
    If your server is configured to use Secure Boot, you need to disable this feature in your BIOS.
    Otherwise, it will block the server from booting after Talos Linux installation.

    Check it with the following command:

    ```console
    # mokutil --sb-state
    SecureBoot disabled
    Platform is in Setup Mode
    ```

For the rest of the guide let's assume that we have the following network configuration:

- Hetzner cloud network is `10.0.0.0/16`, named `network-1`. 
- vSwitch subnet with dedicated servers is `10.0.1.0/24` 
- vSwitch VLAN ID is `4000`

- There are three dedicated servers with the following public and private IPs:
  - `node1`, public IP `12.34.56.101`, vSwitch subnet IP `10.0.1.101`
  - `node2`, public IP `12.34.56.102`, vSwitch subnet IP `10.0.1.102`
  - `node3`, public IP `12.34.56.103`, vSwitch subnet IP `10.0.1.103`

## 1. Install Talos Linux

The first stage of deploying Cozystack is to install Talos Linux on the dedicated servers.

Talos is a Linux distribution made for running Kubernetes in the most secure and efficient way.
To learn why Cozystack adopted Talos as the foundation of the cluster,
read [Talos Linux in Cozystack]({{% ref "/docs/v1/guides/talos" %}}).

### 1.1 Install boot-to-talos in Rescue Mode

Talos will be booted from the Hetzner rescue system using the [`boot-to-talos`](https://github.com/cozystack/boot-to-talos) utility.
Later, when you apply Talm configuration, Talos will be installed to disk.
Run these steps on each dedicated server.

1.  Switch your server into rescue mode and log in to the server using SSH.

1.  Identify the disk that will be used for Talos later (for example, `/dev/nvme0n1`).

1.  Download and install `boot-to-talos`:

    ```bash
    curl -sSL https://github.com/cozystack/boot-to-talos/raw/refs/heads/main/hack/install.sh | sh -s
    ```

    After this, the `boot-to-talos` binary should be available in your `PATH`:

    ```bash
    boot-to-talos -h
    ```

### 1.2. Install Talos Linux with boot-to-talos

1.  Start the installer:

    ```bash
    boot-to-talos
    ```

    When prompted:

    -   Select mode `1. boot`.
    -   Confirm or change the Talos installer image.
        The default value points to the Cozystack Talos image (the default Cozystack image is suitable),
    -   Provide network settings (interface name, IP address, netmask, gateway) matching the configuration you prepared earlier
        (vSwitch subnet or public IPs).
    -   Optionally configure a serial console if you use it for remote access.

    The utility will download the Talos installer image, extract the kernel and initramfs, and boot the node into Talos Linux
    (using the kexec mechanism) without modifying the disks.

### 1.3. Boot into Talos Linux

After `boot-to-talos` finishes, the server reboots automatically into Talos Linux in maintenance mode.

Repeat the same procedure for all dedicated servers in the cluster.
Once all nodes are booted into Talos, proceed to the next section and configure them using Talm.

## 2. Install Kubernetes Cluster

Now, when Talos is booted in the maintenance mode, it should receive configuration and set up a Kubernetes cluster.
There are [several options]({{% ref "/docs/v1/install/kubernetes" %}}) to write and apply Talos configuration.
This guide will focus on [Talm](https://github.com/cozystack/talm), Cozystack's own Talos configuration management tool.

This part of the guide is based on the generic [Talm guide]({{% ref "/docs/v1/install/kubernetes/talm" %}}),
but has instructions and examples specific to Hetzner.

### 2.1. Prepare Node Configuration with Talm

1.  Start by installing the latest version of Talm for your OS, if you don't have it yet:

    ```bash
    curl -sSL https://github.com/cozystack/talm/raw/refs/heads/main/hack/install.sh | sh -s
    ```

1.  Make a directory for cluster configuration and initialize a Talm project in it.

    Note that Talm has a built-in preset for Cozystack, which we use with `--preset cozystack`:

    ```bash
    mkdir -p hetzner-cluster
    cd hetzner-cluster
    talm init --preset cozystack --name hetzner
    ```

    A bunch of files is now created in the `hetzner-cluster` directory.
    To learn more about the role of each file, refer to the
    [Talm guide]({{% ref "docs/v1/install/kubernetes/talm#1-initialize-cluster-configuration" %}}).

1.  Edit `values.yaml`, modifying the following values:

    -   `advertisedSubnets` list should have the vSwitch subnet as an item.
    -   `endpoint` and `floatingIP` should use an unassigned IP from this subnet.
        This IP will be used to access the cluster API with `talosctl` and `kubectl`.
    -   `podSubnets` and `serviceSubnets` should have other subnets from the Hetzner cloud network,
        which don't overlap each other and the vSwitch subnet.

    ```yaml
    endpoint: "https://10.0.1.100:6443"
    clusterDomain: cozy.local
    # floatingIP points to the primary etcd node
    floatingIP: 10.0.1.100
    image: "ghcr.io/cozystack/cozystack/talos:v1.9.5"
    podSubnets:
    - 10.244.0.0/16
    serviceSubnets:
    - 10.96.0.0/16
    advertisedSubnets:
    # vSwitch subnet
    - 10.0.1.0/24
    oidcIssuerUrl: ""
    certSANs: []
    ```

1.  Create node configuration files from templates and values:
    
    ```bash
    mkdir -p nodes
    talm template -e 12.34.56.101 -n 12.34.56.101 -t templates/controlplane.yaml -i > nodes/node1.yaml
    talm template -e 12.34.56.102 -n 12.34.56.102 -t templates/controlplane.yaml -i > nodes/node2.yaml
    talm template -e 12.34.56.103 -n 12.34.56.103 -t templates/controlplane.yaml -i > nodes/node3.yaml
    ```

    This guide assumes that you have only three dedicated servers, so they all must be control plane nodes.
    If you have more and want to separate control plane and worker nodes, use `templates/worker.yaml` to produce worker configs:

    ```bash
    taml template -e 12.34.56.104 -n 12.34.56.104 -t templates/worker.yaml -i > nodes/worker1.yaml
    ```

1.  Edit each node's configuration file, adding the VLAN configuration.

    Use the following diff as an example and note that for each node its subnet IP should be used:

    ```diff
    machine:
      network:
        interfaces:
          - deviceSelector:
            # ...
    -       vip:
    -         ip: 10.0.1.100
    +       vlans:
    +         - addresses:
    +             # different for each node
    +             - 10.0.1.101/24
    +           routes:
    +             - network: 10.0.0.0/16
    +               gateway: 10.0.1.1
    +           vlanId: 4000
    +           vip:
    +             ip: 10.0.1.100
    ```

### 2.2. Apply Node Configuration

1.  Once the configuration files are ready, apply configuration to each node:

    ```bash
    talm apply -f nodes/node1.yaml -i
    talm apply -f nodes/node2.yaml -i
    talm apply -f nodes/node3.yaml -i
    ```

    This command initializes nodes, setting up authenticated connection, so that `-i` (`--insecure`) won't be required further on.
    If the command succeeded, it will return the node's IP:
    
    ```console
    $ talm apply -f nodes/node1.yaml -i
    - talm: file=nodes/node1.yaml, nodes=[12.34.56.101], endpoints=[12.34.56.101]
    ```

1.  Wait until all nodes have rebooted and proceed to the next step.
    When nodes are ready, they will expose port `50000`, which is a sign that the node has completed Talos and rebooted.

    If you need to automate the node readiness check, consider this example:

    ```bash
    timeout 60 sh -c 'until \
      nc -nzv 12.34.56.101 50000 && \
      nc -nzv 12.34.56.102 50000 && \
      nc -nzv 12.34.56.103 50000; \
      do sleep 1; done'
    ```
        
1.  Bootstrap the Kubernetes cluster from one of the control plane nodes:
    
    ```bash
    talm bootstrap -f nodes/node1.yaml
    ```

1.  Generate an administrative `kubeconfig` to access the cluster using the same control plane node:

    ```bash
    talm kubeconfig -f nodes/node1.yaml
    ```

1.  Edit the server URL in the `kubeconfig` to a public IP

    ```diff
      apiVersion: v1                                                                                                          
      clusters:                                                                                                               
      - cluster:                                                                                                              
    -     server: https://10.0.1.101:6443   
    +     server: https://12.34.56.101:6443   
    ```
    
1.  Finally, set up the `KUBECONFIG` variable or other tools making this config
    accessible to your `kubectl` client:

    ```bash
    export KUBECONFIG=$PWD/kubeconfig
    ```        

1.  Check that the cluster is available with this new `kubeconfig`:

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

At this point you have dedicated servers with Talos Linux and a Kubernetes cluster deployed on them.
You also have a `kubeconfig` which you will use to access the cluster using `kubectl` and install Cozystack.

## 3. Install Cozystack

The final stage of deploying a Cozystack cluster on Hetzner is to install Cozystack on a prepared Kubernetes cluster.

### 3.1. Start Cozystack Installer

1.  Install the Cozystack operator:

    ```bash
    helm install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
      --version X.Y.Z \
      --namespace cozy-system \
      --create-namespace
    ```

    Replace `X.Y.Z` with the desired Cozystack version from the [releases page](https://github.com/cozystack/cozystack/releases).

1.  Create a Platform Package file, **cozystack-platform.yaml**.

    Note that this file is reusing the subnets for pods and services which were used in `values.yaml` before producing Talos configuration with Talm.
    Also note how Cozystack's default load balancer MetalLB is replaced with RobotLB using `disabledPackages` and `enabledPackages`.

    Replace `example.org` with a routable fully-qualified domain name (FQDN) that you're going to use for your Cozystack-based platform.
    If you don't have one ready, you can use [nip.io](https://nip.io/) with dash notation.

    ```yaml
    apiVersion: cozystack.io/v1alpha1
    kind: Package
    metadata:
      name: cozystack.cozystack-platform
    spec:
      variant: isp-full
      components:
        platform:
          values:
            bundles:
              disabledPackages:
                - metallb
              enabledPackages:
                - hetzner-robotlb
            publishing:
              host: "example.org"
              apiServerEndpoint: "https://api.example.org:443"
              exposedServices:
                - dashboard
                - api
            networking:
              ## podSubnets from the node config
              podCIDR: "10.244.0.0/16"
              podGateway: "10.244.0.1"
              ## serviceSubnets from the node config
              serviceCIDR: "10.96.0.0/16"
    ```

1.  Apply the Platform Package:

    ```bash
    kubectl apply -f cozystack-platform.yaml
    ```

    The operator starts the installation, which will last for some time.
    You can track the logs of the operator, if you wish:

    ```bash
    kubectl logs -n cozy-system deploy/cozystack-operator -f
    ```

1.  Check the status of installation:
    
    ```bash
    kubectl get hr -A
    ```

    When installation is complete, all services will switch their state to `READY: True`:
    ```console
    NAMESPACE                        NAME                        AGE    READY   STATUS
    cozy-cert-manager                cert-manager                4m1s   True    Release reconciliation succeeded
    cozy-cert-manager                cert-manager-issuers        4m1s   True    Release reconciliation succeeded
    cozy-cilium                      cilium                      4m1s   True    Release reconciliation succeeded
    ...
    ```

### 3.2 Create a Load Balancer with RobotLB

Hetzner requires using its own RobotLB instead of Cozysatck's default MetalLB.
RobotLB is already installed as a component of Cozystack and running as a service in it.
Now it needs a token to create a load balancer resource in Hetzner.

1.  Create a Hetzner API token for RobotLB.

    Navigate to the Hetzner console, open Security, and create a token with `Read` and `Write` permissions.

1.  Pass the token to RobotLB to create a load balancer in Hetzner.

    Use the Hetzner API token to create a Kubernetes secret in Cozystack.

    -   If you're using a **private network** (vSwitch), specify the network name:

        ```bash
        export ROBOTLB_HCLOUD_TOKEN="<token>"
        export ROBOTLB_DEFAULT_NETWORK="<network name>"

        kubectl create secret generic hetzner-robotlb-credentials \
          --namespace=cozy-hetzner-robotlb \
          --from-literal=ROBOTLB_HCLOUD_TOKEN="$ROBOTLB_HCLOUD_TOKEN" \
          --from-literal=ROBOTLB_DEFAULT_NETWORK="$ROBOTLB_DEFAULT_NETWORK"
        ```

    -   If you're using **public IPs only** (no vSwitch), omit `ROBOTLB_DEFAULT_NETWORK`:

        ```bash
        export ROBOTLB_HCLOUD_TOKEN="<token>"

        kubectl create secret generic hetzner-robotlb-credentials \
          --namespace=cozy-hetzner-robotlb \
          --from-literal=ROBOTLB_HCLOUD_TOKEN="$ROBOTLB_HCLOUD_TOKEN"
        ```

        In this case, RobotLB will use nodes' public IPs (ExternalIP) as load balancer targets.
        For this to work, the nodes must have ExternalIP addresses configured.
        The simplest way to achieve this is by installing [local-ccm](https://github.com/cozystack/local-ccm),
        which automatically assigns public IPs to nodes' `.status.addresses` field.

    Upon receiving the token, RobotLB service in Cozystack will create a load balancer in Hetzner.

### 3.3 Configure Storage with LINSTOR

Configuring LINSTOR in Hetzner has no difference from other infrastructure setups.
Follow the [Storage configuration guide]({{% ref "docs/v1/getting-started/install-cozystack#3-configure-storage" %}}) from the Cozystack tutorial.

### 3.4. Start Services in the Root Tenant

Set up the basic services ( `etcd`, `monitoring`, and `ingress`) in the root tenant:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '
{"spec":{
  "ingress": true,
  "monitoring": true,
  "etcd": true
}}'
```

## Notes and Troubleshooting

{{% alert color="warning" %}}
:warning: If you encounter issues booting Talos Linux on your node, it might be related to the serial console options in your GRUB configuration,
`console=tty1 console=ttyS0`.
Try rebooting into rescue mode and remove these options from the GRUB configuration on the third partition of your system's primary disk (`$DISK1`).
{{% /alert %}}
