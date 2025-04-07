---
title: "Frequently asked questions"
linkTitle: "FAQ"
description: "Flux and the GitOps Toolkit frequently asked questions."
weight: 144
---

{{% alert title="Troubleshooting" %}}
Troubleshooting advice can be found on our [Troubleshooting Cheatsheet](/docs/troubleshooting/).
{{% /alert %}}

## General questions

### Bundles

#### How to overwrite parameters for specific components

You might want to overwrite specific options for the components.
To achieve this, you must specify values in JSON or YAML format using the values-<component> option.

For example, if you want to overwrite `k8sServiceHost` and `k8sServicePort` for cilium,
take a look at its [values.yaml](https://github.com/cozystack/cozystack/blob/238061efbc0da61d60068f5de31d6eaa35c4d994/packages/system/cilium/values.yaml#L18-L19) file.

Then specify these options in the `values-cilium` section of your Cozystack configuration, as shown below:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "distro-full"
  ipv4-pod-cidr: "10.244.0.0/16"
  ipv4-svc-cidr: "10.96.0.0/16"
  values-cilium: |
    cilium:
      k8sServiceHost: 11.22.33.44
      k8sServicePort: 6443
```

#### How to disable some components from bundle

Sometimes you may need to disable specific components within a bundle.
To do this, use the `bundle-disable` option and provide a comma-separated list of the components you want to disable. For example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-full"
  bundle-disable: "linstor,dashboard"
  ipv4-pod-cidr: "10.244.0.0/16"
  ipv4-svc-cidr: "10.96.0.0/16"
```

{{% alert color="warning" %}}
:warning: Disabling components using this option will not remove them if they are already installed. To remove them, you must delete the Helm release manually using the `kubectl delete hr -n <namespace> <component>` command.
{{% /alert %}}

### Configuration

#### How to Enable KubeSpan

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

### Operations

#### How to enable access to dashboard via ingress-controller

Update your `ingress` application and enable `dashboard: true` option in it.  
Dashboard will become available under: `https://dashboard.<your_domain>`

#### How to cleanup etcd state

Sometimes you might want to flush the etcd state from a node. You can use the following command:

```bash
talosctl reset --system-labels-to-wipe=EPHEMERAL --graceful=false --reboot
```

{{% alert color="warning" %}}
:warning: This command will remove the state from the specified node. Use it with caution.
{{% /alert %}}


#### How to generate kubeconfig for tenant users

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

#### How to configure Cozystack using FluxCD or ArgoCD

Here you can find reference repository to learn how to configure Cozystack services using GitOps approach:

- https://github.com/cozystack/cozystack-gitops-example

### How to rotate CA
In general, you almost never need to rotate the root CA certificate and key for the Talos API and Kubernetes API. Talos sets up root certificate authorities with the lifetime of 10 years, and all Talos and Kubernetes API certificates are issued by these root CAs. So the rotation of the root CA is only needed if:
- you suspect that the private key has been compromised;
- you want to revoke access to the cluster for a leaked talosconfig or kubeconfig;
- once in 10 years.

#### For tenant k8s cluster:
See: https://kamaji.clastix.io/guides/certs-lifecycle/
```bash
export NAME=k8s-cluster-name
kubectl delete secret ${NAME}-ca
kubectl delete secret ${NAME}-sa-certificate

kubectl delete secret ${NAME}-api-server-certificate
kubectl delete secret ${NAME}-api-server-kubelet-client-certificate
kubectl delete secret ${NAME}-datastore-certificate
kubectl delete secret ${NAME}-front-proxy-client-certificate
kubectl delete secret ${NAME}-konnectivity-certificate

kubectl delete secret ${NAME}-admin-kubeconfig
kubectl delete secret ${NAME}-controller-manager-kubeconfig
kubectl delete secret ${NAME}-konnectivity-kubeconfig
kubectl delete secret ${NAME}-scheduler-kubeconfig

kubectl delete po -l app.kubernetes.io/name=kamaji -n cozy-kamaji
```

Wait for virt-launcher-kubernetes-* pods restart.
Download new k8s certificate.

#### For managment k8s cluster:
See: https://www.talos.dev/v1.9/advanced/ca-rotation/#kubernetes-api
```bash
git clone https://github.com/cozystack/cozystack.git
cd packages/core/testing
make apply
make exec
```

Add to your talosconfig in pod:
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

Exec in pod:
```bash
talosctl rotate-ca -e 12.34.56.77,12.34.56.78,12.34.56.79  --control-plane-nodes 12.34.56.77,12.34.56.78,12.34.56.79 --talos=false  --dry-run=false &
```

Get new kubeconfig:
```bash
talm kubeconfig kubeconfig -f nodes/srv1.yaml
```

#### For talos API
See: https://www.talos.dev/v1.9/advanced/ca-rotation/#talos-api
All like for managment k8s cluster, but talosctl command:
```bash
talosctl rotate-ca -e 12.34.56.77,12.34.56.78,12.34.56.79  --control-plane-nodes 12.34.56.77,12.34.56.78,12.34.56.79 --kubernetes=false  --dry-run=false &
```
