---
title: "Adding External Applications to Cozystack Catalog"
linkTitle: "External Apps"
description: "Learn how to add managed applications from external sources"
weight: 5
---

Cozystack administrators can add applications from external sources in addition to the standard application catalog.
These applications appear in the same catalog and behave like regular managed applications for platform users.

This guide explains the structure of an external application package and how to add it to a Cozystack cluster.

For a complete working example, see [github.com/cozystack/external-apps-example](https://github.com/cozystack/external-apps-example).

Just like standard Cozystack applications, this external application package uses Helm and FluxCD.
To learn more about developing application packages, read the Cozystack [Developer Guide]({{% ref "/docs/next/development" %}}).

## Repository Structure

An external application repository has the following layout:

```text
init.yaml                        # Bootstrap manifest (GitRepository + HelmRelease)
scripts/
  package.mk                     # Shared Makefile targets for app charts
packages/
  core/platform/                 # Platform chart: namespaces, operators, HelmCharts, ApplicationDefinitions
  apps/<app-name>/               # Helm chart for each user-installable application
```

- `packages/core/platform` — a Helm chart deployed by FluxCD. It registers all applications via `ApplicationDefinition` CRDs, creates required namespaces, deploys operators, and defines `HelmChart` resources that point to the app charts in the same Git repository.
- `packages/apps/<app-name>` — standard Helm charts that template the actual Kubernetes resources (CRDs, ConfigMaps, Secrets, etc.).

## Platform Chart

The platform chart (`packages/core/platform/`) is the central piece. It contains templates for:

### Namespaces

Create namespaces for operators and system components:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  labels:
    cozystack.io/system: "true"
  name: external-<operator-name>
```

### HelmCharts

Define `HelmChart` resources that tell FluxCD where to find each app chart within the Git repository:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmChart
metadata:
  name: external-apps-<app-name>
  namespace: cozy-public
spec:
  interval: 5m
  chart: ./packages/apps/<app-name>
  sourceRef:
    kind: GitRepository
    name: external-apps
  reconcileStrategy: Revision
```

Use `reconcileStrategy: Revision` so that charts with a static `version: 0.0.0` are re-reconciled whenever the Git content changes.

### Operator Deployment

If your application requires an operator, deploy it via a `HelmRepository` and `HelmRelease`:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: <operator-name>
  namespace: external-<operator-name>
spec:
  type: oci
  interval: 5m
  url: oci://ghcr.io/<org>/charts
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: <operator-name>
  namespace: external-<operator-name>
spec:
  interval: 5m
  releaseName: <operator-name>
  targetNamespace: external-<operator-name>
  chart:
    spec:
      chart: <operator-chart-name>
      sourceRef:
        kind: HelmRepository
        name: <operator-name>
      version: '>=1.0.0'
```

### ApplicationDefinitions

Register each application in the Cozystack dashboard with an `ApplicationDefinition`:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: ApplicationDefinition
metadata:
  name: <app-name>
spec:
  application:
    kind: <AppKind>
    singular: <appkind>
    plural: <appkinds>
    openAPISchema: '{"title":"Chart Values","type":"object","properties":{...}}'
  release:
    chartRef:
      kind: HelmChart
      name: external-apps-<app-name>
      namespace: cozy-public
    labels:
      cozystack.io/ui: "true"
    prefix: <app-name>-
  dashboard:
    category: <Category>
    singular: <Human-readable Name>
    plural: <Human-readable Names>
    description: <Short description.>
    tags:
      - <tag>
    icon: <base64-encoded SVG>
    keysOrder:
      - - apiVersion
      - - appVersion
      - - kind
      - - metadata
      - - metadata
        - name
      - - spec
        - <field>
```

Follow these naming conventions (matching the main Cozystack repository):

| Field | Convention | Example for `my-app` |
| --- | --- | --- |
| `metadata.name` | lowercase, hyphens allowed | `my-app` |
| `application.kind` | PascalCase, no hyphens | `MyApp` |
| `application.singular` | lowercase, no hyphens | `myapp` |
| `application.plural` | lowercase, no hyphens | `myapps` |
| `release.prefix` | `<metadata.name>-` | `my-app-` |
| `openAPISchema` title | always `"Chart Values"` | — |

The `openAPISchema` field contains a single-line JSON string with the schema for the application values. It intentionally omits `if`/`then`/`else` conditional rules because Kubernetes `apiextensions/v1` `JSONSchemaProps` does not support these keywords. Use conditional validation only in the Helm chart's `values.schema.json`.

## Application Charts

Each application chart in `packages/apps/<app-name>/` is a standard Helm chart:

```text
packages/apps/<app-name>/
  Chart.yaml
  Makefile
  values.yaml
  values.schema.json
  templates/
    <resource>.yaml
```

### Chart.yaml

```yaml
apiVersion: v2
name: <app-name>
description: <Short description>
type: application
version: 0.0.0
appVersion: "1.0.0"
```

Use `version: 0.0.0` — the actual version is derived from the Git revision by FluxCD.

### Makefile

```makefile
export NAME=<app-name>
export NAMESPACE=external-<operator-name>

include ../../../scripts/package.mk
```

### values.schema.json

Define the JSON Schema (draft-07) for the application values. This schema is used by Helm for validation at install time and can include conditional rules (`if`/`then`/`else`) that are not supported at the `ApplicationDefinition` level.

## Bootstrap Manifest

The `init.yaml` file creates two FluxCD resources that bootstrap the entire catalog:

```yaml
---
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: external-apps
  namespace: cozy-public
spec:
  interval: 1m0s
  ref:
    branch: main
  timeout: 60s
  url: https://github.com/<org>/<repo>.git
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: external-apps
  namespace: cozy-system
spec:
  interval: 5m
  targetNamespace: cozy-system
  chart:
    spec:
      chart: ./packages/core/platform
      sourceRef:
        kind: GitRepository
        name: external-apps
        namespace: cozy-public
      reconcileStrategy: Revision
```

Apply it to your Cozystack cluster:

```bash
kubectl apply -f init.yaml
```

After FluxCD reconciles, the applications will appear in the Cozystack dashboard.

## FluxCD Reference

These FluxCD documents will help you understand the resources used in this guide:

- [GitRepository](https://fluxcd.io/flux/components/source/gitrepositories/)
- [HelmRelease](https://fluxcd.io/flux/components/helm/helmreleases/)
- [HelmChart](https://fluxcd.io/flux/components/source/helmcharts/)
