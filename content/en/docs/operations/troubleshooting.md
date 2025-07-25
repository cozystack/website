---
title: "Troubleshooting cheatsheet"
linkTitle: "Troubleshooting"
description: "Showcase various ways to get more information out of Flux controllers to debug potential problems."
weight: 60
aliases:
  - /docs/troubleshooting
---

## Cozystack

### Getting basic information

You can see the logs of main installer by executing:

```yaml
kubectl logs -n cozy-system deploy/cozystack -f
```

All the platform components are installed using fluxcd HelmRelases.

You can get all installed HelmRelases:

```bash
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

Normaly all of them should be `Ready` and `Release reconciliation succeeded`


### Diagnosing `install retries exhausted` error

Sometimes you can face with the error:

```bash
# kubectl get hr -A -n cozy-dashboard dashboard
NAMESPACE          NAME          AGE   READY   STATUS
cozy-dashboard     dashboard     15m   False   install retries exhausted
```

You can try to figure out by checking events:

```bash
kubectl describe hr -n cozy-dashboard dashboard
```

if `Events: <none>` then suspend and reume the release:

```bash
kubectl patch hr -n cozy-dashboard dashboard -p '{"spec": {"suspend": true}}' --type=merge
kubectl patch hr -n cozy-dashboard dashboard -p '{"spec": {"suspend": null}}' --type=merge
```

and check the events again:

```bash
kubectl describe hr -n cozy-dashboard dashboard
```

## Cluster bootstrapping

Errors that can occur when bootstrapping a cluster with `talos-bootstrap`, `talm`, or `talosctl`:

### No Talos nodes in maintenance mode found!

If you encounter issues with the `talos-bootstrap` script not detecting any nodes, follow these steps to diagnose and resolve the issue:

#### Verify Network Segment

Ensure that you are running the script within the same network segment as the nodes. This is crucial for the script to be able to communicate with the nodes.

#### Use Nmap to Discover Nodes

Check if `nmap` can discover your node by running the following command:

```bash
nmap -Pn -n -p 50000 192.168.0.0/24
```

This command scans for nodes in the network that are listening on port `50000`.
The output should list all the nodes in the network segment that are listening on this port, indicating that they are reachable.

#### Verify talosctl Connectivity

Next, verify that `talosctl` can connect to a specific node, especially if the node is in maintenance mode:

```bash
talosctl -e "${node}" -n "${node}" get machinestatus -i
```

Receiving an error like the following usually means your local `talosctl` binary is outdated:

```console
rpc error: code = Unimplemented desc = unknown service resource.ResourceService
```

Updating `talosctl` to the latest version should resolve this issue.

#### Run talos-bootstrap in debug mode

If the previous steps don’t help, run `talos-bootstrap` in debug mode to gain more insight.

Execute the script with the `-x` option to enable debug mode:

```bash
bash -x talos-bootstrap
```

Pay attention to the last command displayed before the error; it often indicates the command that failed and can provide clues for further troubleshooting.


## Kube-OVN crash

In complex cases, you may encounter issues where the Kube-OVN DaemonSet pods crash or fail to start properly.
This usually indicates a corrupted OVN database.
You can confirm this by checking the logs of the Kube-OVN CNI pods.

Get the list of pods in `cozy-kubeovn` namespace:

```console
# kubectl get pod -n cozy-kubeovn
NAME                                   READY   STATUS              RESTARTS       AGE
kube-ovn-cni-5rsvz                     0/1     Running             5 (35s ago)    4m37s
kube-ovn-cni-jq2zz                     0/1     Running             5 (33s ago)    4m39s
kube-ovn-cni-p4gz2                     0/1     Running             3 (23s ago)    4m38s
```

Read the logs of a pod by its name (`kube-ovn-cni-jq2zz` in this example):

```console
# kubectl logs -n cozy-kubeovn kube-ovn-cni-jq2zz
W0725 08:21:12.479452   87678 ovs.go:35] 100.64.0.4 network not ready after 3 ping to gateway 100.64.0.1
W0725 08:21:15.479600   87678 ovs.go:35] 100.64.0.4 network not ready after 6 ping to gateway 100.64.0.1
W0725 08:21:18.479628   87678 ovs.go:35] 100.64.0.4 network not ready after 9 ping to gateway 100.64.0.1
W0725 08:21:21.479355   87678 ovs.go:35] 100.64.0.4 network not ready after 12 ping to gateway 100.64.0.1
W0725 08:21:24.479322   87678 ovs.go:35] 100.64.0.4 network not ready after 15 ping to gateway 100.64.0.1
W0725 08:21:27.479664   87678 ovs.go:35] 100.64.0.4 network not ready after 18 ping to gateway 100.64.0.1
W0725 08:21:30.478907   87678 ovs.go:35] 100.64.0.4 network not ready after 21 ping to gateway 100.64.0.1
W0725 08:21:33.479738   87678 ovs.go:35] 100.64.0.4 network not ready after 24 ping to gateway 100.64.0.1
W0725 08:21:36.479607   87678 ovs.go:35] 100.64.0.4 network not ready after 27 ping to gateway 100.64.0.1
W0725 08:21:39.479753   87678 ovs.go:35] 100.64.0.4 network not ready after 30 ping to gateway 100.64.0.1
W0725 08:21:42.479480   87678 ovs.go:35] 100.64.0.4 network not ready after 33 ping to gateway 100.64.0.1
W0725 08:21:45.478754   87678 ovs.go:35] 100.64.0.4 network not ready after 36 ping to gateway 100.64.0.1
W0725 08:21:48.479396   87678 ovs.go:35] 100.64.0.4 network not ready after 39 ping to gateway 100.64.0.1
```

To resolve this issue, you can clean up the OVN database.
This involves running a DaemonSet that removes the OVN configuration files from each node.
It is safe to perform this cleanup — the Kube-OVN DaemonSet will automatically recreate the necessary files from the Kubernetes API.

Apply the following YAML to deploy the cleanup DaemonSet:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ovn-cleanup
  namespace: cozy-kubeovn
spec:
  selector:
    matchLabels:
      app: ovn-cleanup
  template:
    metadata:
      labels:
        app: ovn-cleanup
        component: network
        type: infra
    spec:
      affinity:
        podAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: ovn-central
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: cleanup
        image: busybox
        command: ["/bin/sh", "-xc", "rm -rf /host-config-ovn/*; rm -rf /host-config-ovn/.*; exec sleep infinity"]
        volumeMounts:
        - name: host-config-ovn
          mountPath: /host-config-ovn
      nodeSelector:
        kubernetes.io/os: linux
        node-role.kubernetes.io/control-plane: ""
      tolerations:
      - operator: "Exists"
      volumes:
      - name: host-config-ovn
        hostPath:
          path: /var/lib/ovn
          type: ""
      hostNetwork: true
      restartPolicy: Always
      terminationGracePeriodSeconds: 1
```

Verify that the DaemonSet is running:

```console
kubectl get pod -n cozy-kubeovn
ovn-cleanup-hjzxb                      1/1     Running             0              6s
ovn-cleanup-wmzdv                      1/1     Running             0              6s
ovn-cleanup-ztm86                      1/1     Running             0              6s
```

Once the cleanup is complete, delete the DaemonSet and restart the Kube-OVN DaemonSet pods to apply the new configuration:

```bash
kubectl delete ds
kubectl get pod -n cozy-kubeovn
```


## Remove a failed node from the cluster

When a cluster node fails, Cozystack automatically handles high availability by recreating replicated PVCs and workloads on other nodes.
However, there can be issues that require removing the node to resolve:

-   Local storage PVs may remain bound to the failed node, which can cause issues with new pods.
    These need to be cleaned up manually.

-   The failed node will still exist in the cluster, which can lead to inconsistencies in the cluster state and affect pod scheduling.


### Step 1: Remove the Node from the Cluster

Run the following command to remove the failed node (replace mynode with the actual node name):

```bash
kubectl delete node mynode
```

If the failed node is a control-plane node, you must also remove its etcd member from the etcd cluster:

```bash
talm -f nodes/node1.yaml etcd member list
```

Example output:

```console
NODE         ID                  HOSTNAME   PEER URLS                    CLIENT URLS                  LEARNER
37.27.60.28  2ba6e48b8cf1a0c1    node1      https://192.168.100.11:2380  https://192.168.100.11:2379  false
37.27.60.28  b82e2194fb76ee42    node2      https://192.168.100.12:2380  https://192.168.100.12:2379  false
37.27.60.28  f24f4de3d01e5e88    node3      https://192.168.100.13:2380  https://192.168.100.13:2379  false
```

Then remove the corresponding member (replace the ID with the one for your failed node):

```bash
talm -f nodes/node1.yaml etcd remove-member f24f4de3d01e5e88
```

### Step 2: Remove PVCs and Pods Bound to the Failed Node

Here are few commands to help you clean up the failed node:

-   **Delete PVCs** bound to the failed node:<br>
    (Replace `mynode` with the name of your failed node)
    
    ```bash
    kubectl get pv -o json | jq -r '.items[] | select(.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0] == "mynode").spec.claimRef | "kubectl delete pvc -n \(.namespace) \(.name)"' | sh -x
    ```
    
-   **Delete pods** stuck in `Pending` state across all namespaces:
    
    ```bash
    kubectl get pod -A | awk '/Pending/ {print "kubectl delete pod -n " $1 " " $2}' | sh -x
    ```

### Step 3: Check Resource Status

After cleanup, check for any resource issues using `linstor advise`:

```console
# linstor advise resource
╭───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
┊ Resource                                 ┊ Issue                                             ┊ Possible fix                                                           ┊
╞═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╡
┊ pvc-02b0c0a1-e0b6-4e98-9384-60ff24f3b3b6 ┊ Resource expected to have 3 replicas, got only 2. ┊ linstor rd ap --place-count 3 pvc-02b0c0a1-e0b6-4e98-9384-60ff24f3b3b6 ┊
┊ pvc-06e3b406-23f0-4f10-8b03-84063c1b2a12 ┊ Resource expected to have 3 replicas, got only 2. ┊ linstor rd ap --place-count 3 pvc-06e3b406-23f0-4f10-8b03-84063c1b2a12 ┊
┊ pvc-a0b8aeaf-076e-4bd9-93ed-c4db09c04d0b ┊ Resource expected to have 3 replicas, got only 2. ┊ linstor rd ap --place-count 3 pvc-a0b8aeaf-076e-4bd9-93ed-c4db09c04d0b ┊
┊ pvc-a523ebeb-c3b6-468d-abe5-f6afbbf31081 ┊ Resource expected to have 3 replicas, got only 2. ┊ linstor rd ap --place-count 3 pvc-a523ebeb-c3b6-468d-abe5-f6afbbf31081 ┊
┊ pvc-cf7e87b5-3e6d-4034-903d-4625830fb5b4 ┊ Resource expected to have 1 replicas, got only 0. ┊ linstor rd ap --place-count 1 pvc-cf7e87b5-3e6d-4034-903d-4625830fb5b4 ┊
┊ pvc-d344bc83-97fd-4489-bbe7-5399eea57165 ┊ Resource expected to have 3 replicas, got only 2. ┊ linstor rd ap --place-count 3 pvc-d344bc83-97fd-4489-bbe7-5399eea57165 ┊
┊ pvc-d39345a9-5446-4c64-a5ba-957ff7c7a31f ┊ Resource expected to have 3 replicas, got only 2. ┊ linstor rd ap --place-count 3 pvc-d39345a9-5446-4c64-a5ba-957ff7c7a31f ┊
┊ pvc-db6d4236-93bd-4268-9dcc-0ed275b17067 ┊ Resource expected to have 1 replicas, got only 0. ┊ linstor rd ap --place-count 1 pvc-db6d4236-93bd-4268-9dcc-0ed275b17067 ┊
┊ pvc-ebb412c3-083c-4eee-93dc-70917ea6d87e ┊ Resource expected to have 1 replicas, got only 0. ┊ linstor rd ap --place-count 1 pvc-ebb412c3-083c-4eee-93dc-70917ea6d87e ┊
┊ pvc-f107aacb-78d7-4ac6-97f8-8ed529a9c292 ┊ Resource expected to have 3 replicas, got only 2. ┊ linstor rd ap --place-count 3 pvc-f107aacb-78d7-4ac6-97f8-8ed529a9c292 ┊
┊ pvc-f347d71a-b646-45e5-a717-f0a745061beb ┊ Resource expected to have 1 replicas, got only 0. ┊ linstor rd ap --place-count 1 pvc-f347d71a-b646-45e5-a717-f0a745061beb ┊
┊ pvc-f6e96c83-6144-4510-b0ab-61936db52391 ┊ Resource expected to have 3 replicas, got only 2. ┊ linstor rd ap --place-count 3 pvc-f6e96c83-6144-4510-b0ab-61936db52391 ┊
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Run the `linstor rd ap` commands suggested in the "Possible fix" column to restore the desired replica count.
