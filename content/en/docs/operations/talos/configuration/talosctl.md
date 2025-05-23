---
title: Bootstrap a Talos Linux cluster for Cozystack using talosctl
linkTitle: talosctl
description: "Bootstrap a Talos Linux cluster for Cozystack using talosctl"
weight: 15
---

This guide explains how to prepare a Talos Linux cluster for deploying Cozystack using `talosctl`,
a specialized command line tool for managing Talos.

## Prerequisites

This guide assumes that you already have Talos OS installed, but not initialized, on several nodes.
These nodes should belong to one subnet or have public IPs.

In this example the nodes of a cluster are located in the subnet `192.168.123.0/24`, having the following IP addresses:

- `192.168.123.11`
- `192.168.123.12`
- `192.168.123.13`

IP `192.168.123.10` is an internal address which does not belong to any of these nodes, but is created by Talos.
It's used as VIP.

## 1. Prepare Configuration Variables

1.  Start working by making a configuration directory for the new cluster:

    ```bash
    mkdir -p cluster1
    cd cluster1
    ```

1.  Generate a secrets file.
    These secrets will later be injected in the configuration and used to establish authenticated connections to Talos nodes:

    ```bash
    talosctl gen secrets
    ```

1.   Make a configuration patch file `patch.yaml`:
    
    ```yaml
    machine:
      kubelet:
        nodeIP:
          validSubnets:
          - 192.168.123.0/24
        extraConfig:
          maxPods: 512
      kernel:
        modules:
        - name: openvswitch
        - name: drbd
          parameters:
            - usermode_helper=disabled
        - name: zfs
        - name: spl
      registries:
        mirrors:
          docker.io:
            endpoints:
            - https://mirror.gcr.io
      files:
      - content: |
          [plugins]
            [plugins."io.containerd.cri.v1.runtime"]
              device_ownership_from_security_context = true      
        path: /etc/cri/conf.d/20-customization.part
        op: create
    
    cluster:
      apiServer:
        extraArgs:
          oidc-issuer-url: "https://keycloak.example.org/realms/cozy"
          oidc-client-id: "kubernetes"
          oidc-username-claim: "preferred_username"
          oidc-groups-claim: "groups"
      network:
        cni:
          name: none
        dnsDomain: cozy.local
        podSubnets:
        - 10.244.0.0/16
        serviceSubnets:
        - 10.96.0.0/16
    ```
   
1.  Make one more configuration patch file, `patch-controlplane.yaml`.

    Note that VIP address is used for `machine.network.interfaces[0].vip.ip`:   

    ```yaml
    machine:
      nodeLabels:
        node.kubernetes.io/exclude-from-external-load-balancers:
          $patch: delete
      network:
        interfaces:
        - interface: eth0
          vip:
            ip: 192.168.123.10
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
        - 192.168.123.0/24
    ```


## 2. Generate Node Configuration

Once you have patch files ready, generate the configuration files for each node.
Note that it's using the three files generated in the previous step: `secrets.yaml`, `patch.yaml`, and `patch-controlplane.yaml`.

URL `192.168.123.10:6443` is the same VIP as mentioned above, and port `6443` is a standard Kubernetes API port.

```bash
talosctl gen config \
    cozystack https://192.168.123.10:6443 \
    --with-secrets secrets.yaml \
    --config-patch=@patch.yaml \
    --config-patch-control-plane @patch-controlplane.yaml
export TALOSCONFIG=$PWD/talosconfig
```

`192.168.123.11`, `192.168.123.12`, and `192.168.123.13` are nodes.
In this setup all nodes are management nodes.

## 3. Apply Node Configuration

Apply configuration to all nodes, not only management nodes

```
talosctl apply -f controlplane.yaml -n 192.168.123.11 -e 192.168.123.11 -i
talosctl apply -f controlplane.yaml -n 192.168.123.12 -e 192.168.123.12 -i
talosctl apply -f controlplane.yaml -n 192.168.123.13 -e 192.168.123.13 -i
```

Further on, you can also use the following options:

- `--dry-run` - dry run mode will show a diff with the existing configuration.
- `-m try` - try mode will roll back the configuration in 1 minute.

## 4. Wait for Nodes Rebooting

Wait until all nodes have rebooted.
Remove the installation media (e.g., USB stick) to ensure that the nodes boot from the internal disk.

Ready nodes will expose port 50000 which is a sign of Talos configuration completed and Talos finished rebooting

If you need to wait for nodes readiness in a script, consider this example:
```bash
timeout 60 sh -c 'until nc -nzv 192.168.123.11 50000 && nc -nzv 192.168.123.12 50000 && nc -nzv 192.168.123.13 50000; do sleep 1; done'
```

## 5. Bootstrap and Access Cluster

Run `talosctl bootstrap` on a single control-plane node — it is enough to bootstrap the whole cluster:

```bash
talosctl bootstrap -n 192.168.123.11 -e 192.168.123.11
```

To access the cluster, generate an administrative `kubeconfig`:

```bash
talosctl kubeconfig kubeconfig -f nodes/node1.yaml
```

Export the `KUBECONFIG` variable:
```bash
export KUBECONFIG=$PWD/kubeconfig
```

Check connection:
```bash
kubectl get ns
```

example output:
```console
NAME              STATUS   AGE
default           Active   7m56s
kube-node-lease   Active   7m56s
kube-public       Active   7m56s
kube-system       Active   7m56s
```

{{% alert color="warning" %}}
:warning: All nodes should currently show as `READY: False`, which is normal.
This happens because in the previous step you have disabled the default CNI plugin .
Cozystack will install its own CNI-plugin on the next step.
{{% /alert %}}


Now you have a Kubernetes cluster prepared for installing Cozystack.
To complete the installation, follow the deployment guide, starting with the
[Install Cozystack]({{% ref "/docs/getting-started/first-deployment#install-cozystack" %}}) section.
