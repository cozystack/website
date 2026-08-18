---
title: "Compliance on Kubernetes: PCI DSS and Security Benchmarks"
linkTitle: "Compliance"
description: "How Cozystack supports PCI DSS and other compliance work: which controls the platform provides by default, which are opt-in, and which stay with you."
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
- **[CIS Benchmark](/compliance/cis-benchmark/)** — a full kube-bench run against Cozystack
  on Talos Linux, with every failure sorted into real deviations, controls met another way,
  and checks that do not apply.
- **[Kubernetes Conformance](/compliance/kubernetes-conformance/)** — what CNCF conformance
  proves, where Cozystack-based clusters appear in the CNCF results, and how to run the
  suite yourself.
