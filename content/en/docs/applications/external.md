---
title: "Adding External Applications to Cozystack Catalog"
linkTitle: "External Apps"
description: "Learn how to add managed applications from external sources"
weight: 5
---

Since v0.35.0, Cozystack administrators can add applications from external sources in addition to the standard application catalog.
These applications will appear in the same application catalog and behave like regular managed applications for platform users.

This guide explains howto define a managed application package and how to add it to Cozystack.


## 1. Create an Application Package Repository

Create a repository with the application package sources.
For a reference, see [github.com/cozystack/external-apps-example](https://github.com/cozystack/external-apps-example).

Application repository has the following structure:

- `./apps`: Helm charts for applications that can be installed from the dashboard.
- `./core`: Manifests for the platform.
    - `./core/cozystackresourcedefinitions`: Manifests with `CozystackResourceDefinition` for registering new resources in the Kubernetes API.
    - `./core/marketplacepanels`: Manifests with `MarketplacePanel` for creating application entries in the dashboard.
- `./system`: `HelmReleases` for system applications and namespaces.
    - `./system/charts`: Helm charts for system applications that will be installed permanently.

Just like standard Cozystack applications, this external application package is using Helm and FluxCD.
To learn more about developing application packages, read the FluxCD docs:

-   [HelmRelease](https://fluxcd.io/flux/components/helm/helmreleases/)
-   [GitRepository](https://fluxcd.io/flux/components/source/gitrepositories/)
-   [Kustomization](https://fluxcd.io/flux/components/kustomize/kustomizations/)

## 2. Add the Application Package with a Manifest

Create a manifest file with resources `GitRepository` and `Kustomization`, as in the example:


```yaml
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
  url: https://github.com/<org>/<your-repo-name>.git
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: external-apps
  namespace: cozy-public
spec:
  force: false
  interval: 10m0s
  path: ./
  prune: true
  sourceRef:
    kind: GitRepository
    name: external-apps
---
```

For a detailed reference, read [Git Repositories in Flux CD](https://fluxcd.io/flux/components/source/gitrepositories/).

Next, write this manifest to a file and apply it to your Cozystack cluster:

```bash
kubectl apply -f init.yaml
```

After applying the manifest, open your application catalog to confirm that the application is available.
