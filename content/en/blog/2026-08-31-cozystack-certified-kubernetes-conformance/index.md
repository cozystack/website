---
title: "Cozystack Is Certified Kubernetes: v1.35 and v1.34 in the CNCF Conformance Record"
slug: cozystack-certified-kubernetes-conformance
date: 2026-08-31
author: "Timur Tukaev"
description: "Tenant Kubernetes clusters created by Cozystack pass the CNCF conformance suite in full on five releases, and the v1.35 and v1.34 results are accepted into the CNCF conformance record."
images:
  - "k8s-conformance.png"
article_types:
  - news
topics:
  - kubernetes
  - platform
---

{{< figure src="k8s-conformance.png" alt="Cozystack is Certified Kubernetes — conformance results for Kubernetes v1.31 to v1.35" width="720" >}}

Cozystack is now listed as a Certified Kubernetes distribution. The conformance results for
Kubernetes v1.35 and v1.34 are accepted and published in the CNCF conformance repository, at
[`v1.35/cozystack`](https://github.com/cncf/k8s-conformance/tree/master/v1.35/cozystack) and
[`v1.34/cozystack`](https://github.com/cncf/k8s-conformance/tree/master/v1.34/cozystack).

The tested artifact is the tenant Kubernetes cluster a user creates from the catalog. Clusters
on five releases, from v1.31 to v1.35, ran the full suite with Sonobuoy in
`certified-conformance` mode on a Cozystack v1.6.1 installation, and every run finished with
zero failed tests.

Conformance answers the question every evaluation starts with: is this real Kubernetes? A
conformant cluster runs standard manifests, Helm charts and operators without a vendor dialect.
Passing on older releases matters too — when migrating from an existing platform, you can move
onto Cozystack at the Kubernetes version you run today and upgrade later on your own schedule.

Hikube, a hosted platform built on Cozystack, holds its own CNCF listings for v1.35, v1.34 and
v1.33.

The full results and methodology are on the
[Kubernetes Conformance](/compliance/kubernetes-conformance/) page.

## Join the community

- [Cozystack on GitHub](https://github.com/cozystack/cozystack)
- Telegram [group](https://t.me/cozystack)
- Slack [group](https://kubernetes.slack.com/archives/C06L3CPRVN1) (Get invite at [https://slack.kubernetes.io](https://slack.kubernetes.io))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
