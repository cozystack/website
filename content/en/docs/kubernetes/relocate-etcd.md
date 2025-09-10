---
title: How to relocate replica for tenant etcd clusters
linkTitle: How to relocate etcd
description: "How to back up and restore resources in cozystack cluster."
weight: 100
---

## How to relocate replica for tenant etcd clusters

Currently management operations for tenant etcd clusters are not automated.

You'd need to install `kubectl-etcd` plugin first:

```bash
go install github.com/aenix-io/etcd-operator/cmd/kubectl-etcd@latest
```

Then you can manage replicas as follows in the example below:

```bash
NAMESPACE=tenant-demo
RM=etcd-2
POD=$(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=etcd --no-headers | awk '$2 == "1/1" && $1 != "'$RM'" {print $1; exit;}')
RMID=$(kubectl etcd -n $NAMESPACE -p $POD members | awk '$2 == "'$RM'" {print $1}')

kubectl delete -n $NAMESPACE pvc/data-$RM pod/$RM
if [ -n $RMID ]; then
  kubectl etcd -n $NAMESPACE -p $POD remove-member "$RMID"
fi
kubectl etcd -n $NAMESPACE -p $POD add-member "https://$RM.etcd-headless.$NAMESPACE.svc:2380"

kubectl wait --for=condition=ready pod $RM --timeout=2m

kubectl etcd -n $NAMESPACE -p $RM members
```

Script above will remove etcd-2 replica from the etcd cluster and add it back.
