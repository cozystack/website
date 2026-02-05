---
title: Install Talos Linux using PXE
linkTitle: PXE
description: "How to install Talos Linux using temporary DHCP and PXE servers running in Docker containers."
weight: 15
aliases:
  - /docs/talos/installation/pxe
  - /docs/talos/install/pxe
  - /docs/operations/talos/installation/pxe
---

This guide explains how to install Talos Linux on bare metal servers or virtual machines
using temporary DHCP and PXE servers running in Docker containers.
This method requires an extra management machine, but allows for installing on multiple hosts at once.

Note that Cozystack provides its own Talos builds, which are tested and optimized for running a Cozystack cluster.

## Dependencies

To install Talos using this method, you will need the following dependencies on the management host:

- `docker`
- `kubectl`

## Infrastructure Overview

![Cozystack deployment](/img/cozystack-deployment.png)

## Installation

Start matchbox with prebuilt Talos image for Cozystack:

```bash
sudo docker run --name=matchbox -d --net=host ghcr.io/cozystack/cozystack/matchbox:v0.30.0 \
  -address=:8080 \
  -log-level=debug
```

Start DHCP-Server:
```bash
sudo docker run --name=dnsmasq -d --cap-add=NET_ADMIN --net=host quay.io/poseidon/dnsmasq:v0.5.0-32-g4327d60-amd64 \
  -d -q -p0 \
  --dhcp-range=192.168.100.3,192.168.100.199 \
  --dhcp-option=option:router,192.168.100.1 \
  --enable-tftp \
  --tftp-root=/var/lib/tftpboot \
  --dhcp-match=set:bios,option:client-arch,0 \
  --dhcp-boot=tag:bios,undionly.kpxe \
  --dhcp-match=set:efi32,option:client-arch,6 \
  --dhcp-boot=tag:efi32,ipxe.efi \
  --dhcp-match=set:efibc,option:client-arch,7 \
  --dhcp-boot=tag:efibc,ipxe.efi \
  --dhcp-match=set:efi64,option:client-arch,9 \
  --dhcp-boot=tag:efi64,ipxe.efi \
  --dhcp-userclass=set:ipxe,iPXE \
  --dhcp-boot=tag:ipxe,http://192.168.100.254:8080/boot.ipxe \
  --log-queries \
  --log-dhcp
```

For an air-gapped installation, add NTP and DNS servers:
```bash
  --dhcp-option=option:ntp-server,10.100.1.1 \
  --dhcp-option=option:dns-server,10.100.25.253,10.100.25.254 \
```

Where:
- `192.168.100.3,192.168.100.199` range to allocate IPs from
- `192.168.100.1` your gateway
- `192.168.100.254` is address of your management server

Check status of containers:

```
docker ps
```

example output:

```console
CONTAINER ID   IMAGE                                               COMMAND                  CREATED          STATUS          PORTS     NAMES
06115f09e689   quay.io/poseidon/dnsmasq:v0.5.0-32-g4327d60-amd64   "/usr/sbin/dnsmasq -…"   47 seconds ago   Up 46 seconds             dnsmasq
6bf638f0808e   ghcr.io/cozystack/cozystack/matchbox:v0.30.0        "/matchbox -address=…"   3 minutes ago    Up 3 minutes              matchbox
```

Start your servers.
Now they should automatically boot from your PXE server.

## Next Steps

Once you have installed Talos, proceed by [installing and bootstrapping a Kubernetes cluster]({{% ref "/docs/install/kubernetes" %}}).
