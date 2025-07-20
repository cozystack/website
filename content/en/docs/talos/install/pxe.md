---
title: How to install Cozystack using PXE
linkTitle: Install using PXE
description: "How to install Cozystack using PXE"
weight: 10
aliases:
  - /docs/talos/installation/pxe
  - /docs/operations/talos/installation/pxe
---

![Cozystack deployment](/img/cozystack-deployment.png)

## Install dependencies:

- `docker`
- `kubectl`

## Netboot server

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

Start your servers, now they should automatically boot from your PXE server.


Now, when they are booted to Talos Linux maintenance mode, you can use [talos-bootstrap](https://github.com/cozystack/talos-bootstrap) or [Talm](https://github.com/cozystack/talm) to bootstrap the cluster


Just follow **Getting Started** guide starting from the [**Bootstrap cluster**](/docs/getting-started/first-deployment/#bootstrap-cluster) section, to continue the installation.
