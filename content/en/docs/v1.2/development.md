---
linkTitle: Developer Guide
title: Cozystack Internals and Developer Guide
description: Cozystack Internals and Development
weight: 100
aliases:
  - /docs/v1.2/development/development
---

## How it works

Cozystack is an operator-driven platform. The bootstrap and ongoing management are
handled by a set of controllers that run inside the cluster. The high-level flow is:

1. **Installer chart** (`packages/core/installer`) is applied via `helm install`.
   It deploys the `cozystack-operator` Deployment into the `cozy-system` namespace.

2. **cozystack-operator** starts and performs one-time bootstrap:
   - Installs Cozystack CRDs (`Package`, `PackageSource`) from embedded manifests
     (`internal/crdinstall`).
   - Installs Flux components (source-controller, helm-controller,
     source-watcher) from embedded manifests (`internal/fluxinstall`).
   - Creates the **initial OCIRepository** (`cozystack-platform`) from the
     `platformSourceUrl` and `platformSourceRef` values configured in the installer.
   - Creates a `PackageSource` that references the initial OCIRepository.

3. **Reconciliation loop** takes over. The operator watches `PackageSource` and
   `Package` CRDs and translates them into Flux `HelmRelease` objects. Flux
   then installs and manages the actual Helm charts.

4. **Platform chart** (`packages/core/platform`) is deployed as a regular
   Package. It reads the cluster configuration from the
   `cozystack.cozystack-platform`
   [Package]({{% ref "/docs/v1.2/operations/configuration/platform-package" %}})
   resource and templates bundle manifests that define which system components
   should be installed.
   
   The platform chart also creates the **secondary OCIRepository** (`cozystack-packages`)
   by copying the spec from the initial OCIRepository. All PackageSources reference
   this secondary repository. During upgrades, the platform chart runs migrations
   as `pre-upgrade` hooks before creating or updating component HelmReleases.

5. **FluxCD** is the execution engine — it reconciles `HelmRelease` objects
   created by the operator, pulling chart artifacts from `ExternalArtifact`
   resources and applying them to the cluster.

For the full reconciliation chain (PackageSource → ArtifactGenerator → ExternalArtifact → Package → HelmRelease → Pods), dependency resolution, update and rollback flows, and the cozypkg CLI, see [Key Concepts]({{% ref "/docs/v1.2/guides/concepts" %}}).

### OCIRepositories and Migration Flow

Cozystack uses two OCIRepository resources to manage platform updates:

| OCIRepository | Created By | References |
|---|---|---|
| `cozystack-platform` | cozystack-operator | Configured via installer values (`platformSourceUrl`, `platformSourceRef`) |
| `cozystack-packages` | Platform chart (`repository.yaml`) | Copies spec from `cozystack-platform` |

All PackageSources in `packages/core/platform/sources/` reference `cozystack-packages`.

#### Migration Execution

Migrations run as Helm `pre-upgrade` hooks in the platform chart:

```yaml
# packages/core/platform/templates/migration-hook.yaml
metadata:
  name: cozystack-migration-hook
  annotations:
    helm.sh/hook: pre-upgrade,pre-install
    helm.sh/hook-weight: "1"
```

The migration container reads the current version from the `cozystack-version` ConfigMap and executes migration scripts sequentially from `CURRENT_VERSION` to `TARGET_VERSION - 1`. Each migration updates the ConfigMap on success, ensuring migrations are idempotent and can resume after failures.

#### Why Two Repositories?

The separation ensures that:

1. The initial OCIRepository is managed by the operator (via installer values).
2. All PackageSources have a consistent reference (`cozystack-packages`) rather than pointing to the operator-managed source directly.
3. The platform chart can run migrations before creating the secondary OCIRepository, guaranteeing migrations execute before component updates.

### Key binaries

| Binary | Source | Role |
|---|---|---|
| **cozystack-operator** | `cmd/cozystack-operator` | Bootstrap (CRDs, Flux, platform source), `PackageSource` and `Package` reconciliation, `cozystack-values` secret replication. |
| **cozystack-controller** | `cmd/cozystack-controller` | Workload and ApplicationDefinition reconciliation, dashboard management. |
| **cozystack-api** | `cmd/cozystack-api` | Kubernetes API aggregation layer for `apps.cozystack.io` and `core.cozystack.io` API groups. |
| **cozypkg** | `cmd/cozypkg` | CLI tool for managing packages — dependency visualization, interactive installation, deletion. |

## Repository Structure

The main structure of the [cozystack](https://github.com/cozystack/cozystack) repository is:

```shell
.
├── api             # Go types for Cozystack CRDs (Package, PackageSource, etc.)
├── cmd             # Entry points for all binaries
│   ├── cozystack-operator      # Main platform operator
│   ├── cozystack-controller    # Workload and application controllers
│   ├── cozystack-api           # Aggregated API server
│   └── cozypkg                 # Package management CLI
├── internal        # Controller and reconciler implementations
│   ├── operator                # PackageSource and Package reconcilers
│   ├── controller              # Workload, ApplicationDefinition controllers
│   ├── fluxinstall             # Embedded Flux manifests and installer
│   ├── crdinstall              # Embedded CRD manifests and installer
│   └── cozyvaluesreplicator    # Secret replication logic
├── packages        # Helm charts organized by layer
│   ├── core            # Bootstrap and platform configuration
│   ├── system          # Infrastructure operators and upstream charts
│   ├── apps            # User-facing application charts
│   └── extra           # Tenant-specific application charts
├── pkg             # Shared Go libraries
├── dashboards      # Grafana dashboards
├── hack            # Helper scripts for local development
└── docs            # Changelogs and release notes
```

Development can be done locally by modifying and updating files in this repository.

## Packages

### [core](https://github.com/cozystack/cozystack/tree/main/packages/core)

Core packages handle bootstrap and platform-level configuration.

#### installer

A Helm chart that deploys the `cozystack-operator` Deployment. It creates the
`cozy-system` namespace, a ServiceAccount with cluster-admin privileges, and the
operator Deployment with flags that trigger CRD and Flux installation on startup.
The operator image and platform source URL are injected at build time.

#### platform

A Helm chart deployed as a regular `Package` (not applied directly). It reads the
cluster configuration from the `cozystack.cozystack-platform`
[Package]({{% ref "/docs/v1.2/operations/configuration/platform-package" %}})
resource and templates manifests according to the specified
[variant]({{% ref "/docs/v1.2/operations/configuration/variants" %}}) and
component settings, defining which system components should be installed.

#### flux-aio

Flux components packaged for deployment by the operator.

#### talos

Talos OS configuration assets.

{{% alert color="info" %}}
Core packages do not use Helm to apply manifests; they are intended to be used only as `helm template . | kubectl apply -f -`.
{{% /alert %}}

### [system](https://github.com/cozystack/cozystack/tree/main/packages/system)

System packages configure the system to manage and deploy user applications. The
necessary system components are specified in the bundle configuration.

System packages include two kinds of components:

- **Operators** (e.g., `postgres-operator`, `kafka-operator`, `redis-operator`): Controllers
  that know how to manage the full lifecycle of a specific application, including day-2 operations.
- **Upstream Helm charts** for applications without a dedicated operator (e.g., `nats`, `ingress-nginx`):
  These charts are placed in system so that apps and extra packages can deploy them
  via Flux `HelmRelease` CRs, effectively using FluxCD as the operator.

{{% alert color="info" %}}
System packages use Helm to install and are managed by FluxCD.
{{% /alert %}}

### [apps](https://github.com/cozystack/cozystack/tree/main/packages/apps)

These user-facing applications appear in the dashboard and include manifests to be applied to the cluster.

Apps charts serve as a high-level API for users. They define only the parameters that
should be exposed and validated through `values.schema.json`, keeping the interface
minimal and secure. Apps charts should not contain business logic for deploying the
application itself — instead they delegate to an operator or to FluxCD.

Depending on whether the application has a dedicated operator, apps follow one of two patterns:

#### Operator-based pattern

When an application has a dedicated operator (e.g., PostgreSQL, MongoDB, Redis, Kafka),
the app chart creates **CRD instances** that the operator manages:

```
packages/system/postgres-operator/   # Operator Helm chart
packages/apps/postgres/              # App chart creates postgresql.cnpg.io/v1.Cluster CRs
```

The operator handles all deployment details and day-2 operations (scaling, backups, failover).
The app chart simply creates the appropriate CRD with values derived from user input.

#### HelmRelease-based pattern

When an application has no dedicated operator and a Helm chart is the standard deployment
method, the upstream chart is placed in `system/` and the app chart creates a
**Flux `HelmRelease` CR** pointing to it:

```
packages/system/nats/                # Upstream NATS Helm chart
packages/apps/nats/                  # App chart creates helm.toolkit.fluxcd.io/v2.HelmRelease
```

In this case FluxCD acts as the operator, managing the Helm release lifecycle. The app
chart controls which upstream values are exposed to the user, providing an additional layer
of security — users cannot bypass validation to deploy the chart with arbitrary values.

Other examples of this pattern: `extra/ingress`, `extra/seaweedfs`, `extra/monitoring`.

### [extra](https://github.com/cozystack/cozystack/tree/main/packages/extra)

Similar to `apps` but not shown in the application catalog. They can only be installed as part of a tenant.
They are allowed to use by bottom tenants installed in current tenant namespace.

Read more about [Tenant System](/docs/guides/concepts/#tenant-system) on the Core Concepts page.

It is possible to use only one application type within a single tenant namespace.

Extra packages follow the same two architectural patterns as apps (operator-based or HelmRelease-based).

{{% alert color="info" %}}
Apps and extra packages use Helm for application and are installed from the dashboard and managed by FluxCD.
{{% /alert %}}

## Package Structure

Every package is a typical Helm chart containing all necessary images and manifests
for the platform. We follow an umbrella chart logic to keep upstream charts in the
`./charts` directory and override values.yaml in the application's root.
This structure simplifies upstream chart updates.

```shell
.
├── Chart.yaml                           # Helm chart definition and parameter description
├── Makefile                             # Common targets for simplifying local development
├── charts                               # Directory for upstream charts
├── images                               # Directory for Docker images
├── patches                              # Optional directory for upstream chart patches
├── templates                            # Additional manifests for the upstream Helm chart
├── templates/dashboard-resourcemap.yaml # Role used to display k8s resources in dashboard
├── values.yaml                          # Override values for the upstream Helm chart
└── values.schema.json                   # JSON schema used for input values validation and to render UI elements in dashboard
```

You can use bitnami's [readme-generator](https://github.com/bitnami/readme-generator-for-helm) for generating `README.md` and `values.schema.json` files.

Just install it as `readme-generator` binary in your system and run generation using `make generate` command.

## Helm Chart Development Principles

The package structure and development workflow in Cozystack are guided by the following principles:

### Easy to update upstream charts

The original upstream chart must be easy to update, override, and modify. We use the umbrella chart pattern — upstream charts live in the `./charts` directory and are vendored as-is. Customizations go into `values.yaml` overrides and additional `templates/`, while structural changes to the upstream chart are applied via `patches/`. This separation ensures that updating to a new upstream version is straightforward: run `make update`, review the diff, and re-apply patches if needed.

### Local-first artifacts

Patches and container images are stored locally and are part of the package. The `patches/` directory holds any modifications to the upstream chart, and the `images/` directory contains Dockerfiles for building all required images. This ensures full reproducibility — everything needed to build and deploy the package is self-contained within the repository.

{{% alert color="info" %}}
Currently, not all packages build their images locally — some still reference externally-built images. We are actively working toward fully local image builds to achieve complete self-containment and reproducibility.
{{% /alert %}}

### Local development and testing workflow

Every package must be easy to update and test locally against a real cluster, without relying on CI. The standard `make` targets (`make image`, `make diff`, `make apply`) provide a fast feedback loop: build images, compare rendered manifests against the live cluster, and apply changes — all from a developer's workstation.

### No external dependencies

Packages must not depend on external resources at runtime. All charts, images, and patches are vendored into the repository. This guarantees that builds and deployments are deterministic and do not break due to upstream registry outages, removed tags, or network issues.

{{% alert color="info" %}}
As noted above, full image self-containment is a work in progress. Some packages still pull images from external registries — this is a known gap that we plan to close as capacity allows.
{{% /alert %}}

## Development

### Buildx configuration

To build images, you need to install and configure the [`docker buildx`](https://github.com/docker/buildx) plugin.

Instead of a built-in builder, you can [configure additional ones](https://docs.docker.com/build/builders/), which may be remote, or support multiple architectures.
This example shows how to create a builder with `kubernetes` driver, which allows you to build images directly in a Kubernetes cluster:

```bash
docker buildx create \
  --bootstrap \
  --name=buildkit \
  --driver=kubernetes \
  --driver-opt=namespace=tenant-kvaps,replicas=2 \
  --platform=linux/amd64 \
  --platform=linux/arm64 \
  --use
```

Alternatively, omit the --driver* options to set up the build environment in an local Docker environment.

### Packages management

Each application includes a Makefile to simplify the development process. We follow this logic for every package:

```shell
make update  # Update Helm chart and versions from the upstream source
make image   # Build Docker images used in the package
make show    # Show output of rendered templates
make diff    # Diff Helm release against objects in a Kubernetes cluster
make apply   # Apply Helm release to a Kubernetes cluster
```

For example, to update cilium:

```shell
cd packages/system/cilium         # Go to application directory
make update                       # Download new version from upstream
make image                        # Build cilium image
git diff .                        # Show diff with changed manifests
make diff                         # Show diff with applied cluster manifests
make apply                        # Apply changed manifests to the cluster
kubectl get pod -n cozy-cilium    # Check if everything works as expected
git commit -m "Update cilium"     # Commit changes to the branch
```

To build the cozystack container with an updated chart:

```shell
cd packages/core/installer        # Go to the cozystack package
make image-packages               # Build packages image
make apply                        # Apply to the cluster
kubectl get pod -n cozy-system    # Check if everything works as expected
kubectl get hr -A                 # Check HelmRelease objects
```

{{% alert color="info" %}}
When rebuilding images, specify the `REGISTRY` environment variable to point to your Docker registry.

Feel free to look inside each Makefile to better understand the logic.
{{% /alert %}}

### Testing

The platform includes an [`e2e.sh`](https://github.com/cozystack/cozystack/blob/main/hack/e2e.sh) script that performs the following tasks:

- Runs three QEMU virtual machines
- Configures Talos Linux
- Installs Cozystack
- Waits for all HelmReleases to be installed
- Performs additional checks to ensure that components are up and running

You can run e2e.sh either locally or directly within a Kubernetes container.

To run tests in a Kubernetes cluster, navigate to the `packages/core/testing` directory and execute the following commands:

```shell
make apply    # Create testing sandbox in Kubernetes cluster
make test     # Run the end-to-end tests in existing sandbox
make delete   # Remove testing sandbox from Kubernetes cluster
```

{{% alert color="warning" %}}
:warning: To run e2e tests in a Kubernetes cluster, your nodes must have sufficient free resources to create 3 VMs and store the data for the deployed applications.

It is recommended to use bare-metal nodes of the parent Cozystack cluster.
{{% /alert %}}

### Dynamic Development Environment

If you prefer to develop Cozystack in virtual machines instead of modifying the existing cluster, you can utilize the same sandbox from testing environment. The Makefile in the `packages/core/testing` includes additional options:

```shell
make exec     # Opens an interactive shell in the sandbox container.
make login    # Downloads the kubeconfig into a temporary directory and runs a shell with the sandbox environment; mirrord must be installed.
make proxy    # Enable a SOCKS5 proxy server; mirrord and gost must be installed.
```

Socks5 proxy can be configured in a browser to access services of a cluster running in sandbox. Firefox has a handy extension for toogling proxy on/off:

- [Proxy Toggle](https://addons.mozilla.org/en-US/firefox/addon/proxy-toggle/)
