---
title: "Deploy and Configure Cozystack"
linkTitle: "Deploy Cozystack"
description: "Learn how to get a running Cozystack cluster on bare metal or VMs in a series of guided steps."
weight: 10
aliases:
- /docs/get-started
---


## Before you begin


Make sure you have defined your [hardware requirements]({{% ref "/docs/getting-started/hardware-requirements" %}}).
As a bare minimum, you should have a management host plus three nodes of the following configuration to install Cozystack:

```yaml
CPU: 4 cores
CPU model: host
RAM: 16 GB
HDD1: 32 GB
HDD2: 100GB (raw)
```

![Cozystack deployment](/img/cozystack-deployment.png)

## Objectives

This tutorial shows how to bootstrap Cozystack.
It will guide you through the following steps:

1.  Create a Kubernetes cluster
1.  Install Cozystack
1.  Configure storage
1.  Configure networking
1.  Deploy etcd, ingress and monitoring stack
1.  Finalize deployment and access Cozystack dashboard


## 1. Create Kubernetes cluster

Cozystack runs on top of a Kubernetes cluster, either bring one up with Talos, or use an existing one.

### 1.1 Install Talos Linux

Boot your machines with Talos Linux image in one of these ways:

- [Install using temporary DHCP and PXE servers](/docs/operations/talos/installation/pxe/) running in Docker containers.
- [Install using ISO](/docs/operations/talos/installation/iso/).
- [Install on Hetzner servers](/docs/operations/talos/installation/hetzner/).


### 1.2 Bootstrap Talos Cluster

Bootstrap your Talos Linux cluster using one of the following tools:

- [**Talm**]({{% ref "/docs/operations/talos/configuration/talm" %}}), for a declarative way of cluster management.
- [**talosctl**]({{% ref "/docs/operations/talos/configuration/talosctl" %}}), for using native `talosctl` tool.
- [**talos-bootstrap**]({{% ref "/docs/operations/talos/configuration/talos-bootstrap" %}}), for an interactive walkthrough.

{{< tabs name="Bootstrapping tools" >}}
{{% tab name="Talm" %}}
Talm is a utility tool for bootstrapping and managing Talos clusters in a declarative way.

Visit the [releases page](https://github.com/cozystack/talm/releases) for the latest Talm binaries
or use the universal installation script:

```bash
curl -sSL https://github.com/cozystack/talm/raw/refs/heads/main/hack/install.sh | sh -s
talm --help
```
{{% /tab %}}

{{% tab name="talos-bootstrap" %}}
[talos-bootstrap](https://github.com/cozystack/talos-bootstrap/) is an interactive script for bootstrapping Kubernetes clusters on Talos OS.

```bash
sudo curl -fsSL -o /usr/local/bin/talos-bootstrap \
    https://github.com/cozystack/talos-bootstrap/raw/master/talos-bootstrap
sudo chmod +x /usr/local/bin/talos-bootstrap
talos-bootstrap --help
```
{{% /tab %}}
{{< /tabs >}}

### Existing cluster or other Kubernetes distributions

For a first tutorial run, it's strongly recommended to install Cozystack on bare metal.
However, Cozystack can also be installed in other ways, including on top of a provided managed Kubernetes cluster.

If you bootstrap your Talos cluster in your own way, or use a different Kubernetes distribution, make sure
to apply all settings from the guides above.
These settings are mandatory:

* All CNI plugins must be disabled, as Cozystack will install its own plugin.
* Kubernetes cluster DNS domain must be set to `cozy.local`.
* Listening address of some Kubernetes components must be changed from `localhost` to a routeable address.
* Kubernetes API server must be reachable on `localhost`.


## 2. Install Cozystack

Installing Cozystack starts with choosing a Cozystack bundle.
In this tutorial, we'll use the complete `paas-full` bundle, made for installing on bare metal and including everything
Cozystack has to offer.

### 2.1. Prepare Configuration File

Take the configuration example below and fill in the values according to your network setup.
Make sure to use the same value in `patch.yaml` and `patch-controlplane.yaml` files.

**cozystack-config.yaml**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "paas-full"
  root-host: example.org
  api-server-endpoint: https://api.example.org:443
  ipv4-pod-cidr: "10.244.0.0/16"
  ipv4-pod-gateway: "10.244.0.1"
  ipv4-svc-cidr: "10.96.0.0/16"
  ipv4-join-cidr: "100.64.0.0/16"
```

- `root-host` is used as the main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc.
- `api-server-endpoint` is primarily used for generating kubeconfig files for your users. It is recommended to use routeable IP addresses instead of local ones.
- `ipv4-pod-cidr` is the pod subnet used by pods to assign IPs
- `ipv4-pod-gateway` is the gateway address for the pod subnet
- `ipv4-svc-cidr` is pod subnet used by managed services to assign IPs
- `ipv4-join-cidr` is the `join` subnet, a special subnet for network communication between the Node and Pod.

To choose a bundle for your future PoC or production installation, read the [bundles overview and comparison]({{% ref "/docs/guides/bundles" %}}).
For the explanation of each configuration parameter, see the [bundles reference]({{% ref "/docs/operations/bundles" %}}).

{{% alert color="info" %}}
Cozystack gathers anonymous usage statistics by default. Learn more about what data is collected and how to opt out in the [Telemetry Documentation](/docs/operations/telemetry/).
{{% /alert %}}

### 2.2. Apply Configuration

Create namespace and install Cozystack system components:

```bash
kubectl create ns cozy-system
kubectl apply -f cozystack-config.yaml
kubectl apply -f https://github.com/cozystack/cozystack/releases/latest/download/cozystack-installer.yaml
```

{{% alert color="warning" %}}
By default, Cozystack is configured to use the [KubePrism](https://www.talos.dev/latest/kubernetes-guides/configuration/kubeprism/) feature of Talos Linux, which allows access to the Kubernetes API via a local address on the node.
If you're installing Cozystack on a system other than Talos Linux, you must update the `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_PORT` environment variables in the `cozystack-installer.yaml` manifest.
{{% /alert %}}

{{% alert color="info" %}}
Normally Cozystack requires at least three worker nodes to run workloads in HA mode. There are no tolerations in
Cozystack components that will allow them to run on control-plane nodes.

However, it's common to have only three nodes for testing purposes. Or you might only have big hardware nodes, and you
want to use them for both control-plane and worker workloads. In this case, you have to remove the control-plane taint
from the nodes. Example of how to do this:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

{{% /alert %}}

(optional) You can track the logs of installer:
```bash
kubectl logs -n cozy-system deploy/cozystack -f
```

Wait for a while, then check the status of installation:
```bash
kubectl get hr -A
```

Wait until all releases become to `Ready` state:
```console
NAMESPACE                        NAME                        AGE    READY   STATUS
cozy-cert-manager                cert-manager                4m1s   True    Release reconciliation succeeded
cozy-cert-manager                cert-manager-issuers        4m1s   True    Release reconciliation succeeded
cozy-cilium                      cilium                      4m1s   True    Release reconciliation succeeded
cozy-cluster-api                 capi-operator               4m1s   True    Release reconciliation succeeded
cozy-cluster-api                 capi-providers              4m1s   True    Release reconciliation succeeded
cozy-dashboard                   dashboard                   4m1s   True    Release reconciliation succeeded
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

## 3. Configure Storage

Setup alias to access LINSTOR:
```bash
alias linstor='kubectl exec -n cozy-linstor deploy/linstor-controller -- linstor'
```

list your nodes
```bash
linstor node list
```

example output:

```console
+-------------------------------------------------------+
| Node | NodeType  | Addresses                 | State  |
|=======================================================|
| srv1 | SATELLITE | 192.168.100.11:3367 (SSL) | Online |
| srv2 | SATELLITE | 192.168.100.12:3367 (SSL) | Online |
| srv3 | SATELLITE | 192.168.100.13:3367 (SSL) | Online |
+-------------------------------------------------------+
```

list empty devices:

```bash
linstor physical-storage list
```

example output:
```console
+--------------------------------------------+
| Size         | Rotational | Nodes          |
|============================================|
| 107374182400 | True       | srv3[/dev/sdb] |
|              |            | srv1[/dev/sdb] |
|              |            | srv2[/dev/sdb] |
+--------------------------------------------+
```


create storage pools:




{{< tabs name="create_storage_pools" >}}
{{% tab name="ZFS" %}}
```bash
linstor ps cdp zfs srv1 /dev/sdb --pool-name data --storage-pool data
linstor ps cdp zfs srv2 /dev/sdb --pool-name data --storage-pool data
linstor ps cdp zfs srv3 /dev/sdb --pool-name data --storage-pool data
```
{{% /tab %}}

{{% tab name="LVM" %}}
```bash
linstor ps cdp lvm srv1 /dev/sdb --pool-name data --storage-pool data
linstor ps cdp lvm srv2 /dev/sdb --pool-name data --storage-pool data
linstor ps cdp lvm srv3 /dev/sdb --pool-name data --storage-pool data
```
{{% /tab %}}
{{< /tabs >}}

list storage pools:

```bash
linstor sp l
```

example output:

```console
+-------------------------------------------------------------------------------------------------------------------------------------+
| StoragePool          | Node | Driver   | PoolName | FreeCapacity | TotalCapacity | CanSnapshots | State | SharedName                |
|=====================================================================================================================================|
| DfltDisklessStorPool | srv1 | DISKLESS |          |              |               | False        | Ok    | srv1;DfltDisklessStorPool |
| DfltDisklessStorPool | srv2 | DISKLESS |          |              |               | False        | Ok    | srv2;DfltDisklessStorPool |
| DfltDisklessStorPool | srv3 | DISKLESS |          |              |               | False        | Ok    | srv3;DfltDisklessStorPool |
| data                 | srv1 | ZFS      | data     |    96.41 GiB |     99.50 GiB | True         | Ok    | srv1;data                 |
| data                 | srv2 | ZFS      | data     |    96.41 GiB |     99.50 GiB | True         | Ok    | srv2;data                 |
| data                 | srv3 | ZFS      | data     |    96.41 GiB |     99.50 GiB | True         | Ok    | srv3;data                 |
+-------------------------------------------------------------------------------------------------------------------------------------+
```


Create default storage classes:
```yaml
kubectl create -f- <<EOT
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: linstor.csi.linbit.com
parameters:
  linstor.csi.linbit.com/storagePool: "data"
  linstor.csi.linbit.com/layerList: "storage"
  linstor.csi.linbit.com/allowRemoteVolumeAccess: "false"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: replicated
provisioner: linstor.csi.linbit.com
parameters:
  linstor.csi.linbit.com/storagePool: "data"
  linstor.csi.linbit.com/autoPlace: "3"
  linstor.csi.linbit.com/layerList: "drbd storage"
  linstor.csi.linbit.com/allowRemoteVolumeAccess: "true"
  property.linstor.csi.linbit.com/DrbdOptions/auto-quorum: suspend-io
  property.linstor.csi.linbit.com/DrbdOptions/Resource/on-no-data-accessible: suspend-io
  property.linstor.csi.linbit.com/DrbdOptions/Resource/on-suspended-primary-outdated: force-secondary
  property.linstor.csi.linbit.com/DrbdOptions/Net/rr-conflict: retry-connect
volumeBindingMode: Immediate
allowVolumeExpansion: true
EOT
```

list storageclasses:

```bash
kubectl get storageclasses
```

example output:

```console
NAME              PROVISIONER              RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
local (default)   linstor.csi.linbit.com   Delete          WaitForFirstConsumer   true                   11m
replicated        linstor.csi.linbit.com   Delete          Immediate              true                   11m
```

## 4. Configure Networking

Cozystack uses MetalLB as the default load balancer.
This documentation section explains how to configure networking with this default option.

{{% alert color="info" %}}
If your cloud provider does not support MetalLB, you can expose the ingress controller using the external IPs of your nodes.
Read the FAQ section [What if my cloud provider does not support MetalLB](
{{% ref "/docs/operations/faq#what-if-my-cloud-provider-does-not-support-metallb" %}}) for more details.
{{% /alert %}}

Cozystack has three types of IP addresses used:

-   Node IPs: constant and valid only within the cluster.
-   Virtual floating IP: used to access one of the nodes in the cluster and valid only within the cluster.
-   External access IPs: used by the load balancer to expose services outside the cluster.

To access your services select the range of unused IPs, for example, `192.168.100.200-192.168.100.250`.
These IPs should be from the same network as the nodes, or they should have all necessary routes to them.

Configure MetalLB to use and announce this range:

```bash
kubectl create -f metallb-l2-advertisement.yml
kubectl create -f metallb-ip-address-pool.yml
```

**metallb-l2-advertisement.yml**:
```yaml
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: cozystack
  namespace: cozy-metallb
spec:
  ipAddressPools:
    - cozystack
```

**metallb-ip-address-pool.yml**:
```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: cozystack
  namespace: cozy-metallb
spec:
  addresses:
    # used to expose services outside the cluster
    - 192.168.100.200-192.168.100.250
  autoAssign: true
  avoidBuggyIPs: false
```

## 5. Setup Basic Applications

Enable `etcd`, `monitoring`, and `ingress` in your `tenant-root`:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '
{"spec":{
  "ingress": true,
  "monitoring": true,
  "etcd": true,
  "isolated": true
}}'
```

## 6. Final steps


### 6.1 Check the cluster state and composition

Check persistent volumes provisioned:

```bash
kubectl get pvc -n tenant-root
```

example output:
```console
NAME                                     STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
data-etcd-0                              Bound    pvc-4cbd29cc-a29f-453d-b412-451647cd04bf   10Gi       RWO            local          <unset>                 2m10s
data-etcd-1                              Bound    pvc-1579f95a-a69d-4a26-bcc2-b15ccdbede0d   10Gi       RWO            local          <unset>                 115s
data-etcd-2                              Bound    pvc-907009e5-88bf-4d18-91e7-b56b0dbfb97e   10Gi       RWO            local          <unset>                 91s
grafana-db-1                             Bound    pvc-7b3f4e23-228a-46fd-b820-d033ef4679af   10Gi       RWO            local          <unset>                 2m41s
grafana-db-2                             Bound    pvc-ac9b72a4-f40e-47e8-ad24-f50d843b55e4   10Gi       RWO            local          <unset>                 113s
vmselect-cachedir-vmselect-longterm-0    Bound    pvc-622fa398-2104-459f-8744-565eee0a13f1   2Gi        RWO            local          <unset>                 2m21s
vmselect-cachedir-vmselect-longterm-1    Bound    pvc-fc9349f5-02b2-4e25-8bef-6cbc5cc6d690   2Gi        RWO            local          <unset>                 2m21s
vmselect-cachedir-vmselect-shortterm-0   Bound    pvc-7acc7ff6-6b9b-4676-bd1f-6867ea7165e2   2Gi        RWO            local          <unset>                 2m41s
vmselect-cachedir-vmselect-shortterm-1   Bound    pvc-e514f12b-f1f6-40ff-9838-a6bda3580eb7   2Gi        RWO            local          <unset>                 2m40s
vmstorage-db-vmstorage-longterm-0        Bound    pvc-e8ac7fc3-df0d-4692-aebf-9f66f72f9fef   10Gi       RWO            local          <unset>                 2m21s
vmstorage-db-vmstorage-longterm-1        Bound    pvc-68b5ceaf-3ed1-4e5a-9568-6b95911c7c3a   10Gi       RWO            local          <unset>                 2m21s
vmstorage-db-vmstorage-shortterm-0       Bound    pvc-cee3a2a4-5680-4880-bc2a-85c14dba9380   10Gi       RWO            local          <unset>                 2m41s
vmstorage-db-vmstorage-shortterm-1       Bound    pvc-d55c235d-cada-4c4a-8299-e5fc3f161789   10Gi       RWO            local          <unset>                 2m41s
```

Check all pods are running:


```bash
kubectl get pod -n tenant-root
```

example output:
```console
NAME                                           READY   STATUS    RESTARTS       AGE
etcd-0                                         1/1     Running   0              2m1s
etcd-1                                         1/1     Running   0              106s
etcd-2                                         1/1     Running   0              82s
grafana-db-1                                   1/1     Running   0              119s
grafana-db-2                                   1/1     Running   0              13s
grafana-deployment-74b5656d6-5dcvn             1/1     Running   0              90s
grafana-deployment-74b5656d6-q5589             1/1     Running   1 (105s ago)   111s
root-ingress-controller-6ccf55bc6d-pg79l       2/2     Running   0              2m27s
root-ingress-controller-6ccf55bc6d-xbs6x       2/2     Running   0              2m29s
root-ingress-defaultbackend-686bcbbd6c-5zbvp   1/1     Running   0              2m29s
vmalert-vmalert-644986d5c-7hvwk                2/2     Running   0              2m30s
vmalertmanager-alertmanager-0                  2/2     Running   0              2m32s
vmalertmanager-alertmanager-1                  2/2     Running   0              2m31s
vminsert-longterm-75789465f-hc6cz              1/1     Running   0              2m10s
vminsert-longterm-75789465f-m2v4t              1/1     Running   0              2m12s
vminsert-shortterm-78456f8fd9-wlwww            1/1     Running   0              2m29s
vminsert-shortterm-78456f8fd9-xg7cw            1/1     Running   0              2m28s
vmselect-longterm-0                            1/1     Running   0              2m12s
vmselect-longterm-1                            1/1     Running   0              2m12s
vmselect-shortterm-0                           1/1     Running   0              2m31s
vmselect-shortterm-1                           1/1     Running   0              2m30s
vmstorage-longterm-0                           1/1     Running   0              2m12s
vmstorage-longterm-1                           1/1     Running   0              2m12s
vmstorage-shortterm-0                          1/1     Running   0              2m32s
vmstorage-shortterm-1                          1/1     Running   0              2m31s
```

Now you can get public IP of ingress controller:
```bash
kubectl get svc -n tenant-root root-ingress-controller
```

example output:
```console
NAME                      TYPE           CLUSTER-IP     EXTERNAL-IP       PORT(S)                      AGE
root-ingress-controller   LoadBalancer   10.96.16.141   192.168.100.200   80:31632/TCP,443:30113/TCP   3m33s
```

### 6.2 Enable and access Cozystack dashboard

First, enable access to the dashboard by exposing it.
In Cozystack v0.31.0 or later, run the following command to expose the dashboard:

```bash
kubectl patch -n cozy-system cm cozystack --type=merge -p '{"data":{
    "expose-services": "dashboard"
    }}'
```

{{% alert color="info" %}}
In Cozystack v0.30.6 and earlier, this was done differently:

```bash
kubectl patch cm -n cozy-system cozystack --type merge -p='{"data":{
  "external-services": "dashboard"
}}'
```
{{% /alert %}}

Use `dashboard.example.org` to access the system dashboard, where `example.org` is your domain specified for `tenant-root`.
In this example, `dashboard.example.org` is located at 192.168.100.200.

Get authentication token from `tenant-root`:
```bash
kubectl get secret -n tenant-root tenant-root -o go-template='{{ printf "%s\n" (index .data "token" | base64decode) }}'
```

### 6.3 Access metrics in Grafana

Use `grafana.example.org` to access the system monitoring, where `example.org` is your domain specified for `tenant-root`.
In this example, `grafana.example.org` is located at 192.168.100.200.

- login: `admin`
- request a password:
  ```bash
  kubectl get secret -n tenant-root grafana-admin-password -o go-template='{{ printf "%s\n" (index .data "password" | base64decode) }}'
  ```

### 6.4 Enable OIDC

If you want to use it, you can now proceed by [configuring OIDC](/docs/operations/oidc/).
