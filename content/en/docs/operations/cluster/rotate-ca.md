---
title: "How to Rotate Certificate Authority"
linkTitle: "How to rotate CA"
description: "How to Rotate Certificate Authority"
weight: 110
---


Talos sets up root certificate authorities with a lifetime of 10 years,
and all Talos and Kubernetes API certificates are issued by these root CAs.
In general, you almost never need to rotate the root CA certificate and key for the Talos API and Kubernetes API.

Rotation of the root CA is only needed:

- when you suspect that the private key has been compromised;
- when you want to revoke access to the cluster for a leaked `talosconfig` or `kubeconfig`;
- once in 10 years.

### Rotate CA for the Management Kubernetes Cluster:

See: https://www.talos.dev/v1.9/advanced/ca-rotation/#kubernetes-api

```bash
git clone https://github.com/cozystack/cozystack.git
cd packages/core/testing
make apply
make exec
```

Add this to your talosconfig in a pod:

```yaml
client-aenix-new:
    endpoints:
    - 12.34.56.77
    - 12.34.56.78
    - 12.34.56.79
    nodes:
    - 12.34.56.77
    - 12.34.56.78
    - 12.34.56.79
```

Execute in a pod:
```bash
talosctl rotate-ca -e 12.34.56.77,12.34.56.78,12.34.56.79 \
    --control-plane-nodes 12.34.56.77,12.34.56.78,12.34.56.79 \
    --talos=false \
    --dry-run=false &
```

Get a new kubeconfig:
```bash
talm kubeconfig kubeconfig -f nodes/srv1.yaml
```

### Rotate CA for Talos API

See: https://www.talos.dev/v1.9/advanced/ca-rotation/#talos-api

All commands are like for the management k8s cluster, but with `talosctl` command:

```bash
talosctl rotate-ca -e 12.34.56.77,12.34.56.78,12.34.56.79 \
    --control-plane-nodes 12.34.56.77,12.34.56.78,12.34.56.79 \
    --kubernetes=false \
    --dry-run=false &
```

### Rotate CA for a Tenant Kubernetes Cluster

See: https://kamaji.clastix.io/guides/certs-lifecycle/

```bash
export NAME=k8s-cluster-name
export NAMESPACE=k8s-cluster-namespace

kubectl -n ${NAMESPACE} delete secret ${NAME}-ca
kubectl -n ${NAMESPACE} delete secret ${NAME}-sa-certificate

kubectl -n ${NAMESPACE} delete secret ${NAME}-api-server-certificate
kubectl -n ${NAMESPACE} delete secret ${NAME}-api-server-kubelet-client-certificate
kubectl -n ${NAMESPACE} delete secret ${NAME}-datastore-certificate
kubectl -n ${NAMESPACE} delete secret ${NAME}-front-proxy-client-certificate
kubectl -n ${NAMESPACE} delete secret ${NAME}-konnectivity-certificate

kubectl -n ${NAMESPACE} delete secret ${NAME}-admin-kubeconfig
kubectl -n ${NAMESPACE} delete secret ${NAME}-controller-manager-kubeconfig
kubectl -n ${NAMESPACE} delete secret ${NAME}-konnectivity-kubeconfig
kubectl -n ${NAMESPACE} delete secret ${NAME}-scheduler-kubeconfig

kubectl delete po -l app.kubernetes.io/name=kamaji -n cozy-kamaji
kubectl delete po -l app=${NAME}-kcsi-driver
```

Wait for the `virt-launcher-kubernetes-*` pods to restart.
After that, download the new Kubernetes certificate.
