---
title: "Network Architecture"
linkTitle: "Architecture"
description: "Overview of Cozystack cluster network architecture: MetalLB load balancing, Cilium eBPF networking, and tenant isolation with Kube-OVN."
weight: 5
aliases:
  - /docs/v1/reference/applications/architecture
  - /docs/reference/applications/architecture
---

## Overview

Cozystack uses a multi-layered networking stack designed for bare-metal Kubernetes clusters. The architecture combines several components, each responsible for a specific layer of the network:

| Layer | Component | Purpose |
| --- | --- | --- |
| External load balancing | MetalLB | Publishing services to external networks |
| Service load balancing | Cilium eBPF | kube-proxy replacement, in-kernel DNAT |
| Network policies | Cilium eBPF | Tenant isolation and security enforcement |
| Pod networking (CNI) | Kube-OVN | Centralized IPAM, overlay networking |
| VM IP passthrough | [cozy-proxy](https://github.com/cozystack/cozy-proxy/) | Passing through external IPs into virtual machines |
| VM secondary interfaces | [Multus CNI](https://github.com/k8snetworkplumbingwg/multus-cni) | Attaching secondary L2 interfaces to virtual machines |
| Observability | Hubble (optional) | Network traffic visibility (disabled by default) |

```mermaid
flowchart TD
    EXT["External Clients"]
    RTR["Upstream Router / Gateway"]
    MLB["MetalLB<br/>(L2 ARP / BGP)"]
    CIL["Cilium eBPF<br/>(Service Load Balancing + Network Policies)"]
    OVN["Kube-OVN<br/>(Pod Networking + IPAM)"]
    PODS["Pods"]

    EXT --> RTR
    RTR --> MLB
    MLB --> CIL
    CIL --> OVN
    OVN --> PODS
```

## Cluster Network Configuration

| Parameter | Default Value |
| --- | --- |
| Pod CIDR | 10.244.0.0/16 |
| Service CIDR | 10.96.0.0/16 |
| Join CIDR | 100.64.0.0/16 |
| Cluster domain | cozy.local |
| Overlay type | GENEVE |
| CNI | Kube-OVN |
| kube-proxy replacement | Cilium eBPF |

### Networking Stack Variants

Cozystack supports several networking stack variants to accommodate different
cluster types. The variant is selected via `bundles.system.variant` in the
platform configuration.

| Variant | Components | Target Platform |
| --- | --- | --- |
| `kubeovn-cilium` | Kube-OVN + Cilium (default) | Talos Linux |
| `kubeovn-cilium-generic` | Kube-OVN + Cilium | kubeadm, k3s, RKE2 |
| `cilium` | Cilium only | Talos Linux |
| `cilium-generic` | Cilium only | kubeadm, k3s, RKE2 |
| `cilium-kilo` | Cilium + Kilo | Talos Linux |
| `noop` | None (bring your own CNI) | Any |

In Kube-OVN variants, Cilium operates as a chained CNI (`generic-veth` mode):
Kube-OVN handles pod networking and IPAM, while Cilium provides service load
balancing, network policy enforcement, and optional observability via Hubble.

In Cilium-only variants, Cilium serves as both the CNI and the service load
balancer.

{{% alert color="info" %}}
The rest of this document describes the default `kubeovn-cilium` variant.
{{% /alert %}}

### Pod CIDR Allocation (Kube-OVN)

Kube-OVN uses a **shared Pod CIDR** model:

- All pods draw from a single shared IP pool (10.244.0.0/16)
- IP addresses are allocated centrally through Kube-OVN's IPAM
- There is no per-node CIDR splitting (unlike Calico or Flannel)
- Because IPs are not tied to node-specific CIDR blocks, pods can be rescheduled to different nodes while retaining their addresses
- Inter-node pod communication uses GENEVE tunnels (Join CIDR: 100.64.0.0/16)

## External Traffic Ingress with MetalLB

MetalLB is a load balancer implementation for bare-metal Kubernetes clusters. It assigns external IP addresses to Services of type `LoadBalancer`, allowing external traffic to reach the cluster.

```mermaid
flowchart TD
    CLIENT["External Client"]
    RTR["Upstream Router"]

    subgraph CLUSTER["Kubernetes Cluster"]
        S1["Node 1<br/>MetalLB Speaker"]
        S2["Node 2<br/>MetalLB Speaker"]
        S3["Node 3<br/>MetalLB Speaker"]
        CIL["Cilium (eBPF)<br/>Service Load Balancing<br/>DNAT to Pod IP"]
        POD["Target Pod<br/>(Pod CIDR)"]
    end

    CLIENT -->|"Traffic to external IP<br/>(e.g. 10.x.x.20)"| RTR
    RTR -->|"L2 (ARP) or BGP"| S1
    RTR -->|"L2 (ARP) or BGP"| S2
    RTR -->|"L2 (ARP) or BGP"| S3
    S1 --> CIL
    S2 --> CIL
    S3 --> CIL
    CIL --> POD
```

### Layer 2 Mode (ARP)

In L2 mode, MetalLB responds to ARP requests for the Service's external IP. A single node becomes the "leader" for that IP and receives all traffic.

How it works:

1. A MetalLB speaker on one node claims the external IP
2. The speaker responds to ARP requests: "IP X is at MAC aa:bb:cc:dd:ee:ff"
3. All traffic for that IP goes to the leader node
4. Cilium on the node performs DNAT to the actual pod

```mermaid
sequenceDiagram
    participant C as Client
    participant L as Node (MetalLB Leader)
    participant CIL as Cilium (eBPF)
    participant P as Pod

    C->>L: ARP: Who has 10.x.x.20?
    L-->>C: ARP Reply: 10.x.x.20 is at aa:bb:cc:dd:ee:ff
    C->>L: Send traffic to 10.x.x.20
    L->>CIL: Packet enters kernel
    CIL->>P: DNAT → Pod 10.244.x.x:8080
```

{{% alert color="info" %}}
In L2 mode, only one node handles traffic for a given Service IP. Failover occurs if the leader node goes down, but there is no true load balancing across nodes for a single Service.
{{% /alert %}}

### BGP Mode

In BGP mode, MetalLB establishes BGP sessions with upstream routers and announces /32 routes for Service IPs. This enables true ECMP load balancing across nodes.

How it works:

1. MetalLB speakers establish BGP sessions with the upstream router(s)
2. Each speaker announces the Service IP as a /32 route
3. The router has multiple next-hops for the same prefix
4. ECMP distributes traffic across nodes
5. Cilium on the receiving node performs DNAT to the actual pod

```mermaid
sequenceDiagram
    participant S1 as Node 1 (Speaker)
    participant S2 as Node 2 (Speaker)
    participant S3 as Node 3 (Speaker)
    participant R as Upstream Router
    participant CIL as Cilium (eBPF)
    participant P as Pod

    S1->>R: BGP UPDATE: 10.x.x.20/32 via Node 1
    S2->>R: BGP UPDATE: 10.x.x.20/32 via Node 2
    S3->>R: BGP UPDATE: 10.x.x.20/32 via Node 3
    Note over R: ECMP: 3 next-hops for 10.x.x.20/32
    R->>S1: Traffic (1/3)
    R->>S2: Traffic (1/3)
    R->>S3: Traffic (1/3)
    S1->>CIL: Packet enters kernel
    CIL->>P: DNAT → Pod
```

### VLAN Integration for External Traffic

External traffic can be delivered to the cluster through additional VLANs (client VLANs, DMZ, public networks, etc.) which are then routed to services via MetalLB and Cilium.

```mermaid
flowchart TD
    EXT["External Traffic"]

    subgraph VLANs["Additional VLANs<br/>(Client, DMZ, Public, etc.)"]
        V1["VLAN A"]
        V2["VLAN B"]
    end

    subgraph LB["MetalLB"]
        L2["L2 Mode → Service → Pod"]
        BGP["BGP Mode → Service → Pod"]
    end

    EXT --> VLANs
    V1 --> L2
    V2 --> BGP
```

## Cilium as kube-proxy Replacement

Cilium replaces kube-proxy by attaching eBPF programs directly in the Linux kernel. This provides more efficient packet processing and advanced capabilities.

### Traditional kube-proxy (iptables) vs Cilium eBPF

```mermaid
flowchart LR
    subgraph IPTABLES["kube-proxy (iptables)"]
        direction LR
        P1["Packet"] --> IPT["iptables<br/>PREROUTING"]
        IPT --> NAT["NAT chains<br/>O(n) rule traversal"]
        NAT --> DNAT1["DNAT to Pod"]
        DNAT1 --> POD1["Pod"]
    end

    subgraph EBPF["Cilium (eBPF)"]
        direction LR
        P2["Packet"] --> BPF["eBPF program<br/>(TC/XDP)"]
        BPF --> MAP["eBPF map lookup<br/>O(1) hash"]
        MAP --> DNAT2["DNAT"]
        DNAT2 --> POD2["Pod"]
    end
```

Key differences:

| Aspect | kube-proxy (iptables) | Cilium (eBPF) |
| --- | --- | --- |
| Lookup complexity | O(n) rule traversal | O(1) hash-based lookup |
| Execution context | Userspace overhead | Native in-kernel |
| Context switches | Required | None |
| Scalability | Degrades with service count | Constant performance |

### eBPF Architecture

```mermaid
flowchart TD
    subgraph KERNEL["Kernel Space"]
        subgraph BPF["eBPF Programs"]
            TC["TC<br/>(ingress/egress)"]
            XDP["XDP<br/>(fastest path)"]
            SOCK["Socket-level<br/>(connect, sendmsg)"]
        end

        subgraph MAPS["eBPF Maps"]
            SVC["Service Tables"]
            EP["Endpoint Maps"]
            POL["Policy Maps"]
        end

        TC --> MAPS
        XDP --> MAPS
        SOCK --> MAPS
    end
```

## Tenant Isolation with Kube-OVN and Cilium

In a multi-tenant Cozystack cluster, all tenants share the same Pod CIDR. This is secure because isolation is enforced by Cilium eBPF policies at the kernel level, not by network segmentation. Tenants cannot communicate even though they share the same IP pool. Kube-OVN allocates IPs from this shared pool centrally, without per-node CIDR splitting.

### CNI Architecture

```mermaid
flowchart TD
    subgraph KO["Kube-OVN"]
        IPAM["Centralized IPAM — Shared pool 10.244.0.0/16"]
        OVN["OVN/OVS Overlay Network (GENEVE)"]
        SUBNET["Subnet management per namespace/tenant"]
    end

    subgraph CIL["Cilium"]
        POLICY["eBPF Network Policies"]
        SVCBAL["Service Load Balancing (kube-proxy replacement)"]
        IDENT["Identity-based Security"]
        HUB["Observability via Hubble"]
    end

    KO --> CIL
```

Kube-OVN provides the primary CNI plugin for pod networking and IPAM. Kube-OVN's
own network policy engine is disabled (`ENABLE_NP: false`), and all policy
enforcement is delegated to Cilium. Cilium operates as a chained CNI component
(`generic-veth` mode) that enforces network policies via eBPF and replaces
kube-proxy for service load balancing.

### Tenant Isolation Model

```mermaid
flowchart TD
    TA["Tenant A — Namespace app-a<br/>Pods: 10.244.0.10, 10.244.0.11"]
    TB["Tenant B — Namespace app-b<br/>Pods: 10.244.1.20, 10.244.1.21"]
    TC["Tenant C — Namespace app-c<br/>Pods: 10.244.2.30, 10.244.2.31"]

    ENGINE{"Cilium eBPF Policy Engine"}

    TA --> ENGINE
    TB --> ENGINE
    TC --> ENGINE

    ENGINE -->|"A ↔ A — ALLOWED"| ALLOW["Same-tenant traffic passes"]
    ENGINE -->|"A ↔ B — DENIED"| DENY["Cross-tenant traffic dropped"]
```

### Identity-based Security

Cilium assigns each endpoint (pod) a **security identity** based on its labels. Policies are enforced using these identities rather than IP addresses.

```mermaid
flowchart LR
    POD["Pod: frontend-abc123<br/>Labels: app=frontend,<br/>tenant=acme, env=prod"]
    AGENT["Cilium Agent<br/>Hash(labels) → Identity: 12345"]
    BPFMAP["eBPF Map<br/>10.244.0.10 → Identity 12345"]

    POD --> AGENT
    AGENT --> BPFMAP
```

### Policy Enforcement in Kernel

When a packet is sent between pods, Cilium enforces policies entirely within kernel space:

```mermaid
flowchart TD
    PKT["Packet: 10.244.0.10 → 10.244.1.20"]
    STEP1["1. Lookup source identity:<br/>10.244.0.10 → ID 12345 (tenant-a)"]
    STEP2["2. Lookup destination identity:<br/>10.244.1.20 → ID 67890 (tenant-b)"]
    STEP3["3. Check policy map:<br/>(12345, 67890, TCP, 80) → DENY"]
    DROP["4. DROP packet"]

    PKT --> STEP1 --> STEP2 --> STEP3 --> DROP
```

All of this happens in kernel space in approximately 100 nanoseconds.

### Why eBPF Enforcement is Secure

| Property | Description |
| --- | --- |
| **Verifier** | eBPF programs are verified before loading — no crashes, no infinite loops |
| **Isolation** | Programs run in a restricted kernel context |
| **No userspace bypass** | All network traffic must pass through eBPF hooks |
| **Atomic updates** | Policy changes are atomic — no race conditions |
| **In-kernel** | No context switches needed, faster than userspace |

### Kernel-level Enforcement

```mermaid
flowchart TD
    subgraph US["User Space"]
        PODA["Pod A<br/>(Tenant A)"]
        PODB["Pod B<br/>(Tenant B)"]
        NOTE["Cannot bypass policy —<br/>traffic MUST go through kernel"]
    end

    subgraph KS["Kernel Space"]
        EBPF["eBPF Programs<br/>• Attached to network interfaces<br/>• Run in privileged kernel context<br/>• Verified by kernel<br/>• Cannot be bypassed by userspace<br/>• Atomic policy updates"]
    end

    US -->|"all traffic"| KS
```

### Default Deny with Namespace Isolation

{{% alert color="warning" %}}
By default, Kubernetes allows all pod-to-pod traffic. Cozystack applies
CiliumNetworkPolicy and CiliumClusterwideNetworkPolicy resources automatically
when a tenant is created. These policies enforce namespace-level isolation and
restrict access to system ports (etcd, kubelet, controllers).
{{% /alert %}}

Cozystack uses hierarchical tenant labels for isolation. Policies match on
`tenant.cozystack.io/*` namespace labels, which allows parent tenants to
include sub-tenant namespaces. Example:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-internal-communication
  namespace: tenant-example
spec:
  endpointSelector: {}
  ingress:
    - fromEndpoints:
        - matchLabels:
            k8s:io.cilium.k8s.namespace.labels.tenant.cozystack.io/tenant-example: ""
  egress:
    - toEndpoints:
        - matchLabels:
            k8s:io.cilium.k8s.namespace.labels.tenant.cozystack.io/tenant-example: ""
    - toEntities:
        - kube-apiserver
        - cluster
```

## Observability with Hubble

Hubble provides network traffic visibility for the Cilium data plane. It is
included in the Cozystack networking stack but **disabled by default** to
minimize resource usage.

When enabled, Hubble provides:

- Real-time flow logs for all pod-to-pod and external traffic
- DNS query visibility
- HTTP/gRPC request-level metrics
- Prometheus metrics integration
- Web UI for traffic visualization

To enable Hubble, set the following in the Cilium configuration:

```yaml
cilium:
  hubble:
    enabled: true
    relay:
      enabled: true
    ui:
      enabled: true
```

See [Enabling Hubble](https://docs.cilium.io/en/stable/observability/hubble/) for full configuration details.

## Traffic Flow Summary

### External Access

```mermaid
flowchart LR
    C["Client"] --> R["Router"]
    R --> M["MetalLB<br/>(L2/BGP)"]
    M --> N["Node"]
    N --> E["Cilium eBPF"]
    E --> P["Pod"]
```

### Tenant Isolation

```mermaid
flowchart LR
    A["Pod A"] --> CHECK{"eBPF<br/>Policy Check"}
    CHECK -->|"Cross-tenant"| DENY["DENY"]
    CHECK -->|"Same tenant"| ALLOW["ALLOW → Pod A'"]
```
