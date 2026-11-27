---
title: "GPU class catalog"
linkTitle: "GPU classes"
description: "Define the hoster's GPU offers and select them in virtual machines and Kubernetes worker pools."
weight: 45
---

A `GPUClass` is a cluster-scoped offer in the hoster's catalog. The hoster creates classes; tenants select them by name in a VMInstance or KubernetesNodes application. Class selection is an unreleased feature. It requires the GPU controller and VM admission integration; creating a class alone does not install a device plugin, configure a GPU profile or advertise capacity.

## Prepare the host

Configure the appropriate GPU path before adding an offer: [whole-GPU passthrough]({{% ref "/docs/next/virtualization/gpu" %}}) or [vGPU]({{% ref "/docs/next/virtualization/vgpu" %}}). The class's source must name the extended resource actually advertised by the device plugin and permitted by KubeVirt. Do not derive that string from the GPU's marketing name.

The examples below are synthetic. Replace their model, profile and resource names with values verified on your hardware and driver. They are not hardware recommendations, and the two vGPU examples represent alternative licensing offers rather than profiles to create on one GPU.

## Define an offer

Keep catalog manifests in the hoster's configuration repository and deploy them through the normal GitOps workflow. Do not put `status` in these manifests: the controller reports availability and conditions there.

### Whole GPU

```yaml
apiVersion: cozystack.io/v1alpha1
kind: GPUClass
metadata:
  name: example-whole-gpu
spec:
  displayName: "Example whole GPU"
  vendor: example
  model: example-model
  mode: passthrough
  source:
    devicePlugin:
      resourceName: example.com/whole-gpu
```

`metadata.name` is the tenant-facing catalog identifier: a DNS label of at most 63 characters. It is distinct from `spec.source.devicePlugin.resourceName`, which is the Kubernetes extended resource supplied by the device plugin. `devicePlugin` is the only supported source; a DRA backend is not configured by this API.

### Platform-licensed vGPU

```yaml
apiVersion: cozystack.io/v1alpha1
kind: GPUClass
metadata:
  name: example-licensed-vgpu
spec:
  displayName: "Example licensed vGPU"
  vendor: nvidia
  model: example-model
  mode: vgpu
  profile: example-profile
  maxCount: 1
  source:
    devicePlugin:
      resourceName: example.com/licensed-vgpu
  license:
    secretName: example-vgpu-license
    featureType: 1
```

`license.secretName` names the hoster's source Secret in `cozy-system`, with the key `client_configuration_token.tok`. Create that Secret through the hoster's secret-management process, not by copying a token into this example, an image or bootstrap values. `featureType` accepts `1` or `4` and defaults to `1`; choose it for the actual vGPU profile and guest driver. Guest image preparation is a separate prerequisite, defined by the accepted [guest licensing contract](https://github.com/cozystack/community/blob/024d8b9133520a17e6610271bed7ad78b0b3edfa/design-proposals/vgpu-vms/README.md#2-the-token-in-the-guest). The image must handle the `GPULICENSE` disk and prepare its licensing client before this offer can work; creating a catalog entry does not do that.

A vGPU class requires `profile`. A passthrough class permits neither `profile` nor `license`. The catalog describes an existing offer; it does not create the host's vGPU instances or set their profiles.

### Tenant-owned licensing

A vGPU offer without `license` is BYOL. The tenant supplies its own guest licensing, but still needs vGPU entitlement. For example:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: GPUClass
metadata:
  name: example-byol-vgpu
spec:
  vendor: nvidia
  model: example-model
  mode: vgpu
  profile: example-profile
  source:
    devicePlugin:
      resourceName: example.com/byol-vgpu
```

Use a different advertised resource for each offer; giving two classes the same resource name does not create two independent pools. The platform-licensing reference must not run in a BYOL guest configuration.

### Optional settings and changes

| Field | Meaning |
| --- | --- |
| `displayName` | Human-readable offer name. |
| `memory` | Optional GPU memory per unit, as a positive Kubernetes quantity such as `16Gi`. It describes the offer; it does not partition GPU memory. |
| `maxCount` | Maximum units of this class per VM. When omitted, the effective limit is one for vGPU, or the GPUs available on one node for passthrough. An explicit limit must be at least one. |
| `tolerations` | Pod-shaped tolerations copied onto class-based virt-launcher pods. Supported operators are `Exists` and `Equal`; the default operator is `Equal`. |

`vendor`, `model`, `mode`, `profile` and `memory` identify the offer and are immutable. Create a new class when changing that identity. Changing the source resource name does not reconfigure the device plugin or move an existing VM to another GPU; check the replacement resource and KubeVirt configuration before using it for new starts. License changes reach a guest through a new VMI, not an OS reboot inside the existing VMI.

Tolerations allow placement on tainted nodes; they do not reserve a GPU or replace other scheduling constraints. An `Exists` toleration has no value, and `tolerationSeconds` applies only with effect `NoExecute`.

## Select a class as a tenant

Use these as application values or the corresponding application `spec` fragment, alongside the application's other required settings. They are not complete VM or worker-pool manifests. The tenant-facing `className` is the catalog name, not the device-plugin resource name.

### VMInstance

```yaml
gpus:
  - className: example-whole-gpu
    count: 1
```

For a licensed VM, select `example-licensed-vgpu` instead; for tenant-owned licensing, select `example-byol-vgpu`. A VM may take vGPUs from only one class. Repeating that class or requesting a larger `count` still has to satisfy its per-VM limit. Use a guest image prepared for that licensing mode, with a compatible driver. This selection fragment does not install the driver or configure the guest's licensing client; platform-licensed images must satisfy the [guest preparation prerequisite](#platform-licensed-vgpu).

Omitting `count` requests one unit. Keep an explicit count positive. The sum of class counts may expand to at most 1024 GPU units per VMI; that is an input bound, not a promise of available hardware. The admission integration resolves the class to KubeVirt GPU entries; do not add raw GPU requests beside those entries.

### KubernetesNodes

Set `gpus` on the KubernetesNodes pool itself:

```yaml
gpus:
  - className: example-whole-gpu
    count: 1
```

The count is **per worker**, not for the whole pool. Each worker needs its requested GPUs on one host. Class entries in this application support passthrough only; do not select a vGPU class for this worker-pool path. GPU drivers and the tenant cluster's GPU addon remain separate configuration. See [managed Kubernetes]({{% ref "/docs/next/kubernetes" %}}) for the cluster and worker-pool setup.

### Raw resource-name compatibility

Existing applications can keep requesting the device-plugin resource directly:

```yaml
gpus:
  - name: example.com/whole-gpu
```

A `gpus` list contains either class entries or raw `name` entries, never both. An entry selects exactly one of `className` and `name`; `count` belongs to class entries only. Raw entries do not opt into class-based license delivery. They are not a substitute for vGPU entitlement.

## Check availability and start failures

Read the catalog and a class's status with an explicitly chosen Kubernetes context:

```bash
kubectl --context YOUR_CONTEXT get gpuclasses
kubectl --context YOUR_CONTEXT get gpuclass example-whole-gpu --output yaml
```

`status.free` reports free units across eligible nodes; `status.maxFreePerNode` reports the largest free count on one node. Nodes must be Ready, not cordoned, and free of untolerated `NoSchedule` or `NoExecute` taints. These counters are observations, not reservations: availability can change before scheduling, and free units spread across hosts cannot satisfy a VM that needs them together on one host.

Check conditions as well as counts:

- `ResourceNameConflict`: another class already uses the resource name; the conflicting offer is not available. Correct the hoster's catalog rather than giving tenants a duplicate name for the same pool.
- `ResourceNameNotPermitted`: the resource is missing from KubeVirt's permitted-device table. Configure the VM-facing GPU path and the table before retrying.
- `LicenseSecretMissing`: a licensed class has no usable source Secret or token key. Inspect Secret names and keys without printing token payloads.

A missing, deleting or conflicting class, or an unpermitted resource, causes a class-based start to be refused. Capacity shortage instead leaves a VM waiting for scheduling. For vGPU, the root entitlement comes from platform `gpu.vgpu`; each child tenant also needs its own entitlement and an entitled parent. Entitlement and GPU quota are separate checks. If a required license copy has not arrived, the launcher waits for its Secret rather than intentionally booting unlicensed.

## Contract sources

The catalog and selection model are defined in the accepted [GPU design](https://github.com/cozystack/community/blob/026c4190c9c1d8d0e458e2d60bb621c2b4ecd6b9/design-proposals/gpudevice/README.md). The field reference above follows the published [GPUClass types](https://github.com/cozystack/cozystack/blob/9f607f0afe1d6a79573fa7a75cf1c8e9f1325344/api/v1alpha1/gpuclass_types.go). Application selection follows the published [class-entry helper](https://github.com/cozystack/cozystack/blob/74847c8c2d816b6d5d82e65dd14fe6030affbc22/packages/library/cozy-lib/templates/_gpu.tpl) and [VMI admission](https://github.com/cozystack/cozystack/blob/74847c8c2d816b6d5d82e65dd14fe6030affbc22/internal/gpu/webhook/vmi.go). These implementation snapshots describe unreleased work, not a feature available in every installed Cozystack version.
