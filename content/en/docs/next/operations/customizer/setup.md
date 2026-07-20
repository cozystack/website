---
title: "Setup Guide"
linkTitle: "Setup"
description: "Step-by-step: enable the customizer package, point it at your git repo, verify reconciliation."
weight: 10
---

This guide walks through enabling the customizer on a fresh cluster and getting your first commit reconciled. It assumes Cozystack is already installed and healthy, and you have admin access (you can patch the `cozystack.cozystack-platform` Package CR).

## Prerequisites

- A running Cozystack cluster on version ≥ 1.5 (the customizer package landed in 1.5).
- `kubectl` configured against the cluster, in the `cozy-system` namespace.
- A git repo you own that the cluster's Flux can reach over HTTPS (or SSH — see the Flux [GitRepository secret docs](https://fluxcd.io/flux/components/source/gitrepositories/#secret-reference) for transport options). The repo doesn't need to exist with content yet — an empty `main` branch is fine for the first reconcile.
- Credentials with read access to that repo. For GitHub HTTPS that's a fine-grained Personal Access Token with `Contents: Read` scope on the repo.

## Step 1 — Create the git auth Secret

The customizer chart does **not** generate the git credentials Secret. You create it in `cozy-system` before enabling the package, so the platform never owns admin credentials.

```sh
kubectl --namespace cozy-system create secret generic cozystack-customizer-git \
  --from-literal=username=<your-github-username> \
  --from-literal=password=<your-github-pat>
```

For SSH auth, the Secret takes an `identity` (private key) and `known_hosts` instead — see the upstream Flux docs.

## Step 2 — Initialize the customizer repo

In your git repo, create the path the Kustomization will reconcile. The minimum is a Kustomize entry-point file at the path you'll point Flux at. For `path: ./clusters/prod`:

```sh
mkdir -p clusters/prod
cat > clusters/prod/kustomization.yaml <<'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources: []
EOF

git add clusters/prod/kustomization.yaml
git commit -m "init: empty customizer overlay"
git push origin main
```

Starting empty is deliberate — it lets you verify Flux can pull and apply *something* before you start adding patches.

See **[Repo layout and worked examples]({{< relref "repo-layout.md" >}})** for the recommended directory structure once you're past the smoke test.

## Step 3 — Enable the customizer in the Platform Package

Patch `cozystack.cozystack-platform` to flip `customizer.enabled` and point at your repo. Replace `<your-org>` and adjust the branch/path as needed.

```sh
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=merge --patch '{
  "spec": {
    "components": {
      "platform": {
        "values": {
          "customizer": {
            "enabled": true,
            "source": {
              "url": "https://github.com/<your-org>/cozystack-customizer.git",
              "ref": {"branch": "main"},
              "secretRef": "cozystack-customizer-git"
            },
            "kustomization": {
              "path": "./clusters/prod"
            }
          }
        }
      }
    }
  }
}'
```

> Once the customizer is up and reconciling, this initial patch becomes the **last** in-cluster `kubectl patch` you'll need — subsequent customizer config (more namespaces, switching to SSH auth, changing branches) can be done via the customizer repo itself by patching `cozystack.cozystack-platform` from a manifest. The bootstrap is a chicken-and-egg you have to do once.

## Step 4 — Verify reconciliation

The `cozystack.customizer` Package CR should now appear and reconcile to a HelmRelease. Watch for `Ready: True`:

```sh
kubectl get packages.cozystack.io cozystack.customizer
```

Expected:

```
NAME                   VARIANT   READY   STATUS
cozystack.customizer   default   True    reconciliation succeeded, generated 1 helmrelease(s)
```

Then check the resources the chart created:

```sh
kubectl --namespace cozy-system get serviceaccount cozystack-customizer
kubectl get clusterrole,clusterrolebinding cozystack-customizer
kubectl get namespace cozy-customizer
kubectl --namespace cozy-customizer get rolebinding cozystack-customizer
kubectl --namespace cozy-system get gitrepository cozystack-customizer-config
kubectl --namespace cozy-system get kustomization cozystack-customizer
```

The `GitRepository` should report `READY=True` with the latest commit revision:

```
NAME                         URL                                                     AGE   READY   STATUS
cozystack-customizer-config  https://github.com/<your-org>/cozystack-customizer.git  30s   True    stored artifact for revision 'main@sha1:...'
```

The `Kustomization` should also be `READY=True`:

```
NAME                  AGE   READY   STATUS
cozystack-customizer  30s   True    Applied revision: main@sha1:...
```

## Step 5 — Sanity check with a no-op commit

To confirm reconciliation reacts to new commits, add a labelled ConfigMap to the customizer repo:

```sh
# in your customizer repo, on the main branch
cat > clusters/prod/sanity-check.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: customizer-sanity-check
  namespace: cozy-customizer
data:
  reconciled-at: "first-sync"
EOF

# add it to the kustomization
cat > clusters/prod/kustomization.yaml <<'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - sanity-check.yaml
EOF

git add clusters/prod/
git commit -m "test: sanity check ConfigMap"
git push origin main
```

Trigger an immediate reconcile (or wait up to the GitRepository interval, default 1 min):

```sh
flux --namespace cozy-system reconcile kustomization cozystack-customizer --with-source
```

Then:

```sh
kubectl --namespace cozy-customizer get configmap customizer-sanity-check
```

If the ConfigMap is present, the loop is wired end-to-end. Delete the sanity ConfigMap (commit, push, wait for reconcile with `prune: true` enabled by default) before moving on to real customizations.

## Troubleshooting first sync

If the `GitRepository` is not `READY=True`:

```sh
kubectl --namespace cozy-system describe gitrepository cozystack-customizer-config
```

Look for `Status.Conditions`:

- `failed to checkout and determine revision: ... authentication required` — the auth Secret name doesn't match `secretRef`, or the username/password are wrong. Recreate the Secret with the correct values (the name must equal `customizer.source.secretRef`).
- `unable to clone: ... repository not found` — the URL is wrong, or the PAT doesn't have read access to that repo.
- `no such file or directory: ./clusters/prod/kustomization.yaml` — surfaced on the Kustomization, not the GitRepository. The path inside the repo doesn't exist or is misspelled.

If the `Kustomization` is not `READY=True`:

```sh
kubectl --namespace cozy-system describe kustomization cozystack-customizer
```

Common causes:

- `accumulating resources: ... no such file or directory` — a path referenced in your `kustomization.yaml` doesn't exist.
- `failed to ... permission denied` on a specific resource — the customizer SA doesn't have RBAC for that kind. See **[Field ownership and RBAC]({{< relref "field-ownership.md" >}})** for what's granted and what's not. To extend the SA's reach inside an admin-owned namespace, add the namespace to `customizer.rbac.ownedNamespaces` in the Platform Package — the chart will create a RoleBinding to `cluster-admin` there.

## Where to go next

You now have a working customizer loop reconciling an empty repo. To turn it into a useful operational tool, see:

- **[Repo layout and worked examples]({{< relref "repo-layout.md" >}})** — recommended directory tree, plus three end-to-end examples (enable OIDC, override a MetalLB option, ship an in-house HelmRelease).
- **[Field ownership, RBAC, limitations]({{< relref "field-ownership.md" >}})** — important reading **before** you start patching Package CRs.
