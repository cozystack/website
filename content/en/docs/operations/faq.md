---
title: "Frequently asked questions"
linkTitle: "FAQ"
description: "Knowledge base with FAQ and advanced configurations"
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
    enabled: true
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
SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl get secret tenant-root -n tenant-root -o go-template='
apiVersion: v1
kind: Config
clusters:
- name: tenant-root
  cluster:
    server: '"$SERVER"'
    certificate-authority-data: {{ index .data "ca.crt" }}
contexts:
- name: tenant-root
  context:
    cluster: tenant-root
    namespace: {{ index .data "namespace" | base64decode }}
    user: tenant-root
current-context: tenant-root
users:
- name: tenant-root
  user:
    token: {{ index .data "token" | base64decode }}
' \
> tenant-root.kubeconfig
```

in the result, you’ll receive the tenant-kubeconfig file, which you can provide to the user.

### How to configure Cozystack using FluxCD or ArgoCD

Here you can find reference repository to learn how to configure Cozystack services using GitOps approach:

- https://github.com/aenix-io/cozystack-gitops-example


### Public-network Kubernetes deployment

A Kubernetes/Cozystack cluster can be deployed using only public networks:

-   Both management and worker nodes have public IP addresses.
-   Worker nodes connect to the management nodes over the public Internet, without a private internal network or VPN.

Such a setup is not recommended for production, but can be used for research and testing,
when hosting limitations prevent provisioning a private network.

To enable this setup when deploying with `talosctl`, add the following data in the node configuration files:

```yaml
cluster:
  controlPlane:
    endpoint: https://<MANAGEMENT_NODE_IP>:6443
```

For `talm`, append the same lines at end of the first node's configuration file, such as `nodes/node1.yaml`.

### How to allocate space on system disk for user storage

Default Talos setup assumes that each node has a primary and secondary disks, used for system and user storage, respectively.
However, it's possible to use a single disk, allocating space for user storage.

This configuration must be applied with the first [`talosctl apply`]({{% ref "/docs/install/kubernetes/talosctl#3-apply-node-configuration" %}})
or [`talm apply`]({{% ref "/docs/install/kubernetes/talm#3-apply-node-configuration" %}})
— the one with the `-i` (`--insecure`) flag.
Applying changes after initialization will not have any effect.

For `talosctl`, append the following lines to `patch.yaml`:

```yaml
---
apiVersion: v1alpha1
kind: VolumeConfig
name: EPHEMERAL
provisioning:
  minSize: 70GiB

---
apiVersion: v1alpha1
kind: UserVolumeConfig
name: data-storage
provisioning:
  diskSelector:
    match: disk.transport == 'nvme'
  minSize: 400GiB
```

For `talm`, append the same lines at end of the first node's configuration file, such as `nodes/node1.yaml`.

Read more in the Talos documentation: https://www.talos.dev/v1.10/talos-guides/configuration/disk-management/.

After applying the configuration, wipe the `data-storage` partition:

```bash
kubectl -n kube-system debug -it --profile sysadmin --image=alpine node/node1

apk add util-linux

umount /dev/nvme0n1p6 ### The partition allocated for user storage
rm -rf /host/var/mnt/data-storage
wipefs -a /dev/nvme0n1p6
exit
```

When the storage is configured, add the new partition to LINSTOR:
```bash
linstor ps cdp zfs node1 nvme0n1p6 --pool-name data --storage-pool data1
```

Check the result:
```bash
linstor sp l
```

Output will be similar to this example:

```text
+---------------------------------------------------------------------------------------------------------------------------------------+
| StoragePool          | Node  | Driver   | PoolName | FreeCapacity | TotalCapacity | CanSnapshots | State | SharedName                 |
|=======================================================================================================================================|
| DfltDisklessStorPool | node1 | DISKLESS |          |              |               | False        | Ok    | node1;DfltDisklessStorPool |
| data                 | node1 | ZFS      | data     |   351.46 GiB |       476 GiB | True         | Ok    | node1;data                 |
| data1                | node1 | ZFS      | data     |   378.93 GiB |       412 GiB | True         | Ok    | node1;data1                |
```

### How to enable Hugepages

Moved to Cluster Configuration, [How to enable Hugepages]({{% ref "/docs/operations/configuration/hugepages" %}}).

### How to Rotate Certificate Authority

Moved to Cluster Maintenance, [How to Rotate Certificate Authority]({{% ref "/docs/operations/cluster/rotate-ca" %}}).

## Bundles

### How to overwrite parameters for specific components

Moved to Cluster configuration, [Components reference]({{% ref "/docs/operations/configuration/components#overwriting-component-parameters" %}}).

### How to disable some components from bundle

Moved to Cluster configuration, [Components reference]({{% ref "/docs/operations/configuration/components#enabling-and-disabling-components" %}}).
