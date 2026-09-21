---
title: "Kubernetes Conformance Results for Cozystack"
linkTitle: "Kubernetes Conformance"
description: "CNCF conformance results for Cozystack: self-hosted clusters passing the suite in full across five Kubernetes releases, listed in the CNCF record for two of them, and a hosted platform built on it listed for three."
date: 2026-09-12
type: "page"
weight: 30
---

**Kubernetes clusters created by Cozystack pass the CNCF conformance suite in full.** The
suite answers one narrow question, and it is the question every evaluation starts with: is
this real Kubernetes, or something Kubernetes-shaped? A conformant cluster runs standard
manifests, Helm charts and operators without a vendor dialect.

Two independent sets of results are recorded below, from the two shapes the platform is used
in — a cluster you run yourself, and a hosted platform built on it. Between them they cover
every Kubernetes release the platform offers.

## Results

### Self-hosted Cozystack

Every run below is a tenant Kubernetes cluster created from the catalog, tested with Sonobuoy
in `certified-conformance` mode against the conformance image pinned to its exact version. All
runs took place on 19 August 2026 against a Cozystack v1.6.1 installation.

| Kubernetes | Passed | Failed | Specs in suite |
|---|---|---|---|
| v1.35.6 | **441** | 0 | 7355 |
| v1.34.9 | **424** | 0 | 7144 |
| v1.33.13 | **419** | 0 | 6741 |
| v1.32.13 | **411** | 0 | 6624 |
| v1.31.14 | **404** | 0 | 6607 |

The v1.35 and v1.34 runs are **accepted and published in the CNCF conformance repository**, at
[`v1.35/cozystack`](https://github.com/cncf/k8s-conformance/tree/master/v1.35/cozystack) and
[`v1.34/cozystack`](https://github.com/cncf/k8s-conformance/tree/master/v1.34/cozystack), filed
by Ænix as a `distribution`. The programme accepts the current Kubernetes release and the two
before it, and with v1.36 current those are the newest releases the platform offers.

### Hikube, a hosted platform built on Cozystack

| Kubernetes | Result | Where |
|---|---|---|
| v1.35 | Passed | [`v1.35/hikube`](https://github.com/cncf/k8s-conformance/tree/master/v1.35/hikube) |
| v1.34 | Passed | [`v1.34/hikube`](https://github.com/cncf/k8s-conformance/tree/master/v1.34/hikube) |
| v1.33 | Passed | [`v1.33/hikube`](https://github.com/cncf/k8s-conformance/tree/master/v1.33/hikube) |

The Hikube entries are formal CNCF submissions, filed by Hidora as a `hosted` platform and
stored permanently in the CNCF's own repository with their full test logs. The two sets cover
different shapes deliberately: a distribution you install and operate, and a managed service
someone else runs for you.

The distinction between a listing and a run is worth keeping straight. A CNCF listing certifies
a named product at a named version. A conformance run tells you the software behaves as
Kubernetes should — and that is what most evaluations actually need to know.

Note the older releases. Conformance holds on v1.31 as it does on v1.35, which matters if you
are migrating from an existing platform: you can move onto Cozystack at the Kubernetes version
you run today and upgrade afterwards, on your own schedule, rather than doing both at once.
That said, v1.33 and older no longer receive upstream patches — only the three most recent
minor releases do — so treat them as a migration path, not a destination.

## The self-hosted run

Taking the most recent release as the example:

```
Ran 441 of 7355 Specs in 7202.504 seconds
SUCCESS! -- 441 Passed | 0 Failed | 0 Pending | 6914 Skipped

API server:  v1.35.6
Node health: 2/2
Pods health: 17/17
```

A tenant Kubernetes cluster provisioned from the catalog with `kind: Kubernetes`, two worker
nodes, tested with Sonobuoy in `certified-conformance` mode against the pinned conformance
image for its exact version. Not a special build and not a laboratory setup: the same
resource a tenant creates for themselves. The other four runs followed the same recipe against
their own clusters.

Two properties of the cluster mattered, and both are worth planning for rather than
discovering:

**A dedicated etcd.** By default the tenant clusters on an installation share one etcd, each
under its own key prefix. Compaction in etcd is global rather than per-prefix, so the API
server runs with `--etcd-compaction-interval=0` — compacting on behalf of one tenant would
truncate history for its neighbours. One conformance test waits for a compaction that
therefore never arrives, and fails on timeout. Giving the tenant its own etcd removes the
constraint.

**Compaction switched on.** With a dedicated etcd, set the interval explicitly through the
application spec rather than by patching the deployment:

```yaml
spec:
  controlPlane:
    apiServer:
      extraArgs:
        - --etcd-compaction-interval=5m
```

Decide both at creation time. Moving a live cluster to a different etcd is not a supported
migration and leaves the existing nodes unable to receive new pods.

## Running the suite yourself

Any Cozystack installation can be tested, and during an evaluation it is a reasonable thing to
ask for.

```bash
sonobuoy version    # record it — the tool version is part of the evidence
kubectl version     # the conformance image must match the cluster's minor version

sonobuoy run \
  --mode=certified-conformance \
  --plugin e2e \
  --kube-conformance-image registry.k8s.io/conformance:v1.35.6 \
  --wait
outfile=$(sonobuoy retrieve)
sonobuoy results "$outfile"
sonobuoy delete --wait
```

**Use `--mode=certified-conformance`, and know what it switches back on.** The default mode
skips tests tagged `[Disruptive]`; certified mode runs them, because a run with skipped tests
is not a valid certification run. Those tests taint nodes, evict pods and restart components
deliberately, and they run serially — which is why a certified run takes hours rather than
minutes.

**Pass `--plugin e2e` on Talos-based clusters.** Sonobuoy's default plugin set includes
`systemd-logs`, which walks every node collecting journal output. Talos Linux has no systemd,
so that plugin hangs and the aggregator never reports the run complete. Excluding it costs
nothing for a submission: both required artifacts come from the `e2e` plugin.

**Do not trust the progress counter.** `sonobuoy status` may sit at `Passed: 0` with the full
count remaining for an entire run while tests finish normally. Follow the e2e pod's log
instead, and remember that a quiet log is a good sign — failures are what produce output.

Expect two to three hours, several hundred short-lived pods and namespaces, and at least two
schedulable worker nodes. Point your kubeconfig at the tenant cluster rather than at the
management cluster: conformance describes the cluster your workloads land in.

## What conformance does and does not prove

The suite checks portable behaviour, and only where that behaviour is generally available. Do
the core APIs behave as specified, does scheduling work, do services route, do namespaces
isolate.

Alpha and beta APIs sit outside the profile, and so do most of the extension points a real
workload leans on: ingress controllers, CSI drivers and their storage classes, LoadBalancer
provisioning, NetworkPolicy enforcement, performance and hardening. Conformance says code
written against the stable Kubernetes API behaves here as the specification says it should. It
says nothing about whether a cluster is secure, fast or well operated — for that, see
[CIS Benchmark](/compliance/cis-benchmark/) and [PCI DSS](/compliance/pci-dss/).

It also says nothing about virtual machines, managed databases or the rest of the catalog.
Those are extensions built on custom resources, and the suite tests the Kubernetes underneath
them.

Nor does it cover what an AI workload needs from a platform beyond plain Kubernetes —
accelerator exposure, gang scheduling, accelerator metrics. That is a separate programme, and
our results for it are on the [AI Conformance](/compliance/ai-conformance/) page.

## Frequently asked questions

### Is Cozystack certified Kubernetes?

Yes, for the releases in the CNCF record. Cozystack v1.6.1 is listed as a Certified Kubernetes
distribution for Kubernetes v1.35 and v1.34, filed by Ænix and published in the CNCF's own
repository. A hosted platform built on Cozystack is listed separately for v1.33, v1.34 and
v1.35. Beyond those, clusters created by Cozystack pass the suite in full on all five Kubernetes
releases the platform offers, in the runs published here.

The Certified Kubernetes mark is granted to a named product at a named version and licensed to
the entity that submitted it, so listings appear under the names of those entities rather than
under the project name.

### Which Kubernetes versions can Cozystack run?

Tenant clusters can be created on v1.31 through v1.35. Each version is a separate conformance
run against its own cluster, and the results are in the table above. Only the three most recent
Kubernetes releases can be submitted to the CNCF — the programme accepts the current release and
the two before it — so with v1.36 current, v1.35 and v1.34 are filed and the rest are published
here.

### Does a hosted platform's certification transfer to our installation?

No. A listing describes one product at one version. Running the same open-source platform
yourself is not covered by someone else's certification — which is why the self-hosted run
above is published separately, with its own artifacts.

### Can we see the raw results?

Yes. A conformance submission consists of `e2e.log` and `junit_01.xml` from the run, and the
CNCF preserves both permanently. They are in the repository for the self-hosted
[v1.35](https://github.com/cncf/k8s-conformance/tree/master/v1.35/cozystack) and
[v1.34](https://github.com/cncf/k8s-conformance/tree/master/v1.34/cozystack) entries and for the
Hikube entries. Artifacts for the older runs are available on request.

## Notes

The self-hosted runs were executed on 19 August 2026 against a Cozystack v1.6.1 installation,
using Sonobuoy v0.57.5 in `certified-conformance` mode with the `e2e` plugin, one run per
Kubernetes version against its own tenant cluster. Passed and failed counts are taken from the
Ginkgo summary in `e2e.log`.

The v1.35 and v1.34 submissions were accepted and published in the CNCF conformance repository
on 28 August 2026. The three older runs on this page are published here rather than filed, since
the programme accepts only the three most recent Kubernetes releases.

"Certified Kubernetes" and the Certified Kubernetes logo are marks of The Linux Foundation,
licensed to the vendor of a conformant product for the product and version it certified.
Nothing here is a certification, a grant of that mark, or a claim that the Cozystack project
holds one.
