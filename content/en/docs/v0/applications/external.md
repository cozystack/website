---
title: "Adding External Applications to Cozystack Catalog"
linkTitle: "External Apps"
description: "Learn how to add managed applications from external sources"
weight: 5
aliases:
  - /docs/applications/external
---

Since v0.37.0, Cozystack administrators can add applications from external sources in addition to the standard application catalog.
These applications will appear in the same application catalog and behave like regular managed applications for platform users.

This guide explains how to define a managed application package and how to add it to Cozystack.


## 1. Create an Application Package Repository

Create a repository with the application package sources.
For a reference, see [github.com/cozystack/external-apps-example](https://github.com/cozystack/external-apps-example).

Application repository has the following structure:

- `./packages/core`: Manifests for the platform configuration and to deploy system applications.
- `./packages/system`: Helm charts for system applications.
- `./packages/apps`: Helm charts for applications that can be installed from the dashboard.

Just like standard Cozystack applications, this external application package is using Helm and FluxCD.
To learn more about developing application packages, read Cozystack [Developer Guide](/docs/v0/development/)

These FluxCD documents will help you understand the resources used in this guide:

-   [GitRepository](https://fluxcd.io/flux/components/source/gitrepositories/)
-   [HelmRelease](https://fluxcd.io/flux/components/helm/helmreleases/)

## 2. Add the Application Package with a Manifest

Create a manifest file with resources `GitRepository` and `HelmRelease`, as in the example:


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
  url: https://github.com/cozystack/external-apps-example.git
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
      version: '*'
```

For a detailed reference, read [Git Repositories in Flux CD](https://fluxcd.io/flux/components/source/gitrepositories/).

Next, write this manifest to a file and apply it to your Cozystack cluster:

```bash
kubectl apply -f init.yaml
```

After applying the manifest, open your application catalog to confirm that the application is available.
