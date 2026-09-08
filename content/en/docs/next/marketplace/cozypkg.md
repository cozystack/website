---
title: "cozypkg Reference"
linkTitle: "cozypkg Reference"
description: "Command and flag reference for the cozypkg marketplace CLI."
weight: 30
---

`cozypkg` is the CLI for authoring, publishing, and managing Cozystack marketplace repositories. This page is a reference for its commands; for task-oriented walkthroughs see [Publishing a Repository]({{% ref "/docs/next/marketplace/publishing" %}}) and [Connecting a Repository]({{% ref "/docs/next/marketplace/connecting" %}}).

Commands that create or read cluster resources accept `--kubeconfig` and otherwise fall back to `~/.kube/config` or the `KUBECONFIG` environment variable. Creating cluster-scoped resources requires cluster-admin.

`push` shells out to the `flux` binary, and so does anything that reads an `oci://` reference: `tap`, `validate` against an artifact, and `search` or short-name `tap` against an `oci://` index. `flux` must be on your `PATH` for those. Its pulls run on your machine and use the registry credentials found there.

## Environment variables

- `COZYPKG_INDEX`: default index location for `search` and short-name `tap`. A local directory or an `oci://` reference. Overridden by `--index`.

## Authoring and publishing

### `cozypkg init [directory]`

Scaffold a new repository built around the `PackageSource` model: a `PackageSource` with one variant and a paired app / `-rd` component, ready to validate and push. The generated tree passes `cozypkg validate` as-is.

| Flag | Description |
| --- | --- |
| `--app <label>` | Name of the sample app/component, an RFC-1123 label (default `myapp`). |
| `--name <name>` | `PackageSource` name (defaults to `example.<app>`). Must be a valid Kubernetes object name; the reserved `cozystack.` and `community.` prefixes are refused. A clash with a core component is caught at tap time. |

```bash
cozypkg init --app hello --name acme.hello ./hello-repo
```

### `cozypkg validate <repository-path-or-oci-ref>`

Validate a repository offline, the same way publication would, without installing anything. Decodes every `PackageSource` and `ApplicationDefinition`, resolves component and library paths to charts, checks that chart references match a component, resolves `dependsOn`, and flags privileged components. Accepts a local path or an `oci://` reference (pulled with the `flux` CLI first).

| Flag | Description |
| --- | --- |
| `--helm-lint` | Run `helm lint` on every component chart (requires the `helm` binary). |
| `--known-source <name>` | `PackageSource` name that `dependsOn` entries may reference without being defined in the repository (repeatable). |
| `--require-signature` | Require a valid keyless cosign signature on the OCI artifact (needs the `cosign` binary and an `oci://` reference). |
| `--certificate-identity <id>` | Expected cosign certificate identity for `--require-signature`. |
| `--certificate-oidc-issuer <url>` | Expected cosign certificate OIDC issuer for `--require-signature`. |
| `--allow-reserved-names` | Permit the reserved `cozystack.`/`community.` name prefixes. Caller-side only; the index gate never sets it. |

```bash
cozypkg validate ./hello-repo --helm-lint
```

### `cozypkg push <oci-ref>`

Validate the repository and push its `packages/` tree as a single versioned OCI artifact using the `flux` CLI, the same artifact shape the platform and `cozypkg tap` consume. Source URL and revision are read from the directory's git `origin` remote and `git describe` when not given; if it is not a git checkout with an `origin` remote, `push` stops and asks for `--source` and `--revision` instead of publishing an artifact with no provenance.

| Flag | Description |
| --- | --- |
| `--path <dir>` | Path to the repository root, which must contain `packages/` (default `.`). |
| `--source <url>` | Source URL recorded in the artifact (defaults to the git origin remote). |
| `--revision <rev>` | Revision recorded in the artifact (defaults to `git describe:sha`). |
| `--reproducible` | Pass `--reproducible` to `flux` for deterministic artifact metadata. |
| `--helm-lint` | Also run `helm lint` during pre-push validation. |
| `--skip-validate` | Skip pre-push validation (not recommended). |

```bash
cozypkg push oci://ghcr.io/acme/hello:v1.0.0 --path ./hello-repo
```

## Discovery and connection

### `cozypkg search [term]`

Search the community package index and list matching repositories without connecting them.

| Flag | Description |
| --- | --- |
| `--index <location>` | Index location: a local directory or an `oci://` reference (defaults to `COZYPKG_INDEX`). |

```bash
cozypkg search database --index ./packages-index
```

The community index is not published yet (see [The community index]({{% ref "/docs/next/marketplace/publishing" %}}#the-community-index)), so `--index` takes a local checkout of an index repository for now; an `oci://` reference works the same way once one exists.

### `cozypkg tap <oci-ref>`

Register an external repository: create a Flux `OCIRepository` for the artifact and materialize the `PackageSource` resources it carries under their declared names. A `PackageSource` name that collides with a core component (or another tap) is rejected rather than overwritten; the `ApplicationDefinition` resources inside the repository are not compared against anything. Nothing is installed until `cozypkg add`.

Tapping is idempotent. It pulls the artifact with the `flux` CLI first and validates its structure by default; `--skip-validate` drops the validation but not the pull. Neither path verifies the artifact's cosign signature.

| Flag | Description |
| --- | --- |
| `--tag <tag>` | OCI tag to tap (overrides a tag in the reference; defaults to latest). |
| `--secret <name>` | Name of a pull-credential `Secret` in `cozy-system` for a private repository. |
| `--index <location>` | Index location for resolving a short name (local dir or `oci://`; defaults to `COZYPKG_INDEX`). |
| `--skip-validate` | Skip validating the artifact before tapping. |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg tap oci://ghcr.io/acme/hello:v1.0.0
```

### `cozypkg untap <packagesource-name>`

Remove a tapped `PackageSource`. Only tapped sources (marked with the marketplace-tap label) can be untapped; official sources are refused. The Flux `OCIRepository` goes with it, but only once no other `PackageSource` still references it, so an artifact carrying several sources needs one untap each. A `Package` of the same name still installed makes the command refuse and delete nothing, unless `--yes` is given; already-installed `Package` resources are left untouched either way.

| Flag | Description |
| --- | --- |
| `--yes` | Untap even if a `Package` from this source is still installed. |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg untap acme.hello
```

## Installing and inspecting

### `cozypkg add [package]...`

Install applications from a `PackageSource` and its dependencies interactively: it creates a `Package`, and the reconciler creates a HelmRelease for each of that package's components that carries an `install:` block. In the scaffold that is the paired registration component, which is what puts the application in the catalog; the application's own release comes later, when a user deploys an instance.

Giving packages as arguments is the interactive path: it prompts for a variant even when only one is declared, and again for a privileged component unless `--allow-privileged` is set. `-f` pointing at a file that carries a matching `Package` manifest creates it directly instead, with no prompts and no dependency resolution.

| Flag | Description |
| --- | --- |
| `--allow-privileged` | Install privileged components without an interactive confirmation. |
| `-f, --file <path>` | Read packages from a file or directory (repeatable). |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg add acme.hello
```

### `cozypkg del [package]...`

Delete `Package` resources. Packages can be given as arguments or read from files with `-f`.

| Flag | Description |
| --- | --- |
| `-f, --file <path>` | Read packages from a file or directory (repeatable). |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg del acme.hello
```

### `cozypkg list`

List `PackageSource` or `Package` resources in table format.

| Flag | Description |
| --- | --- |
| `-i, --installed` | List installed `Package` resources instead of `PackageSource` resources. |
| `--components` | Show components on separate lines. |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg list --installed
```

### `cozypkg dot [package]...`

Generate the dependency graph of `PackageSource` (or installed `Package`) resources in Graphviz DOT format.

| Flag | Description |
| --- | --- |
| `-i, --installed` | Graph installed `Package` resources instead of `PackageSource` resources. |
| `--components` | Show component-level dependencies. |
| `-f, --file <path>` | Read packages from a file or directory (repeatable). |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg dot | dot -Tsvg > packages.svg
```
