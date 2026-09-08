---
title: "Connecting a Repository"
linkTitle: "Connecting"
description: "Discover, connect, install from, and disconnect external application repositories on a Cozystack cluster."
weight: 20
---

This guide is for **operators**: cluster administrators who connect external repositories and install their applications. It covers discovering repositories, connecting them from the CLI or the dashboard, installing applications, and disconnecting.

For the publisher side (packaging and pushing a repository), see [Publishing a Repository]({{% ref "/docs/next/marketplace/publishing" %}}).

## Prerequisites

- The `cozypkg` CLI (see [Install cozypkg]({{% ref "/docs/next/install/cozystack/kubernetes-distribution" %}}#2-install-cozypkg)) and a kubeconfig for the target cluster. Creating cluster-scoped resources requires cluster-admin.
- The `flux` CLI on your `PATH`. `cozypkg tap` pulls the artifact to your own machine before it creates anything on the cluster, and it shells out to `flux pull artifact` to do it. `--skip-validate` skips the validation, not the pull, so `flux` is needed either way.
- A Cozystack release that includes the marketplace. There is no switch to enable: the `taps` API and the tap materializer are always present.

{{% warning %}}

Installing an application from a connected repository runs its charts in your management cluster (tapping itself installs nothing). Connect only sources you trust, or repositories listed in a curated index whose gate verifies signatures. See the [Trust model]({{% ref "/docs/next/marketplace" %}}#trust-model).

{{% /warning %}}

## Discover repositories

`cozypkg search` queries the community index and lists matching repositories without connecting them. Point it at an index with `--index` or the `COZYPKG_INDEX` environment variable (a local directory or an `oci://` reference):

```bash
export COZYPKG_INDEX=oci://ghcr.io/cozystack/packages-index:latest
cozypkg search database
```

The community index is not published yet (see [Publishing]({{% ref "/docs/next/marketplace/publishing" %}}#the-community-index)), so the `oci://` reference above is illustrative. Until it exists, point `--index` at a local checkout of an index repository.

## Connect from the CLI

`cozypkg tap` registers a published repository. It creates a Flux `OCIRepository` pointing at the artifact and materializes the `PackageSource` resources the artifact carries under their declared names. If a name would collide with a core component or another connected repository, the tap is rejected instead of overwriting it. Only the `PackageSource` name is compared; the `ApplicationDefinition` resources the repository registers are not. Nothing is installed yet:

```bash
cozypkg tap oci://ghcr.io/acme/hello:v1.0.0
```

Tapping is idempotent. Use `--tag` to override the tag in the reference, and `--skip-validate` to skip validating the artifact structure before tapping (not recommended).

If the repository is listed in an index, you can tap it by its short name and let the index resolve the reference:

```bash
cozypkg tap acme.hello --index "$COZYPKG_INDEX"
```

### Private repositories

A private repository is pulled twice, and each pull authenticates on its own.

The first pull runs on your machine, when `cozypkg tap` fetches the artifact through the `flux` CLI. It uses the registry credentials that machine already has, so log in before tapping; otherwise the tap fails before it creates anything:

```bash
docker login ghcr.io
```

The cluster then pulls the same artifact for itself. For that, pre-create a pull-credential `Secret` in the `cozy-system` namespace and point the tap at it with `--secret`. Cozystack attaches it as the `OCIRepository`'s `secretRef`; it covers the cluster-side pull only, and `cozypkg` never reads it:

```bash
printf 'Registry token: '
read -rs REGISTRY_TOKEN
echo

kubectl create secret docker-registry acme-pull \
  --namespace cozy-system \
  --docker-server=ghcr.io \
  --docker-username=<user> \
  --docker-password="$REGISTRY_TOKEN"

unset REGISTRY_TOKEN

cozypkg tap oci://ghcr.io/acme/hello:v1.0.0 --secret acme-pull
```

Reading the token from a prompt keeps it out of your shell history. It is still visible in the process list while `kubectl` runs; where that matters, write the `dockerconfigjson` yourself and create the `Secret` from it with `--from-file`.

## Connect from the dashboard

The dashboard "Repositories" view is backed by the `Tap` resource and covers the same flow without the CLI. Open it from the sidebar, choose **Connect**, and provide the `oci://` reference and, for a private repository, the name of a pull-credential `Secret` in `cozy-system`. Connected repositories are listed with their status; a tapped repository still connecting or blocked by a name collision shows its message there, and tapped repositories can be disconnected from the same view.

One difference from the CLI: the dashboard does not run the structural validation `cozypkg tap` runs. It verifies the artifact's digest, reads the `PackageSource` resources out of it, and applies the same name-collision check, but a repository whose charts are broken connects cleanly and fails later, when an application from it is installed.

## Install applications

Once a repository is connected, install an application from it with `cozypkg add`, naming the materialized `PackageSource`. A tapped repository keeps its own declared name, so run `cozypkg list` first to see the exact name to use:

```bash
cozypkg list
cozypkg add acme.hello
```

`cozypkg add` creates a `Package` from the named `PackageSource`, plus one for every source it depends on that is not installed already. The reconciler then creates a HelmRelease for each component that carries an `install:` block, which is how the paired registration chart puts the application in the catalog. `add` needs a terminal: it asks which variant to install even when a `PackageSource` declares only one, and asks again for confirmation when a component is privileged. `--allow-privileged` answers the second question; nothing answers the first. To install without a terminal, write the `Package` manifest yourself and pass it with `-f`, which creates it directly and skips both prompts, along with the dependency resolution that comes with them.

Installed applications appear in the dashboard catalog alongside the built-in ones, and platform users deploy them the same way.

## List what is connected and installed

`cozypkg list` shows every `PackageSource` on the cluster, so the platform's own `cozystack.*` sources are listed alongside the tapped ones. `--installed` shows installed `Package` resources instead, and `--components` breaks components onto separate lines:

```bash
cozypkg list
cozypkg list --installed
```

## Disconnect

Disconnecting has two independent steps, mirroring the two connect steps.

Remove installed applications with `cozypkg del`. It deletes the named `Package` and its resources, and every installed `Package` that depends on it goes too: the command prints the whole set, requested and dependent kept apart, and asks for confirmation before it removes anything. The connected source stays in place:

```bash
cozypkg del acme.hello
```

Then remove the source itself with `cozypkg untap`. It deletes the tapped `PackageSource` (identified by its `apps.cozystack.io/marketplace-tap` marker label, not a name prefix) and refuses official sources. If a `Package` of that name is still installed it refuses and deletes nothing; pass `--yes` to untap anyway (the `Package` stays installed):

```bash
cozypkg untap acme.hello
```

The Flux `OCIRepository` is removed only when no other `PackageSource` still references it. So for an artifact that carries several `PackageSource` resources, untap each one; the shared source is deleted with the last.

From the dashboard, disconnecting a tapped repository in the "Repositories" view follows the same rule: it removes the named `PackageSource`, and the Flux source only once no other `PackageSource` references it. It does not remove already-installed applications, and, unlike `cozypkg untap`, it does not stop to ask when a `Package` from that source is still installed.
