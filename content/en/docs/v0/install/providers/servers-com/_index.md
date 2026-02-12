---
title: Install Cozystack in Servers.com
linkTitle: Servers.com
description: "Install Cozystack in the Servers.com infrastructure."
weight: 40
aliases:
  - /docs/v0/operations/talos/installation/servers_com
  - /docs/v0/talos/installation/servers_com
  - /docs/v0/talos/install/servers_com
  - /docs/install/providers/servers-com
  - /docs/operations/talos/installation/servers_com
  - /docs/talos/installation/servers_com
  - /docs/talos/install/servers_com
---

## Before Installation

### 1. Network

1.  **Set Up L2 Network**

    1.  Navigate to **Networks > L2 Segment** and click **Add Segment**.

        ![L2 Segments](img/l2_segments1.png)

        ![L2 Segments](img/l2_segments2.png)

        ![L2 Segments](img/l2_segments3.png)

        First, select **Private**, choose the region, add the servers, assign a name, and save it.

    1.  Set the type to **Native**.
        Do the same for **Public**.

        ![Type](img/type_native.png)

### 2. Access

1.  Create SSH keys for server access.

1.  Go to **Identity and Access > SSH and Keys**.

    ![SSH](img/ssh_gpg_keys1.png)

1.  Create new keys or add your own.

    ![SSH](img/ssh_gpg_keys2.png)
    ![SSH](img/ssh_gpg_keys3.png)

## Setup OS

### 1. Operating System and Access

{{% alert color="warning" %}}
:warning: In rescue mode only the public network is available; the private L2 network is not reachable.
For Talos installation use a regular OS (for example Ubuntu) instead of rescue mode.
{{% /alert %}}

1.  In the Servers.com control panel, install Ubuntu on the server (for example via **Dedicated Servers > Server Details > OS install**) and make sure your SSH key is selected.

1.  After the installation is complete, connect via SSH using the external IP of the server (**Details** > **Public IP**).

    ![Public IP](img/public_ip.png)

### 2. Install Talos with boot-to-talos

Talos will be booted from the installed Ubuntu using the [`boot-to-talos`](https://github.com/cozystack/boot-to-talos) utility.
Later, when you apply Talm configuration, Talos will be installed to disk.
Run these steps on each server.

1.  Check the information on block devices to find the disk that will be used for Talos later (for example, `/dev/sda`).

    ```console
    # lsblk
    NAME    MAJ:MIN   RM   SIZE     RO   TYPE   MOUNTPOINTS
    sda     259:4     0    476.9G   0    disk
    sdb     259:0     0    476.9G   0    disk
    ```

1.  Download and install `boot-to-talos`:

    ```bash
    curl -sSL https://github.com/cozystack/boot-to-talos/raw/refs/heads/main/hack/install.sh | sudo sh -s
    ```

    After installation, verify that the binary is available:

    ```bash
    boot-to-talos -h
    ```

1.  Run the installer:

    ```bash
    sudo boot-to-talos
    ```

    When prompted:

    -   Select mode `1. boot`.
    -   Confirm or change the Talos installer image (the default Cozystack image is suitable).
    -   Provide network settings matching the public interface (`bond0`) and default gateway.

    The utility will download the Talos installer image and boot the node into Talos Linux (using the kexec mechanism) without modifying the disks.

    For fully automated installations you can use non-interactive mode:

    ```bash
    sudo boot-to-talos -yes
    ```

### 3. Boot into Talos

After `boot-to-talos` finishes, the server reboots automatically into Talos Linux in maintenance mode.
Repeat the same procedure for all servers, then proceed to configure them with Talm.

## Talos Configuration

Use [Talm](https://github.com/cozystack/talm) to apply config and install Talos Linux on the drive.

1. [Download the latest Talm binary](https://github.com/cozystack/talm/releases/latest) and save it to `/usr/local/bin/talm`

1. Make it executable:

   ```bash
   chmod +x /usr/local/bin/talm
   ```

### Installation with Talm

1. Create directory for the new cluster:

   ```bash
   mkdir -p cozystack-cluster
   cd cozystack-cluster
   ```

1. Run the following command to initialize Talm for Cozystack:

   ```bash
   talm init --preset cozystack --name mycluster
   ```

   After initializing, generate a configuration template with the command:

   ```bash
   talm -n 1.2.3.4 -e 1.2.3.4 template -t templates/controlplane.yaml -i > nodes/nodeN.yaml
   ```

1. Edit the node configuration file as needed:

   1.  Update `hostname` to the desired name.
       ```yaml
       machine:
         network:
           hostname: node1
       ```

   1.  Update `nameservers` to the public ones, because internal servers.com DNS is not reachable from the private network.
       ```yaml
       machine:
         network:
           nameservers:
             - 8.8.8.8
             - 1.1.1.1
       ```

   1.  Add private interface configuration, and move `vip` to this section. This section isn’t generated automatically:
       -   `interface` - Obtained from the "Discovered interfaces" by matching the MAC address of the private interface specified in the provider's email.
           (Out of the two interfaces, select the one with the uplink).
       -   `addresses` - Use the address specified for Layer 2 (L2).

       ```yaml
       machine:
         network:
           interfaces:
             - interface: bond0
               addresses:
                 - 1.2.3.4/29
               routes:
                 - network: 0.0.0.0/0
                   gateway: 1.2.3.1
               bond:
                 interfaces:
                   - enp1s0f1
                   - enp3s0f1
                 mode: 802.3ad
                 xmitHashPolicy: layer3+4
                 lacpRate: slow
                 miimon: 100
             - interface: bond1
               addresses:
                 - 192.168.102.11/23
               bond:
                 interfaces:
                   - enp1s0f0
                   - enp3s0f0
                 mode: 802.3ad
                 xmitHashPolicy: layer3+4
                 lacpRate: slow
                 miimon: 100
               vip:
                 ip: 192.168.102.10
       ```

**Execution steps:**

1.   Run `talm apply -f nodeN.yml` for all nodes to apply the configurations. The nodes will be rebooted and Talos will be installed on the disk.

1.   Make sure that talos get installed into disk by executing `talm get systemdisk -f nodeN.yml` for each node. The output should be similar to:
     ```yaml
     NODE      NAMESPACE   TYPE         ID            VERSION   DISK
     1.2.3.4   runtime     SystemDisk   system-disk   1         sda
     ```

     If the output is empty, it means that Talos still runs in RAM and hasn't been installed on the disk yet.
1.   Execute bootstrap command for the first node in the cluster, example:
     ```bash
     talm bootstrap -f nodes/node1.yml
     ```

1.   Get `kubeconfig` from the first node, example:
     ```bash
     talm kubeconfig -f nodes/node1.yml
     ```

1.   Edit `kubeconfig` to set the IP address to one of control-plane node, example:
     ```yaml
     server: https://1.2.3.4:6443
     ```

1.   Export variable to use the kubeconfig, and check the connection to the Kubernetes:
     ```bash
     export KUBECONFIG=${PWD}/kubeconfig
     kubectl get nodes
     ```

Now follow **Get Started** guide starting from the [**Install Cozystack**](/docs/v0/getting-started/install-cozystack) section, to continue the installation.
