---
title: "Troubleshooting LINSTOR CrashLoopBackOff related to a broken database"
linkTitle: "LINSTOR: broken database"
description: "Explains how to resolve LINSTOR CrashLoopBackOff related to a broken database."
weight: 110
---

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


## Example of logs

LINSTOR controller is in a crash loop.
We enabled the `TRACE` log level and see the following in the logs:

```bash
[Main] TRACE LINSTOR/Controller/ffffff SYSTEM - Loaded    4 NODESs
[Main] TRACE LINSTOR/Controller/ffffff SYSTEM - Loading all RESOURCE_DEFINITIONSs
[OkHttp Dispatcher] TRACE io.fabric8.kubernetes.client.http.HttpLoggingInterceptor/ -HTTP START-
[OkHttp Dispatcher] TRACE io.fabric8.kubernetes.client.http.HttpLoggingInterceptor/ > GET https://172.16.0.1:443/apis/internal.linstor.linbit.com/v1-27-1/resourcedefinitions                                                                                                                                                                                                                          
...
[Main] ERROR LINSTOR/Controller/ffffff SYSTEM - Unknown error during loading data from DB [Report number 6792D9CE-00000-000000]
...
[Thread-2] INFO  LINSTOR/Controller/0daedc SYSTEM - Shutdown in progress
```

We see that the controller is loading resource definitions and fails with an unknown error.
Report number is present, but not very useful at the moment since controller can't start to display it,
and the file disappears with restarted container as well.

If you are lucky to *know what action resulted in disrupting the `linstor-controller`*,
you can try to skip the next section and try to fix the offending CRs.


## Obtain the error report

LINSTOR controller creates a file in the `/var/log/linstor-controller/` directory inside container with verbose stack trace.
Unfortunately, it's hard to see it since it gets deleted immediately.
With vanilla piraeus-operator, you can work around this by changing the entrypoint of the container to keep it running after crash.

To be able to see the error report, you need to:

1.  Stop the Piraeus operator controller (scale its deployment to zero).
1.  Replace the entrypoint of the `linstor-controller` container with `sleep infinity`.
1.  Remove probes to avoid restarting the container.
1.  Wait until the container starts, `exec` into it and run the controller manually.
1.  After the controller crashes, read the error report.

Do not bother saving the `linstor-controller` deployment manifest since Piraeus operator will reconcile it back later.

```bash
kubectl -n storage scale deployment/piraeus-operator-controller-manager --replicas 0
kubectl -n storage edit deployment/linstor-controller
```

An editor will open.
Delete the whole `livenessProbe` and `startupProbe` sections. 
Find the `linstor-controller` container section (the main container).
There, replace `args:` section with `command: ["sleep", "infinity"]`.
After saving and exiting, wait for the pod to restart and init.

Start the controller from inside the container:
```bash
kubectl -n storage exec -ti deploy/linstor-controller -- bash
```

```bash
root@linstor-controller-75b886bc59-cxwqd:/# piraeus-entry.sh startController
2025-01-31 21:18:57.587 [Thread-2] INFO  LINSTOR/Controller/6bc981 SYSTEM - Shutdown complete
```

Find the error report(s) and read them:
```bash
root@linstor-controller-75b886bc59-cxwqd:/# ls -l /var/log/linstor-controller/
root@linstor-controller-75b886bc59-cxwqd:/# cat /var/log/linstor-controller/ErrorReport-67935661-00000-000000.log
```

You are looking for messages like this one:

```console
Error message: ObjProt (/resourcedefinitions/PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09) not found!
```

## Fix the database

In the previous example, we see that the resource `PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09` is missing. This happened
because linstor-controller was instructed to delete that volume and CR was already deleted from CR database, but
underlying resources were not deleted yet. CR-based database is not transactional, that's why it's possible to have such
a mess.

CRs have cryptic names, so it's convenient to download all of them as JSON and explore them with convenient tools on your
workstation.

Download all CRs:

```bash
# get snapshot of definitions, Piraeus devs will be happy to see it in the bug report if you create any
# single file holds all
kubectl get crds | grep -o ".*.internal.linstor.linbit.com" | xargs kubectl get -o json crds > crds.json
# get all resources, one file per crd
kubectl get crds | grep -o ".*.internal.linstor.linbit.com" | xargs -I{} sh -xc "kubectl get -o json {} > {}.json"
# make an archive just in case
tar czf crashloop.tar.gz *.json
```

Find all resources that reference the broken one:

```console
$ grep -ri 'PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09'
./propscontainers.internal.linstor.linbit.com.json: "props_instance": "/RESOURCEDEFINITIONS/PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09"
./propscontainers.internal.linstor.linbit.com.json: "props_instance": "/RESOURCEDEFINITIONS/PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09"
./propscontainers.internal.linstor.linbit.com.json: "props_instance": "/RESOURCEDEFINITIONS/PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09"
./propscontainers.internal.linstor.linbit.com.json: "props_instance": "/RESOURCEDEFINITIONS/PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09"
./resourcedefinitions.internal.linstor.linbit.com.json: "resource_dsp_name": "pvc-2abc1180-faeb-4b82-b35f-7b7f1fbf6b09",
./resourcedefinitions.internal.linstor.linbit.com.json: "resource_name": "PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09",
./layerdrbdresourcedefinitions.internal.linstor.linbit.com.json: "resource_name": "PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09",
```

{{% alert color="warning" %}}
:warning: DESTRUCTIVE ACTION!

If you can't fix broken CRs other way than deleting it, you may delete offending ones using plain `kubectl delete`. But
at the moment when CR set is fixed and can be compiled into the database, LINSTOR will start and also DELETE all
physical volumes which are not described in current CRs. So, you should first find and backup the physical volume, then
delete CR.

If there's a lot of broken resources, you can use `jq` to delete them all at once:

```bash
# this will print (not execute) delete commands
jq --arg search "PVC-2ABC1180-FAEB-4B82-B35F-7B7F1FBF6B09" \
  -r '.items[] | tostring | select(test($search; "i")) | fromjson | "kubectl delete \(.kind)/\(.metadata.name)"' \
  *.internal.linstor.linbit.com.json
```
{{% /alert %}}


## Restart controller

After you performed some actions with CR-based database, try to start the controller again, from shell inside the same
controller pod which was created to investigate the problem.
If something is wrong again, repeat the procedure.

When controller starts and not crashes, simply bring the piraeus operator controller back:

```console
$ kubectl -n storage scale deployment/piraeus-operator-controller-manager --replicas 1
```

It will reconcile the linstor-controller deployment and start it with the original entrypoint.

## Restore to the original state

If something went wrong, and you are lost, it's possible to restore at least what you had before the fixing.

```bash
# get saved files in another directory
mkdir restore; cd restore
tar xzf ../crashloop.tar.gz

# drop ALL CRs by CRD names, using json definitions for that (all CRs are removed when you delete CRD)
kubectl delete -f crds.json
# restore definitions (please notice `create` instead of usual `apply`
kubectl create -f crds.json

# restore all resources
kubectl get crds | grep -o ".*.internal.linstor.linbit.com" | xargs -I{} sh -xc "kubectl create -f {}.json"
```

Now you can start again.
