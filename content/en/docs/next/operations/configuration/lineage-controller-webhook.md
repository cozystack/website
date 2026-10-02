---
title: "The Lineage Controller Webhook"
linkTitle: "Lineage Controller Webhook"
description: "What the lineage-controller-webhook does, how it's deployed, and the one knob worth knowing about."
weight: 40
---

The **lineage controller webhook** is a mutating admission webhook shipped as
part of the `cozystack.cozystack-engine` Package. On every CREATE and UPDATE
of a tenant `Pod`, `Secret`, `Service`, `PersistentVolumeClaim`,
`Ingress`, or `WorkloadMonitor` it walks up the ownership graph and stamps the
owning Cozystack `Application`'s identity onto the resource as labels
(`apps.cozystack.io/application.{group,kind,name}`). The Cozystack dashboard,
the aggregated API server, and the SchedulingClass mechanism all rely on those
labels.

The webhook is registered with `failurePolicy: Fail`, so the kube-apiserver
must be able to reach a healthy webhook pod for tenant CREATE/UPDATE traffic
to succeed.

## Default deployment shape

The chart deploys a single `Deployment` modelled on the `cozystack-api` shape:

- **2 replicas** (override via `replicas`).
- **Soft `nodeAffinity`** preferring `node-role.kubernetes.io/control-plane`
  (`Exists` matches both Talos's empty value and k3s/kubeadm's `"true"`). The
  preference is *soft* — pods land on a control-plane node when one is
  reachable, and on any worker otherwise. No override is needed for managed
  Kubernetes (EKS / AKS / GKE), Cozy-in-Cozy tenant clusters, or any other
  cluster where control-plane nodes aren't visible: the webhook simply
  schedules elsewhere.
- **Permissive `tolerations`** (`{operator: Exists}`) so a control-plane node
  with `NoSchedule` taints accepts the pod when the soft affinity is
  satisfiable.
- **Soft `podAntiAffinity`** on `kubernetes.io/hostname` so replicas
  best-effort spread across nodes.
- **`PodDisruptionBudget`** with `maxUnavailable: 1`. At `replicas: 2+` it
  caps disruption to one pod; at `replicas: 1` it's a useful no-op.
- **Service `spec.trafficDistribution: PreferClose`** so the apiserver
  prefers a webhook endpoint on its own node when one exists, and
  transparently falls over to a remote endpoint otherwise. Requires
  Kubernetes ≥ 1.31; older clusters silently fall back to default
  cluster-wide distribution (still safe, just no locality preference).

This shape works as-is on every Kubernetes distribution Cozystack supports.
You shouldn't need to override anything in normal operation.

## Increasing replicas

If you want more than two replicas — for instance, to keep one webhook pod
co-located with each apiserver on a five-node control plane — override the
`replicas` value via the `cozystack.cozystack-engine` Package, the same way
you'd override any other component (see
[Components]({{% ref "/docs/next/operations/configuration/components" %}})):

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-engine
  namespace: cozy-system
spec:
  variant: default
  components:
    lineage-controller-webhook:
      values:
        lineageControllerWebhook:
          replicas: 5
```

## `localK8sAPIEndpoint.enabled` is deprecated

The chart still exposes `localK8sAPIEndpoint.enabled`, which when set to
`true` injects `KUBERNETES_SERVICE_HOST=status.hostIP` and
`KUBERNETES_SERVICE_PORT=6443` so the webhook talks to the apiserver on its
own node. It was originally added to avoid latency on the
webhook-to-apiserver path. It's now defaulted to `false` and slated for
removal once the latency motivation is addressed in the webhook itself.

{{% alert title="Important" color="warning" %}}
Do not enable `localK8sAPIEndpoint.enabled` with the default chart values.
The injected `status.hostIP` is only valid when the pod runs on a node that
hosts a kube-apiserver, and the chart's soft control-plane affinity does not
guarantee that. With the flag enabled and the pod scheduled off a
control-plane node, the controller crash-loops dialing a non-apiserver IP —
and combined with `failurePolicy: Fail` that means a tenant CREATE/UPDATE
outage.
{{% /alert %}}

## Verifying the deployment

```bash
kubectl -n cozy-system get deploy lineage-controller-webhook
kubectl -n cozy-system get pods -l app=lineage-controller-webhook
kubectl -n cozy-system get svc lineage-controller-webhook -o yaml | grep trafficDistribution
```

A quick end-to-end check, exercising the webhook through the apiserver:

```bash
kubectl create ns lineage-webhook-test
kubectl -n lineage-webhook-test create service clusterip probe \
  --clusterip=None --dry-run=server
kubectl delete ns lineage-webhook-test
```

The dry-run CREATE goes through the mutating admission webhook; if the
webhook isn't reachable, it fails with `failed calling webhook
"lineage.cozystack.io"`.
