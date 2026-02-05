---
title: "Cluster Scaling: Adding and Removing Nodes"
linkTitle: "Cluster Scaling"
description: "Adding and removing nodes in a Cozystack cluster."
weight: 20
---

## How to add a node to a Cozystack cluster

Adding a node is done in a way similar to regular Cozystack installation.

1.  [Install Talos on the node]({{% ref "/docs/install/talos" %}}), using the Cozystack's custom-built Talos image.

1.  Generate the configuration for the new node, using the [Talm]({{% ref "/docs/install/kubernetes/talm#3-generate-node-configuration-files" %}})
    or [talosctl]({{% ref "/docs/install/kubernetes/talosctl#2-generate-node-configuration-files" %}}) guide.
    
    For example, configuring a control plane node:

    ```bash
    talm template -e 192.168.123.20 -n 192.168.123.20 -t templates/controlplane.yaml -i > nodes/nodeN.yaml
    ```
    
    and for a worker node:
    ```bash
    talm template -e 192.168.123.20 -n 192.168.123.20 -t templates/worker.yaml -i > nodes/nodeN.yaml
    ```

1.  Apply the generated configuration to the node, using the [Talm]({{% ref "/docs/install/kubernetes/talm#41-apply-configuration-files" %}})
    or [talosctl]({{% ref "/docs/install/kubernetes/talosctl#3-apply-node-configuration" %}}) guide.
    For example:

    ```bash
    talm apply -f nodes/nodeN.yaml -i
    ```

1.  Wait for the node to reboot and bootstrap itself to the cluster.
    You don't need to bootstrap it manually or to install Cozystack on it, as it is all done automatically.

    You can check the result with `kubectl get nodes`.


## How to remove a node from a Cozystack cluster

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

