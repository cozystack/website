---
title: "Networking Mesh"
linkTitle: "Networking Mesh"
description: "Configure Kilo WireGuard mesh with Cilium for multi-location cluster connectivity."
weight: 10
---

Kilo creates a WireGuard mesh between cluster locations. When running with Cilium, it uses
IPIP encapsulation routed through Cilium's VxLAN overlay so that traffic between locations
works even when the cloud network blocks raw IPIP (protocol 4) packets.

## Select the cilium-kilo networking variant

During platform setup, select the **cilium-kilo** networking variant. This deploys both Cilium
and Kilo as an integrated stack with the required configuration:

## How it works

1. Kilo runs in `--local=false` mode -- it does not manage routes within a location (Cilium handles that)
2. Kilo creates a WireGuard tunnel (`kilo0`) between location leaders
3. Non-leader nodes in each location reach remote locations through IPIP encapsulation to their location leader, routed via Cilium's VxLAN overlay
4. The leader decapsulates IPIP and forwards traffic through the WireGuard tunnel
5. Cilium's `enable-ipip-termination` option creates the `cilium_tunl` interface (kernel's `tunl0` renamed) that Kilo uses for IPIP TX/RX -- without it, the kernel detects TX recursion on the tunnel device

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

By default, Kilo only routes pod CIDRs and individual node internal IPs through the WireGuard mesh. If nodes in a
location use a private subnet that other locations need to reach (e.g. for kubelet communication
or NodePort access), annotate the nodes **in that location** with `kilo.squat.ai/allowed-location-ips`:

```bash
# On on-premise nodes — expose the on-premise subnet to cloud nodes
kubectl annotate node <on-premise-node> kilo.squat.ai/allowed-location-ips=192.168.100.0/24
```

This tells Kilo to include the specified CIDRs in the WireGuard allowed IPs for that location,
making those subnets routable through the tunnel from all other locations.

{{% alert title="Warning" color="warning" %}}
Set this annotation on nodes **that own the subnet you want to expose** (i.e. nodes in the
location where that network exists), **not** on remote nodes that want to reach it. If you
set it on the wrong location, Kilo will create a route that sends traffic for that CIDR
through the WireGuard tunnel on all other nodes -- including nodes that are directly connected
to that subnet via L2. This breaks local connectivity between co-located nodes.

For example, if your cloud nodes use `10.2.0.0/24`, add the annotation to the **cloud** nodes.
Do **not** add the on-premise subnet (e.g. `192.168.100.0/23`) to cloud nodes -- this would
hijack all local traffic between on-premise nodes through the WireGuard tunnel.
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
- Check kilo pod logs for `cilium_tunl interface not found` errors -- this means Cilium is not running with `enable-ipip-termination=true` (the cilium-kilo variant configures this automatically)
