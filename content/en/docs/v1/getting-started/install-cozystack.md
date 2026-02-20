---
title: "3. Install and Configure Cozystack"
linkTitle: "3. Install Cozystack"
description: "Install Cozystack, get administrative access, perform basic configuration, and enable the UI dashboard."
weight: 20
---

## Objectives

In this step of the tutorial, we'll install Cozystack on top of a [Kubernetes cluster, prepared in the previous step]({{% ref "./install-kubernetes" %}}).

The tutorial will guide you through the following stages:

1.  Prepare a Cozystack configuration file
1.  Install Cozystack by applying configuration
1.  Configure storage
1.  Configure networking
1.  Deploy etcd, ingress and monitoring stack in the root tenant
1.  Finalize deployment and access Cozystack dashboard

## 1. Prepare a Configuration File

We will start installing Cozystack by making a configuration file.
Take the example below and write it in a file **cozystack-platform.yaml**:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full
  components:
    platform:
      values:
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://api.example.org:443"
          exposedServices:
            - dashboard
            - api
        networking:
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
```

Action points:

1.  Replace `example.org` in `publishing.host` and `publishing.apiServerEndpoint` with a routable fully-qualified domain name (FQDN) that you control.
    If you only have a public IP, but no FQDN, use [nip.io](https://nip.io/) with dash notation.
2.  Use the same values for `networking.*` as on the previous step, where you bootstrapped a Kubernetes cluster with Talm or `talosctl`.
    Settings provided in the example are sane defaults that can be used in most cases.

There are other values in this config that you don't need to change in the course of the tutorial.
However, let's overview and explain each value:

-   `metadata.name` must be `cozystack.cozystack-platform` to match the PackageSource created by the installer.
-   `publishing.host` is used as the main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc.
-   `publishing.apiServerEndpoint` is the Cluster API endpoint. It's used for generating kubeconfig files for your users. It is recommended to use routable IP addresses instead of local ones.
-   `spec.variant: "isp-full"` means that we're using the most complete set of Cozystack components.
    Learn more about variants in the [Cozystack Bundles reference]({{% ref "/docs/v1/operations/configuration/bundles" %}}).
-   `publishing.exposedServices` lists services to make accessible by users — here the dashboard (UI) and API.
-   `networking.*` are internal networking configurations for the underlying Kubernetes cluster.

You can learn more about this configuration file in the [Platform Package reference]({{% ref "/docs/v1/operations/configuration/platform-package" %}}).

{{% alert color="info" %}}
Cozystack gathers anonymous usage statistics by default. Learn more about what data is collected and how to opt out in the [Telemetry Documentation]({{% ref "/docs/v1/operations/configuration/telemetry" %}}).
{{% /alert %}}


## 2. Install Cozystack

Next, we will install Cozystack and check that the installation is complete and successful.


### 2.1. Install the Cozystack Operator

Install the Cozystack operator using the Helm chart from the OCI registry.
The operator manages all Cozystack components and handles the Platform Package lifecycle.

```bash
helm install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version X.Y.Z \
  --namespace cozy-system \
  --create-namespace
```

Replace `X.Y.Z` with the desired Cozystack version.
You can find available versions on the [Cozystack releases page](https://github.com/cozystack/cozystack/releases).


### 2.2. Apply the Platform Package

Apply the configuration file created in the previous step:

```bash
kubectl apply -f cozystack-platform.yaml
```

As the installation goes on, you can track the logs of the operator:

```bash
kubectl logs -n cozy-system deploy/cozystack-operator -f
```


### 2.3. Check Installation Status

Wait for a while, then check the status of installation:

```bash
kubectl get hr -A
```

Wait and check again until you see `True` on each line, as in this example:

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

The list of components in your installation may be different from the example above,
as it depends on your configuration and Cozystack version.

Once every component shows `READY: True`, we're ready to proceed by configuring subsystems.


## 3. Configure Storage

Kubernetes needs a storage subsystem to provide persistent volumes to applications, but it doesn't include one of its own.
Cozystack provides [LINSTOR](https://github.com/LINBIT/linstor-server) as a storage subsystem.

In the following steps, we'll access LINSTOR interface, create storage pools, and define storage classes.


### 3.1. Check Storage Devices

1.  Set up an alias to access LINSTOR:

    ```bash
    alias linstor='kubectl exec -n cozy-linstor deploy/linstor-controller -- linstor'
    ```

1.  List your nodes and check their readiness:
    
    ```bash
    linstor node list
    ```

    Example output shows node names and state:
    
    ```console
    +-------------------------------------------------------+
    | Node | NodeType  | Addresses                 | State  |
    |=======================================================|
    | srv1 | SATELLITE | 192.168.100.11:3367 (SSL) | Online |
    | srv2 | SATELLITE | 192.168.100.12:3367 (SSL) | Online |
    | srv3 | SATELLITE | 192.168.100.13:3367 (SSL) | Online |
    +-------------------------------------------------------+
    ```

1.  List available empty devices:

    ```bash
    linstor physical-storage list
    ```

    Example output shows the same node names:

    ```console
    +--------------------------------------------+
    | Size         | Rotational | Nodes          |
    |============================================|
    | 107374182400 | True       | srv3[/dev/sdb] |
    |              |            | srv1[/dev/sdb] |
    |              |            | srv2[/dev/sdb] |
    +--------------------------------------------+
    ```

### 3.2. Create Storage Pools

1.  Create storage pools using ZFS:

    ```bash
    linstor ps cdp zfs srv1 /dev/sdb --pool-name data --storage-pool data
    linstor ps cdp zfs srv2 /dev/sdb --pool-name data --storage-pool data
    linstor ps cdp zfs srv3 /dev/sdb --pool-name data --storage-pool data
    ```

    It is [recommended](https://github.com/LINBIT/linstor-server/issues/463#issuecomment-3401472020)
    to set `failmode=continue` on ZFS storage pools to allow DRBD to handle disk failures instead of ZFS.
    
    ```bash
    kubectl exec -ti -n cozy-linstor ds/linstor-satellite.srv1 -- zpool set failmode=continue data
    kubectl exec -ti -n cozy-linstor ds/linstor-satellite.srv2 -- zpool set failmode=continue data
    kubectl exec -ti -n cozy-linstor ds/linstor-satellite.srv3 -- zpool set failmode=continue data
    ```

1.  Check the results by listing the storage pools:

    ```bash
    linstor sp l
    ```

    Example output:
    
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

### 3.3. Create Storage Classes

Finally, we can create a couple of storage classes, one of which will be the default class.


1.  Create a file with storage class definitions.
    Below is a sane default example providing two classes: `local` (default) and `replicated`.
    
    **storageclasses.yaml:**
    
    ```yaml
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
    ```

1.  Apply the storage class configuration

    ```bash
    kubectl create -f storageclasses.yaml
    ```

1.  Check that the storage classes were successfully created:

    ```bash
    kubectl get storageclasses
    ```

    Example output:
    
    ```console
    NAME              PROVISIONER              RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
    local (default)   linstor.csi.linbit.com   Delete          WaitForFirstConsumer   true                   11m
    replicated        linstor.csi.linbit.com   Delete          Immediate              true                   11m
    ```


## 4. Configure Networking

Next, we will configure how the Cozystack cluster can be accessed.
This step has two options depending on your available infrastructure:

-   For your own bare metal or self-hosted VMs, choose the MetalLB option.
    MetalLB is Cozystack's default load balancer.
-   For VMs and dedicated servers from cloud providers, choose the public IP setup.
    [Most cloud providers don't support MetalLB](https://metallb.universe.tf/installation/clouds/).

    Check out the [provider-specific installation]({{% ref "/docs/v1/install/providers" %}}) section.
    It may have instructions for your provider, which you can use to deploy a production-ready cluster.

### 4.a MetalLB Setup

Cozystack has three types of IP addresses used:

-   Node IPs: persistent and valid only within the cluster.
-   Virtual floating IP: used to access one of the nodes in the cluster and valid only within the cluster.
-   External access IPs: used by LoadBalancers to expose services outside the cluster.

Services with external IPs may be exposed in two modes: L2 and BGP.
L2 mode is a simple one, but requires that nodes belong to a single L2 domain, and does not load-balance well.
BGP has more complicated setup -- you need BGP peers ready to accept announces, but gives the ability to make proper load-balancing, and provides more options for choosing IP address ranges.

Select a range of unused IPs for the services, here will use the `192.168.100.200-192.168.100.250` range.
If you use L2 mode, these IPs should either be from the same network as the nodes, or have all necessary routes to them.

For BGP mode, you will also need BGP peer IP addresses and local and remote AS numbers. Here we will use `192.168.20.254` as peer IP, and AS numbers 65000 and 65001 as local and remote.

Create and apply a file describing an address pool.

**metallb-ip-address-pool.yml**
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

```bash
kubectl create -f metallb-ip-address-pool.yml
```

Create and apply resources needed for an L2 or a BGP advertisement.

{{< tabs name="metallb_announce" >}}
{{% tab name="L2 mode" %}}
L2Advertisement uses the name of the IPAddressPool resource we created previously. 

**metallb-l2-advertisement.yml**
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
<br/>

Apply changes.

```bash
kubectl create -f metallb-l2-advertisement.yml
```
{{% /tab %}}
{{% tab name="BGP mode" %}}
First, create a separate BGPPeer resource for **each** peer.

**metallb-bgp-peer.yml**
```yaml
apiVersion: metallb.io/v1beta2
kind: BGPPeer
metadata:
  name: peer1
  namespace: cozy-metallb
spec:
  myASN: 65000
  peerASN: 65001
  peerAddress: 192.168.20.254
```  
<br/>

Next, create a single BGPAdvertisement resource.

**metallb-bgp-advertisement.yml**
```yaml
apiVersion: metallb.io/v1beta1
kind: BGPAdvertisement
metadata:
  name: cozystack
  namespace: cozy-metallb
spec:
  ipAddressPools:
  - cozystack
```
<br/>
Apply changes.

```bash
kubectl create -f metallb-bgp-peer.yml
kubectl create -f metallb-bgp-advertisement.yml
```
{{% /tab %}}
{{< /tabs >}}
<br/>

Now that MetalLB is configured, enable `ingress` in the `tenant-root`:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '
{"spec":{
  "ingress": true
}}'
```

To confirm successful configuration, check the HelmReleases `ingress` and `ingress-nginx-system`:

```bash
kubectl -n tenant-root get hr ingress ingress-nginx-system
```

Example of correct output:
```console
NAME                   AGE   READY   STATUS
ingress                47m   True    Helm upgrade succeeded for release tenant-root/ingress.v3 with chart ingress@1.8.0
ingress-nginx-system   47m   True    Helm upgrade succeeded for release tenant-root/ingress-nginx-system.v2 with chart cozy-ingress-nginx@0.35.1
```

Next, check the state of service `root-ingress-controller`:

```bash
kubectl -n tenant-root get svc root-ingress-controller
```

The service should be deployed as `TYPE: LoadBalancer` and have correct external IP:

```console
NAME                      TYPE           CLUSTER-IP      EXTERNAL-IP       PORT(S)          AGE
root-ingress-controller   LoadBalancer   10.96.91.83     192.168.100.200   80/TCP,443/TCP   48m
```

### 4.b. Node Public IP Setup

If your cloud provider does not support MetalLB, you can expose ingress controller using external IPs on your nodes.

If public IPs are attached directly to nodes, specify them.
If public IPs are provided with a 1:1 NAT, as some clouds do, use IP addresses of **external** network interfaces.

Here we will use `192.168.100.11`, `192.168.100.12`, and `192.168.100.13`.

First, patch the Platform Package with the external IPs:

```bash
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=merge -p '{
  "spec": {
    "components": {
      "platform": {
        "values": {
          "publishing": {
            "externalIPs": [
              "192.168.100.11",
              "192.168.100.12",
              "192.168.100.13"
            ]
          }
        }
      }
    }
  }
}'
```

Next, enable `ingress` for the root tenant:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '{
  "spec":{
    "ingress": true
  }
}'
```

Finally, add external IPs to the `externalIPs` list in the Ingress configuration:

```bash
kubectl patch -n tenant-root ingresses.apps.cozystack.io ingress --type=merge -p '{
  "spec":{
    "externalIPs": [
      "192.168.100.11",
      "192.168.100.12",
      "192.168.100.13"
    ]
  }
}'
```

After that, your Ingress will be available on the specified IPs.
Check it in the following way:

```bash
kubectl get svc -n tenant-root root-ingress-controller
```

The service should be deployed as `TYPE: ClusterIP` and have the full range of external IPs:

```console
NAME                     TYPE       CLUSTER-IP   EXTERNAL-IP                                   PORT(S)         AGE
root-ingress-controller  ClusterIP  10.96.91.83  192.168.100.11,192.168.100.12,192.168.100.13  80/TCP,443/TCP  48m
```

## 5. Finalize Installation

### 5.1. Setup Root Tenant Services

Enable `etcd` and `monitoring` for the root tenant:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '
{"spec":{
  "monitoring": true,
  "etcd": true
}}'
```

### 5.2. Check the cluster state and composition

Check the provisioned persistent volumes:

```bash
kubectl get pvc -n tenant-root
```

Example output:

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

Check that all pods are running:

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

Get the public IP of ingress controller:

```bash
kubectl get svc -n tenant-root root-ingress-controller
```

Example output:

```console
NAME                      TYPE           CLUSTER-IP     EXTERNAL-IP       PORT(S)                      AGE
root-ingress-controller   LoadBalancer   10.96.16.141   192.168.100.200   80:31632/TCP,443:30113/TCP   3m33s
```

### 5.3 Access the Cozystack Dashboard

If you included `dashboard` in the `publishing.exposedServices` list of your Platform Package (as shown in step 1), the Cozystack Dashboard is already available.

If the initial configuration did not include it, patch the Platform Package:

```bash
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=json \
  -p '[{"op": "add", "path": "/spec/components/platform/values/publishing/exposedServices/-", "value": "dashboard"}]'
```

Open `dashboard.example.org` to access the system dashboard, where `example.org` is your domain specified for `tenant-root`.
There you will see a login window which expects an authentication token.

Get the authentication token for `tenant-root`:

```bash
kubectl get secret -n tenant-root tenant-root -o go-template='{{ printf "%s\n" (index .data "token" | base64decode) }}'
```

Log in using the token.
Now you can use the dashboard as an administrator.

Further on, you will be able to:

-   Set up OIDC to authenticate with it instead of tokens.
-   Create user tenants and grant users access to them via tokens or OIDC.

### 5.4 Access metrics in Grafana

Use `grafana.example.org` to access the system monitoring, where `example.org` is your domain specified for `tenant-root`.
In this example, `grafana.example.org` is located at 192.168.100.200.

-   login: `admin`
-   request a password:
    
    ```bash
    kubectl get secret -n tenant-root grafana-admin-password -o go-template='{{ printf "%s\n" (index .data "password" | base64decode) }}'
    ```

## Next Step

Continue the Cozystack tutorial by [creating a user tenant]({{% ref "/docs/v1/getting-started/create-tenant" %}}).
