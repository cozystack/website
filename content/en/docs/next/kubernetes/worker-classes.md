---
title: "Worker classes and Kairos pools"
linkTitle: "Worker classes"
description: "Choose a worker OS baseline while preserving existing Talos pools and image compatibility."
weight: 15
---

A `WorkerClass` describes how a managed Kubernetes worker boots and joins its cluster. The hoster administers the cluster-scoped class; the tenant selects it on a standalone `KubernetesNodes` pool through `workerClassName`. Replicas, sizing, labels, taints and health settings remain pool configuration.

{{< warning >}}

This page describes the accepted, unreleased WorkerClass contract, not the old NodeGroupClass draft. Examples are contract examples, not deployment instructions for an installed release. Package settings, application schema and the restore-tool interface must be checked against the release being deployed. No released restore command or verified Kairos recovery procedure is supplied here.

{{< /warning >}}

The accepted [WorkerClass and Kairos design](https://github.com/cozystack/community/blob/77458b33a379e6e8def79ebfd97664129ee4a6f3/design-proposals/kairos-tenant-worker-pools/README.md) defines this contract. [Managed Kubernetes]({{% ref "/docs/next/kubernetes" %}}) remains the starting point for creating the parent cluster. A class does not replace that cluster or its control plane.

## Classes and the platform default

The optional managed-Kubernetes system package owns the WorkerClass CRD, controller and admission webhooks. The class `spec` is immutable: publish another class for another baseline or fixed image rather than editing an offer used by existing pools. Classes contain OS and bootstrap settings, not GPU licenses or tenant credentials.

The built-in names are `talos` and `kairos`. The platform-selected default initially chooses `talos`. New application API creates without a class receive that default as a stored value; it is not a static schema default. Changing the platform default does not retarget stored pools.

| KubernetesNodes application API request | Result |
| --- | --- |
| CREATE with class omitted or empty | Admission writes the current platform default before validating it. |
| CREATE with an explicit class | The selected class is preserved and validated. |
| UPDATE of a classless pool, class omitted or empty | The pool remains legacy Talos. |
| UPDATE of a classified pool, class omitted or empty | The stored class is restored, including on a full replace. Empty is not a request to become legacy. |
| UPDATE selecting another class | The selection must pass bootstrap-family and image/override compatibility checks. |

Direct HelmRelease writers do not pass through that application API mutation. They must choose an explicit class for class semantics; omission retains legacy rendering. ComputePlane keeps its existing classless Talos path and does not expose standalone pool OS or Kubernetes-version selection through its current `nodeGroups` allowlist.

A classless render does not look up a WorkerClass. That is not an API outage exemption: a matching webhook with `failurePolicy: Fail` can refuse an UPDATE even when its healthy handler would leave the legacy pool unchanged. Verify the installed package's webhook matching, readiness and failure behavior before exposing class-defaulting creates.

## Choose a standalone pool

These examples illustrate the accepted interface. The parent cluster, storage and other infrastructure prerequisites must already exist. Their versions are design examples, not a support matrix for every Cozystack release.

### Built-in Kairos

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: KubernetesNodes
metadata:
  name: example-kairos
spec:
  cluster: example
  workerClassName: kairos
  version: v1.35
  minReplicas: 2
  maxReplicas: 3
  sshKeys: []
```

Kairos initially supports KubeVirt, not Proxmox. It boots an immutable disk and joins through the Kairos bootstrap provider's kubeadm path. Bootstrap changes require replacement workers; this is not mutable in-place OS management or general cloud-init support.

`sshKeys` is a list of public-key strings. Kairos currently accepts zero or one key; more than one is rejected. An empty list configures no SSH login through this mechanism. A supplied key authorizes a sudo-capable guest user. Talos has no SSH server: a nonempty list is rejected, while an empty list is allowed. Never put a private key in pool values.

For a Kairos pool that needs SSH, replace `<SSH_PUBLIC_KEY>` with one complete public-key string in this pool-values fragment:

```yaml
sshKeys:
  - "<SSH_PUBLIC_KEY>"
```

### Talos baseline and tenant override

```yaml
apiVersion: cozystack.io/v1alpha1
kind: WorkerClass
metadata:
  name: talos-example-r1
spec:
  bootstrap: talos
  talos:
    version: v1.13.6
---
apiVersion: apps.cozystack.io/v1alpha1
kind: KubernetesNodes
metadata:
  name: example-talos
spec:
  cluster: example
  workerClassName: talos-example-r1
  version: v1.35
  talos:
    version: v1.13.6
  kernelModules:
    - name: nvme_tcp
```

The hoster creates the class; the tenant creates the pool. Other baseline settings still have to resolve to a supported image. Loading `nvme_tcp` requires an image that contains the module: a module list does not install an extension or prove kernel compatibility.

### Fixed custom Kairos image

This is a template, not a pullable artifact. Replace `<PUBLIC_DISK_SHA256>` with the digest of a verified, publicly pullable worker container disk. Its Kubernetes version must describe the kubelet and kubeadm packaged in that disk.

```yaml
apiVersion: cozystack.io/v1alpha1
kind: WorkerClass
metadata:
  name: kairos-example-v1-35-6-r1
spec:
  bootstrap: kairos
  image:
    kubernetesVersion: v1.35.6
    reference: "registry.example.com/workers/kairos-worker@sha256:<PUBLIC_DISK_SHA256>"
---
apiVersion: apps.cozystack.io/v1alpha1
kind: KubernetesNodes
metadata:
  name: example-custom-kairos
spec:
  cluster: example
  workerClassName: kairos-example-v1-35-6-r1
  version: v1.35
```

Both fixed-image fields are required together. This interface does not accept a tenant pull Secret for a private disk. Private worker images wait for the shared catalog; a public reference is not permission to redistribute proprietary drivers.

## Talos overrides and image selection

Resolve the class baseline, apply supported tenant overrides, then check the final image's compatibility contract. An override cannot change bootstrap family. Unsupported nonempty Talos settings on Kairos are rejected rather than silently interpreted as Kairos configuration.

| Setting | Resolution |
| --- | --- |
| Talos scalars | An explicitly supplied pool value replaces the baseline. An explicit empty scalar is not silently replaced by the baseline. |
| `registryMirrors` | A supplied map replaces the baseline map; `{}` clears it, without deep merging. |
| `kernelModules` | A supplied list replaces the baseline; `[]` disables loading. The automatic NVIDIA rule runs only when neither baseline nor pool supplies a list. |
| KubeVirt `osImage` absent | Use the class's KubeVirt source when present; otherwise resolve the default factory path from effective Talos settings. |
| KubeVirt `osImage` supplied | Replace source selection as a unit. `{}` selects the default factory path; builtin and factory cannot both be set. |
| Builtin version/schematic | Nonempty selected source values take precedence; omitted or empty values use effective `talos.version` and `talos.schematicID`. The matching golden must exist. |
| Factory version/schematic/endpoint | Nonempty selected source values take precedence; omitted or empty values use the corresponding effective Talos settings. |
| Proxmox template tags | A supplied pool list replaces the baseline; an empty final list fails. Nonempty `osImage` is not a Proxmox source. |

A factory baseline derives its image from effective Talos settings. A fixed artifact identifies particular bytes or an existing golden/template with declared version and schematic compatibility. After resolving overrides, a conflicting artifact, version or schematic is rejected. Another source selection does not waive this check. Matching Proxmox declarations does not verify an external template's bytes.

Keep reachability consumers separate: `registryMirrors` configures guest pulls, `imageFactoryCA` configures CDI HTTP-import trust, and `installerRepository` selects the in-guest installer source. Resolved version and schematic must agree between disk and installer. These inputs do not grant hoster credentials or change global trust. They remain Talos-specific, not generic Kairos controls.

## Versions and replacement

The tenant chooses a supported Kubernetes minor through pool `version`. The platform version map chooses the exact patch for platform images. A fixed custom Kairos image supplies its own exact patch, and the pool must select that image's minor. No arbitrary pool patch selector is added.

Upgrade the parent control-plane minor first. A custom-image patch upgrade selects the class carrying the new image; a minor upgrade changes the pool minor and matching class together. An unrelated platform patch change must not replace a fixed custom image's declared Kubernetes patch.

Platform Kairos images remain experimental. The accepted design records unchanged-input builds producing different disk digests. Because the reference enters the template hash, a platform rebuild can replace workers even when intended image inputs did not change. A hoster's independently pinned image is a separate choice; pinning a rebuilt platform result does not prove reproducibility.

## Existing pools and rollback prerequisites

Classless Talos pools retain legacy image resolution, tenant settings and rendered templates. Adding WorkerClass support must not rewrite them. The mandatory later Talos migration is a separate stage with its own no-rollout and rollback evidence, not a prerequisite of the initial experimental Kairos release.

The initial release refuses switching a running pool between Talos and Kairos in place. Create a second pool, verify worker join and workloads, then plan workload migration. Removing the old pool removes worker machines and can lose node-local data. Review storage, disruption budgets and backups before an operator approves removal; this guide does not perform or authorize it.

Rollback to a chart without class support needs an operator-controlled plan:

1. Do not leave Kairos pools for an older chart to interpret as Talos. Migrate workloads and obtain approval for removing those pools before reverting.
2. Restore each classified Talos pool's effective settings into the old pool field layout through the release's documented restore interface with hoster authorization. Verify the old chart's resources and template hashes; remaining Talos is not proof of no rollout.
3. Already-classless pools need no class restoration. Retain custom classes and the worker controller while live classified pools depend on them.
4. Establish supported re-upgrade behavior separately. Restoring old fields does not prove automatic return to a prior class on re-upgrade.

A restore recipe requires a published interface and verified prerequisites. No command is shown because the accepted design is not a shipped CLI specification. Do not substitute hand-written class-field removal for a validated restore procedure. Removing the controller can also leave custom classes with finalizers needing hoster handling.

## Recovery and support boundaries

Kairos remediation and scale from zero need separate evidence. Shared MachineDeployment or MachineHealthCheck shapes do not establish successful replacement. With `maxUnhealthy: 50%`, one unhealthy worker in a singleton pool exceeds the rounded-down threshold; this does not explain every recovery failure. The recorded unresolved Kairos recovery cause remains unknown. A successful retry is not proof of a fix.

Verify real worker join, replacement, upgrades and autoscaling for the selected image and substrate before operational use. Guest boot, rollback restore and recovery experiments are not established by the contract examples here.

GPU attachment remains a pool setting, not driver installation or licensing. WorkerClass has no GPUClass fields or license tokens. Talos/vGPU refusal is a known bootstrap-family exception, not evidence that every other image supports vGPU. GPU images need separate driver, runtime and hardware validation; this page does not duplicate GPU catalog or guest-licensing references.
