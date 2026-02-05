---
title: "Upgrading Cozystack and Post-upgrade Checks"
linkTitle: "Upgrading Cozystack"
description: "Upgrade Cozystack system components."
weight: 10
aliases:
  - /docs/upgrade
  - /docs/operations/upgrade
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

- [Troubleshooting Checklist]({{% ref "/docs/operations/troubleshooting/#troubleshooting-checklist" %}})

Make sure that the Cozystack ConfigMap contains all the necessary variables:
If there are missing keys in `data.*`, add them.

```bash
kubectl get configmap -n cozy-system cozystack -oyaml
```
Example output:
```yaml
apiVersion: v1
kind: ConfigMap
data:
  api-server-endpoint: https://33.44.55.66:6443
  bundle-name: paas-full
  ipv4-join-cidr: 100.64.0.0/16
  ipv4-pod-cidr: 10.244.0.0/16
  ipv4-pod-gateway: 10.244.0.1
  ipv4-svc-cidr: 10.96.0.0/16
  root-host: example.org
  ...
```

Learn more about this file and its contents from the [Cozystack ConfigMap reference]({{% ref "/docs/operations/configuration/configmap" %}}).

### 2. Apply the new manifest file

Each Cozystack release includes a manifest file `cozystack-installer.yml`.
Download and apply it, or apply directly from GitHub:

```bash
# note the 'v' before version numbers
version=vX.Y.Z
kubectl apply -f  https://github.com/cozystack/cozystack/releases/download/$version/cozystack-installer.yaml
```

You can read the logs of the main installer:

```bash
kubectl logs -n cozy-system deploy/cozystack -f
```

### 3. Check the cluster status after upgrading

```bash
kubectl get pods -n cozy-system
kubectl get hr -A | grep -v "True"
```

If pod status shows a failure, check the logs:

```bash
kubectl logs -n cozy-system deploy/cozystack --previous
```

To make sure everything works as expected, repeat the steps from

  - [Troubleshooting Checklist]({{% ref "/docs/operations/troubleshooting/#troubleshooting-checklist" %}})

