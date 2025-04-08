---
title: How to install Cozystack in Servers.com
linkTitle: Servers.com
description: "How to install Cozystack in Servers.com"
weight: 40
---

## Before installation

### Network

**Remove Aggregate Interface**
- Go to **Dedicated Server - Server Details**, and click on the second column (highlighted in blue) to remove the aggregate interface.
- Ensure the status appears as shown in the screenshot.

![Remove Aggregate Interface](img/remove_aggregate_interface.png)

Set Up L2 Network
- Navigate to **Networks - L2 Segment** and click **Add Segment**.

![L2 Segments](img/l2_segments1.png)

![L2 Segments](img/l2_segments2.png)

![L2 Segments](img/l2_segments3.png)

First, select **Private**, choose the region, add the servers, assign a name, and save it.
- Set the type to **Native**.

![Type](img/type_native.png)

Do the same for Public.

### Access
- Create SSH keys for server access.
- Go to **Identity and Access > SSH and Keys**.

![SSH](img/ssh_gpg_keys1.png)

- Create new keys or add your own.

![SSH](img/ssh_gpg_keys2.png)
![SSH](img/ssh_gpg_keys3.png)

## Setup OS

### Rescue Mode / Access

- Go to **Dedicated Servers - Server Details**, and click **Reboot to Rescue**. Select your SSH key.

![Rescue](img/rescue.png)

- Connect via SSH
  - Log in via SSH using the external IP of the server (**Public IP** in **Details**).

![Public IP](img/public_ip.png)

### Setup

```console
# lsblk
NAME    MAJ:MIN   RM   SIZE     RO   TYPE   MOUNTPOINTS
sda     259:4     0    476.9G   0    disk
sdb     259:0     0    476.9G   0    disk
```
{{% alert color="warning" %}}
:warning: The following commands will erase your data!
{{% /alert %}}

Wipe disks
```bash
wipefs -a /dev/sda
wipefs -a /dev/sdb
```

Install `kexec-tools`:

```bash
dnf install kexec-tools -y
```

Download kernel and initramfs:

```bash
wget -O /tmp/vmlinuz https://github.com/cozystack/cozystack/releases/latest/download/kernel-amd64
wget -O /tmp/initramfs.xz https://github.com/cozystack/cozystack/releases/latest/download/initramfs-metal-amd64.xz
```

Set environment variables:

```bash
INTERFACE=$(ip -o link show | grep 'master bond0' | grep -m1 'state UP' | awk -F': ' '{print $2}')
INTERFACE_NAME=$(udevadm info -q property "/sys/class/net/$INTERFACE" | grep "ID_NET_NAME_ONBOARD=" | cut -d'=' -f2)
IP_CIDR=$(ip addr show bond0 | grep "inet\b" | awk '{print $2}')
IP=$(echo $IP_CIDR | cut -d/ -f1)
NETMASK=$(ipcalc -m $IP_CIDR | cut -d= -f2-)
GATEWAY=$(ip route | grep default | awk '{print $3}')
```

Set CMDLINE, and echo it to verify:

```bash
CMDLINE="init_on_alloc=1 slab_nomerge pti=on console=tty0 console=ttyS0 printk.devkmsg=on talos.platform=metal ip=${IP}::${GATEWAY}:${NETMASK}::${INTERFACE_NAME}:::::"
echo $CMDLINE
```

### Boot into Talos

Load the kernel and initramfs:

```bash
kexec -l /tmp/vmlinuz --initrd=/tmp/initramfs.xz --command-line="$CMDLINE"
```

Boot into the new kernel:

```bash
kexec -e
```

After executing the command, the system will reboot into the new kernel. Your SSH session will stop responding, and the server will reboot.

Wait ~ 5 minutes for the system to boot.


## Talos Configuration

Use Talm to apply config and install Talos Linux on the drive.

### Installation with Talm

1. Create directory for new cluster:
   ```bash
   mkdir -p mycluster
   cd mycluster
   ```

2. Run the following command to initialize Talm for Cozystack:

   ```bash
   talm init -p cozystack
   ```

   After initializing, generate a configuration template with the command:

   ```bash
   talm -n 1.2.3.4 -e 1.2.3.4 template -t templates/controlplane.yaml -i > nodes/nodeN.yaml
   ```

3. Edit the node configuration file as needed.

   - Update `hostname` to the desired name.
     ```yaml
     machine:
       network:
         hostname: node1
     ```

   - Update `nameservers` to the public ones, because internal servers.com DNS is not reachable from the private network.
     ```yaml
     machine:
       network:
         nameservers:
           - 8.8.8.8
           - 1.1.1.1
     ```
   - Add private interface configuration, and move `vip` to this section. This section isn’t generated automatically:
     - `busPath` - Obtained from the "Discovered interfaces busPath" by matching the MAC address of the private interface specified in the provider's email. (Out of the two interfaces, select the one with the uplink).
     - `addresses` - Use the address specified for Layer 2 (L2).

     Example:
     ```yaml
     matching:
       network:
         interfaces:
           - deviceSelector:
               busPath: "0000:03:00.1"
             addresses:
               - 1.2.3.4/29
             routes:
               - network: 0.0.0.0/0
                 gateway: 1.2.3.1
           - deviceSelector:
               busPath: "0000:03:00.0"
             addresses:
               - 192.168.100.11/24
             vip:
               ip: 192.168.100.10
     ```

**Execution steps:**

1. [Download](https://github.com/cozystack/talm/releases/latest) latest Talm binary and save it to `/usr/local/bin/talm`
2. Make it executable:
   ```
   chmod +x /usr/local/bin/talm
   ```
3. Run `talm apply -f nodeN.yml` for all nodes to apply the configurations. The nodes will be rebooted and Talos will be installed on the disk.
4. Make sure that talos get installed into disk by executing `talm get systemdisk -f nodeN.yml` for each node. The output should be similar to:
   ```yaml
   NODE      NAMESPACE   TYPE         ID            VERSION   DISK
   1.2.3.4   runtime     SystemDisk   system-disk   1         sda
   ```
   If the output is empty, it means that Talos still runs in RAM and hasn't been installed on the disk yet.
5. Click **Exit rescue mode** for each node in the Servers.com panel. The nodes will reboot again.
6. Execute bootstrap command for the first node in the cluster, example:
   ```bash
   talm bootstrap -f nodes/node1.yml
   ```
7. Get `kubeconfig` from the first node, example:
   ```bash
   talm kubeconfig kubeconfig -f nodes/node1.yml
   ```
8. Edit `kubeconfig` to set the IP address to one of control-plane node, example:
   ```yaml
   server: https://1.2.3.4:6443
   ```
9. Export variable to use the kubeconfig, and check the connection to the Kubernetes:
   ```bash
   export KUBECONFIG=${PWD}/kubeconfig
   kubectl get nodes
   ```

Now follow **Get Started** guide starting from the [**Install Cozystack**](/docs/getting-started/first-deployment/#install-cozystack) section, to continue the installation.


