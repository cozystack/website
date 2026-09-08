---
title: "Application Marketplace"
linkTitle: "Marketplace"
description: "Extend the Cozystack application catalog with external repositories using the PackageSource model and the cozypkg CLI."
weight: 48
---

The Cozystack marketplace lets an administrator extend the built-in application catalog with applications published in external repositories. Connecting a repository to a cluster makes its applications available to install; once one is installed, it appears in the same dashboard catalog and behaves like the standard managed applications platform users already know.

A repository is a self-contained, versioned bundle published as an OCI artifact. It is authored and validated with the `cozypkg` CLI, connected to a cluster with a single command (or from the dashboard), and, optionally, listed in a community index so operators can discover it.

{{% note %}}

The marketplace is built on the `PackageSource` model, a newer mechanism alongside the Git-and-HelmRelease bootstrap described in [Adding External Applications]({{% ref "/docs/next/applications/external" %}}). The two coexist on a cluster; the existing External-Apps pipeline is untouched.

{{% /note %}}

## How it works

A marketplace repository ships one or more `PackageSource` resources. Each `PackageSource` declares variants and components, and every component is a Helm chart. A user-installable application takes two of them: the application chart itself, and a paired registration chart whose `ApplicationDefinition` advertises the application to the Cozystack API and dashboard.

The lifecycle has two sides:

- **Publishing** turns a repository into an OCI artifact: `cozypkg init` scaffolds it, `cozypkg validate` lints it offline, and `cozypkg push` bundles the `packages/` tree into a single versioned artifact in any OCI registry.
- **Connecting** registers that artifact on a cluster: `cozypkg tap` (or the dashboard) creates a Flux `OCIRepository` and materializes the repository's `PackageSource` resources. `cozypkg add` then installs individual applications from the connected repository, and they show up in the catalog.

## Key objects

| Object | Group | Role |
| --- | --- | --- |
| `PackageSource` | `cozystack.io/v1alpha1` | Declares a repository's variants and components. |
| `ApplicationDefinition` | `cozystack.io/v1alpha1` | Registers a component as a user-installable application in the API and dashboard. |
| `Tap` | `core.cozystack.io/v1alpha1` | Virtual resource backing the dashboard "Repositories" view: connect, list, and disconnect repositories. |
| `OCIRepository` | `source.toolkit.fluxcd.io/v1` | Flux source Cozystack creates for a connected repository's artifact. |

A connected repository keeps its own declared `PackageSource` name. If that name would collide with a core component or with another connected repository, the connect is rejected instead of overwriting it, so an external repository cannot take over an official `PackageSource`. Only the name is compared: the `ApplicationDefinition` resources a repository registers are not checked against the core catalog.

## Trust model

Installing an application from a connected repository runs its charts in your management cluster, so connect only sources you trust. (Tapping itself installs nothing; it registers the source.)

Connecting is a standing subscription rather than a one-time fetch. Both connect paths create an `OCIRepository` pinned to a **tag**, with `interval: 5m`, so Flux re-resolves that tag every five minutes and a new revision behind it is pulled and its `PackageSource` resources re-applied. Whoever controls the tag controls what your cluster reads from then on: re-pushing the same tag reaches every connected cluster within the interval. `cozypkg tap` rejects digest references, so pinning an immutable digest at connect time is not an option.

Signature verification happens at **publication** time, not at connect time. `cozypkg tap` validates an artifact's structure before it creates anything; the dashboard connect flow does not, it verifies the artifact's digest and reads the `PackageSource` resources out of it, and a broken chart surfaces later as a failed install. Neither verifies a cosign signature, and neither sets `spec.verify` on the `OCIRepository`. The verification point is the community index CI gate, which pins each release to the entry's recorded cosign identity; it attests the artifact as of the moment the entry merged, not whatever the tag resolves to later.

Setting `spec.verify` on the `OCIRepository` in `cozy-system` by hand is what closes that gap: Flux then checks the signature on every pull, including the ones the interval triggers. Connecting the same repository again from the dashboard replaces the source's whole spec and drops the field, so re-add it after a reconnect. See [Publishing a Repository]({{% ref "/docs/next/marketplace/publishing" %}}#the-community-index) for the publication side.

## Where to go next

- [Publishing a Repository]({{% ref "/docs/next/marketplace/publishing" %}}): scaffold, validate, push, and list a repository in the community index.
- [Connecting a Repository]({{% ref "/docs/next/marketplace/connecting" %}}): discover, connect, install, and disconnect repositories on a cluster.
- [`cozypkg` Reference]({{% ref "/docs/next/marketplace/cozypkg" %}}): every command and flag.
