---
linkTitle: Developer Guide
title: Cozystack Internals and Developer Guide
description: Cozystack Internals and Development
weight: 100
aliases:
  - /docs/v1.5/development/development
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
   [Package]({{% ref "/docs/v1.5/operations/configuration/platform-package" %}})
   resource and templates bundle manifests that define which system components
   should be installed.
   
   The platform chart also creates the **secondary OCIRepository** (`cozystack-packages`)
   by copying the spec from the initial OCIRepository. All PackageSources reference
   this secondary repository. During upgrades, the platform chart runs migrations
   as `pre-upgrade` hooks before creating or updating component HelmReleases.

5. **FluxCD** is the execution engine — it reconciles `HelmRelease` objects
   created by the operator, pulling chart artifacts from `ExternalArtifact`
   resources and applying them to the cluster.

For the full reconciliation chain (PackageSource → ArtifactGenerator → ExternalArtifact → Package → HelmRelease → Pods), dependency resolution, update and rollback flows, and the cozypkg CLI, see [Key Concepts]({{% ref "/docs/v1.5/guides/concepts" %}}).

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

Cozystack is, at its core, a **provider of managed services**. Much like the managed
offerings of AWS or Google Cloud, a user comes to order a **final entity** — a
PostgreSQL database, a Kafka queue, an S3 bucket, a Kubernetes cluster, a virtual
machine — rather than to assemble the underlying infrastructure themselves. Each of these is a **first-class object** in the Cozystack
API (`apps.cozystack.io`): the user declares *what* they want, and the platform
provisions and operates the implementation underneath. The user gets an endpoint and
credentials and never has to know — or even see — how or where the service actually runs.

The four package categories follow directly from this model:

- **`core`** — how the platform bootstraps and configures itself.
- **`system`** — the operators and upstream charts that actually run workloads.
- **`apps`** — the first-class managed services a user orders directly.
- **`extra`** — enabler modules a tenant switches on, which power those services under
  the hood without being ordered as standalone services.

The split between `apps` and `extra` is the one most often misunderstood, so it is
spelled out in detail below.

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
[Package]({{% ref "/docs/v1.5/operations/configuration/platform-package" %}})
resource and templates manifests according to the specified
[variant]({{% ref "/docs/v1.5/operations/configuration/variants" %}}) and
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

`apps` are the **first-class managed services** a user orders directly. Each one is a
final entity shown in the dashboard catalog and exposed through the `apps.cozystack.io`
API: `apps/postgres` ("Managed PostgreSQL service"), `apps/kubernetes` ("Managed
Kubernetes service"), `apps/kafka`, `apps/bucket` (an S3 bucket), `apps/vm-instance`,
and so on.

An app chart is a **high-level API**, not a deployment recipe. It defines only the
parameters that should be exposed and validated through `values.schema.json`, keeping
the interface minimal and secure — for example, a user selects a Postgres *version* but
cannot override the container image. The chart contains no business logic for running
the application itself; it delegates to an operator or to FluxCD. This thin API layer
over the raw operator exists so the platform keeps full control of every input
(security) and hands the user a final, ready-to-consume service (UX).

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

`extra` packages are **enabler modules**, not first-class services. A user never orders
them as a final entity; instead they are switched on as **tenant options**, and once
enabled they provide capabilities that the `apps` services build on — working under the
hood. For that reason they are *not* shown in the application catalog and can only be
installed as part of a tenant. Because an `extra` module is enabled at the tenant level,
it is shared by the child (bottom) tenants nested in that tenant's namespace —
provisioned once and reused beneath them (for example, a child tenant without its own
`monitoring` sends its metrics to the parent tenant's monitoring stack instead of
running a second copy).

The clearest example is object storage:

- `extra/seaweedfs` ("Managed SeaweedFS Service") deploys a SeaweedFS cluster and
  registers `BucketClass` resources for the tenant.
- `apps/bucket` ("S3 compatible storage") is what the user actually orders — it creates
  a `BucketClaim` against one of those `BucketClass`es.

So a tenant administrator *enables the SeaweedFS module once*, and from then on users
can order S3 buckets as a first-class service. The user consumes a bucket; they never
see, order, or manage SeaweedFS itself — it is an implementation detail of "S3 bucket".
The same relationship holds for `extra/etcd` ("Storage for Kubernetes clusters"), which
provides the datastore for `apps/kubernetes` managed clusters. Other `extra` modules
supply tenant-wide infrastructure rather than orderable services: `extra/ingress`
(NGINX Ingress Controller), `extra/gateway` (per-tenant Gateway API backed by Cilium),
`extra/external-dns`, and `extra/monitoring`.

Read more about [Tenant System](/docs/guides/concepts/#tenant-system) on the Core Concepts page.

It is possible to use only one application type within a single tenant namespace.

Extra packages follow the same two architectural patterns as apps (operator-based or HelmRelease-based).

{{% alert color="info" %}}
Apps and extra packages use Helm for application and are installed from the dashboard and managed by FluxCD.
{{% /alert %}}

### Choosing apps, extra, or a bundled dependency

When adding a new capability, decide where it belongs by asking who consumes it:

1. **Does the user order it directly as a final service?** Then it is a first-class
   managed service → `apps`, shown in the catalog (e.g., `apps/postgres`, `apps/bucket`).
2. **Is it a shared dependency** — used by several apps, or reused across tenants? Then
   it is an enabler the platform/tenant switches on once and many things build on →
   `extra` (e.g., `extra/seaweedfs` backs every `apps/bucket`; `extra/monitoring` collects
   metrics for all apps in a tenant).
3. **Is it a single, private dependency** of one application, shared with no one? Then it
   is *not* a package at all — it is bundled **inside the consuming chart** and deployed
   together with it, invisible to the user. For example, the `monitoring` stack ships its
   own PostgreSQL database for Alerta as part of its release (the former `ferretdb` app
   likewise shipped its own PostgreSQL inside the chart); the user neither sees nor has
   access to these internal databases.

Dependencies also run **between first-class services**. When a dependency is itself
something the user creates, keeps, and manages on its own, it stays an `apps` service
and other apps simply **reference** it instead of bundling it. For example, `apps/vm-disk`
("Virtual Machine Disk") is ordered on its own, and `apps/vm-instance` attaches one or
more existing disks by name (the dashboard lists the available disks to choose from). A
disk has its own lifecycle — it can outlive an instance, be detached and reattached, or
join several disks on one VM — so it is a service in its own right, not something hidden
inside `vm-instance`.

Two questions settle most cases: **who orders it** (the user → `apps`; the platform or a
tenant → `extra`) and **does it have value on its own** (yes → its own `apps` service
that others reference; no → bundled and hidden inside the consuming chart). Sharing tips
the scale toward `extra`: a dependency that must be provisioned once and reused across
apps or tenants becomes a module rather than a per-instance bundle.

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
