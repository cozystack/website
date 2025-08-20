---
title: "Install Talos Linux using boot-to-talos"
linkTitle: boot-to-talos
description: "Install Talos Linux using boot-to-talos, a convenient CLI application requiring nothing but a Talos image."
weight: 5
---

This guide explains how to install Talos Linux on a host running any other Linux distribution using `boot-to-talos`.

`boot-to-talos` was made by Cozystack team to help users and teams adopting Cozystack with installing Talos, which is the most complex step in the process.
It works entirely from userspace and has no external dependencies except the Talos installer image.

Note that Cozystack provides its own Talos builds, which are tested and optimized for running a Cozystack cluster.

## Installation

### 1. Install `boot-to-talos`

-   Use the installer script:

    ```bash
    curl -sSL https://github.com/cozystack/boot-to-talos/raw/refs/heads/main/hack/install.sh | sh -s
    ```

-   Download the binary from the [GitHub releases page](https://github.com/cozystack/boot-to-talos/releases/latest):

    ```bash
    wget https://github.com/cozystack/boot-to-talos/releases/latest/download/boot-to-talos-linux-amd64.tar.gz
    ```

### 2. Run to install Talos

Run `boot-to-talos` and provide configuration values.
Make sure to use Cozystack's own Talos build, found at [ghcr.io/cozystack/cozystack/talos](https://github.com/cozystack/cozystack/pkgs/container/cozystack%2Ftalos).


```console
$ boot-to-talos
Target disk [/dev/sda]:
Talos installer image [ghcr.io/cozystack/cozystack/talos:v1.10.5]:
Add networking configuration? [yes]:
Interface [eth0]:
IP address [10.0.2.15]:
Netmask [255.255.255.0]:
Gateway (or 'none') [10.0.2.2]:
Configure serial console? (or 'no') [ttyS0]:

Summary:
  Image: ghcr.io/cozystack/cozystack/talos:v1.10.5
  Disk:  /dev/sda
  Extra kernel args: ip=10.0.2.15::10.0.2.2:255.255.255.0::eth0::::: console=ttyS0

WARNING: ALL DATA ON /dev/sda WILL BE ERASED!

Continue? [yes]:

2025/08/03 00:11:03 created temporary directory /tmp/installer-3221603450
2025/08/03 00:11:03 pulling image ghcr.io/cozystack/cozystack/talos:v1.10.5
2025/08/03 00:11:03 extracting image layers
2025/08/03 00:11:07 creating raw disk /tmp/installer-3221603450/image.raw (2 GiB)
2025/08/03 00:11:07 attached /tmp/installer-3221603450/image.raw to /dev/loop0
2025/08/03 00:11:07 starting Talos installer
2025/08/03 00:11:07 running Talos installer v1.10.5
2025/08/03 00:11:07 WARNING: config validation:
2025/08/03 00:11:07   use "worker" instead of "" for machine type
2025/08/03 00:11:07 created EFI (C12A7328-F81F-11D2-BA4B-00A0C93EC93B) size 104857600 bytes
2025/08/03 00:11:07 created BIOS (21686148-6449-6E6F-744E-656564454649) size 1048576 bytes
2025/08/03 00:11:07 created BOOT (0FC63DAF-8483-4772-8E79-3D69D8477DE4) size 1048576000 bytes
2025/08/03 00:11:07 created META (0FC63DAF-8483-4772-8E79-3D69D8477DE4) size 1048576 bytes
2025/08/03 00:11:07 formatting the partition "/dev/loop0p1" as "vfat" with label "EFI"
2025/08/03 00:11:07 formatting the partition "/dev/loop0p2" as "zeroes" with label "BIOS"
2025/08/03 00:11:07 formatting the partition "/dev/loop0p3" as "xfs" with label "BOOT"
2025/08/03 00:11:07 formatting the partition "/dev/loop0p4" as "zeroes" with label "META"
2025/08/03 00:11:07 copying from io reader to /boot/A/vmlinuz
2025/08/03 00:11:07 copying from io reader to /boot/A/initramfs.xz
2025/08/03 00:11:08 writing /boot/grub/grub.cfg to disk
2025/08/03 00:11:08 executing: grub-install --boot-directory=/boot --removable --efi-directory=/boot/EFI /dev/loop0
2025/08/03 00:11:08 installation of v1.10.5 complete
2025/08/03 00:11:08 Talos installer finished successfully
2025/08/03 00:11:08 remounting all filesystems read-only
2025/08/03 00:11:08 copy /tmp/installer-3221603450/image.raw → /dev/sda
2025/08/03 00:11:19 installation image copied to /dev/sda
2025/08/03 00:11:19 rebooting system
```

## About the Application

`boot-to-talos` is opensource and hosted on [github.com/cozystack/boot-to-talos](https://github.com/cozystack/boot-to-talos).
It includes a CLI written in Go and an installer script in Bash.
There are builds for several architectures:

- `linux-amd64`
- `linux-arm64`
- `linux-i386`

### How it Works

Understanding these steps is not required to install Talos Linux.

`boot-to-talos` performs a series of steps after it receives the configuration values: 

1.  **Unpacks Talos installer in RAM**<br>
    Extracts layers from the Talos‑installer container into a throw‑away `tmpfs`.
    Note that Docker is not needed during this step.
2.  **Builds system image**<br>
    Creates a sparse `image.raw`, exposed via a loop device, and executes the Talos *installer* inside a chroot.
    The installer then partitions, formats, and lays down GRUB and system files.
3.  **Streams to disk**<br>
    Copies `image.raw` to the chosen block device in chunks of 4 MiB and runs `fsync` after every write, so that data is fully committed before reboot.
4.  **Reboots**<br>
    Command `echo b > /proc/sysrq-trigger` performs an immediate reboot into the freshly installed Talos Linux.

## Next Steps

Once you have installed Talos, proceed by [installing and bootstrapping a Kubernetes cluster]({{% ref "/docs/install/kubernetes" %}}).
