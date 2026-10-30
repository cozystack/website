---
title: "Running Tenant Kubernetes Workers on Proxmox VE"
linkTitle: "Proxmox VE Substrate"
description: "Run the worker nodes of managed Kubernetes clusters on an external Proxmox VE cluster instead of KubeVirt, using the Cluster API Proxmox provider, the Proxmox cloud-controller-manager and the Proxmox CSI driver."
weight: 70
---

{{< note >}}
The Proxmox VE substrate is **opt-in and experimental** as of Cozystack v1.7.
It is shipped in the platform, tested by its maintainer on Proxmox VE 9.2, and
not yet covered by the project's release gate. Track the decision on support
tier in [cozystack/cozystack#3481](https://github.com/cozystack/cozystack/issues/3481).
{{< /note >}}

## What it is

By default a managed (tenant) Kubernetes cluster in Cozystack has its control
plane run by Kamaji in the management cluster and its worker nodes run as
KubeVirt virtual machines inside the same cluster.

With `substrate: proxmox` the control plane stays exactly where it is, and the
**workers are cloned as VMs on an external Proxmox VE cluster** through the
Cluster API provider for Proxmox (capmox). No nested virtualization, no
KubeVirt on the worker path.

```
Management cluster (Cozystack)                 Proxmox VE cluster
┌──────────────────────────────────┐           ┌─────────────────────────┐
│ Kamaji control plane (tenant A)  │◄── join ──│ worker VM  (pool: a)    │
│ capmox + in-cluster IPAM         │── clone ─►│ worker VM  (pool: a)    │
│ proxmox-ccm   (tenant ns)        │── API ───►│ worker VM  (pool: b)    │
│ proxmox-csi controller (tenant ns)│── API ──►│ Talos VM template       │
└──────────────────────────────────┘           └─────────────────────────┘
```

| Component | Where it runs | What it does |
|---|---|---|
| capmox (`ProxmoxCluster`, `ProxmoxMachineTemplate`) | management cluster, `cozy-cluster-api` | clones worker VMs from a Talos template, assigns static IPs from an in-cluster IPAM pool |
| Proxmox cloud-controller-manager | management cluster, tenant namespace | sets `providerID`, region/zone labels, clears the `uninitialized` taint on tenant Nodes over the tenant's admin kubeconfig |
| Proxmox CSI controller | management cluster, tenant namespace | creates and attaches Proxmox disks for tenant PersistentVolumes |
| Proxmox CSI node plugin | tenant cluster | mounts the disks; carries no hypervisor credential |

The hypervisor token never enters the tenant cluster.

## Support matrix

| | Verified | Notes |
|---|---|---|
| Cozystack | v1.7.0-rc.1 and `main` | the substrate is not in v1.6 |
| Proxmox VE | 9.2.x | 8.x untested; the API calls used exist since 8.x |
| capmox | v0.7.7 (shipped) | |
| Talos | the version in `kubernetes-nodes` `talos.version` | template must match it |
| Storage for workers | ZFS pool (linked clones verified) | any storage that supports clones should work; LVM-thin untested |
| Storage for PVs | any Proxmox storage with `images` content | one storage per tenant recommended, see *Isolation* |
| Networking | VM NIC on a Proxmox bridge, optional VLAN tag | workers must reach the tenant apiserver's LoadBalancer IP |

## Prerequisites

On the **Proxmox VE** side:

- an API endpoint `https://<pve-host>:8006` reachable from the management cluster;
- a bridge the workers attach to, with L3 reachability to the management
  cluster's LoadBalancer range (the tenant apiserver is published as a
  `LoadBalancer` Service on this substrate);
- a range of free static IPv4 addresses on that L2 for the workers, not
  overlapping any DHCP range;
- a storage the Talos template lives on (workers are linked clones of it by default);
- reachable DNS resolvers for the workers (they cannot use the management
  cluster's CoreDNS).

On the **Cozystack** side:

- a working management cluster with the `iaas` bundle;
- a MetalLB / LoadBalancer pool, since each tenant apiserver needs one address.

## 1. Enable the packages

Add the Proxmox infrastructure provider to the platform's enabled packages.
The in-cluster IPAM provider is pulled in as its dependency.

```yaml
# spec.components.platform.values of the cozystack.cozystack-platform Package
bundles:
  enabledPackages:
    - cozystack.capi-provider-infra-proxmox
```

Before the provider is deployed, create the Secret it authenticates with.
capi-operator fetches it first; while it is missing nothing is installed and
the `InfrastructureProvider` reports the fetch error.

```bash
kubectl -n cozy-cluster-api create secret generic capmox-config \
  --from-literal=PROXMOX_URL='https://pve.example.com:8006' \
  --from-literal=PROXMOX_TOKEN='capmox@pve!cozystack' \
  --from-literal=PROXMOX_SECRET='<token secret>'
```

Three things that are easy to get wrong:

- `PROXMOX_URL` is the bare `https://host:8006`; capmox appends `/api2/json` itself.
- `PROXMOX_TOKEN` is the full id `user@realm!tokenid`, not the token id alone.
- a rotated token is picked up only after a restart of the capmox manager pod.

Check:

```bash
kubectl -n cozy-cluster-api get infrastructureproviders,ipamproviders
kubectl -n cozy-cluster-api get deploy | grep -E 'capmox|ipam'
```

## 2. Prepare Proxmox: user, tokens, pool

Create a user and tokens for the platform. Use **privilege-separated tokens**
and grant the privileges to the user as well: Proxmox caps a token at its
user's permissions.

For capmox itself, follow the provider's own
[usage guide](https://github.com/ionos-cloud/cluster-api-provider-proxmox/blob/main/docs/Usage.md):

```bash
pveum user add capmox@pve
pveum aclmod / -user capmox@pve -role PVEVMAdmin
pveum user token add capmox@pve cozystack -privsep 0
```

`PVEVMAdmin` on `/` is what the provider documents; a narrower set is
described in its advanced-setup docs. This token is platform-wide: capmox
clones the workers of every tenant with it (see *Isolation*).

For each **tenant** create a resource pool and a dedicated storage, and grant
the tenant's CCM and CSI tokens their privileges on those paths only:

| Component | Privileges | Path |
|---|---|---|
| CSI controller | `VM.Audit`, `VM.Config.Disk` | `/pool/<tenant-pool>` |
| CSI controller | `Datastore.Allocate`, `Datastore.AllocateSpace`, `Datastore.Audit` | `/storage/<tenant-storage>` |
| CCM | `VM.Audit`, `VM.GuestAgent.Audit` | `/pool/<tenant-pool>` |
| CCM | `Sys.Audit` | `/` |

```bash
pveum pool add tenant-a
pveum user add tenant-a@pve
pveum user token add tenant-a@pve csi --privsep 1
pveum user token add tenant-a@pve ccm --privsep 1
pveum role add CozyCSI -privs "VM.Audit VM.Config.Disk"
pveum role add CozyCSIStorage -privs "Datastore.Allocate Datastore.AllocateSpace Datastore.Audit"
pveum role add CozyCCM -privs "VM.Audit VM.GuestAgent.Audit"
# the user ...
pveum acl modify /pool/tenant-a          --users tenant-a@pve --roles CozyCSI,CozyCCM
pveum acl modify /storage/tenant-a-disks --users tenant-a@pve --roles CozyCSIStorage
pveum acl modify /                       --users tenant-a@pve --roles PVEAuditor
# ... and each token, which Proxmox caps at the user's permissions
pveum acl modify /pool/tenant-a          --tokens 'tenant-a@pve!csi' --roles CozyCSI
pveum acl modify /storage/tenant-a-disks --tokens 'tenant-a@pve!csi' --roles CozyCSIStorage
pveum acl modify /pool/tenant-a          --tokens 'tenant-a@pve!ccm' --roles CozyCCM
pveum acl modify /                       --tokens 'tenant-a@pve!ccm' --roles PVEAuditor
pveum user token permissions tenant-a@pve csi --path /pool/tenant-a
```

Why a pool: capmox adds every worker VM it clones to `proxmox.pool`,
replacements included, so an ACL on `/pool/<name>` follows the tenant's VMs
without being granted again.

## 3. Build the Talos VM template

Workers are cloned from a Talos VM template that already exists on the
hypervisor. Build it with the script shipped in the repository; it reads
`talos.version` and `talos.schematicID` from the `kubernetes-nodes` chart so
the template matches what the chart will render into the machine config.

```bash
# prints the program it would run, for review
hack/proxmox-talos-template.sh print 9000 local-zfs

# creates the template over ssh on the PVE node
COZY_PVE_SSH=root@pve.example.com hack/proxmox-talos-template.sh create 9000 local-zfs
```

The script prints the tags to put into `proxmox.templateTags`. Do **not**
build the template from the platform's `nocloud-amd64.raw.xz`: that is the
bare-metal node image, and its `zfs` extension keeps a VM from completing its
boot, rebooting it every ~70 minutes.

## 4. Create the tenant cluster

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Kubernetes
metadata:
  name: px
  namespace: tenant-a
spec:
  substrate: proxmox
  proxmox:
    allowedNodes: ["pve1", "pve2"]        # empty = every node
    dnsServers: ["10.0.0.1"]
    insecure: true                        # stock PVE serves a self-signed cert
    ipv4Config:
      addresses: ["10.0.0.120-10.0.0.170"]
      gateway: "10.0.0.1"
      prefix: 24
    ccm:
      credentialsSecretName: proxmox-ccm   # keys: url, token_id, token_secret, region
    csi:
      enabled: true
      credentialsSecretName: proxmox-csi
      storageClasses:
        - name: proxmox
          storage: tenant-a-disks
          fstype: ext4
          reclaimPolicy: Delete
  # ... the rest of the usual Kubernetes spec
```

The two credential Secrets live in the **tenant's namespace of the management
cluster** with the keys `url`, `token_id`, `token_secret`, `region`
(`region` is the Proxmox cluster's name; the controllers put it on the
Nodes as `topology.kubernetes.io/region`. Note the URL here carries
`/api2/json`, unlike capmox's `PROXMOX_URL`):

```bash
kubectl -n tenant-a create secret generic proxmox-csi \
  --from-literal=url='https://pve.example.com:8006/api2/json' \
  --from-literal=token_id='tenant-a@pve!csi' \
  --from-literal=token_secret='<secret>' \
  --from-literal=region='pve'
```

`substrate` is immutable: switching an existing cluster is refused. Create a
new one.

## 5. Add a worker pool

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: KubernetesNodes
metadata:
  name: px-md0
  namespace: tenant-a
spec:
  cluster: px
  substrate: proxmox
  minReplicas: 2
  maxReplicas: 2
  resources:
    cpu: 4
    memory: 8Gi
  proxmox:
    templateTags: ["cozystack", "talos", "talos-v1.13.6", "schematic-ce4c9805"]
    full: false                 # linked clone (default)
    network:
      bridge: vmbr0
      vlan: 60                  # optional
    pool: tenant-a
    dnsServers: ["10.0.0.1"]
```

`templateTags` must be **equal** to the template's tag set, not a subset: a
missing tag yields `found 0 VM templates with tags ...` even though the tags
are plainly present on the template.

`resources.cpu` / `memory` are converted to capmox's `numCores` / `memoryMiB`
(rounded up).

## 6. Verify

```bash
# management cluster
kubectl -n tenant-a get cluster,proxmoxcluster,machinedeployment,machine
kubectl -n tenant-a get proxmoxmachines -o custom-columns='NAME:.metadata.name,VMID:.spec.virtualMachineID,NODE:.status.proxmoxNode,IP:.status.ipAddresses.net0.ipv4,STATE:.status.vmStatus'
kubectl -n tenant-a get inclusterippools,ipaddresses.ipam.cluster.x-k8s.io
kubectl -n tenant-a get deploy kubernetes-px-pccm kubernetes-px-pcsi-controller

# tenant cluster
kubectl --kubeconfig <tenant kubeconfig> get nodes -o wide
kubectl --kubeconfig <tenant kubeconfig> get nodes -o custom-columns='NODE:.metadata.name,PROVIDER-ID:.spec.providerID,TAINTS:.spec.taints[*].key'
kubectl --kubeconfig <tenant kubeconfig> -n csi-proxmox get pods
```

A healthy node has the same `providerID` as its CAPI `Machine`
(`proxmox://<SMBIOS UUID>`; the CCM runs in its `capmox` mode for that), the
`topology.kubernetes.io/region|zone` labels, and no
`node.cloudprovider.kubernetes.io/uninitialized` taint.

What is covered by the integration and was verified live on PVE 9.2:
PVC create → attach → online resize → delete; Cluster Autoscaler scale-up and
scale-down through the pool; rolling replacement of a worker;
MachineHealthCheck.

## Isolation: what the design gives and what it does not

- The hypervisor token is composed into the CCM and CSI controllers in the
  management cluster; nothing copies it into the tenant cluster.
- The tenant is cluster-admin of its own cluster, and the controllers act on
  what its objects say: the CSI controller attaches the disk a PV names to the
  VM a Node names. **Scope comes from the Proxmox ACL**, not from the
  controllers: one pool and one storage per tenant.
- A storage shared between tenants cannot be scoped: `Datastore.Allocate` on
  it reaches every volume on it.
- capmox itself (VM creation) currently uses one platform-wide token for all
  tenants; per-tenant `credentialsRef` on `ProxmoxCluster` is being worked on
  upstream.

## Limitations (v1.7)

- Opt-in, experimental; no release gate yet (an e2e lane exists upstream, but its nightly run is opt-in and currently skipped).
- Workers only. Cozystack's `vm-disk` / `vm-instance` applications still run on KubeVirt; a Proxmox substrate for them is in design.
- Tenant `Kubernetes` kinds are published as part of the KubeVirt variant, so a management cluster still needs the KubeVirt packages installed even if every pool runs on Proxmox.
- No DHCP: capmox assigns static addresses from `ipv4Config` only.
- Linked clones keep the template's base snapshot referenced; rotate templates by creating a new VMID with new tags and rolling the pool.
- No live migration awareness: the CCM reports a VM it cannot see as gone and deletes the Node.
- Cozystack's Terraform provider does not model `substrate`/`proxmox.*` yet; `terraform apply` on such a cluster overwrites them.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `InfrastructureProvider` not installing, fetch error | `capmox-config` Secret missing or in the wrong namespace | create it in `cozy-cluster-api` |
| every API call returns 501 | `PROXMOX_URL` already contains `/api2/json` | use bare `https://host:8006` |
| `found 0 VM templates with tags ...` | `templateTags` ≠ the template's tag set | list every tag, exactly |
| Machine `VMProvisioned=True`, node never joins, no CSR | workers cannot reach the tenant apiserver LoadBalancer IP, or no reachable `dnsServers` | fix L3 / DNS |
| Nodes `Ready` but keep `uninitialized` taint, pool `ScalingUp` forever | CCM not running or crash-looping | `kubectl -n <tenant ns> logs deploy/kubernetes-<cluster>-pccm` |
| CSI node plugin `CrashLoopBackOff`, `Failed to get region or zone` | CCM has not labelled the node yet | wait for the CCM |
| VM reboots every ~70 min, never joins | template built from the bare-metal `nocloud` image | rebuild with `hack/proxmox-talos-template.sh` |
| `TalosConfigTemplate.Spec is immutable` | apiserver address changed on an existing cluster | delete the template; the reconcile Job recreates it |
| capmox stuck at `Waiting for Cluster Controller to set OwnerRef` | `cluster.x-k8s.io/managed-by` annotation on the `ProxmoxCluster` | not expected from the chart; report it |

## See also

- [Managed Kubernetes]({{% ref "/docs/v1.7/kubernetes" %}}) — the application this page extends
- Cluster API provider for Proxmox: https://github.com/ionos-cloud/cluster-api-provider-proxmox
- Proxmox CCM / CSI: https://github.com/sergelogvinov/proxmox-cloud-controller-manager, https://github.com/sergelogvinov/proxmox-csi-plugin
- Support-tier proposal: https://github.com/cozystack/community/pull/98
