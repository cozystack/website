---
title: "Migrating from LINSTOR to Blockstor"
linkTitle: "Migrating to Blockstor"
description: "How to move an existing cluster's storage control plane from LINSTOR to Blockstor without recreating volumes"
weight: 7
---

Blockstor is a LINSTOR-API-compatible storage control plane that keeps its state in Kubernetes custom resources. Because it serves the same CSI wire shape through the same CSI driver, an existing cluster can move across without recreating volumes or re-provisioning workloads: the StorageClasses, the PersistentVolumes bound to them, and the DRBD devices on the nodes all stay exactly as they are. What changes is which control plane manages them.

{{% alert color="warning" %}}
Blockstor is **experimental**. This migration rewrites which component owns your storage metadata. Read the whole page before starting, take the backup in step 1, and rehearse on a cluster you can afford to lose.
{{% /alert %}}

## How the migration works

Your data is not copied or moved. DRBD runs in the kernel and is host-scoped: it keeps serving volumes while the control plane is replaced above it. The migration converts LINSTOR's metadata — nodes, storage pools, resource definitions, replicas — into Blockstor custom resources, and Blockstor then *adopts* the running devices rather than creating new ones.

The order matters, and it is the opposite of what feels natural. You switch the backend **first**, which installs Blockstor's CRDs and starts its control plane against an empty database, and you adopt the existing volumes **second**. Adoption cannot come first because the resources it creates have nowhere to live until the CRDs exist.

## Before you start

You need:

- `linstor-migrate`, the converter shipped with Blockstor. Build it from the Blockstor repository with `make build` or take it from a release.
- A Cozystack release whose pinned Blockstor can register your storage pools. This is not optional and it is the first thing to check — see the box below.
- Enough of a maintenance window that CSI cannot attach or detach volumes for its duration. Running workloads keep their volumes; new pods that need an attach will wait.
- Room in the storage pool for the replicas adoption will add. Blockstor brings replica counts up to each resource group's `placeCount`, and a volume LINSTOR left under-replicated is topped up as soon as the controller starts — a new replica and a full sync each. Check that against your free space before you switch, not after.

{{% alert color="warning" %}}
**Check your Cozystack version before anything else.** You do not pick a Blockstor version: it arrives pinned inside the Cozystack release, so what decides whether the migration can work is which Cozystack you are on. Registering a storage pool that LINSTOR created requires reading the pool name from `StorDriver/StorPoolName`, which is where LINSTOR stores it; a pinned Blockstor without that support logs `unknown storage pool "<name>"` on every reconcile and adopts nothing. The failure is safe — Blockstor refuses before touching the data plane — but the migration cannot proceed, and the fix is to upgrade Cozystack rather than to swap an image.
{{% /alert %}}

## 1. Stop everything that writes

Freeze the writers first, and only then take the backup. LINSTOR's controller keeps writing to its database for as long as it runs, so a backup taken underneath it does not match the dump you take a moment later, and the converted manifest would describe a cluster that no longer exists.

Order matters. piraeus-operator owns the controller Deployment and the satellite DaemonSets, so it goes first: scale the controller down while the operator is still running and the operator simply puts it back.

```bash
kubectl -n cozy-system scale deploy/piraeus-operator-controller-manager --replicas=0
kubectl -n cozy-linstor scale deploy/linstor-controller --replicas=0
kubectl -n cozy-linstor scale deploy/linstor-csi-controller --replicas=0
```

The CSI provisioner is on that list for a reason of its own, covered in step 6: a volume it cannot find is a volume it re-provisions.

Confirm nothing is left writing before you continue:

```bash
kubectl -n cozy-linstor get deploy
```

## 2. Back up LINSTOR's metadata

Everything the migration reads lives in LINSTOR's custom resources. Save them, and the CRD definitions themselves, before you touch the cluster:

```bash
kubectl get crds | grep -o ".*.internal.linstor.linbit.com" | \
  xargs kubectl get crds -ojson > crds.json

kubectl get crds | grep -o ".*.internal.linstor.linbit.com" | \
  xargs -I{} sh -xc "kubectl get {} -ojson > {}.json"

tar czvf backup-$(date +%d.%m.%Y).tgz *.json
```

Switching the backend does not delete these resources, so this backup is what lets you go back.

## 3. Dump the LINSTOR tables

The converter reads a directory of per-table JSON dumps:

```bash
mkdir -p linstor-dump
for crd in $(kubectl get crd -o name | grep 'internal.linstor.linbit.com' \
             | sed 's|customresourcedefinition.apiextensions.k8s.io/||'); do
    kubectl get "$crd" -o json > "linstor-dump/${crd}.json"
done
```

This works even when the LINSTOR controller itself is unhealthy: the converter reads the custom resources directly and never talks to the LINSTOR API.

## 4. Capture the live DRBD ports

Adopted replicas must keep the TCP port their running DRBD connection already uses. If the port is not supplied, Blockstor allocates a fresh one and the mesh reconnects — a brief interruption on every replicated volume.

The port is not stored in LINSTOR's custom resources, so read it from the running kernel. It appears inside each connection's `path` block:

```bash
for node in $(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'); do
  pod=$(kubectl get pods -n cozy-linstor -o name | grep "linstor-satellite.${node}-" | head -1)
  kubectl exec -n cozy-linstor "$pod" -c linstor-satellite -- drbdsetup show 2>/dev/null \
  | awk '/^resource /   { res = $2; gsub(/"/, "", res); next }
         /_this_host[ \t]+ipv4/ { addr = $3; gsub(/;/, "", addr)
                                  n = split(addr, p, ":")
                                  if (res != "" && p[n] ~ /^[0-9]+$/) print res, p[n] }'
done | sort -u > drbd-ports.txt
```

A single-replica volume has no peer and therefore no port to preserve; it will not appear in this file, and that is correct.

## 5. Convert

```bash
linstor-migrate -in linstor-dump -drbd-ports drbd-ports.txt -out blockstor-resources.yaml
```

Read the warnings. Resources that LINSTOR has marked for deletion are skipped and named. Flags the converter does not recognise are reported and dropped rather than guessed at.

## 6. Switch the backend

The CSI provisioner was stopped in step 1, and this is the window it was stopped for. It keeps reconciling while the control plane is being replaced, and a volume it cannot find is a volume it re-provisions: it creates a fresh resource definition through the LINSTOR-compatible API — with newly allocated DRBD minors and ports and a different node ID — for a volume that already exists and still holds data. Those definitions also lack `spec.initialized`, so the satellite treats them as new and queues them for `create-md`. Leaving the provisioner running is how a migration quietly acquires duplicate definitions that disagree with the live mesh.

Set the storage backend on the platform Package, as described in [Choose a Storage Backend]({{% ref "/docs/next/install/cozystack/platform#23-choose-a-storage-backend" %}}):

```yaml
spec:
  components:
    platform:
      values:
        storage:
          backend: blockstor
```

Apply it and wait for the Blockstor control plane to come up. The LINSTOR controller and the piraeus-managed satellites go away; piraeus-operator stays on in external mode to keep driving the CSI driver.

{{% alert color="info" %}}
On a cluster that already ran LINSTOR, the compatibility Service that Blockstor provides for the scheduler and GUI collides with the one piraeus-operator owns. Helm refuses to import it. Take ownership of the existing Service so the release can proceed; a fresh install never hits this.
{{% /alert %}}

Your volumes keep serving throughout this step. Blockstor does not yet know about them, so CSI cannot attach or detach until adoption finishes.

## 7. Stop the controller, then adopt

Scale the Blockstor controller to zero before applying the converted resources:

```bash
kubectl -n cozy-linstor scale deploy/blockstor-controller --replicas=0
kubectl apply -f blockstor-resources.yaml
kubectl -n cozy-linstor scale deploy/blockstor-controller --replicas=1
```

The scale-down is not a nicety. Applying the file in one pass makes the resource definitions visible before the replicas further down the file exist, and a running controller reacts by auto-placing replicas from the resource group's placement policy — giving them freshly allocated ports. The real replicas are then rejected, because a replica's DRBD port can be set once and not changed. You are left with replicas whose ports disagree with the live mesh, which is worse than it sounds: reconciling that state reconfigures a running mesh onto ports its peers do not share.

With the controller stopped, the whole file lands before anything reacts to it.

## 8. Verify

Confirm every replica was adopted rather than recreated, and that the ports match what the kernel is using:

```bash
kubectl get resources.blockstor.cozystack.io -o custom-columns=\
'RD:.spec.resourceDefinitionName,NODE:.spec.nodeName,PORT:.spec.drbdPort'
```

Compare against `drbd-ports.txt`. Then check the data plane is untouched — every peer should still be `UpToDate` and no resource should be syncing:

```bash
kubectl exec -n cozy-linstor ds/blockstor-satellite -- drbdsetup status
```

A resource that starts a full resync after adoption means it was treated as new rather than adopted. Stop and investigate before letting it run.

Expect the controller to create replicas for any volume LINSTOR left under-replicated. Blockstor reconciles replica count against the resource group's `placeCount` continuously, where LINSTOR only places on request, so a volume sitting at one replica under a three-replica storage class gets two more — each a full sync. This is correct behaviour, not a migration fault, but it is worth knowing before it happens on a pool with no room for it.

Once the replicas check out, bring the CSI provisioner back:

```bash
kubectl -n cozy-linstor scale deploy/linstor-csi-controller --replicas=1
```

## Rolling back

Switching back is the same operation in reverse: set `storage.backend` to `linstor` and apply. LINSTOR's custom resources are not deleted by the migration, so its controller finds its state where it left it. The Blockstor custom resources can be removed afterwards.
