---
title: "Upgrading Cozystack and Post-upgrade Checks"
linkTitle: "Upgrading Cozystack"
description: "Upgrade Cozystack system components."
weight: 10
aliases:
  - /docs/v1/upgrade
  - /docs/v1/operations/upgrade
---

## About Cozystack Versions

Cozystack uses a staged release process to ensure stability and flexibility during development.

There are three types of releases:

-   **Alpha, Beta, and Release Candidates (RC)** – Preview versions (such as `v0.42.0-alpha.1` or `v0.42.0-rc.1`) used for final testing and validation.
-   **Stable Releases** – Regular versions (e.g., `v0.42.0`) that are feature-complete and thoroughly tested.
    Such versions usually introduce new features, update dependencies, and may have API changes.
-   **Patch Releases** – Bugfix-only updates (e.g., `v0.42.1`) made after a stable release, based on a dedicated release branch.

It's highly recommended to install only stable and patch releases in production environments.

For a full list of releases, see the [Releases page](https://github.com/cozystack/cozystack/releases) on GitHub.

To learn more about Cozystack release process, read the [Cozystack Release Workflow](https://github.com/cozystack/cozystack/blob/main/docs/release.md).

## Upgrading Cozystack

### 1. Check the cluster status

Before upgrading, check the current status of your Cozystack cluster by following steps from

- [Troubleshooting Checklist]({{% ref "/docs/v1/operations/troubleshooting/#troubleshooting-checklist" %}})

Make sure that the Platform Package is healthy and contains the expected configuration:

```bash
kubectl get packages.cozystack.io cozystack.cozystack-platform -o yaml
```

### 2. Protect critical resources

Before upgrading, annotate the `cozy-system` namespace and the `cozystack-version` ConfigMap
with `helm.sh/resource-policy=keep` to prevent Helm from deleting them during the upgrade:

```bash
kubectl annotate namespace cozy-system helm.sh/resource-policy=keep --overwrite
kubectl annotate configmap -n cozy-system cozystack-version helm.sh/resource-policy=keep --overwrite
```

{{% alert color="warning" %}}
**This step is required.** Without these annotations, removing or upgrading the Helm installer
release could delete the `cozy-system` namespace and all resources within it.
{{% /alert %}}

### 3. Upgrade the Cozystack Operator

Upgrade the Cozystack operator Helm release to the target version:

{{< reuse-values-warning >}}

```bash
helm upgrade cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version X.Y.Z \
  --namespace cozy-system
```

You can read the logs of the operator:

```bash
kubectl logs -n cozy-system deploy/cozystack-operator -f
```

### 4. Check the cluster status after upgrading

```bash
kubectl get pods -n cozy-system
kubectl get hr -A | grep -v "True"
```

If pod status shows a failure, check the logs:

```bash
kubectl logs -n cozy-system deploy/cozystack-operator --previous
```

To make sure everything works as expected, repeat the steps from

- [Troubleshooting Checklist]({{% ref "/docs/v1/operations/troubleshooting/#troubleshooting-checklist" %}})

