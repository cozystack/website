---
title: "A Simple Way to Install Talos Linux on Any Machine, with Any Provider"
slug: a-simple-way-to-install-talos-linux-on-any-machine-with-any-provider
date: 2025-04-28
author: "Andrei Kvapil"
description: "Talos Linux is a specialized operating system designed for running Kubernetes. In my opinion, it does that task better than others. First…"
---

### A Simple Way to Install Talos Linux on Any Machine, with Any Provider

Talos Linux is a specialized operating system designed for running Kubernetes. In my opinion, it does that task better than others. First and foremost it handles full lifecycle management for Kubernetes control-plane components.

On the other hand, Talos Linux focuses on security, minimizing the user’s ability to influence the system. A distinctive feature of this OS is the near-complete absence of executables, including the absence of a shell and the inability to log in via SSH. All configuration of Talos Linux is done through a Kubernetes-like API.

![](https://cdn-images-1.medium.com/max/800/1*ca81wgE3M5JA6B9ST8gT1A.png)

Typically, Talos Linux is provided as a set of pre-built images for various environments.

The standard installation method assumes you will take a prepared image for your specific cloud provider or hypervisor and create a virtual machine from it. Talking about physical servers, there might be such options as loading the Talos Linux image using ISO or PXE methods.

Unfortunately, this does not work when dealing with providers that offer a pre-configured server or virtual machine without letting you upload a custom image or even use an ISO for installation through KVM. In that case, your choices are limited to the distributions the cloud provider makes available.

Usually during the Talos Linux installation process, two questions need to be answered: (1) How to load and boot the Talos Linux image, and (2) How to prepare and apply the machine-config (the main configuration file for Talos Linux) to that booted image. Let’s talk about each of these steps.

### Booting into Talos Linux

One of the most universal methods is to use a Linux kernel mechanism called [kexec](https://en.wikipedia.org/wiki/Kexec).

*kexec* is both a utility and a system call of the same name. It allows you to boot into a new kernel from the existing system without performing a physical reboot of the machine. This means you can download the required *vmlinuz* and *initramfs* for Talos Linux, and then, specify the needed kernel *cmdline* and immediately switch over to the new system. It’s as if the kernel were loaded by the standard bootloader at startup, only in this case your existing OS acts as the bootloader.

Essentially, all you need is any Linux distribution. It could be a physical server running in rescue mode, or even a virtual machine with a pre-installed operating system. Let’s take a look at a case using Ubuntu on, but it can be literally any other Linux distribution.

Log in via SSH and install the *kexec-tools* package, it contains the *kexec* utility, which you’ll need later:

``` graf
apt install kexec-tools -y
```

Next, you need to download the Talos Linux, that is the *kernel* and *initramfs*. They can be downloaded from the official repository:

``` graf
wget -O /tmp/vmlinuz https://github.com/siderolabs/talos/releases/latest/download/vmlinuz-amd64
wget -O /tmp/initramfs.xz https://github.com/siderolabs/talos/releases/latest/download/initramfs-amd64.xz
```

If you have a physical server rather than a virtual one, you’ll need to build your own image with all the necessary firmware using [Talos Factory](https://factory.talos.dev) service. Alternatively, you can use the pre-built images from the Cozystack project (a solution for building clouds we created at Ænix and transferred to CNCF Sandbox) — these images already include all required modules and firmware:

``` graf
wget -O /tmp/vmlinuz https://github.com/cozystack/cozystack/releases/latest/download/kernel-amd64
wget -O /tmp/initramfs.xz https://github.com/cozystack/cozystack/releases/latest/download/initramfs-metal-amd64.xz
```

Now you need the network information that will be passed to Talos Linux at boot time. Below is a small script that gathers everything you need and sets environment variables:

``` graf
IP=$(ip -o -4 route get 8.8.8.8 | awk -F"src " '{sub(" .*", "", $2); print $2}')
GATEWAY=$(ip -o -4 route get 8.8.8.8 | awk -F"via " '{sub(" .*", "", $2); print $2}')
ETH=$(ip -o -4 route get 8.8.8.8 | awk -F"dev " '{sub(" .*", "", $2); print $2}')
CIDR=$(ip -o -4 addr show "$ETH" | awk -F"inet $IP/" '{sub(" .*", "", $2); print $2; exit}')
NETMASK=$(echo "$CIDR" | awk '{p=$1;for(i=1;i=8){o=255;p-=8}else{o=256-2^(8-p);p=0}printf(italosctl](https://www.talos.dev/latest/learn-more/talosctl/) utility or the [Talm](https://github.com/cozystack/talm), utility maintained by the Cozystack project (Talm works with vanilla Talos Linux as well).

First, let’s consider configuration using *talosctl*. Before applying the config, ensure it includes network settings for your node; otherwise, after reboot, the node won’t configure networking. During installation, the bootloader is written to disk and does not contain the `ip` option for kernel autoconfiguration.

Here’s an example of a config patch containing the necessary values:

``` graf
# node1.yaml
machine:
  install:
    disk: /dev/sda
  network:
    hostname: node1
    nameservers:
    - 1.1.1.1
    - 8.8.8.8
    interfaces:
    - interface: eno2np0
      addresses:
      - 10.0.0.131/24
      routes:
      - network: 0.0.0.0/0
        gateway: 10.0.0.1
```

You can use it to generate a full machine-config:

``` graf
talosctl gen secrets
talosctl gen config --with-secrets=secrets.yaml --config-patch-control-plane=@node1.yaml  
```

Review the resulting config and apply it to the node:

``` graf
talosctl apply -f controlplane.yaml -e 10.0.0.131 -n 10.0.0.131 -i
```

Once you apply `controlplane.yaml`, the node will install Talos on the `/dev/sda` disk, overwriting the existing OS, and then reboot.

All you need now is to run the `bootstrap` command to initialize the etcd cluster:

``` graf
talosctl --talosconfig=talosconfig bootstrap -e 10.0.0.131 -n 10.0.0.131
```

You can view the node’s status at any time using `dashboard` commnad:

``` graf
talosctl --talosconfig=talosconfig dashboard -e 10.0.0.131 -n 10.0.0.131
```

As soon as all services reach the `Ready` state, retrieve the kubeconfig and you’ll be able to use your newly installed Kubernetes:

``` graf
talosctl --talosconfig=talosconfig kubeconfig kubeconfig
export KUBECONFIG=${PWD}/kubeconfig
```

### Use Talm for configuration management

When you have a lot of configs, you’ll want a convenient way to manage them. This is especially useful with bare-metal nodes, where each node may have different disks, interfaces and specific network settings. As a result, you might need to hold a patch for each node.

To solve this, we developed [Talm](https://github.com/cozystack/talm) — a configuration manager for Talos Linux that works similarly to Helm.

The concept is straightforward: you have a common config template with lookup functions, and when you generate a configuration for a specific node, Talm dynamically queries the Talos API and substitutes values into the final config.

Talm includes almost all of the features of *talosctl*, adding a few extras. It can generate configurations from Helm-like templates, and remember the node and endpoint parameters for each node in the resulting file, so you don’t have to specify these parameters every time you work with a node.

**Let me show how to perform the same steps to install Talos Linux using Talm:**

First, initialize a configuration for a new cluster:

``` graf
mkdir talos
cd talos
talm init
```

Adjust values for your cluster in `values.yaml`:

``` graf
endpoint: "https://10.0.0.131:6443"
podSubnets:
- 10.244.0.0/16
serviceSubnets:
- 10.96.0.0/16
advertisedSubnets:
- 10.0.0.0/24
```

Generate a config for your node:

``` graf
talm template -t templates/controlplane.yaml -e 10.0.0.131 -n 10.0.0.131 > nodes/node1.yaml
```

The resulting output will look something like:

``` graf
# talm: nodes=["10.0.0.131"], endpoints=["10.0.0.131"], templates=["templates/controlplane.yaml"]
# THIS FILE IS AUTOGENERATED. PREFER TEMPLATE EDITS OVER MANUAL ONES.
machine:
  type: controlplane
  kubelet:
    nodeIP:
      validSubnets:
        - 10.0.0.0/24
  network:
    hostname: node1
    # -- Discovered interfaces:
    # eno2np0:
    #   hardwareAddr:a0:36:bc:cb:eb:98
    #   busPath: 0000:05:00.0
    #   driver: igc
    #   vendor: Intel Corporation
    #   product: Ethernet Controller I225-LM)
    interfaces:
      - interface: eno2np0
        addresses:
          - 10.0.0.131/24
        routes:
          - network: 0.0.0.0/0
            gateway: 10.0.0.1
    nameservers:
      - 1.1.1.1
      - 8.8.8.8
  install:
    # -- Discovered disks:
    # /dev/sda:
    #    model: SAMSUNG MZQL21T9HCJR-00A07
    #    serial: S64GNG0X444695
    #    wwid: eui.36344730584446950025384700000001
    #    size: 1.9 TB
    disk: /dev/sda
cluster:
  controlPlane:
    endpoint: https://10.0.0.131:6443
  clusterName: talos
  network:
    serviceSubnets:
      - 10.96.0.0/16
  etcd:
    advertisedSubnets:
      - 10.0.0.0/24
```

All that remains is to apply it to your node:

``` graf
talm apply -f nodes/node1.yaml -i
```

Talm automatically detects the node address and endpoint from the “modeline” (a conditional comment at the top of the file) and applies the config.

You can also run other commands in the same way without specifying node address and endpoint options. Here are a few examples:

View the node status using the built-in dashboard command:

``` graf
talm dashboard -f nodes/node1.yaml
```

Bootstrap etcd cluster on `node1`:

``` graf
talm bootstrap -f nodes/node1.yaml
```

Save the kubeconfig to your current directory:

``` graf
talm kubeconfig -f nodes/node1.yaml
```

Unlike the official *talosctl* utility, the generated configs do not contain secrets, allowing them to be stored in git without additional encryption. The secrets are stored at the root of your project and only in these files: `secrets.yaml`, `talosconfig`, and `kubeconfig`.

### Summary

That’s our complete scheme for installing Talos Linux in nearly any situation. Here’s a quick recap:

1.  Use *kexec* to run Talos Linux on any existing system.
2.  Make sure the new kernel has the correct network settings, by collecting them from the current system and passing via the `ip` parameter in the *cmdline*. This lets you connect to the newly booted system via the API.
3.  When the kernel is booted via *kexec*, Talos Linux runs entirely in RAM. To install Talos on disk, apply your configuration using either *talosctl* or Talm.
4.  When applying the config, don’t forget to specify network settings for your node, because on-disk bootloader configuration doesn’t automatically have them.
5.  Enjoy your newly installed and fully operational Talos Linux.

### Additional materials

- [How we built a dynamic Kubernetes API Server for the API Aggregation Layer in Cozystack](https://kubernetes.io/blog/2024/11/21/dynamic-kubernetes-api-server-for-cozystack/)
- [DIY: Create Your Own Cloud with Kubernetes](https://kubernetes.io/blog/2024/04/05/diy-create-your-own-cloud-with-kubernetes-part-1/)
- [Cozystack Becomes a CNCF Sandbox Project](https://blog.aenix.io/cozystack-becomes-a-cncf-sandbox-project-3702b8906971)
- [Journey to Stable Infrastructures with Talos Linux &amp; Cozystack | Andrei Kvapil | SREday London 2024](https://www.youtube.com/watch?v=uhXujtTzG44)
- [Talos Linux: You don’t need an operating system, you only need Kubernetes / Andrei Kvapil](https://www.youtube.com/watch?v=9CIMTum9bTA)
- [Comparing GitOps: Argo CD vs Flux CD, with Andrei Kvapil | KubeFM](https://www.youtube.com/watch?v=4RVe32xRITo)
- [Cozystack on Talos Linux](https://www.youtube.com/watch?v=s79VqXu-eG4)