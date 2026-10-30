---
title: "Troubleshooting LINSTOR CrashLoopBackOff related to a broken database"
linkTitle: "LINSTOR: broken database"
description: "Explains how to resolve LINSTOR CrashLoopBackOff related to a broken database."
weight: 110
---

{{% alert color="warning" %}}
:warning: **Advanced Users Only**

This guide is intended for experienced users who are comfortable with low-level troubleshooting and data recovery operations.
Corrupted LINSTOR databases are rare and typically indicate a serious underlying issue. 

**If you encounter this situation in a production environment, we strongly recommend contacting qualified support**
rather than attempting to fix it yourself. Incorrect actions can lead to permanent data loss.
{{% /alert %}}

## Introduction

When running outside of Kubernetes, LINSTOR controller uses some kind of SQL database (various kinds).
In Kubernetes, `linstor-controller` does not require a persistent volume or external database.
Instead, it stores all its information as custom resources (CRs) right in the Kubernetes control plane.
Upon startup, LINSTOR controller reads all CRs and creates an in-memory database.

These CRs are listed under the `internal.linstor.linbit.com` API group:

```bash
kubectl get crds | grep internal.linstor.linbit.com
```

Example output:
```console
ebsremotes.internal.linstor.linbit.com                        2024-12-28T00:39:50Z
files.internal.linstor.linbit.com                             2024-12-28T00:39:24Z
keyvaluestore.internal.linstor.linbit.com                     2024-12-28T00:39:24Z
layerbcachevolumes.internal.linstor.linbit.com                2024-12-28T00:39:24Z
layercachevolumes.internal.linstor.linbit.com                 2024-12-28T00:39:25Z
layerdrbdresourcedefinitions.internal.linstor.linbit.com      2024-12-28T00:39:24Z
...
```

If CRs somehow get corrupted, linstor-controller will exit with error and go into CrashLoopBackOff.
While controller pod is crashing, others still work.
Even if the satellites crash, drbd on nodes still work too.
But creation and deletion of volumes is not possible.

Those CRs are not very human-readable, but it's possible to understand what's missing or broken.
You can set `TRACE` log level to see the resource loading process in the logs and make sure that the problem is related to CRs.

CR database could be corrupted in case linstor-controller was restarted during very long create or delete operation.
Very long could also mean "hung up".
If you see that something could not delete properly, it's better to investigate and help it to finish, not restarting the controller.


## CRD API versions and field visibility

LINSTOR's `internal.linstor.linbit.com` CRDs declare multiple served apiVersions (for example `v1-15-0`, `v1-17-0`, `v1-25-1`, `v1-31-1`) but persist data under a single storage version. Newer fields, such as `LayerDrbdResources.spec.tcp_port_list` (where DRBD TCP ports are stored), exist only in the newer schemas. When you read through an older served version, those fields are silently stripped by the Kubernetes API server during conversion, so `kubectl get -o json | jq` returns `null` for them even when the data is there.

To see what `linstor-controller` actually reads, discover and query through the storage version. All subsequent `kubectl get --raw` examples in this guide assume `STORAGE_VERSION` is set as below:

```bash
# Discover the storage version once
STORAGE_VERSION=$(kubectl get crd layerdrbdresources.internal.linstor.linbit.com -o json \
  | jq -r '.spec.versions[] | select(.storage==true) | .name')
echo "$STORAGE_VERSION"

# Query via storage version
kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/layerdrbdresources" \
  | jq '.items[0].spec'
```

This also affects [backups](#backup-and-analyze) taken with plain `kubectl get` — fields that are not present in the discovered served version are not written to the backup file. Restoring such a backup can produce records that `linstor-controller` refuses to load (see [Example 4: Missing tcp_port_list on LayerDrbdResources](#example-4-missing-tcp_port_list-on-layerdrbdresources)).


## Example of logs

LINSTOR controller is in a crash loop:

```bash
# kubectl get pod -n cozy-linstor
linstor-controller-6574668cf9-kjtq5 0/1     CrashLoopBackOff 2 (25s ago)     15d
```

Viewing logs:

```bash
# kubectl logs -n cozy-linstor linstor-controller-6574668cf9-kjtq5
...
2025-10-31 13:08:36.016 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Initializing the k8s crd database connector
2025-10-31 13:08:36.016 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Kubernetes-CRD connection URL is "k8s"
2025-10-31 13:08:37.674 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Starting service instance 'K8sCrdDatabaseService' of type K8sCrdDatabaseService
2025-10-31 13:08:37.690 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Security objects load from database is in progress
2025-10-31 13:08:37.960 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Security objects load from database completed
2025-10-31 13:08:37.961 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Core objects load from database is in progress
2025-10-31 13:08:38.446 [Main] ERROR LINSTOR/Controller/ffffff SYSTEM - Unknown error during loading data from DB [Report number 6904B4D1-00000-000000]

...
time="2025-10-31T13:08:38Z" level=fatal msg="failed to run" err="exit status 199"
```

This indicates a corrupted CRD database.

## Obtain the error report

LINSTOR controller creates a file in the `/var/log/linstor-controller/` directory inside container with verbose stack trace.
Unfortunately, it's hard to see it since it gets deleted immediately when the container restarts.
To work around this, you need to stop the Piraeus operator controller and modify the entrypoint of the linstor-controller container.

To be able to see the error report:

1.  Stop the Piraeus operator controller (scale its deployment to zero).
2.  Stop the linstor-controller deployment (scale it to zero).
3.  Modify the linstor-controller deployment entrypoint to run `sleep infinity`.
4.  Remove probes to avoid restarting the container.
5.  Wait until the container starts, `exec` into it and run the controller manually.
6.  After the controller crashes, read the error report.

```bash
kubectl scale deployment -n cozy-linstor piraeus-operator-controller-manager --replicas 0
kubectl scale deployment -n cozy-linstor linstor-controller --replicas 0
kubectl edit deploy -n cozy-linstor linstor-controller
```

An editor will open.
Delete the whole `livenessProbe`, `readinessProbe` and `startupProbe` sections. 
Find the `linstor-controller` container section (the main container).
There, replace `args:` section with:
```yaml
command:
  - sleep
  - infinity
```
After saving and exiting, scale the deployment to 1 replica and wait for the pod to start:

```bash
kubectl scale deployment -n cozy-linstor linstor-controller --replicas 1
```

Start the controller from inside the container:
```bash
kubectl exec -ti -n cozy-linstor deploy/linstor-controller -- bash
```

```bash
root@linstor-controller-85fd6d6496-cdhbc:/# piraeus-entry.sh startController
```

You'll see the error report with the report number:
```
2025-10-31 13:19:46.765 [Main] ERROR LINSTOR/Controller/ffffff SYSTEM - Unknown error during loading data from DB [Report number 6904B76C-00000-000000]
```

Now read the error report:
```bash
root@linstor-controller-85fd6d6496-cdhbc:/# ls -l /var/log/linstor-controller/
root@linstor-controller-85fd6d6496-cdhbc:/# cat /var/log/linstor-controller/ErrorReport-6904B76C-00000-000000.log
```

Example error report:
```
ERROR REPORT 6904B76C-00000-000000

============================================================

Application:                        LINBIT? LINSTOR
Module:                             Controller
Version:                            1.31.3
Build ID:                           3734cb10b55e71a97b4c3004877e43641e820f9e
Build time:                         2025-07-10T06:00:07+00:00
Error time:                         2025-10-31 13:19:46
Node:                               linstor-controller-85fd6d6496-cdhbc
Thread:                             Main

============================================================

Reported error:
===============

Category:                           Error
Class name:                         ImplementationError
Class canonical name:               com.linbit.ImplementationError
Generated at:                       Method 'loadCoreObjects', Source file 'DatabaseLoader.java', Line #680

Error message:                      Unknown error during loading data from DB

Call backtrace:

    Method                                   Native Class:Line number
    loadCoreObjects                          N      com.linbit.linstor.dbdrivers.DatabaseLoader:680
    loadCoreObjects                          N      com.linbit.linstor.core.DbDataInitializer:169
    initialize                               N      com.linbit.linstor.core.DbDataInitializer:101
    startSystemServices                      N      com.linbit.linstor.core.ApplicationLifecycleManager:91
    start                                    N      com.linbit.linstor.core.Controller:379
    main                                     N      com.linbit.linstor.core.Controller:635

Caused by:
==========

Category:                           LinStorException
Class name:                         DatabaseException
Class canonical name:               com.linbit.linstor.dbdrivers.DatabaseException
Generated at:                       Method 'getInstance', Source file 'ObjectProtectionFactory.java', Line #89

Error message:                      ObjProt (/resources/GLD-CSXHK-006/PVC-91C1486F-CFE9-41E2-80E1-86477B187F2D) not found!

ErrorContext:


Call backtrace:

    Method                                   Native Class:Line number
    getInstance                              N      com.linbit.linstor.security.ObjectProtectionFactory:89
    getObjectProtection                      N      com.linbit.linstor.dbdrivers.AbsDatabaseDriver:288
    load                                     N      com.linbit.linstor.core.objects.ResourceDbDriver:173
    load                                     N      com.linbit.linstor.core.objects.ResourceDbDriver:47
    loadAll                                  N      com.linbit.linstor.dbdrivers.k8s.crd.K8sCrdEngine:237
    loadAll                                  N      com.linbit.linstor.dbdrivers.AbsDatabaseDriver:180
    loadCoreObjects                          N      com.linbit.linstor.dbdrivers.DatabaseLoader:444
    loadCoreObjects                          N      com.linbit.linstor.core.DbDataInitializer:169
    initialize                               N      com.linbit.linstor.core.DbDataInitializer:101
    startSystemServices                      N      com.linbit.linstor.core.ApplicationLifecycleManager:91
    start                                    N      com.linbit.linstor.core.Controller:379
    main                                     N      com.linbit.linstor.core.Controller:635


END OF ERROR REPORT.
```

You are looking for messages like this one:

```console
Error message: ObjProt (/resources/GLD-CSXHK-006/PVC-91C1486F-CFE9-41E2-80E1-86477B187F2D) not found!
```

or

```console
Error message: Database entry of table LAYER_DRBD_VOLUMES could not be restored.
ErrorContext:   Details:     Primary key: LAYER_RESOURCE_ID = '4804', VLM_NR = '0'
```

These tell us what resource is missing or broken.


## Backup and analyze

Before making any changes, save all CRs for analysis and recovery:

```bash
kubectl get crds | grep -o ".*.internal.linstor.linbit.com" | \
  xargs kubectl get crds -ojson > crds.json

kubectl get crds | grep -o ".*.internal.linstor.linbit.com" | \
  xargs -I{} sh -xc "kubectl get {} -ojson > {}.json"

tar czvf backup-$(date +%d.%m.%Y).tgz *.json
```

CRs have cryptic names, so it's convenient to download all of them as JSON and explore them with convenient tools on your workstation.

{{% alert color="warning" %}}
:warning: **Backup via storage apiVersion**

The plain `kubectl get` commands above query the CRDs via the discovered served apiVersion, which can drop newer fields (notably `LayerDrbdResources.spec.tcp_port_list`) — see [CRD API versions and field visibility](#crd-api-versions-and-field-visibility). If you intend to use the backup for restore, fetch each CRD via the storage apiVersion explicitly:

```bash
STORAGE_VERSION=$(kubectl get crd layerdrbdresources.internal.linstor.linbit.com -o json \
  | jq -r '.spec.versions[] | select(.storage==true) | .name')

for crd in $(kubectl get crds | grep -o '.*\.internal\.linstor\.linbit\.com'); do
  resource=$(echo "$crd" | cut -d. -f1)
  kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/${resource}" > "${crd}.json"
done
```
{{% /alert %}}


## Fix the database

{{% alert color="warning" %}}
:warning: DESTRUCTIVE ACTION!

If you can't fix broken CRs other way than deleting it, you may delete offending ones using plain `kubectl delete`. Keep in
mind that when you delete CRs, the physical volumes will remain as orphan volumes on the storage nodes. They won't be
automatically managed by LINSTOR anymore. You should manually clean them up later if needed.
{{% /alert %}}

### Method 1: Using a helper script

A helper script `linstor-find-db.sh` can be used to find resources by different criteria:

```bash
#!/usr/bin/env bash
set -euo pipefail

layer_resource_id=""
vlm_nr=""
resource_name=""
node_name=""

for kv in "$@"; do
  k="${kv%%=*}"
  v="${kv#*=}"
  case "$k" in
    layer_resource_id) layer_resource_id="$v" ;;
    vlm_nr) vlm_nr="$v" ;;
    resource_name) resource_name="$v" ;;
    node_name) node_name="$v" ;;
    *) echo "Unknown key: $k" >&2; exit 2 ;;
  esac
done

shopt -s nullglob
files=(*.internal.linstor.linbit.com.json)
if ((${#files[@]}==0)); then
  echo "No *.internal.linstor.linbit.com.json files found" >&2
  exit 1
fi

if [[ -n "$layer_resource_id" && -n "$vlm_nr" ]]; then
  cat "${files[@]}" \
  | jq -r --arg lrid "$layer_resource_id" --arg vlnr "$vlm_nr" '
      .items[]?
      | select(.spec.layer_resource_id == ($lrid|tonumber) and .spec.vlm_nr == ($vlnr|tonumber))
      | "\(.kind).\(.apiVersion|split("/")[0])/\(.metadata.name)"
    '
  exit 0
fi

if [[ -n "$resource_name" && -n "$node_name" ]]; then
  cat "${files[@]}" \
  | jq -r --arg res "$resource_name" --arg node "$node_name" '
      .items[]?
      | select((.spec.resource_name|tostring|ascii_upcase) == ($res|tostring|ascii_upcase)
            and (.spec.node_name|tostring|ascii_upcase) == ($node|tostring|ascii_upcase))
      | "\(.kind).\(.apiVersion|split("/")[0])/\(.metadata.name)"
    '
  exit 0
fi

echo "Usage:
  $(basename "$0") layer_resource_id=NUM vlm_nr=NUM
  $(basename "$0") resource_name=NAME node_name=NAME" >&2
exit 2
```

Save it as `linstor-find-db.sh`, make it executable and use it to find problematic resources.

#### Example 1: Missing ObjProt

If the error is about missing ObjProt for a specific resource:

```console
Error message: ObjProt (/resources/GLD-CSXHK-006/PVC-91C1486F-CFE9-41E2-80E1-86477B187F2D) not found!
```

Find all resources for that resource and node:
```bash
chmod +x linstor-find-db.sh
./linstor-find-db.sh resource_name=PVC-91C1486F-CFE9-41E2-80E1-86477B187F2D node_name=GLD-CSXHK-006
```

Example output:
```
LayerResourceIds.internal.linstor.linbit.com/b3e34e9fe5a79d4e8753d0ad4107d0af969d8faaefb88fbd68316950fa2a9242
LayerResourceIds.internal.linstor.linbit.com/dcbff8f66de95d7c6148b3fbb3a9934d226ffb6dfd405c8394ae5454dc87d348
Resources.internal.linstor.linbit.com/43319bec4ca2bbc21324663a9b716c3e4a7ba2607f0fa513dcc59172a1b37270
Volumes.internal.linstor.linbit.com/4ef559b8fe14b58647c99a76a2d3a11f9bbf2b413a448eaf3771777f673c0b4c
```

Delete them all at once:
```bash
kubectl delete $(./linstor-find-db.sh resource_name=PVC-91C1486F-CFE9-41E2-80E1-86477B187F2D node_name=GLD-CSXHK-006)
```

#### Example 2: Missing LayerDRBD volume

If the error is about missing LayerDRBD volume:

```console
Error message: Database entry of table LAYER_DRBD_VOLUMES could not be restored.
ErrorContext:   Details:     Primary key: LAYER_RESOURCE_ID = '4804', VLM_NR = '0'
```

Find resources by layer_resource_id and vlm_nr:
```bash
./linstor-find-db.sh layer_resource_id=4804 vlm_nr=0
```

Example output:
```
LayerStorageVolumes.internal.linstor.linbit.com/5b597f878f6bb586ddd7d7dc3bbddacbdabedf511861a411712440f66cc61a52
```

Delete it:
```bash
kubectl delete $(./linstor-find-db.sh layer_resource_id=4804 vlm_nr=0)
```

#### Example 3: Duplicate TCP ports on a node

If the error report mentions a TCP port allocation conflict:

```console
Error message: cozy01's TCP port 7012 is already in use
```

with the stacktrace pointing at `DynamicNumberPoolImpl.allocate` → `DrbdRscData.setPorts` → `LayerDrbdRscDbDriver.loadImpl`, this means two different `LayerDrbdResources` records on the same node hold the same value in `spec.tcp_port_list`. On controller startup, the second `allocate(port)` call against the node's port pool throws `ValueInUseException`.

This can happen after `toggle-disk` operations or restore from snapshot/backup on LINSTOR versions affected by a regression introduced in v1.31.2 (when TCP ports were moved to a per-node pool); tracked upstream in [LINBIT/linstor-server#476](https://github.com/LINBIT/linstor-server/pull/476).

To find the duplicate records, query through the storage apiVersion (the field is hidden via older served versions — see [CRD API versions and field visibility](#crd-api-versions-and-field-visibility)):

```bash
PORT=7012        # from the error message
NODE=COZY01      # from the error message, uppercase

kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/layerdrbdresources" \
  | jq -r --arg p "[$PORT]" '.items[] | select(.spec.tcp_port_list == $p) | .spec.layer_resource_id' \
  | while read lri; do
      kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/layerresourceids" \
        | jq -r --argjson l "$lri" '.items[] | select(.spec.layer_resource_id == $l and .spec.layer_resource_kind == "DRBD") | [.spec.layer_resource_id, .spec.node_name, .spec.resource_name] | @tsv'
    done
```

Expected output: more than one record on the same node. For example:

```console
147   COZY02   PVC-EF2A414E-4D11-4660-B292-53DB0DD80A84
142   COZY03   PVC-EF2A414E-4D11-4660-B292-53DB0DD80A84
627   COZY01   PVC-31690526-8027-412F-9F13-2766E8D26341    <- duplicate on COZY01
633   COZY01   PVC-E36C9A57-0DF1-452E-BAD3-CB1117B8D995    <- duplicate on COZY01
```

In this example the legitimate resource is `PVC-EF2A414E`, with replicas on `COZY02` and `COZY03`, both with port `7012` (DRBD resources use the same port across all peers — this is correct). The two records on `COZY01` belong to different resources but share that same port; only one of them can stay.

Before deleting, identify the orphan by cross-checking:

1.  **PV existence**: does the underlying `PersistentVolume` still exist?

    ```bash
    kubectl get pv pvc-31690526-8027-412f-9f13-2766e8d26341
    kubectl get pv pvc-e36c9a57-0df1-452e-bad3-cb1117b8d995
    ```

    `NotFound` means the PV was removed but the LINSTOR records remained — safe to delete.

2.  **Peer replica consistency**: do all replicas of the resource hold the same `tcp_port_list`?

    ```bash
    RSC=PVC-31690526-8027-412F-9F13-2766E8D26341
    kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/layerresourceids" \
      | jq -r --arg r "$RSC" '.items[] | select(.spec.resource_name == $r and .spec.layer_resource_kind == "DRBD") | .spec.layer_resource_id' \
      | while read l; do
          kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/layerdrbdresources" \
            | jq -r --argjson l "$l" '.items[] | select(.spec.layer_resource_id == $l) | [.spec.layer_resource_id, .spec.tcp_port_list, .spec.flags] | @tsv'
        done
    ```

    Inconsistent port lists across replicas of the same resource indicate corruption: the resource is broken on the LINSTOR side and is a candidate for cleanup.

3.  **DRBD flags**: `spec.flags` on `LayerDrbdResources` is a bitmask over `DrbdRscFlags`:

    | Flag | Value |
    | ---- | ----- |
    | `CLEAN` | 1 |
    | `DELETE` | 2 |
    | `DISKLESS` | 4 |
    | `DISK_ADD_REQUESTED` | 8 |
    | `DISK_ADDING` | 16 |
    | `DISK_REMOVE_REQUESTED` | 32 |
    | `DISK_REMOVING` | 64 |
    | `INITIALIZED` | 128 |
    | `FROM_BACKUP` | 256 |
    | `FORCE_NEW_METADATA` | 512 |
    | `INVALIDATE` | 1024 |

    A record with `flags=4` (DISKLESS without INITIALIZED) is a tiebreaker replica that never reached steady state — frequently a leftover of a botched `toggle-disk`.

Use `linstor-find-db.sh` from [Method 1](#method-1-using-a-helper-script) to delete the orphan and all its related records. `linstor-find-db.sh` does not return the resource-level definitions; fetch them separately and add to the delete list:

```bash
RSC=PVC-31690526-8027-412F-9F13-2766E8D26341
for kind in resourcedefinitions layerdrbdresourcedefinitions volumedefinitions layerdrbdvolumedefinitions; do
  kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/$kind" \
    | jq -r --arg r "$RSC" '.items[] | select(.spec.resource_name == $r) | "\(.kind).internal.linstor.linbit.com/\(.metadata.name)"'
done
```

Then [iterate](#iterative-fixing) — restart the controller, get the next error report, fix the next conflict.

#### Example 4: Missing tcp_port_list on LayerDrbdResources

If the error report mentions:

```console
Error message: Node: 'cozyXX', Rsc: 'pvc-XXX' did not have tcpPorts stored!
```

The `LayerDrbdResources` record for that resource on that node has no `tcp_port_list` field. This typically happens after a restore from a backup that was taken through an older served apiVersion (which strips the field — see [CRD API versions and field visibility](#crd-api-versions-and-field-visibility)).

To find all affected records via the storage apiVersion:

```bash
kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/layerdrbdresources" \
  | jq -r '.items[] | select(.spec.tcp_port_list == null or .spec.tcp_port_list == "") | .spec.layer_resource_id' \
  | while read lri; do
      kubectl get --raw "/apis/internal.linstor.linbit.com/${STORAGE_VERSION}/layerresourceids" \
        | jq -r --argjson l "$lri" '.items[] | select(.spec.layer_resource_id == $l and .spec.layer_resource_kind == "DRBD") | [.spec.layer_resource_id, .spec.node_name, .spec.resource_name] | @tsv'
    done
```

For each affected record, decide between two paths:

-   **Salvageable**: peer replicas of the same resource have a consistent non-null `tcp_port_list`. Patch the affected record with the same value:

    ```bash
    kubectl patch layerdrbdresources.internal.linstor.linbit.com/<name> \
      --type=merge --patch '{"spec":{"tcp_port_list":"[7018]"}}'
    ```

-   **Already broken**: PV is `NotFound`, or peer replicas have inconsistent ports, or it's a stale tiebreaker (`flags=4`). Use the [Example 3](#example-3-duplicate-tcp-ports-on-a-node) cleanup procedure to remove the resource and all its related records.

### Iterative fixing

After deleting the problematic resources, try to start the controller again from inside the container:

```bash
piraeus-entry.sh startController
```

If it crashes again, you'll get a new error report with a different resource. Repeat the process:
1. Read the error report to identify the problematic resource
2. Find and delete it
3. Try to start the controller again

Continue until the controller starts successfully:

```console
2025-10-31 13:42:17.483 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Core objects load from database is in progress
2025-10-31 13:42:19.190 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Core objects load from database completed
...
2025-10-31 13:42:27.309 [Main] INFO  LINSTOR/Controller/ffffff SYSTEM - Controller initialized
```


## Restart controller

After you've fixed the CR-based database, you need to restore the linstor-controller deployment to its original state.
Exit from the container and delete the modified deployment so the Piraeus operator recreates it:

```bash
kubectl delete deployment -n cozy-linstor linstor-controller
```

Bring the piraeus operator controller back:

```bash
kubectl scale deployment -n cozy-linstor piraeus-operator-controller-manager --replicas 1
```

It will reconcile the linstor-controller deployment and start it with the original entrypoint.

## Restore to the original state

If something went wrong, and you are lost, it's possible to restore at least what you had before the fixing.

{{% alert color="warning" %}}
:warning: **Verify the backup was taken via the storage apiVersion**

If your backup was produced with plain `kubectl get -o json`, it may be missing newer fields (notably `LayerDrbdResources.spec.tcp_port_list`) — see [CRD API versions and field visibility](#crd-api-versions-and-field-visibility). Restoring such a backup creates records that look intact but cause `linstor-controller` to crash with `did not have tcpPorts stored!` — see [Example 4](#example-4-missing-tcp_port_list-on-layerdrbdresources). Before restoring, sanity-check the JSON files for the affected field, e.g. `jq '[.items[] | select(.spec.tcp_port_list != null)] | length' layerdrbdresources.internal.linstor.linbit.com.json` should match the number of items in that CRD.
{{% /alert %}}

```bash
# get saved files in another directory
mkdir restore; cd restore
tar xzf ../backup-*.tgz

# drop ALL CRs by CRD names, using json definitions for that (all CRs are removed when you delete CRD)
kubectl delete -f crds.json
# restore definitions (please notice `create` instead of usual `apply`
kubectl create -f crds.json

# restore all resources
kubectl get crds | grep -o ".*.internal.linstor.linbit.com" | xargs -I{} sh -xc "kubectl create -f {}.json"
```

Now you can start again.
