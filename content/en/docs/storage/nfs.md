---
title: "Using NFS shares with Cozystack"
linkTitle: "Using NFS"
description: "Configure optional module `nfs-driver` to order volumes from NFS shares in Cozystack"
weight: 30
aliases:
  - /docs/operations/storage/nfs
---

## Driver and provisioner setup

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  labels:
    cozystack.io/system: "true"
    pod-security.kubernetes.io/enforce: privileged
  name: cozy-nfs-driver
spec:
  finalizers:
  - kubernetes
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  labels:
    cozystack.io/repository: system
    cozystack.io/system-app: "true"
  name: nfs-driver
  namespace: cozy-nfs-driver
spec:
  chart:
    spec:
      chart: cozy-nfs-driver
      reconcileStrategy: Revision
      sourceRef:
        kind: HelmRepository
        name: cozystack-system
        namespace: cozy-system
      version: '>= 0.0.0-0'
  dependsOn:
  - name: cilium
    namespace: cozy-cilium
  - name: kubeovn
    namespace: cozy-kubeovn
  install:
    crds: CreateReplace
    remediation:
      retries: -1
  interval: 5m
  releaseName: nfs-driver
  suspend: true
  upgrade:
    crds: CreateReplace
    remediation:
      retries: -1
```

Finally, apply the configuration:

```bash
cd packages/system/csi-driver-nfs
make apply
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
