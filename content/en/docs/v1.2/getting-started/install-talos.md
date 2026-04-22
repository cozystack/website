---
title: "1. Установка Talos Linux"
linkTitle: "1. Установка Talos"
description: "Установка Talos Linux на любую машину с помощью cozystack/boot-to-talos."
weight: 10
aliases:
  - /docs/v1.2/getting-started/first-deployment
  - /docs/v1.2/getting-started/deploy-cluster
---

## Перед началом

Убедитесь, что у вас есть узлы (bare-metal серверы или виртуальные машины), соответствующие
[требованиям к оборудованию]({{% ref "./requirements" %}}).

## Цели

На этом шаге вы установите Talos Linux на bare-metal серверы или виртуальные машины, на которых сейчас работает другой дистрибутив Linux.

В этом руководстве используется `boot-to-talos` — простой CLI-инструмент, созданный командой Cozystack для пользователей и команд, внедряющих Cozystack.
Существуют и другие способы [установки Talos Linux для Cozystack]({{% ref "/docs/v1.2/install/talos" %}}), но они здесь не рассматриваются и описаны в отдельных руководствах.

## Установка

### 1. Установите `boot-to-talos`

Установите `boot-to-talos` с помощью установочного скрипта:

```bash
curl -sSL https://github.com/cozystack/boot-to-talos/raw/refs/heads/main/hack/install.sh | sh -s
```

### 2. Запустите установку Talos

Запустите `boot-to-talos` и укажите значения конфигурации.
Убедитесь, что используете сборку Talos от Cozystack, опубликованную в [ghcr.io/cozystack/cozystack/talos](https://github.com/cozystack/cozystack/pkgs/container/cozystack%2Ftalos).

```console
$ boot-to-talos
Target disk [/dev/sda]:
Talos installer image [ghcr.io/cozystack/cozystack/talos:v1.10.5]:
Add networking configuration? [yes]:
Interface [eth0]:
IP address [10.0.2.15]:
Netmask [255.255.255.0]:
Gateway (or 'none') [10.0.2.2]:
Configure serial console? (or 'no') [ttyS0]:

Summary:
  Image: ghcr.io/cozystack/cozystack/talos:v1.10.5
  Disk:  /dev/sda
  Extra kernel args: ip=10.0.2.15::10.0.2.2:255.255.255.0::eth0::::: console=ttyS0

WARNING: ALL DATA ON /dev/sda WILL BE ERASED!

Continue? [yes]:

2025/08/03 00:11:03 created temporary directory /tmp/installer-3221603450
2025/08/03 00:11:03 pulling image ghcr.io/cozystack/cozystack/talos:v1.10.5
2025/08/03 00:11:03 extracting image layers
2025/08/03 00:11:07 creating raw disk /tmp/installer-3221603450/image.raw (2 GiB)
2025/08/03 00:11:07 attached /tmp/installer-3221603450/image.raw to /dev/loop0
2025/08/03 00:11:07 starting Talos installer
2025/08/03 00:11:07 running Talos installer v1.10.5
2025/08/03 00:11:07 WARNING: config validation:
2025/08/03 00:11:07   use "worker" instead of "" for machine type
2025/08/03 00:11:07 created EFI (C12A7328-F81F-11D2-BA4B-00A0C93EC93B) size 104857600 bytes
2025/08/03 00:11:07 created BIOS (21686148-6449-6E6F-744E-656564454649) size 1048576 bytes
2025/08/03 00:11:07 created BOOT (0FC63DAF-8483-4772-8E79-3D69D8477DE4) size 1048576000 bytes
2025/08/03 00:11:07 created META (0FC63DAF-8483-4772-8E79-3D69D8477DE4) size 1048576 bytes
2025/08/03 00:11:07 formatting the partition "/dev/loop0p1" as "vfat" with label "EFI"
2025/08/03 00:11:07 formatting the partition "/dev/loop0p2" as "zeroes" with label "BIOS"
2025/08/03 00:11:07 formatting the partition "/dev/loop0p3" as "xfs" with label "BOOT"
2025/08/03 00:11:07 formatting the partition "/dev/loop0p4" as "zeroes" with label "META"
2025/08/03 00:11:07 copying from io reader to /boot/A/vmlinuz
2025/08/03 00:11:07 copying from io reader to /boot/A/initramfs.xz
2025/08/03 00:11:08 writing /boot/grub/grub.cfg to disk
2025/08/03 00:11:08 executing: grub-install --boot-directory=/boot --removable --efi-directory=/boot/EFI /dev/loop0
2025/08/03 00:11:08 installation of v1.10.5 complete
2025/08/03 00:11:08 Talos installer finished successfully
2025/08/03 00:11:08 remounting all filesystems read-only
2025/08/03 00:11:08 copy /tmp/installer-3221603450/image.raw → /dev/sda
2025/08/03 00:11:19 installation image copied to /dev/sda
2025/08/03 00:11:19 rebooting system
```

## Следующий шаг

Продолжите руководство по Cozystack и [установите Kubernetes-кластер с помощью Talm]({{% ref "./install-kubernetes" %}}).

Дополнительно:

-   Прочитайте [обзор Talos Linux]({{% ref "/docs/v1.2/guides/talos" %}}), чтобы понять, почему Talos Linux — оптимальный выбор ОС для Cozystack
    и что он даёт платформе.
-   Узнайте больше о [`boot-to-talos`]({{% ref "/docs/v1.2/install/talos/boot-to-talos#about-the-application" %}}).
-   Загляните в [github.com/cozystack/boot-to-talos](https://github.com/cozystack/boot-to-talos) и поставьте проекту звезду.
