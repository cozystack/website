---
title: "Cozyhr: How We Simplified Local Development with Helm and Flux"
slug: cozyhr-how-we-simplified-local-development-with-helm-and-flux
date: 2025-06-18
author: "Andrei Kvapil"
description: "Hi! I'm Andrei Kvapil CEO of Ænix and developer of Cozystack, an open source platform and framework for building cloud infrastructure. In…"
aliases:
  - /blog/cozypkg-how-we-simplified-local-development-with-helm-and-flux/
---

### Cozyhr: How We Simplified Local Development with Helm and Flux

Hi! I’m Andrei Kvapil CEO of Ænix and developer of Cozystack, an open source platform and framework for building cloud infrastructure. In this article I’ll walk through the way we deliver applications to Kubernetes, explain why regular GitOps can be awkward in local development, an show how the new tool [cozyhr](https://github.com/cozystack/cozyhr) fixes those pain points. The article targets engineers who already know Helm and Flux.

![](https://cdn-images-1.medium.com/max/800/1*St3iowqHrppmH_dV7mqDCQ.png)

First, I’ll introduce Cozystack, as it’s important for the context. Cozystack is a cloud platform that lets you run and offer managed services — databases, VMs, Kubernetes clusters, and more. Cozystack takes care of the full life‑cycle of every service.

Cozystack exposes many infrastructure services and an interface for requesting them via the Kubernetes API. Each service starts with ready‑made configs, built‑in monitoring and alerts. Some services are IaaS (such as managed Kubernetes and VMs), others are PaaS (DBaaS, queues, S3 buckets, and so on).

![](https://cdn-images-1.medium.com/max/800/1*InvDol94MrQaW9uQtE8TbA.png)

The platform itself is built on top of Kubernetes, also employing a host of free/open-source cloud‑native components. These include Kubernetes operators, a storage system, a networking fabric, and a custom image for Talos Linux including a pinned kernel version and pre‑loaded modules that guarantee stable operation for all components.

![](https://cdn-images-1.medium.com/max/800/1*TorLYCH01rC0-HiIZbX8pw.png)

Flux handles the delivery of those components. In practice the platform uses only the Helm Controller part of Flux, which installs Helm charts via `HelmRelease` custom resources.

Although every service has its own CRD kind, under the hood each one is just an isolated Helm chart that defines the user interface (both UI and API) for creating resources.

We divide our charts into three categories:

- [core charts](https://github.com/cozystack/cozystack/tree/main/packages/core) are the platform’s fundamental pieces that define its logic.  
  These are used to install, test, and configure all other charts.  
  The key chart, `platform`, contains Flux settings and is reconciled every minute, adjusting to changes in the cluster.
- [system charts](https://github.com/cozystack/cozystack/tree/main/packages/system) are components installed only once per cluster: CSI, CNI, KubeVirt, various operators, Cluster API, and so on.
- [apps charts](https://github.com/cozystack/cozystack/tree/main/packages/apps) are tenant‑level charts that end users install in their own namespaces. They expose only the minimally required parameters in `values.yaml` and use the [Cozystack API](https://blog.aenix.io/cozystack-v0-18-d724cd6d2fa1) to create higher-level Kubernetes resources. Those then spawn lower‑level custom resources (CRs) for Kubernetes operators which, in turn, which run and manage the actual applications.

With this scheme we got a simple and unified way to define almost any application. It’s applicable both for cluster configuration and for building our own Kubernetes distribution.

### Cozy Flow: How Cozystack Development is Organised

In Cozystack, all components live in a single repo that stores their common configuration and templating.  
To keep maintenance painless we follow a few principles. The key principle is that every component is a Helm chart.

For system components we use the *umbrella chart* pattern: each component’s chart has just one dependency, which is the upstream chart of the project. We include that upstream chart directly in the Cozystack repository, instead of referencing an external repository. That enables us to patch it on the fly, when we need to, and override configuration values at a higher level.

A typical component layout looks like this:

``` graf
.
├── Chart.yaml           # Chart definition and parameter docs
├── Makefile             # Common targets for local dev
├── charts               # Vendored upstream charts
├── images               # Dockerfiles / image build context
├── patches              # Optional patches for upstream
├── templates            # Extra manifests layered on top
├── values.yaml          # Our default overrides
└── values.schema.json   # JSON Schema for validation + UI hints
```

Dockerfiles may sit right inside the chart directory. After building an image, the image path and digest are automatically injected into the component’s `values.yaml`.

You’ll also notice a `Makefile` with default targets that speed up developer workflows:

``` graf
make update  # Pull the latest upstream chart & versions
make image   # Build Docker images used by the package
make show    # helm template (render manifests)
make diff    # Diff rendered output vs live cluster objects
make apply   # Install/upgrade the HelmRelease into the cluster
```

So a developer can upgrade a chart, build its image, review the diff and deploy to a cluster for integration tests in seconds.

> *The show / diff / apply pattern first appeared in* [Ksonnet](https://github.com/ksonnet/ksonnet/blob/master/docs/concepts.md) *and lives on in Jsonnet tools like Qbec and Grafana Tanka. We borrowed the best bits but kept Helm, which is far more common in the Kubernetes world.*

After testing, the change is committed and the reviewer can inspect the rendered manifests in the PR.  
When making a release we package all Helm charts into a container image and run tests. Once they pass, a distributive is published, ready for installing on other clusters.

### Technical Implementation

All these Makefiles are quite simple on the inside. Originally each `make` target was a thin shell script: it pulled data from Flux CRs in the cluster, turned them into `values.yaml`, then called Helm.

We used the [helm-diff](https://github.com/databus23/helm-diff) plugin, which shows a neat diff showing what would change in the cluster. Another script, [fluxcd-kustomize.sh](https://github.com/cozystack/cozystack/blob/release-0.31/scripts/fluxcd-kustomize.sh), post‑processed the output to add Flux annotations so that `helm diff` showed only real changes.

At some point we wanted a single tool that did all of that.  
Enter `cozyhr` — a tiny Go binary (5× smaller than `kubectl`!) that wraps the functionality of multiple other tools: Helm, `helm-diff`, `flux` CLI, `kubectl`, and our own Flux post-processor.

![](https://cdn-images-1.medium.com/max/800/1*lhDT9REuXI-MRj0aHYJyIg.png)

`cozyhr` is focused on *local* chart development and integrates tightly with Flux.  
The default assumption is that you run it from the chart directory.

Here’s the list of all available `cozyhr` commands:

``` graf
$ cozyhr --help
Cozy wrapper around Helm and Flux CD for local development
```

``` graf
Usage:
  cozyhr [command]
```

``` graf
Available Commands:
  apply       Upgrade or install the HelmRelease and sync status
  completion  Generate shell‑autocomplete script
  delete      Uninstall the release
  diff        Show live vs desired manifests
  get         Get one or many HelmReleases
  list        List HelmReleases
  reconcile   Trigger Flux reconciliation
  resume      Resume a suspended release
  show        Render manifests (helm template)
  suspend     Suspend a release (Flux stops reconciling)
  version     Print version
```

When you deploy local changes, `cozyhr` auto‑sets `suspend: true` on the `HelmRelease` to avoid a race with Flux. To re‑enable Flux, run `cozyhr resume`.

We also wanted to improve how charts are processed. For that, we enabled `cozyhr` to add proper `conditions` into the statuses of `HelmRelease` resources, so other dependent releases no longer have to wait for Flux and get the correct status immediately.

> *We use such composite charts to deploy resources into tenant clusters. For example, one* *`HelmRelease`* *can spawn a batch of child releases that install components in the user’s cluster.*

### Looking Ahead

You might ask, “Why not name the tool `cozyctl`?"

The answer is that Cozystack positions itself as a platform that exposes high‑level resources, ones of `kind: Kubernetes`, `kind: Postgres`, and `kind: VirtualMachine`. End users operate the higher‑level API and never have to touch Helm. We therefore decided to save `cozyctl for a future tool aimed at those resources. `cozyhr\`, in contrast, stays low‑level and is primarily for developers who use Helm and Flux in their own projects.

Right now we’re actively modularising Cozystack and plan to expand the framework so you can plug in your own repo and offer management services powered by Cozystack.  
`cozyhr` is one of the steps toward shipping an example repo and a ready‑made development flow for Cozystack plugins.

### Conclusion

With `cozyhr`, we accumulate our experience in accelerating development in a single tool and share our approach with the community.

We welcome feedback and pull requests: [https://github.com/cozystack/cozyhr](https://github.com/cozystack/cozyhr)

*Happy coding & stay cozy!*

### Join the Cozystack Community

- [Telegram](https://t.me/cozystack)
- [Slack](https://kubernetes.slack.com/archives/C06L3CPRVN1) (in the [Kubernetes Slack](https://communityinviter.com/apps/kubernetes/community))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)

### See also

- [How Cozystack Was Born: The Philosophy Behind Its Architecture](https://t.me/aenix_io/219)
- [How we built a dynamic Kubernetes API Server for the API Aggregation Layer in Cozystack](https://blog.aenix.io/how-we-built-a-dynamic-kubernetes-api-server-for-the-api-aggregation-layer-in-cozystack-15709a183c86?source=collection_home---4------9-----------------------)
- [DIY: Create Your Own Cloud with Kubernetes (3-part series)](https://blog.aenix.io/diy-create-your-own-cloud-with-kubernetes-part-1-7a692c37f0a8)
- [Cozystack joins the CNCF Sandbox](https://t.me/aenix_io/192)
- [Cozystack Recognized in CNCF’s CNAI Landscape!](https://blog.aenix.io/cozystack-recognized-in-cncfs-cnai-landscape-331f892b9639)
- [A Simple Way to Install Talos Linux on Any Machine, with Any Provider](https://blog.aenix.io/a-simple-way-to-install-talos-linux-on-any-machine-with-any-provider-c652b35b902e)
- [The Evolution of Virtualization Platforms: The Rise of Managed Services and Local Providers’ Edge Against Hyperscalers](https://blog.aenix.io/the-evolution-of-virtualization-platforms-the-rise-of-managed-services-and-local-providers-edge-0cb5db21a330)

### Recorded talks by Andrei Kvapil

- [GPU-Powered AI on VMs, Kubernetes &amp; Bare Metal with Cozystack](https://www.youtube.com/watch?v=slQxsj6Oj4M)
- [Journey to Stable Infrastructures with Talos Linux &amp; Cozystack | Andrei Kvapil | SREday London 2024](https://www.youtube.com/watch?v=uhXujtTzG44)
- [Talos Linux: You don’t need an operating system, you only need Kubernetes / Andrei Kvapil](https://www.youtube.com/watch?v=9CIMTum9bTA)
- [Comparing GitOps: Argo CD vs Flux CD, with Andrei Kvapil | KubeFM](https://www.youtube.com/watch?v=4RVe32xRITo)
- [Cozystack on Talos Linux](https://www.youtube.com/watch?v=s79VqXu-eG4)
- [Kubernetes is the new Skynet or the rise of Kubernetes automation: CNCF webinar](https://www.youtube.com/watch?v=9LSwnr31t7Y)
