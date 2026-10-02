---
title: "Troubleshooting Flux CD"
linkTitle: "Flux CD"
description: "Explains how to resolve Flux CD errors."
weight: 10
---

## Diagnosing `install retries exhausted` error

Sometimes you can face with the error:

```console
# kubectl get hr -A -n cozy-dashboard dashboard
NAMESPACE          NAME          AGE   READY   STATUS
cozy-dashboard     dashboard     15m   False   install retries exhausted
```

You can try to figure out by checking events:

```bash
kubectl describe hr -n cozy-dashboard dashboard
```

if `Events: <none>` then suspend and resume the release:

```bash
kubectl patch hr -n cozy-dashboard dashboard -p '{"spec": {"suspend": true}}' --type=merge
kubectl patch hr -n cozy-dashboard dashboard -p '{"spec": {"suspend": null}}' --type=merge
```

and check the events again:

```bash
kubectl describe hr -n cozy-dashboard dashboard
```
