---
title: "Site-to-Site IPsec with Site Router"
linkTitle: "Site-to-Site IPsec"
description: "How the Site Router application works and how to use it: connect a tenant network to a remote network over IPsec, configure the remote device, verify the tunnel, and troubleshoot it."
weight: 13
---

This page explains how the Site Router application works and walks through using it end to end. The [Managed Site-to-Site Router]({{% ref "/docs/next/networking/site-router" %}}) reference page is generated from the package README and covers the parameters, the settings for the remote peer, events and limitations. This page adds the architecture, an end-to-end walkthrough, day-2 operations, troubleshooting and the security model.

## What Site Router does

Site Router connects a tenant to a remote network, such as an office, a data center, or another cloud, over an IKEv2 IPsec tunnel. The two sides see each other through plain routing:

- Whole subnets are reachable in both directions, for TCP, UDP, ICMP and SCTP.
- Addresses are not translated. A workload in the tenant sees the real address of the remote host that connected to it, and the remote host sees the real address of the pod.
- The tenant keeps its own gateway. The tunnel terminates in a virtual machine inside the tenant namespace, so it is created, sized and removed together with the tenant's other applications.

Site Router is not a NAT gateway. It does not hide tenant traffic behind a single address, and it does not forward inbound ports to individual services. If you need address translation, Site Router is the wrong tool in this release.

## How it works

### The pieces

Creating a `SiteRouter` instance named `office` in a tenant namespace produces the objects below. All of them are named after the instance, with the prefix `site-router-`:

| Object | Name | Purpose |
| --- | --- | --- |
| `VirtualMachine` | `site-router-office` | The gateway. It runs the [barerouter](#the-gateway-image) appliance with 2 CPU cores and 2 GiB of memory by default, attached to the tenant pod network. |
| `DataVolume` | `site-router-office-boot` | The gateway's boot disk, imported from the appliance image by digest. |
| `Service` (`LoadBalancer`) | `site-router-office-tunnel` | The public tunnel endpoint. It exposes UDP 500 (IKE) and UDP 4500 (NAT-T) and keeps the remote peer's source address (`externalTrafficPolicy: Local`). |
| `Secret` | `site-router-office-psk` | The pre-shared key, in the key `psk`. |
| `CiliumNetworkPolicy` | `site-router-office-gateway-ingress`, `site-router-office-gateway-egress-deny` | Restrict what can reach the gateway and what the gateway can reach. See [Security model](#security-model). |
| `WorkloadMonitor` | `site-router-office` | Reports whether the gateway VM is running. The application's `WorkloadsReady` condition reads it. |

A platform controller, `site-router-controller`, runs in the `cozy-site-router` namespace. It does the parts a Helm chart cannot do, and it keeps doing them for the life of the instance:

1. Validates the declared `remoteCIDRs` against the cluster's own networks and rejects overlaps.
1. Programs the **return route** for the remote networks into the tenant namespace, so tenant pods send traffic for those networks to the gateway.
1. Waits for the tunnel Service to get its LoadBalancer address, because that address is the gateway's IKE identity.
1. Renders the gateway's configuration (IPsec, firewall, routes, BGP) and pushes it to the gateway's management API over HTTPS as one atomic transaction.
1. Confirms that the gateway's source filter is active before it counts a reconcile as successful, and applies it again if it disappears.

The controller re-checks every instance about every 30 seconds. A reconcile with no changes makes no call to the gateway.

### The data path

```text
 remote site                            Cozystack tenant namespace
+----------------+                     +--------------------------------------------+
| remote device  |   IKEv2, ESP in UDP |  Service site-router-office-tunnel         |
| 192.168.50.0/24| ------------------> |  (LoadBalancer, UDP 500 and 4500)          |
+----------------+                     |        |                                   |
                                       |        v                                   |
                                       |  gateway VM (barerouter)                   |
                                       |        |  decrypted, source IP preserved   |
                                       |        v                                   |
                                       |  tenant pods and Service ClusterIPs        |
                                       +--------------------------------------------+
                                                ^
                                                | configuration over HTTPS
                                       site-router-controller (cozy-site-router)
```

Three properties of this design show up in day-to-day use:

- **The gateway only responds.** The remote peer must initiate the tunnel. The gateway never dials out, so a tunnel that dropped (for example after a gateway restart) comes back only when the remote device dials in again.
- **ESP is always carried in UDP.** Only UDP 500 and 4500 reach the gateway, and the gateway forces NAT-T encapsulation on its side. The remote device must use UDP encapsulation too.
- **One instance is one tunnel to one peer.** To connect a second site, create a second `SiteRouter` in the same tenant. Each instance takes one address from the tenant's LoadBalancer pool, so the number of sites you can connect is bounded by that pool and its quota.

## Requirements

- **Platform.** Site Router is part of the NaaS bundle, and it is installed only when the IaaS bundle (KubeVirt and CDI) is enabled as well, because the gateway is a virtual machine. See [Variants]({{% ref "/docs/next/operations/configuration/variants" %}}) for what each variant enables. The tenant also needs a free LoadBalancer address.
- **Network reachability.** The remote site must be able to send UDP 500 and UDP 4500 to the tunnel address. If a firewall sits in front of the remote device, allow the same ports outbound to that address.
- **Remote device.** It must support IKEv2 with a pre-shared key and forced UDP encapsulation, and it must be able to initiate the tunnel.
- **Non-overlapping addressing.** The remote networks must not overlap the cluster's pod, service or join networks, node addresses, or allocated LoadBalancer addresses. See [Remote networks](#remote-networks).

## Creating a Site Router

You can create a Site Router from the dashboard (category **NaaS**) or with a manifest. The minimum is the address of the remote device and the networks behind it:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: SiteRouter
metadata:
  name: office
  namespace: tenant-root
spec:
  peer:
    address: 203.0.113.10        # public address the remote device connects from
  remoteCIDRs:
    - 192.168.50.0/24            # networks behind the remote device
```

`peer.address` is the address the remote device connects **from**, and it is also the identity the gateway expects from it. Use the public address of the remote device, not an internal interface address.

Wait for the gateway to boot. The first start imports the boot disk, so it takes longer than later restarts:

```bash
kubectl get siterouters.apps.cozystack.io -n tenant-root
kubectl get datavolume,vm,svc -n tenant-root | grep site-router-office
```

### Remote networks

`remoteCIDRs` lists the networks behind the remote device. Up to 16 are accepted, and they are IPv4 only. Each network must be disjoint from everything the cluster owns:

- the cluster's pod, service and join networks,
- the address of any node,
- any allocated LoadBalancer or external service address,
- link-local (`169.254.0.0/16`) and loopback (`127.0.0.0/8`) ranges,
- and `0.0.0.0/0`, which is never accepted.

An overlapping value is rejected when you apply the manifest, and the error names the network and the address it collides with. The controller runs the same check on every reconcile. If the cluster changes later so that a declared network now overlaps, the controller records an `InvalidRemoteCIDR` event and withdraws the affected routes instead of leaving a blackhole.

Two instances in the same tenant namespace cannot declare the same remote network. The second one reports a `RouteConflict` event, and the first one's route stays in place.

### Pre-shared key

If you do not set `peer.auth.psk`, Cozystack generates a 32-character key and keeps it stable across reconciles. To supply your own, either set `peer.auth.psk`, or create a Secret in the tenant namespace with the key in the field `psk` and reference it:

```yaml
spec:
  peer:
    address: 203.0.113.10
    auth:
      existingSecret: office-psk
```

`existingSecret` takes precedence over `psk`, and the two are mutually exclusive.

## Getting the connection details

The remote device needs the tunnel address and the pre-shared key:

```bash
# Tunnel address (the LoadBalancer address of the gateway)
kubectl get svc site-router-office-tunnel -n tenant-root \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}{"\n"}'

# Pre-shared key
kubectl get secret site-router-office-psk -n tenant-root \
  -o jsonpath='{.data.psk}' | base64 -d; echo
```

The dashboard shows the same two values on the application page. Both are readable at the tenant's `use` access level, because the remote side needs them. The gateway's management API key is not readable by tenants.

## Configuring the remote device

The gateway offers fixed proposals in this release, and the remote device has to match them. The full list of settings (IKE and ESP proposals, identities, traffic selectors and encapsulation) is in [Configuring the remote peer]({{% ref "/docs/next/networking/site-router#configuring-the-remote-peer" %}}) in the reference. The notes below cover the points that most often go wrong.

Lifetimes are local policy in IKEv2, so they do not need to match. The identity settings are the usual cause of a tunnel that never comes up: the gateway looks up the pre-shared key by the identity the remote device presents (`peer.address`), and the remote device authenticates the gateway by the tunnel address. If the remote device sits behind NAT, its default identity is usually its private interface address, which does not match `peer.address`, so set the local identity explicitly.

The gateway pairs each declared remote network with its own child SA, so offer one child (one pair of traffic selectors) per network in `remoteCIDRs`.

As an illustration, this is how the remote side looks in strongSwan's `swanctl.conf`. Translate it to your device's syntax if it is not strongSwan:

```text
connections {
    cozystack {
        version = 2
        local_addrs  = 203.0.113.10
        remote_addrs = 198.51.100.20       # tunnel address
        proposals = aes256-sha256-modp2048
        encap = yes
        local {
            auth = psk
            id = 203.0.113.10              # peer.address
        }
        remote {
            auth = psk
            id = 198.51.100.20             # tunnel address
        }
        children {
            office {
                local_ts  = 192.168.50.0/24
                remote_ts = 0.0.0.0/0
                esp_proposals = aes256-sha256-modp2048
                start_action = start
                dpd_action = restart
            }
        }
    }
}
secrets {
    ike-cozystack {
        id-local  = 203.0.113.10
        id-remote = 198.51.100.20
        secret = "<pre-shared key>"
    }
}
```

## Using the tunnel

### Tenant workloads reaching the remote network

The controller writes a return route for every remote network into the tenant namespace, with the gateway as the next hop. Pods created after that point inherit it automatically.

{{% alert color="warning" %}}

kube-ovn stamps routes onto a pod when the pod is created. Pods that were already running when you created the Site Router, or when you added a network to `remoteCIDRs`, do not have the route and cannot reach the remote site until they are restarted. The controller does not restart anything on its own. It records a `PendingRoutes` event that lists the pods still waiting:

```bash
kubectl get events -n tenant-root --field-selector reason=PendingRoutes
```

{{% /alert %}}

### The remote site reaching tenant workloads

The remote site reaches tenant workloads by **pod IP** or **Service ClusterIP**, and only those that belong to the tenant namespace that owns the Site Router. The gateway builds this list from the namespace's live pods and Services, so:

- A pod or Service created after the last reconcile becomes reachable from the remote site on the next one, within about 30 seconds.
- Other tenants' workloads, cluster nodes, the Kubernetes API and the public internet are not reachable through the tunnel, even if the remote device sends traffic for them.
- Gateway pods, terminating pods, completed Job pods and `hostNetwork` pods are left out of the list.

Because addresses are not translated, the source address your workload sees is the remote host's real address. To Cilium, traffic from the remote site arrives from the `world` entity.

### Static routes and BGP

`staticRoutes` adds extra routes on the gateway itself. Each entry is a destination in CIDR notation and a next-hop address, and the destination goes through the same overlap check as `remoteCIDRs`.

`bgp` enables BGP peering over the tunnel: `localASN` and a list of `neighbors`, each with an address and a `remoteASN`. In this release a BGP session receives the neighbor's routes and does not originate any of its own. The return route in the tenant namespace and the gateway's source filter are built from `remoteCIDRs` only, so list every remote network you want to reach there as well, whether or not BGP also learns it.

## Operating a Site Router

### Changing the configuration

| Change | Effect |
| --- | --- |
| `remoteCIDRs`, `staticRoutes`, `bgp`, `peer` | Applied to the running gateway in place, with no VM restart. Established IPsec SAs survive the change. |
| `peer.auth.psk` or `existingSecret` | Applied the same way. Update the remote device to the new key at the same time. |
| `resources` | Part of the VM definition. Treat it as a maintenance event: restarting the gateway drops the tunnel. |
| `storageClass` | Cannot be changed after creation. Delete and recreate the instance to change it. |
| A new appliance image | Existing gateways keep the image they imported. A new image is used only when the instance is recreated. |

Restarting the gateway VM tears down every SA. Because the gateway only responds, the tunnel is back only after the VM boots, the controller pushes the configuration, and the remote device dials in again.

### High availability

A Site Router is a single virtual machine. With the default `storageClass: replicated` (DRBD-backed), the boot disk is live-migratable, so draining a node moves the gateway without dropping the tunnel. If the node fails, the tunnel stays down until the VM is rescheduled and the remote device reconnects. Use a non-replicated storage class only on a platform without DRBD, because the gateway then cannot be moved off its node while it is running.

### Monitoring

The application's `WorkloadsReady` condition reflects whether the gateway VM is running. It does **not** reflect controller failures in this release, so a gateway can be running while its configuration has not been applied. Check events and metrics as well:

```bash
kubectl get events -n tenant-root \
  --field-selector involvedObject.kind=HelmRelease,involvedObject.name=site-router-office
```

The controller exports these metrics to the platform's monitoring stack, labelled by tenant namespace, instance and peer:

| Metric | Meaning |
| --- | --- |
| `site_router_tunnel_up` | 1 when the IPsec tunnel is up, 0 when it is down or connecting |
| `site_router_bgp_session_up` | 1 when the BGP session is established. Set only when BGP is enabled |
| `site_router_config_apply_errors_total` | Failed configuration pushes to the gateway |

Alert on `site_router_tunnel_up == 0` for longer than your tolerance for a dropped site link.

## Troubleshooting

The gateway has no shell. SSH is not installed, the login is locked and the bootloader is locked, so the serial console shows boot output and nothing more. This is deliberate (see [Security model](#security-model)), and it means the remote device's own SA status is usually the most useful diagnostic.

**The tunnel does not come up**

1. Confirm the remote device can send UDP 500 and 4500 to the tunnel address, and that no firewall drops them. Only IKE and NAT-T reach the gateway, so native ESP (IP protocol 50) never arrives.
1. Confirm the remote device connects from the address you set in `peer.address`.
1. Check the identities: local identity `peer.address`, remote identity the tunnel address. See [Configuring the remote device](#configuring-the-remote-device).
1. Compare the pre-shared key byte for byte.
1. Compare the proposals, and make sure UDP encapsulation is forced on the remote device.
1. Check `site_router_tunnel_up` and the events below for a controller-side cause.

**Events**

The reference lists the main event reasons in [Events]({{% ref "/docs/next/networking/site-router#events" %}}). The controller also records these while the gateway comes up, or when part of the configuration is unusable:

| Reason | Meaning |
| --- | --- |
| `GatewayPending` | The gateway pod is not scheduled yet or has no IP. |
| `TunnelNotConfigured` | `peer.address` or the pre-shared key is empty, so no tunnel is configured. |
| `SourceFilterPending` | The gateway's source filter is not confirmed active yet. |
| `NoTunnelDestinations` | The namespace has no pods or Services the remote site could reach, so only return traffic is accepted. |
| `BGPLocalASNInvalid` | BGP is enabled without a usable `localASN`, so it is skipped. |

`PortSecurityRelaxationPending`, `APIKeySecretPending` and `APITLSUnverified` indicate a platform-level problem with the gateway pod or its management channel. Report them to your platform administrator.

**Pods cannot reach the remote network while the tunnel is up.** Restart the pods listed in the `PendingRoutes` event.

**A new pod is not reachable from the remote site.** Wait for the next reconcile, about 30 seconds.

**Large transfers stall while small packets work.** The tunnel path has a reduced MTU, and the gateway clamps the TCP MSS to 1280 by default. UDP and other protocols that do not negotiate MSS must stay within the tunnel MTU.

## Security model

The gateway is more privileged than an ordinary tenant pod. It decrypts traffic and forwards packets whose source address is not its own, and it is reachable from the public internet on the tunnel ports. The platform contains that privilege with several independent guards.

- **Source filter inside the gateway.** kube-ovn's per-port anti-spoofing is turned off for the gateway's port, and only for that port, so that it can forward packets with the remote host's source address. The gateway's own firewall compensates: it accepts decrypted traffic only if the source is in `remoteCIDRs` **and** the destination is a pod IP or Service ClusterIP of this tenant namespace. Everything else is dropped, including traffic to other tenants, to nodes and to the internet. With no remote networks or no destinations, the filter fails closed.
- **Default-deny forwarding.** The gateway forwards nothing that is not a recognized flow: return traffic, the tenant's own outbound traffic, and decrypted tunnel traffic that passed the source filter.
- **Management API isolation.** The gateway's HTTPS management API is reachable only by the platform controller. It is closed to tenant workloads and to the remote peer, including traffic that arrives through the tunnel and addresses the gateway itself. The API key is held in a Secret that tenant roles cannot read.
- **No interactive access.** The appliance ships with no SSH service, the default login is locked, and the bootloader is password-locked with a password nobody holds, so the serial console cannot lead to a root shell.
- **Cilium policies.** The gateway admits from the world only UDP 500 and 4500, and admits the controller only on TCP 443. It is denied egress to link-local addresses, which includes the cloud metadata endpoint.
- **Input validation.** Remote networks, static route destinations and BGP neighbor addresses are all checked against the cluster's own addresses before they reach the gateway's configuration.

Known limitations of this release:

- The gateway's port is relaxed from boot. Until the controller's first configuration push installs the source filter, there is no filter. The tunnel is not up in that window, so there is no decrypted traffic to forward.
- A tenant super-admin, who has full rights on `VirtualMachine` objects, can edit the gateway VM and replace its configuration. Tenants also keep console, VNC and restart rights on the gateway VM. The locked bootloader and login limit what the console gives, but a restart is still possible and drops the tunnel.
- The pre-shared key is stored in a Secret and appears in plaintext in the gateway's configuration. It is redacted from events, conditions and logs.
- The Cilium ingress policy narrows access to the gateway but does not replace the gateway's own firewall, which remains the main protection for the management API.

## The gateway image

The gateway boots [barerouter](https://github.com/aenix-io/barerouter), a router image published by Aenix. barerouter is built from the public VyOS rolling sources, with the VyOS name, trademarks and logo artwork removed. It is not produced, endorsed or supported by VyOS Inc.

- **Build.** Each barerouter release is built from a pinned `vyos-build` commit, Debian bookworm and the VyOS rolling package repository. The release publishes the SBOM (CycloneDX and SPDX), the list of every installed package with its source package and version, and a manifest that says where the source of each package is.
- **KubeVirt disk.** Cozystack uses the KubeVirt disk of a release, published as a container image. The disk adds a serial console, a configuration seed that installs the per-instance configuration before the router starts, the guest agent, and the locked bootloader.
- **Pinned by digest.** The platform references one barerouter release by digest. Each gateway imports that exact image when it is created, so a platform upgrade never changes the image under a running gateway.
- **License.** The build scripts are Apache-2.0. The image is a collection of components under their own licenses: the image's EULA is at `/usr/share/vyos/EULA` inside the image, and each installed package's license is under `/usr/share/doc/<package>/copyright`. See also the [Licenses]({{% ref "/docs/next/operations/configuration/licenses" %}}) and [Platform Stack]({{% ref "/docs/next/guides/platform-stack" %}}) pages.

## Limitations

The reference lists the main [limitations]({{% ref "/docs/next/networking/site-router#limitations" %}}): one peer per instance, a gateway that only answers, one route owner per remote network, and a site count bounded by the LoadBalancer pool. Also not available in this release:

- IPv6 remote networks.
- NAT, masquerading and inbound port forwarding.
- Gateway high availability. A Site Router is a single VM.
- Per-tunnel byte and rekey counters. Only up and down state is exported.
- Originating BGP routes. A BGP session only receives them.
- Configurable IKE and ESP proposals. The proposals in [Configuring the remote device](#configuring-the-remote-device) are fixed.

## See also

- [Managed Site-to-Site Router]({{% ref "/docs/next/networking/site-router" %}}): the parameter reference.
- [Network Architecture]({{% ref "/docs/next/networking/architecture" %}}): the tenant pod network that the gateway attaches to.
- [Virtual Routers]({{% ref "/docs/next/networking/virtual-router" %}}): building a router from a plain VM by hand.
- [barerouter](https://github.com/aenix-io/barerouter): the gateway image, its SBOM and sources.
