---
title: "Networking Mesh"
linkTitle: "Networking Mesh"
description: "Configure Kilo WireGuard mesh with Cilium for multi-location cluster connectivity."
weight: 10
---

Kilo creates a WireGuard mesh between cluster locations. When running with Cilium, it uses
IPIP encapsulation routed through Cilium's VxLAN overlay so that traffic between locations
works even when the cloud network blocks raw IPIP (protocol 4) packets.

{{% alert title="Compatibility" color="warning" %}}
Multi-location support has been tested with the **Cilium** networking variant only.
The **KubeOVN+Cilium** variant has not been tested yet.
{{% /alert %}}

## Install Kilo

```bash
cozypkg add cozystack.kilo
```

When prompted, select the **cilium** variant. This deploys kilo with `--compatibility=cilium`,
enabling Cilium-aware IPIP encapsulation.

## Configure Cilium

### Disable host firewall

Cilium host firewall drops IPIP (protocol 4) traffic because the protocol is not in
Cilium's network policy API
(see [cilium#44386](https://github.com/cilium/cilium/issues/44386)).
Disable it:

```bash
kubectl patch package cozystack.networking --type merge -p '
spec:
  components:
    cilium:
      values:
        cilium:
          hostFirewall:
            enabled: false
'
```

## How it works

1. Kilo runs in `--local=false` mode -- it does not manage routes within a location (Cilium handles that)
2. Kilo creates a WireGuard tunnel (`kilo0`) between location leaders
3. Non-leader nodes in each location reach remote locations through IPIP encapsulation to their location leader, routed via Cilium's VxLAN overlay
4. The leader decapsulates IPIP and forwards traffic through the WireGuard tunnel

## Talos machine config for cloud nodes

Cloud worker nodes must include Kilo annotations in their Talos machine config:

```yaml
machine:
  nodeAnnotations:
    kilo.squat.ai/location: <cloud-location-name>
    kilo.squat.ai/persistent-keepalive: "20"
  nodeLabels:
    topology.kubernetes.io/zone: <cloud-location-name>
```

{{% alert title="Note" color="info" %}}
Kilo reads `kilo.squat.ai/location` from **node annotations**, not labels. The
`persistent-keepalive` annotation is critical for cloud nodes behind NAT -- it enables
WireGuard NAT traversal, allowing Kilo to discover the real public endpoint automatically.
{{% /alert %}}

## Allowed location IPs

By default, Kilo only routes pod and service CIDRs through the WireGuard mesh. If nodes in a
location use a private subnet that other locations need to reach (e.g. for kubelet communication
or NodePort access), annotate the location leader node with `kilo.squat.ai/allowed-location-ips`:

```yaml
machine:
  nodeAnnotations:
    kilo.squat.ai/allowed-location-ips: 192.168.102.0/24,192.168.103.0/24
```

This tells Kilo to include the specified CIDRs in the WireGuard allowed IPs for that location,
making those subnets routable through the tunnel from all other locations.

{{% alert title="Note" color="info" %}}
Set this annotation on the **location leader** node (the node elected by Kilo to terminate
the WireGuard tunnel for a given location). The annotation accepts a comma-separated list of
CIDRs. Typically you would list all node subnets used in that cloud location.
{{% /alert %}}

## Troubleshooting

### WireGuard tunnel not established
- Verify the node has `kilo.squat.ai/persistent-keepalive: "20"` annotation
- Verify the node has `kilo.squat.ai/location` annotation (not just as a label)
- Check that the cloud firewall allows inbound UDP 51820
- Inspect kilo logs: `kubectl logs -n cozy-kilo <kilo-pod>`
- Repeating "WireGuard configurations are different" messages every 30 seconds indicate a missing `persistent-keepalive` annotation

### Non-leader nodes unreachable (kubectl logs/exec timeout)
- Verify IP forwarding is enabled on the cloud network interfaces (required for the Kilo leader to forward traffic)
- Check kilo pod logs for `failed to create tunnel interface` errors
