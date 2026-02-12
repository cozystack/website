---
title: "Troubleshooting Kube-OVN"
linkTitle: "Kube-OVN"
description: "Explains how to resolve Kube-OVN crashes caused by a corrupted OVN database."
weight: 20
---


## Getting information about Kube-OVN database state

```bash
# Northbound DB
kubectl -n cozy-kubeovn exec deploy/ovn-central -c ovn-central -- ovn-appctl \
    -t /var/run/ovn/ovnnb_db.ctl cluster/status OVN_Northbound
# Southbound DB
kubectl -n cozy-kubeovn exec deploy/ovn-central -c ovn-central -- ovn-appctl \
    -t /var/run/ovn/ovnsb_db.ctl cluster/status OVN_Southbound
```

Example output:

```console
Name: OVN_Northbound
Cluster ID: abf6 (abf66f15-9382-4b2b-b14c-355d64ae1bda)
Server ID: 8d8a (8d8a2985-c444-43bb-99f6-21c82f05b58d)
Address: ssl:[10.200.1.22]:6643
Status: cluster member
Role: leader
Term: 3
Leader: self
Vote: self

Last Election started 146211 ms ago, reason: leadership_transfer
Last Election won: 146202 ms ago
Election timer: 5000
Log: [2, 1569]
Entries not yet committed: 0
Entries not yet applied: 0
Connections: ->2a66 ->c23f <-2a66 <-c23f
Disconnections: 30
Servers:
    2a66 (2a66 at ssl:[10.200.1.18]:6643) next_index=1569 match_index=1568 last msg 17 ms ago
    8d8a (8d8a at ssl:[10.200.1.22]:6643) (self) next_index=1471 match_index=1568
    c23f (c23f at ssl:[10.200.1.1]:6643) next_index=1569 match_index=1568 last msg 18 ms ago
```


To kick a node out of the cluster (for example, if it is down, and you want to remove it from the cluster), use:

```bash
# Northbound DB
kubectl -n cozy-kubeovn exec deploy/ovn-central -c ovn-central -- ovn-appctl -t /var/run/ovn/ovnnb_db.ctl cluster/kick OVN_Northbound <server-id>
# Southbound DB
kubectl -n cozy-kubeovn exec deploy/ovn-central -c ovn-central -- ovn-appctl -t /var/run/ovn/ovnsb_db.ctl cluster/kick OVN_Southbound <server-id>
```

## Resolving Kube-OVN Pods Crashing

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
# kubectl get pod -n cozy-kubeovn
ovn-cleanup-hjzxb                      1/1     Running             0              6s
ovn-cleanup-wmzdv                      1/1     Running             0              6s
ovn-cleanup-ztm86                      1/1     Running             0              6s
```

Once the cleanup is complete, delete the `ovn-cleanup` DaemonSet and restart the Kube-OVN CNI pods to apply the new configuration:

```bash
# Delete the cleanup DaemonSet
kubectl -n cozy-kubeovn delete ds ovn-cleanup

# Restart Kube-OVN pods by deleting them
kubectl -n cozy-kubeovn delete pod -l app!=ovs
```
