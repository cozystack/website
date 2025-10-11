---
title: "Cozystack Troubleshooting Guide"
linkTitle: "Troubleshooting"
description: "This guide shows the initial steps to check your cluster's health and discover problems."
weight: 110
aliases:
  - /docs/troubleshooting
---

This guide shows the initial steps to check your cluster's health and discover problems.
In the bottom of the page you will find links to troubleshooting guides for various Cozystack components and aspects of cluster operations.

## Troubleshooting Checklist

You can use the following commands to check the health of your cluster.

```bash
# === Flux CD ===
# broken Helm Releases are missing
kubectl get hr -A | grep -v True

# === Kubernetes ===
# you have no Nodes that are not in Ready state
kubectl get node

# === LINSTOR ===
alias linstor='kubectl exec -n cozy-linstor deploy/linstor-controller -ti -- linstor'

# LINSTOR nodes are online
linstor node list

# LINSTOR storage-pools are Ok
linstor storage-pool list

# You have no broken resources
linstor resource list --faulty

# === Kube-OVN ===
alias ovn-appctl='kubectl -n cozy-kubeovn exec deploy/ovn-central -c ovn-central -- ovn-appctl' 

# Check Northbound database
ovn-appctl -t /var/run/ovn/ovnnb_db.ctl cluster/status OVN_Northbound

# Check Southbound database
ovn-appctl -t /var/run/ovn/ovnsb_db.ctl cluster/status OVN_Southbound

# make sure that you have
# 1. Same amount of Servers as your control-plane nodes
# 2. IPs are correct
# 3. There are no duplicates (eg. two servers  with the same IP)

# to list your control-plane nodes
kubectl get node -o wide -l node-role.kubernetes.io/control-plane=
```

Additionally, you can check if there are any non-running pods in your cluster:
```bash
kubectl get pod -A | grep -v 'Running\|Completed'
```

## Getting basic information

You can see the logs of main installer by executing:

```bash
kubectl logs -n cozy-system deploy/cozystack -f
```

All the platform components are installed using Flux CD HelmReleases.

You can get all installed HelmReleases:

```console
# kubectl get hr -A
NAMESPACE                        NAME                        AGE    READY   STATUS
cozy-cert-manager                cert-manager                4m1s   True    Release reconciliation succeeded
cozy-cert-manager                cert-manager-issuers        4m1s   True    Release reconciliation succeeded
cozy-cilium                      cilium                      4m1s   True    Release reconciliation succeeded
cozy-cluster-api                 capi-operator               4m1s   True    Release reconciliation succeeded
cozy-cluster-api                 capi-providers              4m1s   True    Release reconciliation succeeded
cozy-dashboard                   dashboard                   4m1s   True    Release reconciliation succeeded
cozy-fluxcd                      cozy-fluxcd                 4m1s   True    Release reconciliation succeeded
cozy-grafana-operator            grafana-operator            4m1s   True    Release reconciliation succeeded
cozy-kamaji                      kamaji                      4m1s   True    Release reconciliation succeeded
cozy-kubeovn                     kubeovn                     4m1s   True    Release reconciliation succeeded
cozy-kubevirt-cdi                kubevirt-cdi                4m1s   True    Release reconciliation succeeded
cozy-kubevirt-cdi                kubevirt-cdi-operator       4m1s   True    Release reconciliation succeeded
cozy-kubevirt                    kubevirt                    4m1s   True    Release reconciliation succeeded
cozy-kubevirt                    kubevirt-operator           4m1s   True    Release reconciliation succeeded
cozy-linstor                     linstor                     4m1s   True    Release reconciliation succeeded
cozy-linstor                     piraeus-operator            4m1s   True    Release reconciliation succeeded
cozy-mariadb-operator            mariadb-operator            4m1s   True    Release reconciliation succeeded
cozy-metallb                     metallb                     4m1s   True    Release reconciliation succeeded
cozy-monitoring                  monitoring                  4m1s   True    Release reconciliation succeeded
cozy-postgres-operator           postgres-operator           4m1s   True    Release reconciliation succeeded
cozy-rabbitmq-operator           rabbitmq-operator           4m1s   True    Release reconciliation succeeded
cozy-redis-operator              redis-operator              4m1s   True    Release reconciliation succeeded
cozy-telepresence                telepresence                4m1s   True    Release reconciliation succeeded
cozy-victoria-metrics-operator   victoria-metrics-operator   4m1s   True    Release reconciliation succeeded
tenant-root                      tenant-root                 4m1s   True    Release reconciliation succeeded
```

Normally all of them should be `Ready` and `Release reconciliation succeeded`

## Specific Troubleshooting Guides

### Cluster Bootstrapping

See the [Kubernetes installation troubleshooting]({{% ref "/docs/install/kubernetes/troubleshooting" %}}).

### Cluster Maintenance

#### Remove a failed node from the cluster

See the [Cluster Maintenance > Cluster Scaling]({{% ref "/docs/operations/cluster/scaling" %}}).

### Flux CD

[Flux CD troubleshooting]({{% ref "/docs/operations/troubleshooting/flux-cd" %}}).

### Kube-OVN

[Kube-OVN troubleshooting]({{% ref "/docs/operations/troubleshooting/kube-ovn" %}}).

