---
title: "Kubernetes AI Conformance Results for Cozystack"
linkTitle: "AI Conformance"
description: "How Cozystack meets each requirement of the CNCF Kubernetes AI Conformance programme, with the mechanism behind it and the command that verifies it."
date: 2026-09-12
type: "page"
weight: 40
---

**Tenant Kubernetes clusters created by Cozystack meet the requirements of the CNCF Kubernetes
AI Conformance programme.** Where base Kubernetes conformance answers "is this real
Kubernetes", AI conformance answers a narrower and more practical question: will an AI
workload that runs on one conformant platform run here too, without platform-specific
workarounds.

The programme defines twelve requirements across accelerators, networking, scheduling,
observability, security and operators. This page records how each is met, and what to run to
check it yourself. It is the evidence referenced from our submission to
[`cncf/k8s-ai-conformance`](https://github.com/cncf/k8s-ai-conformance).

## What is being certified

A **tenant Kubernetes cluster** — the resource a tenant creates for themselves from the
catalog with `kind: Kubernetes`. Its control plane is managed by Kamaji; its worker nodes run
as KubeVirt virtual machines on Talos Linux. This is the same artifact certified under
[base Kubernetes conformance](/compliance/kubernetes-conformance/), and it is where the
accelerator and AI capabilities below are configured, as addons of that application.

The management cluster of an installation is not the subject: a tenant never runs workloads
there.

Unless stated otherwise, every result below comes from a tenant cluster running Kubernetes
v1.35.6 on a Cozystack v1.6.1 installation.

## Accelerators

### Dynamic Resource Allocation

Dynamic Resource Allocation is the Kubernetes API for requesting and sharing devices with
more expressiveness than an integer count — filtering on device attributes, sharing one
device between pods, and configuring a device per workload rather than per node. It reached
general availability in the `resource.k8s.io/v1` group.

Tenant clusters serve that group. All four GA kinds are present:

```console
$ kubectl api-versions | grep resource.k8s.io
resource.k8s.io/v1

$ kubectl api-resources --api-group=resource.k8s.io
NAME                     SHORTNAMES   APIVERSION            NAMESPACED   KIND
deviceclasses                         resource.k8s.io/v1    false        DeviceClass
resourceclaims                        resource.k8s.io/v1    true         ResourceClaim
resourceclaimtemplates                resource.k8s.io/v1    true         ResourceClaimTemplate
resourceslices                        resource.k8s.io/v1    false        ResourceSlice
```

`DeviceTaintRule` is deliberately absent. It lives in `resource.k8s.io/v1alpha3` behind the
`DRADeviceTaints` feature gate and is not part of the GA group.

`DeviceClass` and `ResourceSlice` are empty until a DRA driver is installed — a driver is what
publishes the device inventory. Installing one is a tenant's choice, and for NVIDIA GPUs worth
knowing that the GPU allocation side of the upstream driver is not yet officially supported and
ships disabled by default. Accelerator allocation on this platform is therefore served today by
the device plugin path described below, which is what production workloads use.

### Accelerator drivers and runtime

The NVIDIA GPU Operator is an addon of the tenant Kubernetes application:

```yaml
addons:
  gpuOperator:
    enabled: true
```

Enabling it installs and then maintains, on every node that has an accelerator, the NVIDIA
driver, the NVIDIA Container Toolkit, the Kubernetes device plugin, GPU Feature Discovery for
node labelling, and DCGM for monitoring. Because it is an operator rather than a one-time
install, driver and runtime configuration are reconciled rather than drifting, and node labels
report the versions actually present.

### Sharing a GPU between workloads

Two strategies are available, and they answer different needs.

**Hardware partitioning.** On accelerators that support MIG, the GPU Operator exposes the
partitions as schedulable resources, so a workload that needs a fraction of a card requests a
fraction rather than a whole one.

**Software sharing and oversubscription.** HAMi ships as its own addon and provides
time-sliced sharing, allowing more workloads than cards:

```yaml
addons:
  gpuOperator:
    enabled: true
  hami:
    enabled: true
```

HAMi requires the GPU Operator, which the platform enforces.

### Accelerators in virtual machines

Worker nodes of a tenant cluster are virtual machines, which makes the accelerator question a
virtualization question — and the platform answers it in the node pool definition rather than
by hand. A pool declares the devices its nodes carry:

```yaml
gpus:
  - name: nvidia.com/AD102GL_L40S
```

The named device is attached to each virtual worker in the pool and surfaces inside the tenant
cluster through the same resource model as on a bare-metal node, so a workload does not need to
know which it landed on. Physical passthrough and vendor virtualized modes are both expressed
this way.

This is worth stating plainly because it is where a virtual-machine-based platform differs from
a container-only one: the accelerator crosses the virtualization boundary as part of the pool's
declaration, not as an operator-level exception.

## Networking

### Gateway API for inference traffic

Gateway API ships as an addon, and Cilium — the platform CNI — provides the implementation:

```yaml
addons:
  gatewayAPI:
    enabled: true
```

```console
$ kubectl get gatewayclass -o wide
NAME     CONTROLLER                     ACCEPTED   AGE
cilium   io.cilium/gateway-controller   True       ...
```

Two properties matter for serving models, and both were verified on a programmed Gateway with
accepted routes.

**Weighted traffic splitting**, for shifting load between two versions of a model server:

```yaml
rules:
  - backendRefs:
      - name: backend-a
        port: 80
        weight: 80
      - name: backend-b
        port: 80
        weight: 20
```

Thirty requests against that route landed 26 on `backend-a` and 4 on `backend-b`.

**Header-based routing**, which is how OpenAI-protocol headers are used to steer a request to a
particular model or a canary deployment:

```yaml
rules:
  - matches:
      - headers:
          - name: X-Env
            value: canary
    backendRefs:
      - name: backend-b
        port: 80
```

Requests without the header reached `backend-a`; requests carrying `X-Env: canary` reached
`backend-b`, repeatably.

## Scheduling and orchestration

### Gang scheduling

Distributed training needs all-or-nothing admission: a job that gets half its workers holds
accelerators without making progress. The platform runs a gang scheduler as an ordinary
workload.

Kueue v0.19.4 installs and runs on a tenant cluster. With a `ClusterQueue` holding a two-CPU
quota, the behaviour in both directions is what the requirement asks for.

A job that fits is admitted whole:

| Job | Request | Result |
|---|---|---|
| two pods, 500m each | 1 CPU of 2 | `Admitted=True`, 2/2 pods Running |
| four pods, 1 CPU each | 4 CPU of 2 | suspended, **0 pods**, quota not reserved |

The second case is the point. The job is not partially started — it does not take two of its
four slots and wait, which would hold accelerators without making progress. Kueue reports why:

```
insufficient quota for cpu in flavor default-flavor ...
current podset request (4) > maximum capacity (2)
```

### Scaling node pools with accelerators

A node pool of a tenant cluster is a Cluster API `MachineDeployment` driven by
cluster-autoscaler, and the pool declares its own bounds:

```yaml
minReplicas: 0
maxReplicas: 10
gpus:
  - name: nvidia.com/AD102GL_L40S
```

`minReplicas` and `maxReplicas` are the autoscaler's floor and ceiling for that pool. Because
the accelerator is declared on the pool, a pool of accelerator nodes scales in response to pods
pending for that accelerator, and scales back to its floor — including to zero — when they are
gone.

One piece of per-pool tuning matters for accelerator nodes specifically, because they boot
slowly:

```yaml
maxNodeProvisionTime: "30m"
```

This is rendered onto the `MachineDeployment` as the
`cluster.x-k8s.io/autoscaling-options-maxnodeprovisiontime` annotation, overriding the
autoscaler's default for that pool alone. Set it above the slowest healthy join — the disk
image import, the guest boot and the CNI rollout — or the autoscaler will ask for a replacement
for capacity already on its way.

### Pod autoscaling

Horizontal Pod Autoscaler is part of the conformant Kubernetes control plane. Vertical Pod
Autoscaler ships as an addon:

```yaml
addons:
  verticalPodAutoscaler: {}
```

Scaling on custom and external metrics is served from the platform monitoring stack described
below, so an inference deployment can scale on queue depth or token throughput rather than only
on CPU.

## Observability

### Accelerator metrics

The GPU Operator addon deploys the NVIDIA DCGM exporter, which publishes utilization, memory
use, temperature and power in Prometheus exposition format. The monitoring agents addon scrapes
it:

```yaml
addons:
  monitoringAgents:
    enabled: true
```

### Metrics from AI workloads

The same addon deploys VMAgent, which discovers targets through the standard `ServiceMonitor`
and `PodMonitor` resources. Any workload exposing Prometheus-format metrics is collected
without platform-specific configuration — which covers the metrics model servers publish, such
as vLLM's queue depth, batch size and token counters.

## Security

### Isolation of accelerator access

Accelerator access is mediated by the Kubernetes device plugin framework rather than by
privileged access to device nodes. Device files, libraries and environment are injected into
the container by the runtime through the Container Device Interface, on the basis of what the
scheduler allocated.

Tenant clusters add a second boundary that a single-cluster platform does not have. Each
tenant's workers are separate virtual machines with their own kernel, so an accelerator
attached to one tenant's node pool is not addressable from another tenant's workload even in
the presence of a container escape.

## Operators

### Running a complex AI operator

AI tooling arrives as operators with custom resources, webhooks and controllers. The
requirement is that at least one such operator installs and reconciles reliably.

Two were installed on a tenant cluster, and together they cover the requirement in full.

**Kueue v0.19.4** satisfies all three parts. Its controller runs; it installs both a
`MutatingWebhookConfiguration` and a `ValidatingWebhookConfiguration` with their serving
service; and its own custom resources — `ClusterQueue`, `LocalQueue`, `Workload` — reconcile.
The webhooks are not merely present but demonstrably operational: admission of a `batch/v1`
Job is what sets that Job's `suspend` field, which is the mechanism behind the gang scheduling
result above. Kueue's webhook set also covers Ray, Kubeflow, JobSet and AppWrapper resources,
which is a fair indication of how much of the AI ecosystem it interposes on.

**KubeRay v1.7.0** is recorded as a second, independent example of reconciliation. The operator
runs, a `RayCluster` reaches `state: ready` with its head and worker pods scheduled on separate
nodes, and the operator maintains status conditions (`RayClusterProvisioned`, `HeadPodReady`).

One honest note, because it would otherwise look like an omission: a default KubeRay v1.7.0
installation deploys no admission or conversion webhooks — no webhook configurations, no webhook
service, and `conversion.strategy: None` on its CRDs. KubeRay is a full reconciling controller
with CRDs and conditions, but the webhook part of this requirement rests on Kueue rather than on
KubeRay.

## Running the checks yourself

Every command on this page runs against a tenant cluster's kubeconfig, not the management
cluster. During an evaluation this is a reasonable thing to ask for, and nothing here requires
a special build.

The addons referenced above are fields of the `Kubernetes` application. See the
[managed Kubernetes documentation](/docs/) for the full list and their defaults.

## What AI conformance does and does not prove

It proves portability of the platform capabilities an AI workload depends on: that accelerators
are exposed through standard APIs, that a gang scheduler and an AI operator can run, that
metrics are collectable, that pools scale on accelerator demand.

It does not benchmark anything. It says nothing about how fast a model trains here, how many
tokens per second a server sustains, or how a cluster is sized, secured or operated. It does
not certify the catalog around the Kubernetes clusters — the virtual machines, the managed
databases — and it does not certify any particular model or framework.

Certification is granted per product, per version and per configuration, and is valid for one
year.

## Notes

Verified on 12 September 2026 against a tenant Kubernetes cluster at v1.35.6 on a Cozystack
v1.6.1 installation. Kueue v0.19.4 and KubeRay v1.7.0 were installed for the scheduling and
operator requirements and removed afterwards; everything else on this page is platform
configuration rather than an addition to the cluster. The submission is filed for Kubernetes v1.35, matching the base
Kubernetes conformance submission at
[`v1.35/cozystack`](https://github.com/cncf/k8s-conformance/tree/master/v1.35/cozystack).

Until the submission is accepted and published in the CNCF repository, this page reports
conformance results rather than a completed certification, and makes no claim to the mark.

"Certified Kubernetes AI Platform" and the associated logos are marks of The Linux Foundation,
licensed to the participant that certified a platform, for that platform and version. Nothing
here is a certification, a grant of that mark, or a claim that the Cozystack project holds one.
