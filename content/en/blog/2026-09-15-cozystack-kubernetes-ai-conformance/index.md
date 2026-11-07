---
title: "Cozystack Passes CNCF Kubernetes AI Conformance"
slug: cozystack-kubernetes-ai-conformance
date: 2026-09-15
author: "Timur Tukaev"
description: "Tenant Kubernetes clusters created by Cozystack meet all twelve requirements of the CNCF Kubernetes AI Conformance programme, and the v1.35 self-assessment is accepted into the CNCF record."
images:
  - "ai-conformance.png"
article_types:
  - news
topics:
  - kubernetes
  - gpu
  - platform
---

{{< figure src="ai-conformance.png" alt="Cozystack passes Kubernetes AI Conformance — all twelve CNCF requirements met" width="720" >}}

Cozystack meets all twelve requirements of the CNCF Kubernetes AI Conformance programme. The
v1.35 self-assessment, filed by Ænix for Cozystack v1.6.1, is accepted and published in the
CNCF repository at
[`v1.35/cozystack`](https://github.com/cncf/k8s-ai-conformance/tree/main/v1.35/cozystack).

Base Kubernetes conformance answers "is this real Kubernetes". AI conformance answers a more
practical question: will an AI workload that runs on one conformant platform run here too,
without platform-specific workarounds.

The requirements span accelerators, networking, scheduling, observability, security and
operators. On a tenant Kubernetes cluster, Cozystack covers them with:

- the Dynamic Resource Allocation API and the NVIDIA GPU Operator as a cluster addon;
- GPU sharing through MIG partitions or HAMi time-slicing;
- GPUs attached to virtual worker nodes, declared in the node pool definition;
- Gateway API with weighted and header-based routing for model serving;
- gang scheduling with Kueue and node pools that scale on GPU demand, down to zero;
- accelerator and workload metrics collected through DCGM and VMAgent.

Because tenant workers are separate virtual machines with their own kernel, a GPU attached to
one tenant's node pool is not reachable from another tenant's workloads.

Each requirement, the mechanism behind it and the command that verifies it are on the
[AI Conformance](/compliance/ai-conformance/) page.

## Join the community

- [Cozystack on GitHub](https://github.com/cozystack/cozystack)
- Telegram [group](https://t.me/cozystack)
- Slack [group](https://kubernetes.slack.com/archives/C06L3CPRVN1) (Get invite at [https://slack.kubernetes.io](https://slack.kubernetes.io))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
