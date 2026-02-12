---
title: "Using NFS shares with Cozystack"
linkTitle: "Using NFS"
description: "Configure optional module `nfs-driver` to order volumes from NFS shares in Cozystack"
weight: 30
aliases:
  - /docs/v1/operations/storage/nfs
---

## Enable NFS driver

Add `bundle-enable: nfs-driver` to your Cozystack configuration:

```yaml
bundle-enable: nfs-driver
```

Wait a minute for the platform chart to reconcile, then verify the HelmRelease has been created:

```bash
kubectl get helmrelease --namespace cozy-nfs-driver nfs-driver
```

## Export share

```bash
apt install nfs-server
mkdir /data
chmod 777 /data
echo '/data *(rw,sync,no_subtree_check)' >> /etc/exports
exportfs -a
```

## Configure connection

```yaml
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs
provisioner: nfs.csi.k8s.io
parameters:
  server: 10.244.57.210
  share: /data
reclaimPolicy: Delete
volumeBindingMode: Immediate
allowVolumeExpansion: true
mountOptions:
  - nfsvers=4.1
```


## Order volume

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: task-pv-claim
spec:
  storageClassName: nfs
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 3Gi
```
