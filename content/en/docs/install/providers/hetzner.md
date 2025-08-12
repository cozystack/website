---
title: How to install Cozystack in Hetzner
linkTitle: Hetzner.com
description: "How to install Cozystack in Hetzner"
weight: 30
aliases:
  - /docs/operations/talos/installation/hetzner
  - /docs/talos/installation/hetzner
  - /docs/talos/install/hetzner
---

This guide will help you to install Cozystack on a dedicated server from [Hetzner](https://www.hetzner.com/).
There are several steps to follow, including preparing the infrastructure, installing Talos Linux, configuring cloud-init, and bootstrapping the cluster.


## Prepare Infrastructure and Networking

Installation on Hetzner includes the common [hardware requirements]({{% ref "/docs/install/hardware-requirements" %}}) with several additions.

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
read [Talos Linux in Cozystack]({{% ref "/docs/guides/talos" %}}).

### 1.1 Write Talos Image on Primary Disk

First stage is to prepare the primary disk and write the Talos Linux image on it.
Run these steps with each of the dedicated servers.

1.  Switch your server into rescue mode and login to the server using SSH.

1.  Check the available disks:

    ```console
    # lsblk
    NAME        MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINTS
    nvme0n1     259:4    0 476.9G  0 disk
    nvme1n1     259:0    0 476.9G  0 disk
    ```

    In this example, we have two NVMe disks: `nvme0n1` and `nvme1n1`.
    We will use `nvme0n1` as a primary disk for the Talos Linux installation and `nvme1n1` as a secondary disk for user data.

    Further on in this guide, all Bash snippets will use variables for disk names.
    Set them up in your console to conveniently copy and run the commands:
    
    ```bash
    DISK1=nvme0n1
    DISK2=nvme1n1
    ```

1.  Wipe both disks selected for Cozystack installation.

    {{% alert color="warning" %}}
    :warning: The following commands will erase your data.
    Make sure that all valuable information is backed up elsewhere.
    {{% /alert %}}
    
    ```bash
    sfdisk /dev/$DISK1 --delete
    sfdisk /dev/$DISK2 --delete
    wipefs -a /dev/$DISK1
    wipefs -a /dev/$DISK2
    ```

1.  Download Talos Linux asset from the Cozystack's [releases page](https://github.com/cozystack/cozystack/releases), and write it on the primary disk:

    ```bash
    cd /tmp
    wget https://github.com/cozystack/cozystack/releases/latest/download/nocloud-amd64.raw.xz
    xz -d -c /tmp/nocloud-amd64.raw.xz | dd of="/dev/$DISK1" bs=4M oflag=sync
    ```
    
    Note that Cozystack has its own Talos distribution and there are several options.
    For dedicated servers, you need the `nocloud-amd64.raw.xz`.

1.  Resize the partition table and prepare an additional partition for the cloud-init data:

    ```bash
    # resize gpt partition
    sgdisk -e "/dev/$DISK1"
    
    # Create 20MB partition at the end of the disk
    end=$(sgdisk -E "/dev/$DISK1")
    sgdisk -n7:$(( $end - 40960 )):$end -t7:ef00 "/dev/$DISK1"
    
    # Create FAT filesystem for cloud-init and mount it
    PARTITION=$(sfdisk -d "/dev/$DISK1" | awk 'END{print $1}' | awk -F/ '{print $NF}')
    mkfs.vfat -n CIDATA "/dev/$PARTITION"
    mount  "/dev/$PARTITION" /mnt
    ```

### 1.2. Configure Cloud-Init

Proceed by configuring cloud-init for each dedicated server.

1.  Start by setting environment variables:
    
    ```bash
    INTERFACE_NAME=$(udevadm info -q property /sys/class/net/eth0 | grep "ID_NET_NAME_PATH=" | cut -d'=' -f2)
    IP_CIDR=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}')
    GATEWAY=$(ip route | grep default | awk '{print $3}')
    
    echo "INTERFACE_NAME=$INTERFACE_NAME"
    echo "IP_CIDR=$IP_CIDR"
    echo "GATEWAY=$GATEWAY"
    ```

1.  Write the cloud-init configuration files.

    Edit network-config and specify your network settings using [network-config-format-v2](https://cloudinit.readthedocs.io/en/latest/reference/network-config-format-v2.html).
    This step depends on whether your installation is using a vSwitch-enabled subnet or public IPs.

    -   Cloud-init configuration using [Hetzner vSwitch](https://docs.hetzner.com/robot/dedicated-server/network/vswitch/).

        Note how this example is using subnet, VLAN ID, and subnet IPs of each node.
        
        ```bash
        echo 'hostname: talos' > /mnt/meta-data
        echo '#cloud-config' > /mnt/user-data
        cat > /mnt/network-config <<EOT
        version: 2
        ethernets:
          $INTERFACE_NAME:
            dhcp4: false
            addresses:
              - "${IP_CIDR}"
            gateway4: "${GATEWAY}"
            nameservers:
              addresses: [8.8.8.8]
        vlans:
          vlan4000:
            id: 4000
            link: $INTERFACE_NAME
            mtu: 1400
            dhcp4: false
            addresses:
              # node's own IP in the vSwitch subnet, change it for each node
              - 10.0.1.101/24           
            routes:
              # Hetzner cloud network
              - to: 10.0.0.0/16
                via: 10.0.1.1
        EOT
        ```

    -   Cloud-init configuration using [public IPs]({{% ref "/docs/operations/faq#public-network-kubernetes-deployment" %}}):
            
        ```bash
        echo 'hostname: talos' > /mnt/meta-data
        echo '#cloud-config' > /mnt/user-data
        cat > /mnt/network-config <<EOT
        version: 2
        ethernets:
          $INTERFACE_NAME:
            dhcp4: false
            addresses:
              - "${IP_CIDR}"
            gateway4: "${GATEWAY}"
            nameservers:
              addresses: [8.8.8.8]
        EOT
        ```

    You can find more comprehensive examples in the codebase of [siderolabs/talos](
    https://github.com/siderolabs/talos/blob/10f958cf41ec072209f8cb8724e6f89db24ca1b6/internal/app/machined/pkg/runtime/v1alpha1/platform/nocloud/testdata/metadata-v2.yaml)

### 1.3. Boot into Talos Linux

On each server, unmount the cloud-init partition, sync changes, and reboot the server:

```bash
umount /mnt
sync
reboot
```

At this point, each node (server) has Talos Linux installed and booted in the maintenance mode.

## 2. Install Kubernetes Cluster

Now, when Talos is booted in the maintenance mode, it should receive configuration and set up a Kubernetes cluster.
There are [several options]({{% ref "/docs/install/kubernetes" %}}) to write and apply Talos configuration.
This guide will focus on [Talm](https://github.com/cozystack/talm), Cozystack's own Talos configuration management tool.

This part of the guide is based on the generic [Talm guide]({{% ref "/docs/install/kubernetes/talm" %}}),
but has instructions and examples specific to Hetzner.

### 2.1. Prepare Node Configuration with Talm

1.  Start by installing the latest version of Talm for your OS, if you don't have it yet:

    ```bash
    curl -sSL https://github.com/cozystack/talm/raw/refs/heads/main/hack/install.sh | sh -s
    ```

1.  Make a directory for cluster configuration and initialize a Talm project in it.

    Note that Talm has a built-in preset for Cozystack, which we use with `--preset cozystack`:

    ```bash
    mkdir -p hetzner
    cd hetzner
    talm init --preset cozystack
    ```

    A bunch of files is now created in the `hetzner` directory.
    To learn more about the role of each file, refer to the
    [Talm guide]({{% ref "docs/install/kubernetes/talm#1-initialize-cluster-configuration" %}}).

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
    talm kubeconfig kubeconfig -f nodes/node1.yaml
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

1.  Start by making a Cozystack configuration file, **cozystack-config.yaml**.
    
    Note that this file is reusing the subnets for pods and services which were used in `values.yaml` before producing Talos configuration with Talm.
    Also note how Cozystack's default load balancer MetalLB is replaced with RobotLB using `bundle-disable` and `bundle-enable`.

    Replace `example.org` with a routable fully-qualified domain name (FQDN) that you're going to use for your Cozystack-based platform.
    If you don't have one ready, you can use [nip.io](https://nip.io/) with dash notation.

    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: cozystack
      namespace: cozy-system
    data:
      bundle-name: "paas-full"
      bundle-disable: "metallb"
      bundle-enable: "hetzner-robotlb"
      root-host: "example.org"
      api-server-endpoint: "https://api.example.org:443"
      expose-services: "dashboard,api"
      ## podSubnets from the node config
      ipv4-pod-cidr: "10.244.0.0/16"
      ipv4-pod-gateway: "10.244.0.1"
      ## serviceSubnets from the node config
      ipv4-svc-cidr: "10.96.0.0/16"
    ```

1.  Next, create a namespace `cozy-system` and install Cozystack system components:

    ```bash
    kubectl create ns cozy-system
    kubectl apply -f cozystack-config.yaml
    kubectl apply -f https://github.com/cozystack/cozystack/releases/latest/download/cozystack-installer.yaml
    ```
    
    The last command starts Cozystack installation, which will last for some time.
    You can track the logs of installer, if you wish:

    ```bash
    kubectl logs -n cozy-system deploy/cozystack -f
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

    Use the Hetzner API token and Hetzner network name to create a Kubernetes secret in Cozystack:

    ```bash
    export ROBOTLB_HCLOUD_TOKEN="<token>"
    export ROBOTLB_DEFAULT_NETWORK="<network name>"
    
    kubectl create secret generic hetzner-robotlb-credentials \
      --namespace=cozy-hetzner-robotlb \
      --from-literal=ROBOTLB_HCLOUD_TOKEN="$ROBOTLB_HCLOUD_TOKEN" \
      --from-literal=ROBOTLB_DEFAULT_NETWORK="$ROBOTLB_DEFAULT_NETWORK"
    ```
    
    Upon receiving the token, RobotLB service in Cozystack will create a load balancer in Hetzner.

### 3.3 Configure Storage with LINSTOR

Configuring LINSTOR in Hetzner has no difference from other infrastructure setups.
Follow the [Storage configuration guide]({{% ref "docs/getting-started/install-cozystack#3-configure-storage" %}}) from the Cozystack tutorial.

### 3.4. Start Services in the Root Tenant

Set up the basic services ( `etcd`, `monitoring`, and `ingress`) in the root tenant:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '
{"spec":{
  "ingress": true,
  "monitoring": true,
  "etcd": true,
  "isolated": true
}}'
```

## Notes and Troubleshooting

{{% alert color="warning" %}}
:warning: If you encounter issues booting Talos Linux on your node, it might be related to the serial console options in your GRUB configuration,
`console=tty1 console=ttyS0`.
Try rebooting into rescue mode and remove these options from the GRUB configuration on the third partition of your system's primary disk (`$DISK1`).
{{% /alert %}}
