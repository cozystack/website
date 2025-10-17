---
title: "Cozystack Becomes a CNCF Sandbox Project"
slug: cozystack-becomes-a-cncf-sandbox-project
date: 2025-03-13
author: "Andrei Kvapil"
description: "On February 28, members of the CNCF Technical Oversight Committee completed their voting and unanimously accepted Cozystack, a platform for…"
---

### Cozystack Becomes a CNCF Sandbox Project

On February 28, members of the CNCF Technical Oversight Committee [completed their voting](https://github.com/cncf/sandbox/issues/322) and unanimously accepted [Cozystack](https://cozystack.io), a platform for building private clouds and PaaS, into the CNCF Sandbox. The project is currently undergoing the [onboarding process](https://github.com/cncf/sandbox/issues/351). Let’s break down what this means in practice, what Cozystack is, and what the CNCF Sandbox represents.

![](https://cdn-images-1.medium.com/max/800/1*9fPSDNGw-DholkjtUfkSMQ.png)

### What is Cozystack?

Cozystack is an open-source platform that enables the creation of a bare metal cloud for deploying proven cloud-native and open-source tools: managed Kubernetes clusters, databases as a service, applications as a service, and virtual machines based on KubeVirt (see the [full list of components](https://cozystack.io/docs/components/)). Cozystack also provides a ready-made stack for observability and alerting based on Victoria Metrics, Victoria Logs, Grafana, and Alerta.

Service and hosting providers, banks, SaaS solution vendors, medtech, fintech, AI/ML services, and other companies use Cozystack to offer customers managed services, managed Kubernetes, and databases that run directly on hardware, ensuring maximum performance and service stability. Additionally, Cozystack can be used to build geo-distributed clusters.

The platform is developed and maintained by [Ænix](http://aenix.io). The core developer and creator of Cozystack is Andrey Kvapil, known in the engineering community by the nickname “kvaps.” He is an active contributor to Linstor, KubeVirt, Kamaji, Kubernetes, Cilium, and others.

### What is CNCF Sandbox, and What Does It Mean for Users?

CNCF (Cloud Native Computing Foundation) is part of the larger Linux Foundation, a non-profit organization that supports and curates promising cloud-native projects, including Kubernetes, Envoy, Prometheus, Cilium, Istio, K3s, FluxCD, and others. The CNCF Sandbox is the “entry point” for projects that want to join the CNCF and become part of it. From there, projects progress through the stages of Incubating and Graduated.

Transferring the project to the CNCF guarantees all Cozystack users that the platform will always be available under the Apache 2.0 license and will not suffer the fate of projects like Mongo, Redis, Terraform, and Vault, whose licenses were changed to closed-source and no longer comply with the [Open Source Initiative](https://opensource.org) criteria. From this point forward, the rights to Cozystack belong to the non-profit industry organization, the CNCF.

Moreover, inclusion in the CNCF provides an opportunity to engage a broad engineering community in the development and use of Cozystack, making project management more transparent. Expanding the base of contributors and users will, in turn, significantly accelerate the platform’s development and the exploration of a wide range of use cases.

> Andrey Kvapil, CEO of Ænix and creator of Cozystack:

> “I believe in honest and genuine open source, in the tools we use to build the platform, and I am happy that we can be useful to the community. In just one year, our small team of excellent engineers, with the support of our clients and the open-source community, has created a project worthy of inclusion in the CNCF. This is truly a significant achievement. Thank you to everyone who believed in us and supported us throughout this time. We will continue to improve the platform and plan to apply for CNCF Incubating status this fall. From an engineering perspective, we are already a mature project and ready for this. The main task now is to refine the project management process and community interaction.”

> Matthew Robin, CEO & Founder of Hidora:

> *“Cozystack represents a significant advancement in simplifying complex cloud infrastructure deployment. Its integration into the CNCF Sandbox marks an important milestone that will accelerate its adoption and enrich its ecosystem through community collaboration. We are confident that Cozystack will play a key role in democratizing cloud-native technologies for businesses of all sizes.*”

> Kingdon Barrett, FluxCD & Cozystack maintainer:

> *“Cozystack combines cutting edge open source cloud native technologies in a way that I could probably set up myself, the hard way, if I wanted to spend 6 months figuring out how they fit together. It’s Talos Linux configured as a cloud on bare metal, ready in half an hour or so!”*

Ænix will continue to actively develop the platform and support both clients and community users.

### Useful Links:

- [Cozystack Website](https://cozystack.io)
- [GitHub](https://github.com/cozystack)
- [Telegram Community](https://t.me/cozystack)
- [Slack Community](https://slack.k8s.io) (registration in the [Kubernetes Slack workspace](https://communityinviter.com/apps/kubernetes/community) required)
- [Community Meeting Calendar](https://calendar.google.com/calendar/embed?src=cozystack.io)
- [Cozystack Community Meetings Recordings](https://youtube.com/cozystack)
- [Cozystack on CNCF Landscape](https://landscape.cncf.io)
- [Cozystack in CNCF Sandbox](https://www.cncf.io/sandbox-projects/)
- [Cozystack on Devstat](https://devstats.cncf.io)