---
title: "Frequently asked questions"
linkTitle: "FAQ"
description: "Flux and the GitOps Toolkit frequently asked questions."
weight: 144
aliases:
  - /docs/faq
  - /docs/guides/faq
---

{{% alert title="Troubleshooting" %}}
Troubleshooting advice can be found on our [Troubleshooting Cheatsheet](/docs/operations/troubleshooting/).
{{% /alert %}}



## Configuration

### How to Enable KubeSpan

Talos Linux provides a full mesh WireGuard network for your cluster.

To enable this functionality, you need to configure [KubeSpan](https://www.talos.dev/v1.8/talos-guides/network/kubespan/) and [Cluster Discovery](https://www.talos.dev/v1.2/kubernetes-guides/configuration/discovery/) in your Talos Linux configuration:

```yaml
machine:
  network:
    kubespan:
      enabled: true
cluster:
  discovery:
    enabled: false
```

Since KubeSpan encapsulates traffic into a WireGuard tunnel, Kube-OVN should also be configured with a lower MTU value.

To achieve this, add the following to the Cozystack ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  values-kubeovn: |
    kube-ovn:
      mtu: 1222
```

## Operations

### How to enable access to dashboard via ingress-controller

Update your `ingress` application and enable `dashboard: true` option in it.
Dashboard will become available under: `https://dashboard.<your_domain>`

### What if my cloud provider does not support MetalLB

You still have the opportunity to expose the main ingress controller using the external IPs method.

Take IP addresses of the **external** network interfaces for your nodes.
Add them to the `externalIPs` list in the Ingress configuration:

```bash
kubectl patch -n tenant-root ingresses.apps.cozystack.io ingress --type=merge -p '{"spec":{
  "externalIPs": [
    "192.168.100.11",
    "192.168.100.12",
    "192.168.100.13"
  ]
}}'

kubectl patch -n cozy-system configmap cozystack --type=merge -p '{
  "data": {
    "expose-external-ips": "192.168.100.11,192.168.100.12,192.168.100.13"
  }
}'
```

After that, your Ingress will be available on the specified IPs:

```console
# kubectl get svc -n tenant-root root-ingress-controller
root-ingress-controller   ClusterIP   10.96.91.83   37.27.60.28,65.21.65.173,135.181.169.168   80/TCP,443/TCP   133d
```

### How to cleanup etcd state

Sometimes you might want to flush etcd state from a node.
This can be done with Talm or talosctl using the following commands:

{{< tabs name="etcd reset tools" >}}
{{% tab name="Talm" %}}

Replace `nodeN` with the name of the failed node, for instance, `node0.yaml`:

```bash
talm reset -f nodes/nodeN.yaml --system-labels-to-wipe=EPHEMERAL --graceful=false --reboot
```

{{% /tab %}}

{{% tab name="talosctl" %}}
```bash
talosctl reset --system-labels-to-wipe=EPHEMERAL --graceful=false --reboot
```

{{% /tab %}}
{{< /tabs >}}

{{% alert color="warning" %}}
:warning: This command will remove the state from the specified node. Use it with caution.
{{% /alert %}}


### How to generate kubeconfig for tenant users

Use the following script:

```bash
user=tenant-root

cluster=$(kubectl config get-contexts | awk '$1 == "*" {print $3}')
token=$(kubectl get secret -n "$user" "$user" -o go-template='{{ printf "%s\n" (index .data "token" | base64decode) }}')

kubectl config view --minify --raw > tenant-kubeconfig
kubectl config --kubeconfig tenant-kubeconfig unset users
kubectl config --kubeconfig tenant-kubeconfig unset contexts
kubectl config --kubeconfig tenant-kubeconfig set "users.$user.token" "$token"  --set-raw-bytes=true
kubectl config --kubeconfig tenant-kubeconfig set "contexts.$user@$cluster.user" "$user"
kubectl config --kubeconfig tenant-kubeconfig set "contexts.$user@$cluster.namespace" "$user"
kubectl config --kubeconfig tenant-kubeconfig set "contexts.$user@$cluster.cluster" "$cluster"
kubectl config --kubeconfig tenant-kubeconfig set current-context "$user@$cluster"
```

in the result, you’ll receive the tenant-kubeconfig file, which you can provide to the user.

### How to configure Cozystack using FluxCD or ArgoCD

Here you can find reference repository to learn how to configure Cozystack services using GitOps approach:

- https://github.com/aenix-io/cozystack-gitops-example

### How to Rotate Certificate Authority

In general, you almost never need to rotate the root CA certificate and key for the Talos API and Kubernetes API.
Talos sets up root certificate authorities with a lifetime of 10 years,
and all Talos and Kubernetes API certificates are issued by these root CAs.

So the rotation of the root CA is only needed if:

- you suspect that the private key has been compromised;
- you want to revoke access to the cluster for a leaked talosconfig or kubeconfig;
- once in 10 years.

#### Rotate CA for a Tenant Kubernetes Cluster

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

#### Rotate CA for the Management Kubernetes Cluster:

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

#### For Talos API

See: https://www.talos.dev/v1.9/advanced/ca-rotation/#talos-api

All commands are like for the management k8s cluster, but with `talosctl` command:

```bash
talosctl rotate-ca -e 12.34.56.77,12.34.56.78,12.34.56.79 \
    --control-plane-nodes 12.34.56.77,12.34.56.78,12.34.56.79 \
    --kubernetes=false \
    --dry-run=false &
```

## Bundles

### How to overwrite parameters for specific components

Moved to the [Bundles reference]({{% ref "docs/operations/bundles#how-to-overwrite-parameters-for-specific-components" %}}).

### How to disable some components from bundle

Moved to the [Bundles reference]({{% ref "docs/operations/bundles#how-to-disable-some-components-from-bundle" %}}).
