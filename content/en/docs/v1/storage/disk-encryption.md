---
title: "Creating Encrypted Storage on LINSTOR"
linkTitle: "Encrypted Storage"
description: "Learn how to configure and use at-rest volume encryption for persistent volumes with LINSTOR"
weight: 100
aliases:
  - /docs/operations/storage/disk-encryption
---

Cozystack administrators can enable encrypted storage by creating a custom StorageClass.
This guide explains how to set up encryption passphrase, create an encrypted storage class, and use it in applications.

LINSTOR provides at-rest encryption for persistent volumes using [LUKS](https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-encrypted-volumes).
This ensures that data stored on disk is encrypted and can only be accessed when the volume is mounted and unlocked.

## Set Up Encryption in LINSTOR

To start using encryption, set up an encryption passphrase in LINSTOR.

```bash
kubectl exec -i -t -n cozy-linstor deploy/linstor-controller -- linstor encryption create-passphrase 
```

{{% alert color="warning" %}}
:warning: Save the passphrase securely.<br/>
If you lose the encryption passphrase, all encrypted data will be permanently lost.
{{% /alert %}}

You will need to enter the passphrase each time after restarting the LINSTOR Controller.
To enter the passphrase, use the following command:

```bash
kubectl exec -i -t -n cozy-linstor deploy/linstor-controller -- linstor encryption enter-passphrase
```

## Create Encrypted Storage Class

Create a `StorageClass` for encrypted storage:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-encrypted
provisioner: linstor.csi.linbit.com
parameters:
  linstor.csi.linbit.com/storagePool: "data"
  linstor.csi.linbit.com/layerList: "luks storage"
  linstor.csi.linbit.com/encryption: "true"
  linstor.csi.linbit.com/allowRemoteVolumeAccess: "false"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: replicated-encrypted
provisioner: linstor.csi.linbit.com
parameters:
  linstor.csi.linbit.com/storagePool: "data"
  linstor.csi.linbit.com/autoPlace: "3"
  linstor.csi.linbit.com/layerList: "drbd luks storage"
  linstor.csi.linbit.com/encryption: "true"
  linstor.csi.linbit.com/allowRemoteVolumeAccess: "true"
  property.linstor.csi.linbit.com/DrbdOptions/auto-quorum: suspend-io
  property.linstor.csi.linbit.com/DrbdOptions/Resource/on-no-data-accessible: suspend-io
  property.linstor.csi.linbit.com/DrbdOptions/Resource/on-suspended-primary-outdated: force-secondary
  property.linstor.csi.linbit.com/DrbdOptions/Net/rr-conflict: retry-connect
volumeBindingMode: Immediate
allowVolumeExpansion: true
```

Now you can use the `StorageClass` to create `PersistentVolumeClaims` (PVCs) for encrypted storage.

