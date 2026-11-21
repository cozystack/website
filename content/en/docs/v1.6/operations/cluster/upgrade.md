---
title: "Upgrading Cozystack and Post-upgrade Checks"
linkTitle: "Upgrading Cozystack"
description: "Upgrade Cozystack system components."
weight: 10
aliases:
  - /docs/v1.6/upgrade
  - /docs/v1.6/operations/upgrade
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

- [Troubleshooting Checklist]({{% ref "/docs/v1.6/operations/troubleshooting/#troubleshooting-checklist" %}})

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

### 3. Pre-pull the new images (optional)

By default Talos Linux keeps `/var/lib/etcd` and `/var/lib/containerd` as directories on the same `EPHEMERAL` volume, and its kubelet pulls images in parallel.
During the upgrade many platform components restart at once, so every node pulls and unpacks their new images at the same time.
If this delays the disk writes of the etcd leader long enough, etcd logs `slow fdatasync` and `failed to send out heartbeat on time`, the other members elect a new leader, and requests to the Kubernetes API stall during each election.
Pulling the new images before the upgrade, one node at a time, keeps this load out of the rollout.

To limit I/O during this and later rollouts, configure the control-plane kubelets to pull at most two images at once. With the Cozystack talm preset, set these values for the control-plane nodes and check the rendered kubelet configuration before applying it:

```yaml
extraKubeletExtraArgs:
  serializeImagePulls: false
  maxParallelImagePulls: 2
```

Prepare `images.txt` from the images used by your workloads and the image references in the target release. The following command lists candidates for images tagged with the installed Cozystack version. Set `FROM` and `TO` to your versions.

```bash
FROM=v1.6.4
TO=v1.6.5
kubectl get pods --all-namespaces --output json | jq --raw-output --arg from "$FROM" --arg to "$TO" '
  [.items[].spec | (.initContainers // [])[], .containers[] | .image | split("@")[0]
   | select(startswith("ghcr.io/cozystack/cozystack/") and endswith(":" + $from))
   | rtrimstr(":" + $from) + ":" + $to] | unique[]' > images.txt
```

Check each candidate against the target release and use its published image reference. Add changed images that use a different tag or registry.

On a healthy multi-member etcd cluster, pre-pull on one control-plane node at a time, starting with a follower. Set `CONTROL_PLANES` to the comma-separated control-plane addresses and `NODE` to the address you are about to pull on. Before each node, check which member is leader:

```bash
talosctl --nodes "$CONTROL_PLANES" etcd status
```

If the target node's `MEMBER` matches `LEADER`, transfer leadership first:

```bash
talosctl --nodes "$NODE" etcd forfeit-leadership
talosctl --nodes "$CONTROL_PLANES" etcd status
```

Wait until all members report the same new leader and the target is a follower. Use that Raft term as the baseline for the pull. A single-member cluster has no follower to take leadership.

```bash
(
  set -e
  while IFS= read -r image; do
    talosctl --nodes "$NODE" image pull --namespace cri "$image"
  done < images.txt
)
```

Check `etcd status` and the target node's etcd logs after each pull batch. If the term changed during the pull or new slow disk writes appeared, pause before starting the next node.

```bash
talosctl --nodes "$NODE" logs etcd | grep 'slow fdatasync'
```

Start the upgrade soon after the pull.
The pre-pulled images stay unused until the rollout, and the kubelet removes unused images once the disk usage goes above its garbage collection threshold, 85% by default.

### 4. Upgrade the Cozystack Operator

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

### 5. Check the cluster status after upgrading

```bash
kubectl get pods -n cozy-system
kubectl get hr -A | grep -v "True"
```

If pod status shows a failure, check the logs:

```bash
kubectl logs -n cozy-system deploy/cozystack-operator --previous
```

To make sure everything works as expected, repeat the steps from

- [Troubleshooting Checklist]({{% ref "/docs/v1.6/operations/troubleshooting/#troubleshooting-checklist" %}})

