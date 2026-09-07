---
title: "Publishing a Repository"
linkTitle: "Publishing"
description: "Scaffold, validate, and push an External-Apps repository as an OCI artifact, then list it in the community index."
weight: 10
---

This guide is for **publishers**: developers who package applications and make them available to Cozystack clusters. It covers scaffolding a repository, validating it offline, pushing it as an OCI artifact, and, optionally, listing it in the community index.

For the operator side (connecting a published repository to a cluster), see [Connecting a Repository]({{% ref "/docs/next/marketplace/connecting" %}}).

## Prerequisites

- The `cozypkg` CLI; see [Install cozypkg]({{% ref "/docs/next/install/cozystack/kubernetes-distribution" %}}#2-install-cozypkg).
- The `flux` CLI, which `cozypkg push` uses to build and push the OCI artifact.
- Access to an OCI registry you can push to (for example GitHub Container Registry).
- `helm` on your `PATH` if you want `--helm-lint` to run `helm lint` on the charts.

## Scaffold a repository

`cozypkg init` writes a complete repository skeleton that passes validation as-is:

```bash
cozypkg init --app hello --name acme.hello ./hello-repo
```

- `--app` is the RFC-1123 name of the sample application component (default `myapp`).
- `--name` is the `PackageSource` name (defaults to `example.<app>`).

{{% note %}}

A `PackageSource` name must be a valid Kubernetes object name (lowercase, no underscores), and it must not start with a reserved prefix: `cozystack.` is the platform's own namespace and `community.` is reserved, so `cozypkg init` and `cozypkg validate` both refuse those two prefixes. Beyond that the name is yours to choose; use your organization as a prefix, for example `acme.hello`. The real anti-shadowing boundary is on the cluster: a tapped repository keeps its declared name, and a clash with a core component is rejected at connect time (see [Connecting a Repository]({{% ref "/docs/next/marketplace/connecting" %}})).

{{% /note %}}

### Repository layout

The scaffold produces the layout that validation and the platform expect:

```text
packages/
  core/platform/sources/hello.yaml   # PackageSource: variants and components
  apps/hello/                        # application Helm chart
    Chart.yaml
    values.yaml
    templates/configmap.yaml
  system/hello-rd/                   # ApplicationDefinition registration
    Chart.yaml
    templates/cozyrd.yaml
    cozyrds/hello.yaml
README.md
```

The `PackageSource` ties the two components together:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: PackageSource
metadata:
  name: acme.hello
spec:
  sourceRef:
    kind: OCIRepository
    name: hello-packages
    namespace: cozy-system
    path: /
  variants:
    - name: default
      components:
        - name: hello
          path: apps/hello
        - name: hello-rd
          path: system/hello-rd
          install:
            namespace: cozy-system
```

- `packages/apps/hello` is the application chart that templates the user-facing resources.
- `packages/system/hello-rd` is a paired chart whose `cozyrds/` asset carries the `ApplicationDefinition` that registers the application in the API and dashboard. Its `chartRef` names the app component's assembled artifact by its concrete name.

Replace the placeholder chart in `packages/apps/hello/templates/` with your application's real resources, and add more components or variants to the `PackageSource` as needed.

## Validate

`cozypkg validate` lints a repository the same way publication would, without touching a cluster. Run it against a local checkout:

```bash
cozypkg validate ./hello-repo
```

Validation decodes every `PackageSource` and `ApplicationDefinition`, resolves each component and library path to a chart directory, checks that each `ApplicationDefinition` chart reference matches a component, resolves `dependsOn` entries, and flags privileged components.

Useful flags:

- `--helm-lint` additionally runs `helm lint` on every component chart (requires the `helm` binary).
- `--known-source <name>` allows a `dependsOn` entry to reference a `PackageSource` that lives outside this repository (repeatable).
- `--require-signature`, with `--certificate-identity` and `--certificate-oidc-issuer`, verifies a keyless cosign signature on a published `oci://` artifact. This is what the community index gate runs; see [The community index](#the-community-index).

You can also validate an already-published artifact by passing an `oci://` reference instead of a path; `cozypkg` pulls it with the `flux` CLI first.

## Push

`cozypkg push` bundles the repository's `packages/` tree into a single versioned OCI artifact, the same artifact shape the platform and `cozypkg tap` consume. The repository is validated first (unless you pass `--skip-validate`), so a validation error aborts the push before anything is published:

```bash
cozypkg push oci://ghcr.io/acme/hello:v1.0.0 --path ./hello-repo
```

The source URL and revision recorded in the artifact are derived from git when not given. Override them with `--source` and `--revision`, and pass `--reproducible` for deterministic artifact metadata.

## The community index

The community index is a standalone repository (`cozystack/packages-index`) that lets operators discover published repositories with `cozypkg search`. It is planned: the repository is not published yet, and today only the scaffold under `hack/packages-index/` ships. It is metadata only: it records where packages live and who owns them. Artifacts stay in ordinary OCI registries; nothing is hosted in the index.

To list a repository, add one metadata file under `entries/`:

```yaml
name: acme.hello
ociRef: oci://ghcr.io/acme/hello
version: v1.0.0
description: A friendly sample application
maintainer: Acme <maintainers@example.com>
homepage: https://example.com/hello
tags:
  - sample
signing:
  identity: https://github.com/acme/hello/.github/workflows/release.yaml@refs/heads/main
  issuer: https://token.actions.githubusercontent.com
```

### Two-lane merge policy

Following the model of krew-index, submissions take one of two lanes:

- **Auto lane.** A change that leaves the security-relevant fields untouched (`ociRef`, `maintainer`, and `signing.identity`/`signing.issuer`) auto-merges once the new artifact validates and is signed by the entry's recorded cosign identity. A routine `version`, `description`, `homepage`, or `tags` edit takes this lane, keeping the "new release of a listed package" path fast.
- **Review lane.** A new entry, or any change to `ociRef`, `maintainer`, or `signing`, is security-relevant and requires maintainer review before merge.

### Signing

Cosign verification is mandatory on the index gate for both lanes. The trust anchor is the entry's recorded `signing.identity`, so a version bump fails if the new artifact is not signed by the originally approved identity. Sign your artifacts with keyless cosign from your release workflow, and record the workflow identity and OIDC issuer in the entry's `signing` block.

{{% warning %}}

Signature verification is enforced here, at publication time, not when a cluster connects a repository. A repository that is not listed in a curated index carries no signature guarantee at connect time. See the [Trust model]({{% ref "/docs/next/marketplace" %}}#trust-model).

{{% /warning %}}
