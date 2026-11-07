---
title: "Upgrading Cozystack and Post-upgrade Checks"
linkTitle: "Upgrading Cozystack"
description: "Upgrade Cozystack system components."
weight: 10
aliases:
  - /docs/v1.7/upgrade
  - /docs/v1.7/operations/upgrade
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

Before moving to a new minor version, read the upgrade notes of every minor version you cross, such as [Upgrading from v1.6 to v1.7]({{% ref "/docs/v1.7/operations/cluster/upgrade-to-v1.7" %}}). Some changes need an action before the upgrade starts.

### 1. Check the cluster status

Before upgrading, check the current status of your Cozystack cluster by following steps from

- [Troubleshooting Checklist]({{% ref "/docs/v1.7/operations/troubleshooting/#troubleshooting-checklist" %}})

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

Build the list of new images from the Cozystack images the cluster runs now.
Set `FROM` to the installed version and `TO` to the target version.

```bash
FROM=v1.6.4
TO=v1.6.5
kubectl get pods --all-namespaces --output json \
  | jq --raw-output '.items[].spec | (.initContainers // [])[], .containers[] | .image' \
  | grep -E "^ghcr.io/cozystack/cozystack/[^:]+:${FROM}(@|$)" \
  | sed -E "s/:${FROM}(@sha256:[0-9a-f]+)?$/:${TO}/" \
  | sort -u > images.txt
```

The list covers the images that carry the Cozystack version in their tag.
Add other images that change in the release to `images.txt` by hand if you want them pulled too.

Find the etcd leader.
It is the node whose `MEMBER` matches the `LEADER` column.

```bash
talosctl --nodes <node1>,<node2>,<node3> etcd status
```

Then pull the images on each control plane node in turn, the leader last.
Nodes that do not run etcd can skip this step.

```bash
while read -r image; do
  talosctl --nodes <node> image pull --namespace cri "$image"
done < images.txt
```

Before you move to the next node, run `etcd status` again and check that the leader and the `RAFT TERM` are the same, and that the etcd log of the node has no new `slow fdatasync` warnings.

```bash
talosctl --nodes <node> logs etcd | grep 'slow fdatasync'
```

A pull on the leader node can still delay its heartbeats.
To avoid that, move the leadership to a node that already has the images before you pull on the leader.

```bash
talosctl --nodes <leader-node> etcd forfeit-leadership
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

- [Troubleshooting Checklist]({{% ref "/docs/v1.7/operations/troubleshooting/#troubleshooting-checklist" %}})

