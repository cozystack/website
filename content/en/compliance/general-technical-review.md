---
title: "CNCF General Technical Review of Cozystack"
linkTitle: "General Technical Review"
description: "The CNCF General Technical Review for Cozystack: how the platform is planned, installed, upgraded and operated, what was measured on a reference bench, and which gaps are still open."
date: 2026-09-29
type: "page"
weight: 50
---

**Cozystack has completed the CNCF General Technical Review (GTR).** The review is the
technical half of the due diligence a project goes through on its way from Sandbox to
Incubation. Where conformance programmes ask whether a platform behaves as a standard says it
should, the GTR asks the questions an operator asks before trusting a platform in production:
how it is installed, how it is upgraded and rolled back, what it costs to run, how it fails,
and how security issues are found and fixed.

The questionnaire is answered in full and kept in the project repository as
[`GENERAL_TECHNICAL_REVIEW.md`](https://github.com/cozystack/cozystack/blob/main/GENERAL_TECHNICAL_REVIEW.md).
A dated snapshot is filed with the CNCF Technical Oversight Committee in
[cncf/toc#2305](https://github.com/cncf/toc/pull/2305), alongside the Cozystack
[incubation application](https://github.com/cncf/toc/issues/1916). This page summarises what
the review records; the document itself is the source of every figure below.

## What the review covers

The template follows the life of a platform in three phases, and each answer points at code,
documentation or a measurement rather than at intentions.

- **Day 0, planning** — scope, target users, architecture, dependencies, API design, release
  process, installation and the security posture of the project.
- **Day 1, installation and deployment** — enabling and removing the platform in a live
  cluster, resource cleanup, and upgrade and rollback planning.
- **Day 2, operations** — scalability limits, observability, dependency management,
  troubleshooting, compliance and security response.

The review is answered for Cozystack v1.6.3, the latest stable release at the time of
submission.

## Deployment model

One correction to a common assumption is worth stating first, because the review makes it
explicit: **Cozystack is not Talos-only.** Talos Linux is the recommended path, where the
platform owns the nodes and they run immutable, with no SSH and no shell. The same platform
also installs on generic Linux — Ubuntu, Debian, RHEL, Rocky or openSUSE — through the
Ansible collection, which bootstraps k3s, and onto an existing Kubernetes cluster. Every path
recommends at least three servers.

## Measured on a reference bench

The questions about overhead, scale and upgrades were answered by running the platform rather
than by estimating. The bench was three servers with 32 vCPU and 128 GB of memory each,
installed on the generic Linux path.

| What was measured | Result |
|---|---|
| Idle platform overhead | about 1 CPU core and 19 GiB of memory across all three nodes, before any tenant workload |
| Concurrent managed databases | 71 PostgreSQL instances, each with a replicated volume, with no failures and no node pressure |
| Mixed load across application types | about 76 applications and 402 pods — tenants, VMs, Redis, MariaDB, ClickHouse, Kafka — all Ready |
| Upgrade to the next patch release | converged in about 175–200 seconds |
| Downgrade back | converged in about 250 seconds |
| Data across upgrade and downgrade | every replicated volume survived all four version changes |

The ceiling the bench reached was not compute, memory or storage. It was the kubelet
`max-pods` limit and the throughput of the Flux helm-controller — and when the helm-controller
became congested, Cozystack's shard operator added a second shard on its own. The review also
records one upgrade-time hazard found on the bench: after a control-plane node is replaced,
the address of the original node must be repointed in the CNI configuration, or service
networking can drop during the next reconcile.

## Security

The review is filed together with the Cozystack
[security self-assessment](https://github.com/cozystack/cozystack/blob/main/docs/security/self-assessment.md),
[threat model](https://github.com/cozystack/cozystack/blob/main/docs/security/threat-model.md)
and [incident-response process](https://github.com/cozystack/cozystack/blob/main/docs/security/incident-response.md).
It describes how vulnerabilities reach the project and how fast they are handled:

- reports arrive through GitHub private vulnerability reporting, handled by a security
  response team drawn from more than one organisation and more than one country;
- every repository in the organisation is scanned with Trivy for vulnerable dependencies and
  container images — critical findings every six hours, the rest weekly — and each actionable
  finding becomes a tracked issue;
- a rotating Security Champion owns the triage clock and runs a weekly pass;
- monthly aggregate reports are published in
  [`docs/security/reports/`](https://github.com/cozystack/cozystack/tree/main/docs/security/reports),
  with identifiers withheld until a fix has shipped.

## What is still open

A review that lists only strengths is not useful to anyone evaluating a platform, and this one
records its gaps plainly:

- release images are not yet signed, build provenance is disabled, and SBOM generation is
  implemented but off by default;
- there is no published API stability and deprecation policy — the application API group is
  still `v1alpha1`;
- there is no top-level `NOTICE` file aggregating attribution for the bundled components;
- no default Kubernetes audit policy ships with the platform;
- the scheduled full end-to-end test run has been unreliable, so coverage rests on the
  per-pull-request end-to-end job;
- the upgrade matrix still needs a pristine three-node rerun and a run on the Talos path.

Each of these is tracked in the open, and the review links to the issue where one exists.

## Related results

- [Kubernetes Conformance](/compliance/kubernetes-conformance/) — tenant clusters pass the
  CNCF conformance suite in full, with v1.35 and v1.34 in the CNCF record.
- [AI Conformance](/compliance/ai-conformance/) — all twelve requirements of the CNCF
  Kubernetes AI Conformance programme met, with the v1.35 self-assessment accepted.

## Notes

The review follows version 1.0 of the CNCF
[General Technical Review template](https://github.com/cncf/toc/blob/main/toc_subprojects/project-reviews-subproject/general-technical-questions.md).
Bench measurements were taken on 18–19 September 2026 on the generic Linux path with the
`isp-full-generic` variant.
