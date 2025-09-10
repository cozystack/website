---
title: How to relocate etcd replicas in tenant clusters
linkTitle: How to relocate etcd replicas
description: "Learn how to relocate replicas of tenant etcd clusters, which are used by tenant Kubernetes clusters."
weight: 100
---

Tenant Kubernetes clusters are using their own etcd clusters, not the one that is used by the management cluster.
Such etcd clusters are deployed in tenants and are available to managed Kubernetes clusters deployed in the tenant and its sub-tenants.

Replicas of a tenant etcd cluster can be relocated between nodes for maintenance reasons.
Currently, management operations for tenant etcd clusters are not automated,
but such a task can be done manually.

First, you need to install the `kubectl-etcd` plugin for `kubectl`:

```bash
go install github.com/aenix-io/etcd-operator/cmd/kubectl-etcd@latest
```

Now you can manage etcd replicas.
The example script shown below removes the `etcd-2` replica from the etcd cluster and then add it back.

```bash
# tenant which the etcd cluster belongs to
NAMESPACE=tenant-demo
# etcd replica
RM=etcd-2
POD=$(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=etcd --no-headers | awk '$2 == "1/1" && $1 != "'$RM'" {print $1; exit;}')
RMID=$(kubectl etcd -n $NAMESPACE -p $POD members | awk '$2 == "'$RM'" {print $1}')

# delete the replica
kubectl delete -n $NAMESPACE pvc/data-$RM pod/$RM
if [ -n $RMID ]; then
  kubectl etcd -n $NAMESPACE -p $POD remove-member "$RMID"
fi

# add the replica back
kubectl etcd -n $NAMESPACE -p $POD add-member "https://$RM.etcd-headless.$NAMESPACE.svc:2380"

kubectl wait --for=condition=ready pod $RM --timeout=2m

kubectl etcd -n $NAMESPACE -p $RM members
```

To learn more about tenant nesting and shared services, read the [Tenants guide]({{% ref "/docs/guides/tenants" %}}).
