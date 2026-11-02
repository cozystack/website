---
title: "Upgrading from v1.6 to v1.7"
linkTitle: "Upgrading to v1.7"
description: "What changes when a Cozystack v1.6 cluster is upgraded to v1.7, and what has to be done before and after the upgrade."
weight: 11
---

Cozystack v1.7 changes the behaviour of running clusters in several places. This page lists those changes for a cluster that runs v1.6.x, and the action each one needs. The upgrade itself follows the usual procedure in [Upgrading Cozystack]({{% ref "/docs/v1.7/operations/cluster/upgrade" %}}). Read this page first: several actions have to be taken before the upgrade starts, because once it runs it is too late to act on them.

{{% alert title="Platform migrations do not run on the default variant" color="warning" %}}

On every other variant the v1.7 platform release runs platform migrations 54 to 60 as a pre-upgrade hook, before any package moves to its new chart. The [`default`]({{% ref "/docs/v1.7/operations/configuration/variants#default" %}}) variant runs none, so on such a cluster the steps those migrations would take for SeaweedFS, VM volume hotplug, HTTPCache and FoundationDB are yours, before the upgrade.

{{% /alert %}}

## Before you upgrade

- Every node: add `drbd_transport_tcp` to the Talos kernel modules before the node moves to Talos v1.14. See [Talos v1.14](#talos-v114).
- Every node: make sure it has free disk space. On a test cluster, nodes reported `DiskPressure` during the platform upgrade and the kubelet evicted pods.
- Right after the upgrade: read the log of the migration hook. On a test cluster it could no longer be read about 20 minutes after the run. See [Platform migrations](#platform-migrations).
- `isp-full` and `isp-full-generic`: check that `networking.podCIDR` has a prefix of /20 or shorter. See [Cilium address block](#cilium-address-block).
- A `cozystack.networking` variant set by hand: list `cozystack.networking` in `bundles.disabledPackages`. See [Networking variant switch](#networking-variant-switch).
- Tenant Kubernetes clusters: remove `controlPlane.apiServer.extraArgs` entries that name a flag the tenant control plane sets itself. See [Kamaji and tenant control planes](#kamaji-and-tenant-control-planes).
- Tenant Kubernetes clusters: plan for every tenant kube-apiserver to roll at least twice. See [Kamaji and tenant control planes](#kamaji-and-tenant-control-planes).
- Tenant Kubernetes clusters: plan for the Talos workers of every pool to be replaced once. See [Worker pools become KubernetesNodes resources](#worker-pools-become-kubernetesnodes-resources).
- Multus: decide whether the reference CNI plugins may be written to `/opt/cni/bin` on every node. See [Multus stages CNI plugins](#multus-stages-cni-plugins).
- FoundationDB: upgrade every cluster that runs 7.1.x to 7.3, and check the running patch of every cluster. On the `default` variant, also set `version` on every release. See [FoundationDB](#foundationdb).
- Kubernetes, KubernetesNodes and OpenSearch: check releases that set `images.*`, OpenSearch releases that run a custom image, and OpenSearch releases that store `version: null`. See [Image overrides](#image-overrides).
- PostgreSQL with `external: true`: find clients that disable TLS. See [PostgreSQL](#postgresql).
- PostgreSQL: plan for every instance to restart at least once, and find clients that log in with a role no longer listed in `users`. See [PostgreSQL](#postgresql) and [PostgreSQL and MariaDB passwords](#postgresql-and-mariadb-passwords).
- OpenSearch with `external: true` or Dashboards: see [OpenSearch](#opensearch).
- Gateway API: check the certificate served on `api.<apex>` and the hostnames of routes in tenant namespaces. See [Gateway API](#gateway-api).
- `VMInstance` VMs: move every volume hot-plugged only on the running VM into `spec.disks`. See [Declarative volume hotplug](#declarative-volume-hotplug).
- VM disks: let running imports finish. See [VM disks](#vm-disks).
- VM instances: fix `resources` values that cannot size a VM. See [Smaller changes](#smaller-changes).
- Kafka: plan a maintenance window for every instance. See [Kafka moves to KRaft](#kafka-moves-to-kraft).
- `default` variant only: pin the SeaweedFS volume size limit, look for volumes hotplugged on a VM instance only, and freeze HTTPCache or remove it from the platform. See [SeaweedFS volume size limit](#seaweedfs-volume-size-limit), [Declarative volume hotplug](#declarative-volume-hotplug) and [HTTPCache](#httpcache).
- While the platform upgrade runs, do not edit `Kubernetes` resources. See [Worker pools become KubernetesNodes resources](#worker-pools-become-kubernetesnodes-resources).

## Platform migrations

The platform migration version moves from 54, where v1.6 left it, to 61. On every variant except `default`, the migrations below run once each, in order, as a pre-upgrade hook of the platform release:

| Migration | What it does |
| --- | --- |
| 54 | Labels every existing `RedisFailover` for the new Redis operator (`redis-failover.freshworks.com/operator-group: cozystack`) and sets `redis:6.2.6-alpine` wherever its Redis or Sentinel image is empty, so the new operator does not move the engine to another version when it adopts the instance. |
| 55 | Detaches the HelmReleases of the removed FluxCD addon of tenant Kubernetes clusters without uninstalling Flux inside the tenant cluster. See [FluxCD addon removed](#fluxcd-addon-removed). |
| 56 | Moves the worker pools of every tenant Kubernetes cluster into one `kubernetes-nodes-<cluster>-<pool>` release per pool. See [Worker pools become KubernetesNodes resources](#worker-pools-become-kubernetesnodes-resources). |
| 57 | Writes `master.volumeSizeLimitMB: 1000` into every SeaweedFS instance that has no valid value of its own. See [SeaweedFS volume size limit](#seaweedfs-volume-size-limit). |
| 58 | Freezes HTTPCache on the packages artifact the cluster already runs, or removes it from the platform where no instance exists. See [HTTPCache](#httpcache). |
| 59 | Copies volumes that are hotplugged on a running VM instance but missing from its `VirtualMachine` spec into that spec. See [Declarative volume hotplug](#declarative-volume-hotplug). |
| 60 | Carries the release line of every FoundationDB release's `cluster.version` over to the new `version` value, and records the FoundationDB, OpenSearch, Kubernetes and KubernetesNodes releases that need attention in the `cozystack.io/migration-60-needs-attention` annotation of the `cozystack-version` ConfigMap. See [FoundationDB](#foundationdb) and [Image overrides](#image-overrides). |

After the upgrade, the `cozystack-version` ConfigMap shows the version the migrations reached:

```bash
kubectl -n cozy-system get configmap cozystack-version -o jsonpath='{.data.version}{"\n"}'
```

A migration that fails stops the platform upgrade and is retried on the next attempt; one that succeeded does not run again.

The migrations write what they did, warnings included, to the log of the `cozystack-migration-hook` Job. Read it as soon as the migrations finish. The chart does not delete the Job when it finishes, but on a test cluster the container log of its pod was gone about 20 minutes after the run, while nodes reported disk pressure. The cause is not established.

```bash
kubectl -n cozy-system logs job/cozystack-migration-hook
```

If the log can no longer be read, migration 60's records are still in the annotation it writes on the `cozystack-version` ConfigMap, which exists only when the migration recorded at least one release:

```bash
kubectl -n cozy-system get configmap cozystack-version -o jsonpath='{.metadata.annotations.cozystack\.io/migration-60-needs-attention}{"\n"}'
```

## Talos v1.14

Cozystack v1.7.0 ships Talos v1.14.2, with DRBD 9.3.4 and ZFS 2.4.4; v1.6 shipped Talos v1.13.6. The platform upgrade does not touch the Talos version of the nodes: each node moves when you upgrade it, and the steps below belong to that point.

**Add `drbd_transport_tcp` before a node moves to Talos v1.14.** Talos v1.14 kernels no longer load kernel modules on demand, so DRBD cannot load its TCP transport when it connects to a peer, and every DRBD resource on the node stays in `Connecting`. List the module explicitly, next to `drbd`, in the node's machine config:

```yaml
machine:
  kernel:
    modules:
      - name: drbd
        parameters:
          - usermode_helper=disabled
      - name: drbd_transport_tcp
```

The module ships in the DRBD extension of Talos v1.13 as well, so the line can be applied before the node is upgraded. The `cozystack` preset of talm v0.35.0 and earlier does not list it; with such a preset add it through `extraKernelModules` in the project's `values.yaml`, and apply the configuration before upgrading the node:

```yaml
extraKernelModules:
  - name: drbd_transport_tcp
```

Talos v1.14 accepts a direct upgrade from v1.12.0 or later, and supports Kubernetes 1.32 to 1.37. See [talm]({{% ref "/docs/v1.7/install/kubernetes/talm" %}}) for how nodes are configured and upgraded.

**A drain can stop on a PodDisruptionBudget.** CloudNativePG covers the primary of each PostgreSQL instance with a PodDisruptionBudget, `<release>-primary`, that allows no disruption. On a test cluster, `kubectl drain` evicted most pods of the node within the first minute, but every eviction of the primary of an instance with a single replica, or of one whose second replica was pending, was refused until the drain ran into its timeout and exited with the node cordoned. Before draining a node, list the budgets that allow no disruption, and plan for the downtime of what they cover:

```bash
kubectl get poddisruptionbudgets -A -o json \
  | jq -r '.items[] | select(.status.disruptionsAllowed == 0) | "\(.metadata.namespace)/\(.metadata.name)"'
```

**etcd metrics move to port 2383.** Talos v1.14 serves etcd's HTTP endpoints, such as `/metrics` and `/health`, on a separate listener on port 2383, and port 2379 serves gRPC only. On the variants where Cozystack manages Cilium, the host network policy `restrict-system-components` denies port 2383 from outside the cluster, as it does 2379 and 2380. Cozystack's own monitoring reads neither port. A scraper of your own inside the cluster that reads etcd's HTTP endpoints from port 2379 has to move to 2383.

Tenant Kubernetes clusters are not part of this: their workers keep the Talos version their `KubernetesNodes` pool sets.

## Tenant Kubernetes clusters

### Worker pools become KubernetesNodes resources

The `Kubernetes` resource no longer describes worker nodes. `spec.nodeGroups` and `spec.nodeHealthCheck` are removed, and each worker pool is a `KubernetesNodes` resource (`apps.cozystack.io/v1alpha1`) in the same namespace, named `<cluster>-<pool>`, whose `spec.cluster` names the parent cluster. Pool size and machine settings, the health-check settings (`maxUnhealthy`, `nodeStartupTimeout`, `readyUnknownTimeout`, `readyFalseTimeout`) and the autoscaler budget `maxNodeProvisionTime` are set per pool. `cluster` and `storageClass` are meant to stay fixed once the pool exists, but the API accepts an edit of either. The pool's release refuses to render a changed `cluster` until it is restored, and a changed `storageClass` rolls the pool's workers onto the new class. For now only the dashboard refuses a `storageClass` edit.

Platform migration 56 moves the pools of existing clusters. For every pool in `spec.nodeGroups` it creates a `kubernetes-nodes-<cluster>-<pool>` release, which appears as a `KubernetesNodes` resource, and hands the pool's existing worker objects over to it. A cluster that had no `nodeGroups` gets a pool named `md0` with the defaults the old chart used for it: `u1.medium` workers, 0 to 10 replicas, a 20Gi disk and the `ingress-nginx` role.

The upgrade then rolls the Talos workers of every pool once. This is expected. v1.7 names each pool's `TalosConfigTemplate` after a hash of its content, `kubernetes-<cluster>-<pool>-<hash>`, instead of the fixed `kubernetes-<cluster>-<pool>`, so the pool's `MachineDeployment` refers to a new template and Cluster API replaces the workers under the pool's rolling-update strategy: up to `maxReplicas` new machines at once, and at most one old machine unavailable at a time. No action is needed on the pools; plan the upgrade window for the workers of every tenant cluster to be replaced. Data on a worker's own system disk, such as local-path volumes, does not survive the replacement, as with any roll of the pool. The same roll brings each pool's machine configuration up to date where the old fixed-name template could not follow a later change, and gives a pool that holds `nvidia.com/*` GPUs the NVIDIA kernel modules that v1.7 declares in its machine configuration: a Talos system extension installs a module but does not load it.

While the platform upgrade runs, do not edit `Kubernetes` resources: a change in that window renders the old chart, and its apply fails until the new chart arrives.

A pool the migration cannot adopt keeps running but is left unmanaged. That happens, among other cases the migration's log names, when `kubernetes-nodes-<cluster>-<pool>` is longer than the 53 characters a Helm release name allows, so `<cluster>-<pool>` must fit in 36 characters, when the pool name holds characters a release name cannot carry, or when the pool's objects belong to another release. The migration pins such a pool's objects with `helm.sh/resource-policy: keep` so nothing deletes them, and records each one in a ConfigMap:

```bash
kubectl -n cozy-system get configmap cozystack-migration-56-unadopted -o yaml
```

The ConfigMap exists only when at least one pool was skipped. Migration 56 does not run again, so such a pool has to be recreated or adopted by hand.

The removed fields stay stored on upgraded `Kubernetes` resources and have no effect. Every write to a resource that still carries one returns a warning such as `spec.nodeGroups is ignored on the Kubernetes resource since Phase 2: worker pools are managed as separate KubernetesNodes resources`. Change a pool through its `KubernetesNodes` resource instead. `talos.registryMirrors` is new in v1.7 and only the `KubernetesNodes` chart reads it, so set it on each pool. The `Kubernetes` resource accepts the same key, but no template of the `kubernetes` chart reads it.

Rolling the platform back to v1.6 after migration 56 is not automatic: the old chart cannot render worker objects that now belong to the per-pool releases.

A `Kubernetes` resource created on v1.7 has a name of at most 32 characters; existing clusters with longer names keep working. A cluster created on v1.7 has no workers until a `KubernetesNodes` pool exists for it. With the ingress-nginx addon in its default `Proxied` mode, at least one pool needs `roles: [ingress-nginx]`, because the Service that publishes the tenant's ingress selects the workers carrying that role:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: KubernetesNodes
metadata:
  name: mycluster-md0
  namespace: tenant-example
spec:
  cluster: mycluster
  roles:
    - ingress-nginx
  minReplicas: 1
  maxReplicas: 3
  instanceType: u1.medium
```

### FluxCD addon removed

The `addons.fluxcd` addon of the `Kubernetes` application is removed. Platform migration 55 detaches its HelmReleases from the management cluster without uninstalling anything, so a tenant cluster that had the addon keeps its Flux running, unmanaged. To remove it, uninstall its two Helm releases from inside the tenant cluster, the instance first and the operator second, using the tenant cluster's kubeconfig:

```bash
helm uninstall fluxcd --namespace cozy-fluxcd
helm uninstall fluxcd-operator --namespace cozy-fluxcd
```

An `addons.fluxcd` key left in a `Kubernetes` resource is accepted and has no effect.

### Kamaji and tenant control planes

Kamaji moves from 26.3.6-edge to 26.9.4-edge. Kamaji now tracks the kube-apiserver arguments of a tenant control plane by a hash of its `extraArgs` and rebuilds the list from scratch whenever the hash differs, so on the first reconcile after the upgrade every tenant control plane rebuilds its arguments and its kube-apiserver rolls once. It also rolls when the tenant's `kubernetes` release moves to the new chart, which changes the image of the talos-csr-signer sidecar, as every Cozystack upgrade does. A tenant with OIDC enabled can roll a third time when the chart's own flags land. Plan the upgrade window for that.

Kamaji now sets a list of kube-apiserver flags itself and drops any `controlPlane.apiServer.extraArgs` entry that names one, and the `Kubernetes` application refuses to render such an entry. A tenant cluster that carries one stops reconciling after the upgrade until the entry is fixed. Two of these flags are moved instead of refused: an `--enable-admission-plugins=<list>` entry goes into the new `controlPlane.apiServer.admissionControllers`, and a `--kubelet-preferred-address-types=<list>` entry into the new `controlPlane.kubelet.preferredAddressTypes`, as long as the field is empty and the entry is a single unquoted `--flag=value` string. List the entries to look at before upgrading:

```bash
kubectl get kuberneteses.apps.cozystack.io --all-namespaces --output json | jq --raw-output '["--advertise-address","--client-ca-file","--enable-admission-plugins","--service-cluster-ip-range","--kubelet-client-certificate","--kubelet-client-key","--kubelet-preferred-address-types","--proxy-client-cert-file","--proxy-client-key-file","--requestheader-allowed-names","--requestheader-client-ca-file","--secure-port","--service-account-key-file","--service-account-signing-key-file","--tls-cert-file","--tls-private-key-file","--etcd-servers","--etcd-cafile","--etcd-certfile","--etcd-keyfile","--etcd-prefix","--etcd-compaction-interval","--egress-selector-config-file"] as $owned | .items[] | .metadata as $m | (.spec.controlPlane.apiServer.extraArgs // [])[] | select((split("=")[0]) as $f | $owned | index($f)) | "\($m.namespace)/\($m.name): \(.)"'
```

Remove every entry it lists, together with its value if the value sits in a separate entry. The exceptions are the two moved flags written as one unquoted `--flag=value` entry next to an empty field, which need no change. Between the Kamaji update and the upgrade of the tenant's `kubernetes` release, though, a tenant with an `--enable-admission-plugins=` entry runs its kube-apiserver with Kamaji's default admission plugins, which do not include NodeRestriction. On a test cluster this lasted about seven minutes.

Do not roll Kamaji back to an earlier build after the upgrade. The older build expects a number where the new one stores the hash, and from then on it never removes a flag you take out of `extraArgs`, on any tenant control plane, until the annotation `kube-apiserver.kamaji.clastix.io/args` is set back to a number by hand.

## Networking

### Cilium address block

On `isp-full` and `isp-full-generic`, Cilium now takes the addresses of its router and of its Gateway API ingress from the last /21 of `networking.podCIDR`, and Kube-OVN no longer hands out addresses from that block. `networking.podCIDR` therefore needs a prefix of /20 or shorter; a narrower one fails the platform render with `networking.podCIDR <cidr> is too small`. The default `10.244.0.0/16` qualifies. Each node takes a /29 of the block, which caps these variants at 256 nodes.

An existing cluster moves to the block in a post-upgrade hook of the Cilium release, the Job `cilium-ipam-migration` in `cozy-cilium`. It excludes the block from the Kube-OVN default subnet, then moves the nodes one at a time, so each Cilium agent restarts twice: once for the configuration change and once in the hook. The hook stops, and the Cilium release upgrade fails, if pods still hold addresses inside the block; its log names them, and once they are recreated the next upgrade attempt continues. A failed Job is kept for its log. A cluster on v1.6.5 already moved to the block in that patch release: the move, and the two restarts it takes, apply only when upgrading from v1.6.4 or earlier.

### Multus stages CNI plugins

On the variants that ship Multus, it now installs the upstream reference CNI plugins into `/opt/cni/bin` on every node: bridge, host-local, static, macvlan, ipvlan, vlan, tuning, portmap, firewall, bandwidth, host-device, ptp, sbr and vrf. They are written every time a Multus pod is recreated and replace files of the same name. On Talos four of them, bridge, firewall, host-local and portmap, are rewritten with the same upstream version Talos carries. On a generic Linux node a plugin of your own under one of those names does not survive.

To decline, set `networking.stageCniPlugins: false` on the `platform` component of the Platform Package before upgrading. Setting it later does not restore files already replaced. The value accepts `true`, `false` and their usual YAML spellings; anything else fails the whole platform render.

### East-west encryption

`networking.encryption.enabled` is a new opt-in that encrypts pod traffic between nodes with Kube-OVN IPsec on `isp-full` and `isp-full-generic`. It is off by default, so the upgrade changes nothing. See the [Platform Package reference]({{% ref "/docs/v1.7/operations/configuration/platform-package" %}}).

### Networking variant switch

The platform render now refuses to change the variant of the live `cozystack.networking` Package, because the operator would then delete every HelmRelease of that Package the new variant does not install: `isp-full` to `isp-hosted` removes Cilium and Kube-OVN, and `isp-full` to `isp-slim` removes Kube-OVN. The error names the value that lets one switch through, `networking.acknowledgeVariantChange` set to the new networking variant on the `platform` component of the Platform Package.

A cluster whose `cozystack.networking` variant was set by hand fails the upgrade until `cozystack.networking` is listed in `bundles.disabledPackages`. Acknowledging the switch does not help there, because the render writes the bundle's variant over the one set by hand.

### Gateway API

These apply where Gateway API resources are in use.

- An `HTTPRoute`, `TLSRoute` or `GRPCRoute` in a `tenant-*` namespace must declare a non-empty `spec.hostnames`. An existing route that relied on inheriting its listener's hostnames keeps serving, but its next update is refused until it names them, a Helm upgrade of the chart that renders it included.
- Under HTTP-01, a hostname a TLS-passthrough listener answers is reserved to that listener and gets no HTTPS listener and no certificate on 443. With `gateway.enabled` on, the publishing tenant therefore passes `api.<apex>`, `vm-exportproxy.<apex>` and `cdi-uploadproxy.<apex>` through after the upgrade, for the names `publishing.exposedServices` lists, and the only certificate on `api.<apex>` is the management kube-apiserver's own serving certificate. It has to carry `api.<apex>` in its SANs before the upgrade. A cluster that came to the Gateway from ingress-nginx already meets this.
- The three platform passthrough listeners are rendered only on the publishing tenant. A child tenant that rendered them before loses them, together with any `TLSRoute` attached to them by hand.
- An existing `TLSRoute` whose hostname no passthrough listener answers stays unattached after the upgrade. Remove it, or declare a `tlsPassthroughListeners` entry for its hostname on the `TenantGateway`.
- The certificates of the shed HTTPS listeners are deleted, but their TLS Secrets stay in the namespace and can be removed by hand.

See [Gateway API]({{% ref "/docs/v1.7/networking/gateway-api" %}}) for the details, including `tlsPassthroughListeners`, the new native-port passthrough form.

## Virtual machines

### Eviction of non-migratable VMs

The cluster-wide KubeVirt eviction strategy changes from `LiveMigrate` to `LiveMigrateIfPossible`. A VM that can live-migrate still migrates when its pod is evicted. A VM that cannot, for example one on a ReadWriteOnce disk or with a GPU or host device passed through, is shut down instead of blocking the drain, and started again according to its `runStrategy`: a VM with `runStrategy: Always` comes back, while one with `RerunOnFailure`, `Manual` or `Once` that shuts down cleanly stays off until it is started. A VM whose disk is bound to the drained node stays down until the node returns. This applies to any eviction through the API, not only a drain.

A running VM instance keeps the strategy it was created with, so a non-migratable VM started before the upgrade still blocks a drain until its VM is restarted. Restart such VMs once after the upgrade if their nodes have to drain. From then on, a KubeVirt upgrade shuts down non-migratable VMs to move them to the new version, ten every minute.

### Declarative volume hotplug

KubeVirt v1.9.0 runs with `DeclarativeHotplugVolumes` instead of the deprecated `HotplugVolumes` feature gate, and the kubevirt-csi driver of tenant Kubernetes clusters no longer hot-plugs volumes through the VM instance. Hotplugged volumes now follow the `VirtualMachine` spec: on its first reconcile, KubeVirt removes every hotplugged volume of a running VM instance that the VM spec does not list.

Platform migration 59 copies such volumes into the VM spec before that happens, so on the workers of tenant Kubernetes clusters they stay attached. This also makes a volume that was added to the VM instance only, without being persisted, permanent: it attaches again after a VM restart, and from then on it can be removed only through the VM.

A `VMInstance` does not keep the copy. Its VM is rendered by its own release, which the same upgrade moves to the new chart, and that release writes the VM's volume list back from `spec.disks`, so KubeVirt unplugs the copied volume from the running VM. To keep such a volume, before upgrading and on every variant, detach it inside the guest, remove it with `virtctl removevolume`, and list the disk in the VMInstance's `spec.disks`, which takes only `VMDisk` names. On v1.6.5 a disk added to `spec.disks` attaches only at the VM's next restart, because nothing restarts the VM for it. These steps follow from the charts and were not run on a live VM.

On the `default` variant this migration does not run. Before upgrading such a cluster, list the affected volumes:

```bash
kubectl get vm,vmi --all-namespaces --output json | jq --raw-output '
  ([.items[] | select(.kind == "VirtualMachine")
    | {key: "\(.metadata.namespace)/\(.metadata.name)", value: [.spec.template.spec.volumes[]?.name]}]
    | from_entries) as $vm
  | .items[] | select(.kind == "VirtualMachineInstance")
  | ([.metadata.ownerReferences[]? | select(.controller == true and .kind == "VirtualMachine" and (.apiVersion | startswith("kubevirt.io/"))) | .name][0]) as $owner
  | "\(.metadata.namespace)/\($owner)" as $key
  | select(.status.phase == "Running" and $owner != null and $vm[$key] != null)
  | .spec.volumes[]? | select(.dataVolume.hotpluggable == true or .persistentVolumeClaim.hotpluggable == true)
  | .name as $n | select($vm[$key] | index($n) | not)
  | "\($key) \($n)"'
```

Empty output means nothing is affected. Each line names a VM and a volume the upgrade would detach. Recreate each tenant Kubernetes node it lists before the upgrade, so that its volumes are attached the new way. For the VM of a `VMInstance`, named `vm-instance-<name>`, handle the volume as described above instead.

### VM disks

A `vm-disk` release created before v1.7 moves to the new chart during the platform upgrade, and until cozystack-controller copies the new readiness settings onto it, helm-controller waits for the disk's DataVolume to be ready. cozystack-controller is upgraded only after the `cozystack.networking` Package, which holds Cilium and Kube-OVN on `isp-full` and `isp-full-generic`, so the release of a disk whose import is still running, or never finishes, can fail its upgrade and hold one helm-controller worker until an attempt starts after the settings were copied. An attempt already running when they arrive still waits out its 10-minute timeout: on a test cluster that took two failed 10-minute attempts, about 20 minutes. The release then upgrades whether or not the import has finished. Let running imports finish before upgrading. `kubectl get dv -A` shows the phase of every DataVolume.

A new disk created from a golden image is refused when CDI would clone it into a LINSTOR StorageClass that does not allow remote volume access from every node, a node-local class for example. Before, such a disk stayed pending forever without an error. Use the golden image's StorageClass, or have the platform administrator set the CDI `cloneStrategyOverride` to `copy` in the kubevirt-cdi package. Existing disks are exempt.

## Monitoring

Container logs now keep only the pod, namespace and container name of their Kubernetes metadata. The node name (`host`), labels, annotations, pod ID, container image and container ID are removed from every container log, in platform namespaces as well, so saved log queries and alerts that filter on those fields have to be updated.

## Managed applications

### Redis

A Redis instance can now be exposed outside the cluster only when it is created with both `external: true` and `tls.enabled: true`. The `cozystack-database-external-tls-policy` admission policy refuses to create an external instance without TLS, to turn `external` on for an existing instance, whether or not it has TLS, and to change `tls.enabled` while `external` is on. TLS is fixed when an instance is created, so an existing instance cannot gain it: to expose one with TLS, create a new instance with both values set and move the clients to it.

Instances that were already external without TLS keep working and stay editable, apart from `tls.enabled`. Setting `external: false` in the same edit lifts that freeze, but external access can then be turned on again only by creating a new instance.

On upgrade the Sentinel pods of every instance move to the Redis image of the data pods and roll once, and the data pods roll once for a new metrics exporter image.

### PostgreSQL

An external PostgreSQL instance now refuses sessions that are not encrypted. The new `tls.required` value has three states:

- unset (the default): follows `external`, so an instance with `external: true` accepts only TLS sessions;
- `true`: TLS sessions only, whether or not the instance is external;
- `false`: no extra rule, so plaintext sessions are accepted as before.

The rule covers every client of such an instance, in-cluster ones included. libpq's default `sslmode=prefer` already negotiates TLS, so only clients that disable TLS explicitly, with `sslmode=disable`, are refused. An instance that was external before the upgrade refuses those clients afterwards; update them, or set `tls.required: false` to keep accepting them.

An instance with a memory limit below 512Mi and no explicit `shared_buffers` (the `t1.nano` preset and the default `t1.micro`) now gets `shared_buffers` set to a quarter of the limit, 64MB for `t1.micro`, where PostgreSQL used its built-in 128MB before. The setting needs a restart, so on upgrade CloudNativePG restarts the replicas first and then the primary in place: writes pause for one restart, and an instance with a single replica is unavailable during it. A cluster that already runs v1.6.5 or later has this value from that patch and is not restarted for it again. Set `postgresql.parameters.shared_buffers` before the upgrade to take the restart on your own schedule.

Apart from `shared_buffers`, the upgrade moves the CloudNativePG operator from 1.28 to 1.30.0. On a test cluster upgraded from v1.6.5, every PostgreSQL instance restarted once in it, and an instance with a single replica was unavailable while its pod restarted. Upgrades from v1.6.4 or earlier were not tested, and there an instance can also take the `shared_buffers` restart described above.

### PostgreSQL and MariaDB passwords

User passwords can no longer be set from values: `users.<name>.password` is removed from both applications, and every password, MariaDB's `root` included, is generated into the `<release>-credentials` Secret. On upgrade the charts keep the passwords already stored in that Secret, so existing logins keep working. A `password` left in values is ignored with an admission warning, but the value it set stays the live password until it is rotated. Read a user's password from the Secret:

```bash
kubectl get secret <release>-credentials -o json | jq -r '.data["user1"]' | base64 -d
```

An upgraded MariaDB release refuses to render if its `<release>-credentials` Secret is missing, rather than generating new passwords that would not match the server.

On the first reconcile after the upgrade, a PostgreSQL release drops the roles of users that were removed from `users` while on v1.6.x but were left behind in the database, and their objects move to the `cozystack:orphaned` role. Clients that still log in with such a role lose access.

### OpenSearch

- An external release that never set `tls.issuer` moves from the operator's certificate authority to a per-release cert-manager CA the first time it reconciles after the upgrade. That rolls the cluster and re-anchors it on the new CA, published to the tenant as `opensearch-<name>.tenant-ca`, so anything pinned to the old CA has to move. Set `tls.issuer: operator` before the upgrade to stay on the operator's CA.
- The external-dns names of an external release move from the in-cluster domain to `<release>.<tenant host>` and `<release>-dashboards.<tenant host>`, whatever `tls.issuer` says. The old records are not deleted and have to be removed from the zone by hand.
- With `dashboards.enabled`, an application name is limited to 41 characters, and to 32 when `external` is also on. A longer existing release stops rendering after the upgrade; set `dashboards.enabled: false`, or recreate the application under a shorter name to keep Dashboards.
- Every OpenSearch cluster rolls once on upgrade.
- A release that stores `version: null` fails to render after the upgrade instead of falling back to `v2`, although the API still reads it back as `v2`. Set its `version` before upgrading.
- On a cluster whose `networking.clusterDomain` is not `cluster.local`, the default `cozy.local` included, an instance created on v1.6.x keeps its `<release>-securityconfig-update` Job, which targets the `.svc.cluster.local` host that does not resolve there. The operator leaves that Job in place: on a test cluster it had ended `Failed` with `BackoffLimitExceeded`, and no new Job followed. Deleting the Job there made the operator create a new one 3 seconds later, with the host on the platform's cluster domain, and the new Job connected to the cluster. Whether the instance then finishes initializing was not confirmed.

### FoundationDB

A FoundationDB release now selects a release line with `version`, `v7.3` by default or `v7.4`, and the platform pins the patch: `v7.3` deploys 7.3.63 and `v7.4` deploys 7.4.1. `cluster.version` no longer selects the deployed version.

- Platform migration 60 carries each release's line over from `cluster.version`. A cluster that runs another patch of its line is moved to the pinned one, downwards included: on a test cluster a 7.3.69 cluster was moved to 7.3.63, and the migration's annotation entry was the only lasting signal. Before upgrading, check the running patch of every cluster in the `VERSION` column of `kubectl get foundationdbclusters.apps.foundationdb.org -A`.
- The FoundationDB operator no longer ships the 7.1 client, so it cannot manage or upgrade a cluster that runs FoundationDB 7.1.x. Before upgrading the platform, move every such cluster to 7.3 through its `cluster.version` value. A release whose `cluster.version` still names 7.1 is refused when it renders, whatever its `version` is, so the release stays on its current revision and the cluster on 7.1, which the operator can no longer upgrade.
- A release whose `cluster.version` is on a different line than its `version` is refused, with a message that names both.
- On the `default` variant migration 60 does not run. Before upgrading such a cluster, set `version` to the line each FoundationDB cluster runs.

### Image overrides

The Kubernetes, KubernetesNodes and OpenSearch charts no longer read their image overrides: `images.kubectl`, `images.waitForKubeconfig` and `images.talosCsrSigner` of `Kubernetes`, `images.kubectl` of `KubernetesNodes`, and `images.opensearch` of `OpenSearch`. They use the images the platform ships. A release that still carries such a value keeps it stored, the chart ignores it, and the API shows no warning for it. Migration 60 lists such releases in its annotation.

On the first reconcile, OpenSearch nodes move to the image of their selected version, and Kubernetes components whose image changed restart. Before upgrading, check every OpenSearch release that runs a custom image: if it runs a newer OpenSearch version than its `version` maps to, switching back can leave the nodes unable to read their data. An air-gapped installation needs `docker.io` and `ghcr.io` mirrored on the nodes of the management cluster.

### Kafka moves to KRaft

The Kafka application now runs Kafka in KRaft mode, and existing ZooKeeper-based instances are migrated in place, automatically, on their first upgrade to the new chart. The migration runs as the Job `<release>-kafka-migration` in the instance's namespace; follow it with:

```bash
kubectl logs -n <namespace> job/<release>-kafka-migration
```

Plan a maintenance window of up to a few hours per instance: the migration rolls the brokers, and when several ZooKeeper-based instances share a namespace they migrate one after another. Once a cluster passes the `PreKRaft` state the migration cannot be reversed, so do not downgrade the Kafka application or the platform afterwards.

This release is a mandatory stop on the upgrade path: make sure every Kafka instance has reached KRaft on v1.7 before upgrading past it, because later Strimzi releases no longer migrate ZooKeeper clusters. The application also gains a `version` value, `v3.9` by default.

### SeaweedFS volume size limit

New SeaweedFS instances start with `master.volumeSizeLimitMB: 400` instead of 1000, and a bucket now grows three volumes at a time instead of six at `replicationFactor: 2`. Lowering the limit on an instance that already holds data stops writes to buckets whose volumes have all crossed the new limit until they can grow, so existing instances keep 1000:

- On every variant except `default`, platform migration 57 writes `master.volumeSizeLimitMB: 1000` into each instance that has no valid value of its own.
- An instance whose value was already set to a whole number from 1 to 30000 keeps it. The previous chart ignored that value, so it takes effect with the upgrade.
- On the `default` variant nothing writes the value, and every instance without one would drop to 400. Before upgrading, apply the migration's change yourself with the commands below.

```sh
kubectl get helmreleases.helm.toolkit.fluxcd.io -A -o json \
  -l apps.cozystack.io/application.kind=SeaweedFS,apps.cozystack.io/application.group=apps.cozystack.io \
  | jq -r '"instances \(.items | length)",
      (.items[] | "\(.metadata.namespace) \(.metadata.name)" as $id | .spec.values as $s
       | [(.spec.valuesFrom // [])[] | select(. != {kind: "Secret", name: "cozystack-values"})] as $extra
       | (if $extra != [] then "valuesfrom \($id) \($extra | tojson)" else empty end),
         (if $s != null and ($s | type) != "object" then "unreadable \($id) \($s | tojson)", "pin \($id)"
          elif $s.master != null and ($s.master | type) != "object" then "unrenderable \($id) \($s.master | tojson)"
          else $s.master.volumeSizeLimitMB as $v
          | select(($v | type) != "number" or $v != ($v | floor) or $v < 1 or $v > 30000)
          | "pin \($id)" end)),
      "complete \(.items | length)"' \
  | while read -r what ns name detail; do
      case "$what" in
        pin) ;;
        instances|complete) echo "$what $ns"; continue ;;
        *) echo "$what $ns $name $detail"; continue ;;
      esac
      echo "pinning $ns/$name"
      kubectl -n "$ns" patch helmreleases.helm.toolkit.fluxcd.io "$name" --type=merge \
        -p '{"spec":{"values":{"master":{"volumeSizeLimitMB":1000}}}}' </dev/null \
        || { echo "stopped: patching $ns/$name failed"; break; }
    done
```

The last line must read `complete` with the same number as the first. If it is missing, or a `stopped` line appears, the releases after that point were neither listed nor pinned: fix the cause and run it again. Then run it a second time; it must print no `pinning` line. An `unrenderable` line names a release whose `master` is not an object, which no chart renders; set `volumeSizeLimitMB` in the same edit that repairs it. Patch the HelmRelease as shown, not the SeaweedFS resource, so that only this one key is written.

The full check to run before lowering the limit of an instance that holds data is in [SeaweedFS volume size limit: lowering it on an existing instance](https://github.com/cozystack/cozystack/blob/main/docs/operations/seaweedfs-lowering-the-volume-size-limit.md).

### HTTPCache

The HTTPCache application is removed from the catalog and no new instance can be created. Its PackageSource, `cozystack.http-cache-application`, is no longer part of the platform release, so the upgrade prunes it, and the ArtifactGenerator and both ExternalArtifacts it owns go with it. They are the chart sources of `http-cache-rd` in `cozy-system` and of every tenant `http-cache-<name>` release. Left alone, those releases stay `Ready=False` for good: each instance reads as not ready while its pods keep serving, and `HelmReleaseNotReady` fires where the monitoring agents run.

- On every variant except `default`, platform migration 58 handles this. On a cluster that runs an instance, it freezes the application on the packages artifact the cluster already renders from: the instance keeps working and stays manageable, but receives no further updates, security fixes included. On a cluster without one, the migration removes the application from the platform.
- On the `default` variant nothing does. Before upgrading such a cluster, take the migration's steps yourself with the commands below, while `cozystack-packages` still resolves the release the cluster runs.

List the HTTPCache releases. They are selected by chart and by application label, so a release whose chart reference was never rewritten is found too:

```bash
kubectl get helmreleases.helm.toolkit.fluxcd.io --all-namespaces -o json \
  | jq -r '.items[]
      | select(.spec.chartRef.name == "cozystack-http-cache-application-default-http-cache"
            or .metadata.labels["apps.cozystack.io/application.kind"] == "HTTPCache")
      | "\(.metadata.namespace)/\(.metadata.name)"'
```

If it prints nothing, remove the application from the platform. Run the commands in this order: the first one waits until the Package is gone, so that a reconcile already in flight does not re-create what the others remove. On a cluster where the application was never installed they change nothing.

```bash
kubectl delete packages.cozystack.io cozystack.http-cache-application --ignore-not-found
kubectl -n cozy-system delete helmreleases.helm.toolkit.fluxcd.io http-cache-rd --ignore-not-found --wait=false
kubectl delete applicationdefinitions.cozystack.io http-cache --ignore-not-found
kubectl -n cozy-system delete secret -l owner=helm,name=http-cache-rd --ignore-not-found
```

An instance that is no longer needed can be deleted before the check, so that the cluster takes this path instead of the freeze.

Otherwise, freeze the application. Run the remaining commands in one shell session, because they carry the digest from one step to the next. First read the manifest digest `cozystack-packages` resolves to now:

```bash
src=$(kubectl -n cozy-system get ocirepositories.source.toolkit.fluxcd.io cozystack-packages -o json)
digest=$(printf '%s' "$src" | jq -r '
  .spec.ref.digest
    // ((.status.artifact.revision // "") | capture("@(?<d>sha256:[0-9a-f]{64})$").d)
    // empty')
echo "$digest"
```

It must print `sha256:` followed by 64 hexadecimal characters. If it prints nothing, `cozystack-packages` has neither a digest ref nor a resolved artifact revision, and there is nothing to freeze on: do not go further until it has one. The freeze also assumes `cozystack-packages` is pinned to a fixed release, since a floating tag re-pointed in place would pin an artifact that no longer carries the chart.

Then create the frozen source, point the application at it, and keep the access of instance owners:

```bash
printf '%s' "$src" | jq --arg name cozystack-packages-http-cache --arg digest "$digest" '
  {
    apiVersion: .apiVersion,
    kind: .kind,
    metadata: {
      name: $name,
      namespace: .metadata.namespace,
      labels: { "platform.cozystack.io/no-delete": "true" },
      annotations: { "platform.cozystack.io/frozen": "http-cache" }
    },
    spec: (.spec | .ref = { digest: $digest })
  }' | kubectl apply --filename -

kubectl patch packagesources.cozystack.io cozystack.http-cache-application --type=merge \
  -p '{"metadata":{"annotations":{"helm.sh/resource-policy":"keep","meta.helm.sh/release-name":null,"meta.helm.sh/release-namespace":null},"labels":{"app.kubernetes.io/managed-by":null}},"spec":{"sourceRef":{"name":"cozystack-packages-http-cache"}}}'

kubectl patch packages.cozystack.io cozystack.http-cache-application --type=merge \
  -p '{"metadata":{"annotations":{"meta.helm.sh/release-name":null,"meta.helm.sh/release-namespace":null},"labels":{"app.kubernetes.io/managed-by":null}}}'

kubectl apply --filename - <<'YAML'
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cozy:tenant:admin:http-cache-frozen
  labels:
    rbac.cozystack.io/aggregate-to-tenant-admin: "true"
    platform.cozystack.io/no-delete: "true"
  annotations:
    platform.cozystack.io/frozen: http-cache
rules:
- apiGroups: ["apps.cozystack.io"]
  resources: ["httpcaches"]
  verbs: ["create", "update", "patch", "delete"]
YAML
```

The first command creates `cozystack-packages-http-cache`, a copy of `cozystack-packages` pinned to that digest. It keeps the registry, pull secret and verification settings of the original and carries no owner references or Helm metadata, so nothing reconciles or prunes it. The two patches point the PackageSource at the copy and detach it and the Package from the platform release, so the upgrade does not prune them. The ClusterRole keeps the owner of an instance able to change and delete it once v1.7 drops `httpcaches` from `cozy:tenant:admin:base`. After the upgrade, `http-cache-rd` and every release the first listing printed stay `Ready`.

### Smaller changes

- **VM instances.** `resources.cpu` and `resources.sockets` must be positive whole numbers and `resources.memory` at least `1M`. A value such as `500m`, `1.5` or `0` now fails the render of the release, and a release carrying one fails its next upgrade until the value is fixed, with an error such as `resources.cpu (500m) must be a positive whole number, such as 2`. A value such as `1e1` or `2.`, which used to give the VM one core, now sizes it with the number it spells.
- **Application definitions.** `ApplicationDefinition.spec.release.prefix` must match `^[a-z0-9-]*$`. A definition whose prefix holds a dot or any other character is refused when it is created, so check definitions that come from external application repositories.
- **RabbitMQ and Redis TLS** are new and off by default; nothing changes on upgrade until TLS is enabled on an instance.
- **Keycloak realm name.** The realm is now configurable with `authentication.oidc.realmName`, `cozy` by default. Set it only at install time; see the [Platform Package reference]({{% ref "/docs/v1.7/operations/configuration/platform-package" %}}).
- **Pod rolls.** Besides the rolls described above, every Kafka cluster rolls once because its JVM environment changes, the SeaweedFS master, volume, filer and S3 components move to a patched image, the `kube-multus` DaemonSet rolls node by node for its new resources, and the LINSTOR controller and satellite pods move to a rebuilt `piraeus-server` image.
