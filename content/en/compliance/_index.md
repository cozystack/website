---
title: "Compliance on Kubernetes: PCI DSS, GDPR, DORA, CIS, Conformance"
linkTitle: "Compliance"
description: "How Cozystack supports PCI DSS, GDPR, DORA and the CIS Benchmark, plus CNCF Kubernetes and AI Conformance: which controls the platform provides by default, which are opt-in, and which stay with you."
type: "page"
weight: 45
---

Auditors do not certify a platform. They certify the environment you build on it, so the
honest question is not "is Cozystack compliant" but "which controls does Cozystack give me,
and which ones remain mine".

These pages answer that question one framework at a time. Each of them separates what the
platform enforces by default, what it can enforce once you turn it on, and what no
infrastructure product can do for you.

Cozystack is open source, so every claim on these pages points at code, documentation or a
command you can run against your own cluster.

## Frameworks

- **[PCI DSS](/compliance/pci-dss/)** — a requirement-by-requirement mapping of what
  Cozystack enforces by default, what is opt-in, and what stays with you, with commands to
  verify each control on your own cluster.
- **[GDPR](/compliance/gdpr/)** — the Article 32 technical measures the platform supplies,
  where personal data physically sits, and the awkward parts of erasure nobody should gloss
  over.
- **[CIS Benchmark](/compliance/cis-benchmark/)** — a full kube-bench run against Cozystack
  on Talos Linux, with every failure sorted into real deviations, controls met another way,
  and checks that do not apply.
- **[DORA](/compliance/dora/)** — resilience, backup and restore, incident evidence, and the
  ICT third-party risk chapter where an open platform on your own hardware changes the
  answer.
- **[Kubernetes Conformance](/compliance/kubernetes-conformance/)** — CNCF conformance results
  for both shapes the platform is used in: a self-hosted cluster passing 446 of 446, and a
  hosted platform listed in the CNCF record for three releases.
- **[AI Conformance](/compliance/ai-conformance/)** — all twelve requirements of the CNCF
  Kubernetes AI Conformance programme met and the v1.35 self-assessment merged into the CNCF
  record, with the mechanism and a command behind each: DRA, GPU Operator and MIG/HAMi sharing,
  GPUs across the VM boundary, Gateway API inference routing, Kueue gang scheduling, and
  accelerator metrics.
