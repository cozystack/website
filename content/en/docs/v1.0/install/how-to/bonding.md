---
title: "How to configure network bonding (LACP)"
linkTitle: "Configure bonding (LACP)"
description: "How to configure LACP (802.3ad) network bonding for link aggregation and redundancy"
weight: 120
---

Network bonding allows you to combine multiple physical network interfaces into a single logical interface.
This provides increased bandwidth and link redundancy.

LACP (Link Aggregation Control Protocol, IEEE 802.3ad) is the most common bonding mode,
which dynamically negotiates link aggregation with the network switch.

{{% alert color="warning" %}}
LACP requires configuration on both the server and the network switch.
Make sure your switch has a corresponding LACP port-channel configured for the server's ports.
{{% /alert %}}

## Identify network interfaces

After running `talm template`, the generated node configuration file will contain
a comment block with discovered network interfaces:

```yaml
machine:
  network:
    # -- Discovered interfaces:
    # eno1:
    #   hardwareAddr: aa:bb:cc:dd:ee:f0
    #   busPath: 0000:02:00.0
    #   driver: tg3
    #   vendor: Broadcom Inc. and subsidiaries
    #   product: NetXtreme BCM5719 Gigabit Ethernet PCIe
    # eno2:
    #   hardwareAddr: aa:bb:cc:dd:ee:f1
    #   busPath: 0000:02:00.1
    #   driver: tg3
    #   vendor: Broadcom Inc. and subsidiaries
    #   product: NetXtreme BCM5719 Gigabit Ethernet PCIe
    # eth0:
    #   hardwareAddr: aa:bb:cc:dd:ee:f2
    #   busPath: 0000:04:00.0
    #   driver: bnx2x
    #   vendor: Broadcom Inc. and subsidiaries
    #   product: NetXtreme II BCM57810 10 Gigabit Ethernet
    # eth1:
    #   hardwareAddr: aa:bb:cc:dd:ee:f3
    #   busPath: 0000:04:00.1
    #   driver: bnx2x
    #   vendor: Broadcom Inc. and subsidiaries
    #   product: NetXtreme II BCM57810 10 Gigabit Ethernet
```

Choose the interfaces you want to bond. Typically these are ports of the same speed
connected to the same switch or switch stack. Note the `busPath` values — you will need them.

## Configure bonding

Edit the generated node configuration file (e.g. `nodes/node1.yaml`) and replace the default
`machine.network.interfaces` section with a bond configuration:

```yaml
machine:
  network:
    interfaces:
      - interface: bond0
        dhcp: false
        bond:
          mode: 802.3ad
          adSelect: bandwidth
          miimon: 100
          updelay: 200
          downdelay: 200
          minLinks: 1
          xmitHashPolicy: encap3+4
          deviceSelectors:
            - busPath: "0000:04:00.0"
            - busPath: "0000:04:00.1"
        addresses:
          - 192.168.100.11/24
        routes:
          - network: 0.0.0.0/0
            gateway: 192.168.100.1
```

### Bond parameters explained

| Parameter | Value | Description |
| --- | --- | --- |
| `mode` | `802.3ad` | LACP — dynamic link aggregation with switch negotiation |
| `adSelect` | `bandwidth` | Selects the active aggregator by highest total bandwidth |
| `miimon` | `100` | Link monitoring interval in milliseconds |
| `updelay` | `200` | Delay (ms) before a recovered link becomes active |
| `downdelay` | `200` | Delay (ms) before a failed link is declared down |
| `minLinks` | `1` | Minimum number of active links to keep the bond up |
| `xmitHashPolicy` | `encap3+4` | Hash by IP and TCP/UDP port for load distribution across links |

### Selecting interfaces

The recommended way to select bond members is by PCI bus path using `deviceSelectors`.
This is more reliable than interface names, which may change across reboots:

```yaml
bond:
  deviceSelectors:
    - busPath: "0000:04:00.0"
    - busPath: "0000:04:00.1"
```

Alternatively, you can select by interface name:

```yaml
bond:
  interfaces:
    - eth0
    - eth1
```

Or by hardware address:

```yaml
bond:
  deviceSelectors:
    - hardwareAddr: "aa:bb:cc:dd:ee:f2"
    - hardwareAddr: "aa:bb:cc:dd:ee:f3"
```

## VLAN on top of bond

You can create VLAN interfaces on top of the bond.
This is useful for separating traffic (e.g. management, storage, tenant networks):

```yaml
machine:
  network:
    interfaces:
      - interface: bond0
        dhcp: false
        bond:
          mode: 802.3ad
          adSelect: bandwidth
          miimon: 100
          updelay: 200
          downdelay: 200
          minLinks: 1
          xmitHashPolicy: encap3+4
          deviceSelectors:
            - busPath: "0000:04:00.0"
            - busPath: "0000:04:00.1"
        addresses:
          - 192.168.100.11/24
        routes:
          - network: 0.0.0.0/0
            gateway: 192.168.100.1
        vlans:
          - vlanId: 100
            addresses:
              - 10.0.0.11/24
```

## Floating IP (VIP) with bonding

For control plane nodes, place the `vip` section on the interface (or VLAN)
that is used for the cluster API endpoint:

```yaml
machine:
  network:
    interfaces:
      - interface: bond0
        dhcp: false
        bond:
          mode: 802.3ad
          adSelect: bandwidth
          miimon: 100
          updelay: 200
          downdelay: 200
          minLinks: 1
          xmitHashPolicy: encap3+4
          deviceSelectors:
            - busPath: "0000:04:00.0"
            - busPath: "0000:04:00.1"
        addresses:
          - 192.168.100.11/24
        routes:
          - network: 0.0.0.0/0
            gateway: 192.168.100.1
        vip:
          ip: 192.168.100.10
```

Make sure the floating IP matches the one configured in `values.yaml`.

## Apply configuration

After editing all node files, apply the configuration as usual:

```bash
talm apply -f nodes/node1.yaml -i
talm apply -f nodes/node2.yaml -i
talm apply -f nodes/node3.yaml -i
```

{{% alert color="info" %}}
The `-i` (`--insecure`) flag is only needed for the first apply, when nodes are in maintenance mode.
For already initialized nodes, omit the flag: `talm apply -f nodes/node1.yaml`.
{{% /alert %}}
