---
title: Install Talos Linux using the kernel execute mechanism
linkTitle: kexec
description: "How to install Talos Linux using the kernel execute mechanism (`kexec`)"
weight: 10
aliases:
  - /docs/talos/install/kexec
---

This guide explains how to boot Talos Linux from a running Linux OS using the `kexec`
([kernel execute](https://en.wikipedia.org/wiki/Kexec)) mechanism.
Using `kexec` is a convenient way of installing Talos when you have machines with another Linux distribution already installed.

Kexec is both a utility `kexec` and a system call of the same name.
It allows you to boot into a new kernel from the existing system without performing a physical reboot of the machine.
It’s as if the kernel was loaded by the standard bootloader at startup, only in this case your existing OS acts as the bootloader.

Note that Cozystack provides its own Talos builds, which are tested and optimized for running a Cozystack cluster.

## 1. Install `kexec-tools` package

Here and further this guide assumes an Ubuntu / Debian system.
Commands for other distributions may vary.

```bash
apt install kexec-tools -y
```

## 2. Download Cozystack-specific Talos Distribution

Cozystack developers have made a special Talos Linux distribution, tailored for the requirements of Cozystack.
These distributions are released together with Cozystack, and can be downloaded from the
[Cozystack releases page](https://github.com/cozystack/cozystack/releases/latest) on GitHub.

Choice of distribution depends on whether you are using VMs or bare metal.

In most cases, it is best to take the latest stable release:

```bash
wget -O /tmp/vmlinuz https://github.com/cozystack/cozystack/releases/latest/download/kernel-amd64
wget -O /tmp/initramfs.xz https://github.com/cozystack/cozystack/releases/latest/download/initramfs-metal-amd64.xz
```

To install a specific version, download matching distributive.
Note that the URL is slightly different from the one for `latest`:

```text
VERSION=v0.34.3
wget -O /tmp/vmlinuz https://github.com/cozystack/cozystack/releases/download/${VERSION}/kernel-amd64
wget -O /tmp/initramfs.xz https://github.com/cozystack/cozystack/releases/download/${VERSION}/initramfs-metal-amd64.xz
```

Cozystack supports `kexec` installation since version `v0.29.2`

## 3. Gather Network Information

Talos Linux needs network configuration to use during boot time.
At this step we will gather the required information and pack it into a command line parameter.

The mechanism we're using is called "Kernel level IP configuration".
It allows the Linux kernel to set up interfaces and assign IP addresses automatically during boot,
based on information passed with the `kernel cmdline`.
It's a built-in kernel feature which is enabled by default in Talos Linux.

All we need is to make a properly formatted network settings parameter.
Below is a small script that does all the work:

```bash
IP=$(ip -o -4 route get 8.8.8.8 | awk -F"src " '{sub(" .*", "", $2); print $2}')
GATEWAY=$(ip -o -4 route get 8.8.8.8 | awk -F"via " '{sub(" .*", "", $2); print $2}')
ETH=$(ip -o -4 route get 8.8.8.8 | awk -F"dev " '{sub(" .*", "", $2); print $2}')
CIDR=$(ip -o -4 addr show "$ETH" | awk -F"inet $IP/" '{sub(" .*", "", $2); print $2; exit}')
NETMASK=$(echo "$CIDR" | awk '{p=$1;for(i=1;i<=4;i++){if(p>=8){o=255;p-=8}else{o=256-2^(8-p);p=0}printf(i<4?o".":o"\n")}}')
DEV=$(udevadm info -q property "/sys/class/net/$ETH" | awk -F= '$1~/ID_NET_NAME_ONBOARD/{print $2; exit} $1~/ID_NET_NAME_PATH/{v=$2} END{if(v) print v}')

CMDLINE="init_on_alloc=1 slab_nomerge pti=on console=tty0 console=ttyS0 printk.devkmsg=on talos.platform=metal ip=${IP}::${GATEWAY}:${NETMASK}::${DEV}:::::"
echo $CMDLINE
```

The output should be similar to:

```console
init_on_alloc=1 slab_nomerge pti=on console=tty0 console=ttyS0 printk.devkmsg=on talos.platform=metal ip=10.0.0.131::10.0.0.1:255.255.255.0::eno2np0:::::
```

If it looks correct, you can proceed to the next step.

For details and deep explanation of this step, see the documentation:

-   [Kernel level IP autoconfiguration](https://cateee.net/lkddb/web-lkddb/IP_PNP.html)
-   [Talos Linux documentation on kernel command line](https://www.talos.dev/latest/talos-guides/install/bare-metal-platforms/network-config/#kernel-command-line).
-   [Official Linux Kernel documentation](https://www.kernel.org/doc/Documentation/filesystems/nfs/nfsroot.txt)

## 4. Boot Talos Linux

Now that we have the Talos distributive and the network configuration, it's time to boot Talos.
The first command loads the Talos kernel into RAM, and the second switches the current system to this new kernel:

```text
kexec --load /tmp/vmlinuz --initrd=/tmp/initramfs.xz --command-line="$CMDLINE"
kexec --exec
```

To monitor how `kexec` works and debug any problems with installation, run `dmesg -w` in a separate console session.

```console
# dmesg -w
... (some logs before running `kexec --load`)
... this message is expected after `kexec --load`:
[Wed Jul 23 18:33:56 2025] PEFILE: Unsigned PE binary
```

From [`kexec` manual pages](https://www.man7.org/linux/man-pages/man8/kexec.8.html#):
```text
-l (--load) kernel
       Load the specified kernel into the current kernel.
--initrd=file
       Use file as the kernel's initial ramdisk.
--command-line=string
        Set the kernel command line to string.
-e (--exec)
        Run the currently loaded kernel. Note that it will reboot```
        into the loaded kernel without calling shutdown(8).
```

Once the machine has rebooted, Talos Linux will be loaded in memory.
To finalize installation, follow with cluster bootstrapping using one of available tools:

Once you apply the configuration with `talm apply -i ...` or `talosctl apply -i`,
Talos image gets written to disk and installation is complete.

## Next steps

Once you have installed Talos, proceed by [installing and bootstrapping a Kubernetes cluster]({{% ref "/docs/install/kubernetes" %}}).
