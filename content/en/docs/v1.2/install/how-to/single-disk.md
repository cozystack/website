---
title: "Как установить Talos на машину с одним диском"
linkTitle: "Установка на один диск"
description: "Как установить Talos на машину с одним диском, выделив место на системном диске под пользовательское хранилище"
weight: 100
aliases:
  - /docs/v1.2/operations/faq/single-disk-installation
---

Стандартная конфигурация Talos предполагает, что у каждого узла есть основной и дополнительный диски, используемые соответственно для системного и пользовательского хранилища.
Однако можно использовать один диск, выделив на нем место для пользовательского хранилища.

Эту конфигурацию нужно применить при первом [`talosctl apply`]({{% ref "/docs/v1.2/install/kubernetes/talosctl#3-apply-node-configuration" %}})
или [`talm apply`]({{% ref "/docs/v1.2/install/kubernetes/talm#3-apply-node-configuration" %}})
— том, который выполняется с флагом `-i` (`--insecure`).
Применение изменений после инициализации не даст эффекта.

Для `talosctl` добавьте следующие строки в `patch.yaml`:

```yaml
---
apiVersion: v1alpha1
kind: VolumeConfig
name: EPHEMERAL
provisioning:
  minSize: 70GiB

---
apiVersion: v1alpha1
kind: UserVolumeConfig
name: data-storage
provisioning:
  diskSelector:
    match: disk.transport == 'nvme'
  minSize: 400GiB
```

Для `talm` добавьте те же строки в конец конфигурационного файла первого узла, например `nodes/node1.yaml`.

Подробнее см. в документации Talos: https://www.talos.dev/v1.10/talos-guides/configuration/disk-management/.

После применения конфигурации очистите раздел `data-storage`:

```bash
kubectl -n kube-system debug -it --profile sysadmin --image=alpine node/node1

apk add util-linux

umount /dev/nvme0n1p6 ### Раздел, выделенный под пользовательское хранилище
rm -rf /host/var/mnt/data-storage
wipefs -a /dev/nvme0n1p6
exit
```

После настройки хранилища добавьте новый раздел в LINSTOR:
```bash
linstor ps cdp zfs node1 nvme0n1p6 --pool-name data --storage-pool data1
```

Проверьте результат:
```bash
linstor sp l
```

Вывод будет похож на этот пример:

```text
+---------------------------------------------------------------------------------------------------------------------------------------+
| StoragePool          | Node  | Driver   | PoolName | FreeCapacity | TotalCapacity | CanSnapshots | State | SharedName                 |
|=======================================================================================================================================|
| DfltDisklessStorPool | node1 | DISKLESS |          |              |               | False        | Ok    | node1;DfltDisklessStorPool |
| data                 | node1 | ZFS      | data     |   351.46 GiB |       476 GiB | True         | Ok    | node1;data                 |
| data1                | node1 | ZFS      | data     |   378.93 GiB |       412 GiB | True         | Ok    | node1;data1                |
```
