---
title: "CNCF Kubernetes Conformance and Cozystack"
linkTitle: "Kubernetes Conformance"
description: "What CNCF conformance testing proves, where Cozystack clusters appear in the CNCF results, and how to run the Sonobuoy conformance suite yourself."
date: 2026-08-18
type: "page"
weight: 30
---

**Kubernetes clusters created by Cozystack have passed the CNCF conformance suite on three
consecutive Kubernetes releases, and the runs are in the CNCF's public record — submitted by
a vendor, against its own installation, as the program requires.** Conformance answers a
narrow but important question: is this real Kubernetes, or something Kubernetes-shaped? A
conformant cluster runs standard manifests, Helm charts and operators without a vendor
dialect. It is not a property the project carries by itself: the CNCF certifies a named
product at a named version, and a result describes the cluster that was tested.

## What conformance actually tests

The Certified Kubernetes program is run by the CNCF. It has one test set — the end-to-end
tests in the Kubernetes source tree tagged `[Conformance]` — and one rule: a certification
run may skip none of them.

The suite checks portable behavior, and only where that behavior is generally available. Do
the core APIs behave as specified, does scheduling work, do services route, do namespaces
isolate. Alpha and beta APIs sit outside the profile, and so do most of the extension points
a real workload leans on: ingress controllers, CSI drivers and their storage classes,
LoadBalancer provisioning, NetworkPolicy enforcement, performance and hardening.

Read the badge accordingly. Conformance says *code written against the stable Kubernetes API
behaves here as the specification says it should*. It is not a promise that an arbitrary
workload runs unchanged — that depends on the extensions above, none of which a conformance
run covers. It says nothing about whether the cluster is secure, fast or well operated — for the security
posture of the platform, see [CIS Benchmark](/compliance/cis-benchmark/) and
[PCI DSS](/compliance/pci-dss/).

## Where the Cozystack conformance results are published

Conformance results are submitted as pull requests to
[cncf/k8s-conformance](https://github.com/cncf/k8s-conformance) and stay there permanently:
the test log, the machine-readable results, and a description of how to reproduce the run.

Cozystack-based clusters appear in that repository for **Kubernetes v1.33, v1.34 and v1.35**,
in the folders [`v1.33/hikube`](https://github.com/cncf/k8s-conformance/tree/master/v1.33/hikube),
[`v1.34/hikube`](https://github.com/cncf/k8s-conformance/tree/master/v1.34/hikube) and
[`v1.35/hikube`](https://github.com/cncf/k8s-conformance/tree/master/v1.35/hikube). The
submitting entity is Hidora and the certified product is Hikube. The Cozystack project is not
a party to those submissions, does not certify products, and has no listing of its own — the
program certifies products, not upstream projects. Each folder holds the full `e2e.log` and
`junit_01.xml` from the run, and the reproduction steps use the platform's own API:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Kubernetes
metadata:
  name: my-first-cluster
  namespace: tenant-example
spec:
  controlPlane:
    replicas: 3
  nodeGroups:
    general:
      minReplicas: 1
      maxReplicas: 5
      instanceType: "u1.xlarge"
  storageClass: "replicated"
```

That is the same resource a tenant creates from the catalog, and it is worth being precise
about which cluster the results describe: a tenant Kubernetes cluster, whose control plane
runs as Kamaji Deployments on the management cluster. The management cluster Cozystack itself
runs on is a separate Kubernetes and was not the subject of these runs — for that one, see the
[CIS Benchmark](/compliance/cis-benchmark/) page, which covers the management cluster only.
The two pages measure different clusters on purpose.

Certification is awarded to a named product and version, not to an upstream project, so the
listings carry the names of the entities that submitted them. The program has three
categories — Distribution, Hosted Platform and Installer — and the Cozystack-based
submissions are filed as `hosted`, meaning the certified artifact is an operated offering
rather than software you download and install yourself. If your own procurement requires a
certified product, check the listing for that exact product and version: running Cozystack
yourself does not transfer someone else's certification to your installation.

## How to run the Kubernetes conformance suite with Sonobuoy

Any Cozystack installation can be tested with the same suite. The tooling is
[Sonobuoy](https://github.com/vmware-tanzu/sonobuoy), which runs the suite inside the cluster
and collects the artifacts a submission needs.

```bash
sonobuoy version    # record it — the tool version is part of the evidence
kubectl version     # the conformance image must match the cluster's minor version

sonobuoy run \
  --mode=certified-conformance \
  --plugin e2e \
  --kube-conformance-image registry.k8s.io/conformance:v1.34.3 \
  --wait
outfile=$(sonobuoy retrieve)
sonobuoy results "$outfile"
sonobuoy delete --wait
```

Two things are worth knowing before you start.

**Use `--mode=certified-conformance`, and understand what it switches back on.** The default
mode skips tests tagged `[Disruptive]` and the NoExecuteTaintManager cases; certified mode
runs them, because a run with skipped tests is not a valid certification run. Those tests
taint nodes, evict pods and restart components deliberately, and they run serially — which is
why a certified run takes far longer than a default one.

**Pass `--plugin e2e` on Talos-based clusters.** Sonobuoy's default plugin set includes
`systemd-logs`, which walks every node collecting journal output. Talos Linux has no systemd,
so the plugin hangs on every node and the aggregator never reports the run complete. The
conformance tests themselves pass, but `--wait` never returns and the retrieved tarball stays
incomplete. Restricting the run to the `e2e` plugin avoids this and costs nothing for a
submission: both required artifacts, `e2e.log` and `junit_01.xml`, come from the `e2e` plugin,
and the CNCF submission asks for no `systemd-logs` output at all.

One quirk to know before you start staring at the terminal: `sonobuoy status` may sit at
`Passed: 0` with the full test count remaining for the whole run, even while tests are
finishing normally. The aggregator's progress channel is not always wired up. Follow the e2e
pod's log instead:

```bash
kubectl -n sonobuoy logs -l sonobuoy-plugin=e2e -c e2e -f
```

Expect one and a half to three hours, several hundred short-lived pods and namespaces, and at
least two schedulable worker nodes — a number of conformance tests need more than one.
Sonobuoy runs from its own namespace under a cluster-admin service account, so this is an
administrative operation on the cluster being tested, not something a tenant performs. Run it
on a cluster you can afford to disrupt, never on one carrying production traffic, and remove
the namespace afterwards with `sonobuoy delete --wait`.

For tenant Kubernetes clusters, point your kubeconfig at the tenant cluster rather than at
the management cluster: conformance describes the cluster your workloads land in.

## How to submit conformance results to the CNCF

The submission is a pull request to `cncf/k8s-conformance` containing four files: `e2e.log`
and `junit_01.xml` from the run, a `README.md` describing how to reproduce it, and a
`PRODUCT.yaml` naming the product.

One requirement in that process is organizational rather than technical: the vendor named in
`PRODUCT.yaml` must be a legal entity with a signed participation form on file with the CNCF.
The test run can be done by anyone; the listing belongs to whoever signs.

## Frequently asked questions

### Is Cozystack certified Kubernetes?

Clusters created by Cozystack have passed the CNCF conformance suite for Kubernetes v1.33,
v1.34 and v1.35, and the results are published in `cncf/k8s-conformance`. The Certified
Kubernetes mark itself is granted to a named product and version, so the listings appear
under the names of the entities that submitted them rather than under the project name.

### What does conformance guarantee?

That standard Kubernetes APIs behave as specified, so manifests, Helm charts and operators
written for Kubernetes work without modification. It is a portability guarantee, not a
security or performance one.

### Does conformance cover virtual machines and managed services?

No. KubeVirt virtual machines, managed databases and the rest of the catalog are extensions
built on custom resources, and the conformance suite does not test them. It tests the
Kubernetes underneath.

### Can we run the conformance suite on our own cluster?

Yes, and during an evaluation it is a reasonable thing to do. The commands above are the whole
procedure, the tooling is open source, and nothing in the run depends on a vendor
relationship. Publishing the result as a certification is the separate, organizational step
described above, and it is open to any legal entity with a participation form on file with
the CNCF — not to one company.

## Notes

Conformance results referenced here were published to `cncf/k8s-conformance` for Kubernetes
v1.33, v1.34 and v1.35 under the product name Hikube. A listing describes one product at one
version: Kubernetes releases newer than v1.35 are not covered by those submissions, the
program expects re-certification as releases move on, and the repository — not this page — is
the current record. The Sonobuoy guidance was checked against Cozystack v1.6 on Talos Linux in
August 2026; your installation may differ.

"Certified Kubernetes" and the Certified Kubernetes logo are marks of The Linux Foundation,
licensed to the vendor of a conformant product for the product and version it certified.
Nothing on this page is a certification, a grant of that mark, or a claim that the Cozystack
project holds one.
