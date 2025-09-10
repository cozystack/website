---
title: Use talos-bootstrap script to bootstrap a Cozystack cluster
linkTitle: talos-bootstrap
description: "`talos-bootstrap` is a CLI for step-by-step cluster bootstrapping, made by Cozystack devs.<br> Recommended for first deployments."
weight: 10
aliases:
  - /docs/talos/bootstrap/talos-bootstrap
  - /docs/talos/configuration/talos-bootstrap
  - /docs/operations/talos/configuration/talos-bootstrap
---

[talos-bootstrap](https://github.com/cozystack/talos-bootstrap/) is an interactive script for bootstrapping Kubernetes clusters on Talos OS.

It was created by Cozystack developers to simplify the installation of Talos Linux on bare-metal nodes in a user-friendly manner.

## 1. Install Dependencies

Install the following dependencies

- `talosctl`
- `dialog`
- `nmap`

Download the latest version of `talos-bootstrap` from the [releases page](https://github.com/cozystack/talos-bootstrap/releases) or directly from the trunk:

```bash
curl -fsSL -o /usr/local/bin/talos-bootstrap \
    https://github.com/cozystack/talos-bootstrap/raw/master/talos-bootstrap
chmod +x /usr/local/bin/talos-bootstrap
talos-bootstrap --help
```

## 2. Prepare Configuration Files

1.  Start by making a configuration directory for the new cluster:

    ```bash
    mkdir -p cluster1
    cd cluster1
    ```

1.  Make a configuration patch file `patch.yaml` with common node settings, using the following example:

    ```yaml
    machine:
      kubelet:
        nodeIP:
          validSubnets:
          - 192.168.100.0/24
        extraConfig:
          maxPods: 512
      sysctls:
        net.ipv4.neigh.default.gc_thresh1: "4096"
        net.ipv4.neigh.default.gc_thresh2: "8192"
        net.ipv4.neigh.default.gc_thresh3: "16384"
      kernel:
        modules:
        - name: openvswitch
        - name: drbd
          parameters:
            - usermode_helper=disabled
        - name: zfs
        - name: spl
        - name: vfio_pci
        - name: vfio_iommu_type1
      install:
        image: ghcr.io/cozystack/cozystack/talos:v1.10.3
      registries:
        mirrors:
          docker.io:
            endpoints:
            - https://mirror.gcr.io
      files:
      - content: |
          [plugins]
            [plugins."io.containerd.grpc.v1.cri"]
              device_ownership_from_security_context = true
            [plugins."io.containerd.cri.v1.runtime"]
              device_ownership_from_security_context = true
        path: /etc/cri/conf.d/20-customization.part
        op: create
      - op: overwrite
        path: /etc/lvm/lvm.conf
        permissions: 0o644
        content: |
          backup {
            backup = 0
            archive = 0
          }
          devices {
            global_filter = [ "r|^/dev/drbd.*|", "r|^/dev/dm-.*|", "r|^/dev/zd.*|" ]
          }

    cluster:
      network:
        cni:
          name: none
        dnsDomain: cozy.local
        podSubnets:
        - 10.244.0.0/16
        serviceSubnets:
        - 10.96.0.0/16
    ```

1.  Make another configuration patch file `patch-controlplane.yaml` with settings exclusive to control plane nodes:

    ```yaml
    machine:
      nodeLabels:
        node.kubernetes.io/exclude-from-external-load-balancers:
          $patch: delete
    cluster:
      allowSchedulingOnControlPlanes: true
      controllerManager:
        extraArgs:
          bind-address: 0.0.0.0
      scheduler:
        extraArgs:
          bind-address: 0.0.0.0
      apiServer:
        certSANs:
        - 127.0.0.1
      proxy:
        disabled: true
      discovery:
        enabled: false
      etcd:
        advertisedSubnets:
        - 192.168.100.0/24
    ```

1.  To configure Keycloak as an OIDC provider, add the following section to `patch-controlplane.yaml`, replacing `example.com` with your domain:

    ```yaml
    cluster:
      apiServer:
        extraArgs:
        oidc-issuer-url: "https://keycloak.example.com/realms/cozy"
        oidc-client-id: "kubernetes"
        oidc-username-claim: "preferred_username"
        oidc-groups-claim: "groups"
    ```

## 3. Bootstrap and Access the Cluster

Once you have the configuration files ready, run `talos-bootstrap` on each node of a cluster:

```bash
# in the cluster config directory
talos-bootstrap install
```

{{% alert color="warning" %}}
:warning: If your nodes are running on an external network, you must specify each node explicitly in the argument:
```bash
talos-bootstrap install -n 1.2.3.4
```

Where `1.2.3.4` is the IP-address of your remote node.
{{% /alert %}}

{{% alert color="info" %}}
`talos-bootstrap` will enable bootstrap on the first configured node in a cluster.
If you want to re-bootstrap the etcd cluster, remove the line `BOOTSTRAP_ETCD=false` from your `cluster.conf` file.
{{% /alert %}}

Repeat this step for the other nodes in a cluster.

After completing the `install` command, `talos-bootstrap` saves the cluster's config as `./kubeconfig`.

Set up `kubectl` to use this new config by exporting the `KUBECONFIG` variable:

```bash
export KUBECONFIG=$PWD/kubeconfig
```

{{% alert color="info" %}}
To make this `kubeconfig` permanently available, you can make it the default one (`~/.kube/config`),
use `kubectl config use-context`, or employ a variety of other methods.
Check out the [Kubernetes documentation on cluster access](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/).
{{% /alert %}}

Check that the cluster is available with this new `kubeconfig`:

```bash
kubectl get ns
```

Example output:

```console
NAME              STATUS   AGE
default           Active   7m56s
kube-node-lease   Active   7m56s
kube-public       Active   7m56s
kube-system       Active   7m56s
```

{{% alert color="info" %}}
:warning: All nodes will show as `READY: False`, which is normal at this step.
This happens because the default CNI plugin was disabled in the previous step to enable Cozystack installing its own CNI plugin.
{{% /alert %}}


## Further Steps

Now you have a Kubernetes cluster bootstrapped and ready for installing Cozystack.
To complete the installation, follow the deployment guide, starting with the
[Install Cozystack]({{% ref "/docs/getting-started/install-cozystack" %}}) section.
