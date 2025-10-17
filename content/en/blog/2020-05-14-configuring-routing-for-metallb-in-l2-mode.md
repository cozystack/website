---
title: "Configuring routing for MetalLB in L2 mode"
slug: configuring-routing-for-metallb-in-l2-mode
date: 2020-05-14
author: "Andrei Kvapil"
description: "In this article I will show you how to configure source-based and policy-based routing for the external network on your cluster."
---

### Configuring routing for MetalLB in L2 mode

![](https://cdn-images-1.medium.com/max/800/0*wI1GLh4MrCzuwiwB.png)

Not so far ago, I was faced with a quite unusual task of configuring routing for MetalLB. All would be nothing, since MetalLB usually does not require any additional configuration from user side, but in our case there is a fairly large cluster with a quite simple network configuration.

In this article I will show you how to configure source-based and policy-based routing for the external network on your cluster.

I will not dwell on installing and configuring MetalLB in detail, as I assume you already have some experience. Let’s understand the essence and configure the routing. So we have four cases:

### Case 1: When you don’t need to configure anything

Let’s think over a simple case.

![](https://cdn-images-1.medium.com/max/800/0*TvAegKAqMruqV-i9.png)

An additional routing configuration is not required when the addresses issued by MetalLB are on the same subnet as the addresses configured on your nodes.

For example, you have a subnet `192.168.1.0/24`, it has a router `192.168.1.1`, and your nodes have the addresses: `192.168.1.10–30`, then you can configure the range `192.168.1.100–120` for MetalLB and be sure that it will work without any additional configuration.

Why so? Because your nodes already have configured routes:

``` graf
# ip route
default via 192.168.1.1 dev eth0 onlink 
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.10
```

Addresses from the same subnet will reuse them without any additional settings.

### Case 2: When you need additional configuration

![](https://cdn-images-1.medium.com/max/800/0*VuxN4tUFDv7hQAFh.png)

You need to configure additional routes whenever your nodes do not have a configured IP address or route for the subnet in which MetalLB issues addresses.

I’ll explain in more detail. Whenever MetalLB issues an address, this can be compared to a simple assignment like:

``` graf
ip addr add 10.9.8.7/32 dev lo
```

Pay attention to:

- **a)** The address is assigned with the prefix `/32`, thus the route for this subnet will not be added automatically (this is just an IP address)
- **b)** The address can be assigned on any interface on the node (for example, loopback). It is worth mentioning here about the features of the Linux network stack. It doesn’t matter what interface you add the address on, the kernel is always processing arp-requests and sending arp-replies to any of them, this behavior is considered correct and, moreover, it is widely used in such a dynamic environment as Kubernetes.

This behavior can be configured, for example, by enabling strict arp:

``` graf
echo 1 > /proc/sys/net/ipv4/conf/all/arp_ignore
echo 2 > /proc/sys/net/ipv4/conf/all/arp_announce
```

In this case, arp-replies will be sent only if the interface explicitly contains a specific IP address. This setting is required if you plan to use MetalLB and your kube-proxy works in IPVS mode.

Nevertheless, MetalLB does not use the kernel to process arp requests, but does it on its own in user-space, so this option will not affect the operation of MetalLB.

Let’s get back to our task. If the route for the issued addresses does not exist on your nodes, add it in advance to all your nodes:

``` graf
ip route add 10.9.8.0/24 dev eth1
```

### Case 3: When you need source-based routing

You need to configure source-based routing when you receive packets through a separate gateway, not the one which is configured by default, respectively, response packets must go through the same gateway.

For example, you have the same subnet `192.168.1.0/24` allocated for your nodes, but you want to issue external addresses using MetalLB. Suppose you have several addresses from the `1.2.3.0/24` subnet located in VLAN 100, and you want to access Kubernetes services from outside using them.

![](https://cdn-images-1.medium.com/max/800/0*yQPI8HI4Q4nmvjRO.png)

When accessing `1.2.3.4`, you will make requests from a different subnet outside of `1.2.3.0/24` and wait for a response. The node that is currently containing address `1.2.3.4` assigned by MetalLB, will receive a packets from the router `1.2.3.1`, but the answers for them must go along the same route, through `1.2.3.1`.

Since our node already has a configured default gateway `192.168.1.1`, by default these response packets will go through it, but not through `1.2.3.1`, from which we received the original packet.

So how to cope with this situation?

In this case, you need to prepare all your nodes in such a way to be ready to serve external addresses without additional configuration. That is, for the above example, you need to create a VLAN interface in advance on the node:

``` graf
ip link add link eth0 name eth0.100 type vlan id 100
ip link set eth0.100 up
```

And then add the routes:

``` graf
ip route add 1.2.3.0/24 dev eth0.100 table 100
ip route add default via 1.2.3.1 table 100
```

Pay attention that we add the routes to the separate routing table `100`, it will contain only two routes necessary to send a response packet from via `eth0.100` interface and `1.2.3.1` gateway.

Now we need to add a simple rule:

``` graf
ip rule add from 1.2.3.0/24 lookup 100
```

which explicitly says: if the source address of the packet is in `1.2.3.0/24`, then use the routing table `100`. We have already added the route that will send it through `1.2.3.1` gateway.

### Case 4: When you need policy-based routing

The network topology is the same as in the previous example, but let’s say you also want to be able to access the external addresses of the `1.2.3.0/24` range from inside your pods:

![](https://cdn-images-1.medium.com/max/800/0*2Wvn3XyfAEuQkd8y.png)

The peculiarity is that when accessing any address in `1.2.3.0/24`, the response packet coming to the node and having the source address in the range `1.2.3.0/24` will be obediently sent via `eth0.100`, but we want let Kubernetes to redirect it back to our first pod, which is generated the original request.

It wasn’t easy to solve this problem, but it became possible thanks to policy-based routing.

Let’s begin with the same, as in the previous case, create an additional routing table and add required routes to it:

``` graf
ip route add 1.2.3.0/24 dev eth0.100 table 100
ip route add default via 1.2.3.1 table 100
```

**Method proposed by** [**George Shuklin**](https://medium.com/u/d67b2f5867f9)

After the publishing this article, I was offered a simpler and more elegant method to solve this problem, to do this you just need to add two rules:

``` graf
ip rule add from 1.2.3.0/24 lookup 100
ip rule add from 1.2.3.0/24 to 10.112.0.0/12 lookup main
```

Where:

- `1.2.3.0/24` — is external network
- `10.112.0.0/12` — is your podNetwork

The second rule must be added after the first one in order to get the highest priority.

**Method with connection marking**

For a better understanding, I’ll provide a netfilter block diagram here:

![](https://cdn-images-1.medium.com/max/800/0*UAr5xjHUxma-BNs2.jpg)

Now add few iptables rules:

``` graf
iptables -t mangle -A PREROUTING -j CONNMARK --restore-mark
iptables -t mangle -A PREROUTING -m mark ! --mark 0 -j RETURN
iptables -t mangle -A PREROUTING -i bond0.100 -j MARK --set-mark 0x100
iptables -t mangle -A POSTROUTING -j CONNMARK --save-mark
```

These rules will mark incoming connections to the `eth0.100` interface, by adding the `0x100` tag to all packets in it, the response packet within the same connection will also be marked with the same tag.

Now we can add a routing rule:

``` graf
ip rule add from 1.2.3.0/24 fwmark 0x100 lookup 100
```

That is, all packets with the source address `1.2.3.0/24` and the tag `0x100` should be routed using table `100`.

Thus, other packets from the other interfaces will not satisfy this rule, which allows them to be routed using standard Kubernetes mechanisms.

There is one more thing in Linux, it is called reverse path filter, which s̶p̶o̶i̶l̶s̶ ̶t̶h̶e̶ ̶w̶h̶o̶l̶e̶ ̶r̶a̶s̶p̶b̶e̶r̶r̶y performs a simple check: for all incoming packets, it changes the source address with the destination one and checks if the packet can go through the same interface on which it was received, if not, then it will be dropped by kernel.

The problem is that in our case it will not work correctly, but we can disable it:

``` graf
echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter
echo 0 > /proc/sys/net/ipv4/conf/eth0.100/rp_filter
```

Note that the first command controls the global behavior of rp_filter, It must be disabled, otherwise the second command will not have any effect. However, other interfaces will remain with rp_filter enabled.

In order to not limit the filter completely, we can use the rp_filter implementation for netfilter. Using rpfilter as the iptables module, you can configure fairly flexible rules, for example:

``` graf
iptables -t raw -A PREROUTING -i eth0.100 -d 1.2.3.0/24 -j RETURN
iptables -t raw -A PREROUTING -i eth0.100 -m rpfilter --invert -j DROP
```

will enable rp_filter on `eth0.100` interface for all addresses except `1.2.3.0/24.`