---
title: "cozypkg Reference"
linkTitle: "cozypkg Reference"
description: "Command and flag reference for the cozypkg marketplace CLI."
weight: 30
---

`cozypkg` is the CLI for authoring, publishing, and managing Cozystack marketplace repositories. This page is a reference for its commands; for task-oriented walkthroughs see [Publishing a Repository]({{% ref "/docs/next/marketplace/publishing" %}}) and [Connecting a Repository]({{% ref "/docs/next/marketplace/connecting" %}}).

Commands that create or read cluster resources accept `--kubeconfig` and otherwise fall back to `~/.kube/config` or the `KUBECONFIG` environment variable. Creating cluster-scoped resources requires cluster-admin.

## Environment variables

- `COZYPKG_INDEX`: default index location for `search` and short-name `tap`. A local directory or an `oci://` reference. Overridden by `--index`.

## Authoring and publishing

### `cozypkg init [directory]`

Scaffold a new repository built around the `PackageSource` model: a `PackageSource` with one variant and a paired app / `-rd` component, ready to validate and push. The generated tree passes `cozypkg validate` as-is.

| Flag | Description |
| --- | --- |
| `--app <label>` | Name of the sample app/component, an RFC-1123 label (default `myapp`). |
| `--name <name>` | `PackageSource` name (defaults to `example.<app>`). Reserved prefixes `cozystack.` and `community.` are rejected. |

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
| `--allow-reserved-names` | Permit reserved `PackageSource` name prefixes. The index gate never sets this. |

```bash
cozypkg validate ./hello-repo --helm-lint
```

### `cozypkg push <oci-ref>`

Validate the repository and push its `packages/` tree as a single versioned OCI artifact using the `flux` CLI, the same artifact shape the platform and `cozypkg tap` consume. Source URL and revision are derived from git when not given.

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
cozypkg search database --index oci://ghcr.io/cozystack/packages-index:latest
```

### `cozypkg tap <oci-ref>`

Register an external repository: create a Flux `OCIRepository` for the artifact and materialize the `PackageSource` resources it carries, named under the `community.` prefix. Nothing is installed until `cozypkg add`. Tapping is idempotent and validates the artifact's structure but does not verify its cosign signature.

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

Remove a community-tapped `PackageSource` and its Flux source. Only `community.*` sources can be untapped; official sources are refused. Already-installed `Package` resources are left untouched.

| Flag | Description |
| --- | --- |
| `--yes` | Untap even if a `Package` from this source is still installed. |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg untap community.acme.hello
```

## Installing and inspecting

### `cozypkg add [package]...`

Install a `PackageSource` and its dependencies interactively. Packages can be given as arguments or read from files with `-f`.

| Flag | Description |
| --- | --- |
| `--allow-privileged` | Install privileged components without an interactive confirmation. |
| `-f, --file <path>` | Read packages from a file or directory (repeatable). |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg add community.acme.hello
```

### `cozypkg del [package]...`

Delete `Package` resources. Packages can be given as arguments or read from files with `-f`.

| Flag | Description |
| --- | --- |
| `-f, --file <path>` | Read packages from a file or directory (repeatable). |
| `--kubeconfig <path>` | Path to kubeconfig file. |

```bash
cozypkg del community.acme.hello
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

### `cozypkg dot`

Generate the dependency graph of `PackageSource` resources in Graphviz DOT format.

```bash
cozypkg dot | dot -Tsvg > packages.svg
```
