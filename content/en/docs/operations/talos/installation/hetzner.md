---
title: How to install Cozystack in Hetzner
linkTitle: Hetzner
description: "How to install Cozystack in Hetzner"
weight: 30
---

{{% alert color="warning" %}}
:warning: Secure Boot is currently not supported.

If your server configured to use Secure Boot, you need to disable this feature in your BIOS. Otherwise, it will block the server from booting after Talos Linux installation.

```bash
# mokutil --sb-state
SecureBoot disabled
Platform is in Setup Mode
```
{{% /alert %}}

Switch your server into rescue mode

Login to the server using SSH

Check Disks:

```console
# lsblk
NAME        MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINTS
nvme0n1     259:4    0 476.9G  0 disk
nvme1n1     259:0    0 476.9G  0 disk
```
{{% alert color="warning" %}}
:warning: The following commands will erase your data!
{{% /alert %}}

Wipe disks
```bash
sfdisk /dev/nvme0n1 --delete
sfdisk /dev/nvme1n1 --delete
wipefs -a /dev/nvme0n1
wipefs -a /dev/nvme1n1
```


Set environment variable:
```bash
DISK=$(lsblk -dn -o NAME,SIZE,TYPE -e 1,7,11,14,15 | sort | sed -n 1p | awk '{print $1}')

echo "DISK=$DISK"
```

Download Talos Linux asset from the Cozystack's [releases page](https://github.com/cozystack/cozystack/releases), and write it into disk:

```bash
cd /tmp
wget https://github.com/cozystack/cozystack/releases/latest/download/nocloud-amd64.raw.xz
xz -d -c /tmp/nocloud-amd64.raw.xz | dd of="/dev/$DISK" bs=4M oflag=sync
```

Resize the partition table and prepare additional partition for the cloud-init data:

```bash
# resize gpt partition
sgdisk -e "/dev/$DISK"

# Create 20MB partition in the end of disk
end=$(sgdisk -E "/dev/$DISK")
sgdisk -n7:$(( $end - 40960 )):$end -t7:ef00 "/dev/$DISK"

# Create FAT filesystem for cloud-init and mount it
PARTITION=$(sfdisk -d "/dev/$DISK" | awk 'END{print $1}' | awk -F/ '{print $NF}')
mkfs.vfat -n CIDATA "/dev/$PARTITION"
mount  "/dev/$PARTITION" /mnt
```

Set environment variables:

```bash
INTERFACE_NAME=$(udevadm info -q property /sys/class/net/eth0 | grep "ID_NET_NAME_PATH=" | cut -d'=' -f2)
IP_CIDR=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}')
GATEWAY=$(ip route | grep default | awk '{print $3}')

echo "INTERFACE_NAME=$INTERFACE_NAME"
echo "IP_CIDR=$IP_CIDR"
echo "GATEWAY=$GATEWAY"
```

Write cloud-init configuration:

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

Edit network-config and specify your network settings using [network-config-format-v2](https://cloudinit.readthedocs.io/en/latest/reference/network-config-format-v2.html).

Cloud-init configuration example when using [Hetzner vSwitch](https://docs.hetzner.com/robot/dedicated-server/network/vswitch/) with the VLAN ID 4000.

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
      - "10.3.3.101/24"
    routes:
      - to: 10.3.0.0/16
        via: 10.3.3.1

EOT
```

You can find more comprehensive example under the [link](https://github.com/siderolabs/talos/blob/10f958cf41ec072209f8cb8724e6f89db24ca1b6/internal/app/machined/pkg/runtime/v1alpha1/platform/nocloud/testdata/metadata-v2.yaml)

Umount cloud-init partition, sync changes, and reboot the server

```bash
umount /mnt
sync
reboot
```

Now, when it is booted to Talos Linux maintenance mode, you can use [talos-bootstrap](https://github.com/cozystack/talos-bootstrap) or [Talm](https://github.com/cozystack/talm) to bootstrap the cluster


Just follow **Get Started** guide starting from the [**Bootstrap cluster**](/docs/get-started/#bootstrap-cluster) section, to continue the installation.

{{% alert color="warning" %}}
:warning: If you encounter issues booting Talos Linux on your node, it might be related to the serial console options in your GRUB configuration, console=tty1 console=ttyS0. Try rebooting into rescue mode and remove these options from the GRUB configuration on the third partition of your system `$DISK`.
{{% /alert %}}

