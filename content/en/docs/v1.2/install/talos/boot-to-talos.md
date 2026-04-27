---
title: "Установка Talos Linux с помощью boot-to-talos"
linkTitle: boot-to-talos
description: "Установите Talos Linux с помощью boot-to-talos — удобного CLI-приложения, которому нужен только образ Talos."
weight: 5
aliases:
  - /docs/v1.2/talos/install/kexec
---

В этом руководстве описано, как установить Talos Linux на хост с любым другим дистрибутивом Linux с помощью `boot-to-talos`.

`boot-to-talos` создан командой Cozystack, чтобы помочь пользователям и командам, внедряющим Cozystack, установить Talos — самый сложный шаг процесса.
Он полностью работает из userspace и не имеет внешних зависимостей, кроме установочного образа Talos.

Обратите внимание, что Cozystack предоставляет собственные сборки Talos, протестированные и оптимизированные для запуска кластера Cozystack.

## Совместимость версий

При установке Cozystack на Talos должны совпасть три версии:

| Компонент | Откуда берется | Что должно совпадать |
| --- | --- | --- |
| **Talos** на узле | флаг `-image`, переданный в `boot-to-talos` | версия Talos, поставляемая с релизом Cozystack, который вы устанавливаете |
| **`talosctl`** на вашей рабочей станции | скачивается отдельно из [релизов siderolabs/talos](https://github.com/siderolabs/talos/releases) | major.minor версии Talos, записанной на узел |
| **Cozystack** | флаг `--version`, переданный в `helm upgrade --install cozy-installer` | — (основа; все остальное следует за ней) |

Для **Cozystack v1.2.x** закрепленная версия Talos — **v1.12.6**
([`packages/core/talos/images/talos/profiles/installer.yaml`](https://github.com/cozystack/cozystack/blob/release-1.2.1/packages/core/talos/images/talos/profiles/installer.yaml)).
Используйте `ghcr.io/cozystack/cozystack/talos:v1.12.6` как образ для `boot-to-talos` и скачайте `talosctl` v1.12.x.

{{% alert color="warning" %}}
`boot-to-talos` v0.7.x содержит собственный жестко заданный образ по умолчанию
(`ghcr.io/cozystack/cozystack/talos:v1.11.6` в v0.7.1, см.
[`cmd/boot-to-talos/main.go`](https://github.com/cozystack/boot-to-talos/blob/v0.7.1/cmd/boot-to-talos/main.go)).
Если в интерактивном prompt оставить это значение по умолчанию для кластера,
на котором вы планируете запускать Cozystack v1.2.x, в итоге вы получите узел Talos v1.11,
тогда как installer Cozystack и шаблоны Talm рассчитаны на Talos v1.12 — вы
столкнетесь с несовпадением на этапе bootstrap. Всегда вводите образ, соответствующий
целевому релизу Cozystack (или передавайте `-image` в командной строке).
{{% /alert %}}

## Режимы

`boot-to-talos` поддерживает два режима установки:

1. **boot** – извлекает kernel и initrd из Talos installer и загружает их напрямую с помощью механизма kexec.
2. **install** – подготавливает окружение, запускает Talos installer, а затем перезаписывает системный диск установленным образом.

{{< note >}}
Если один режим не работает в вашей системе, попробуйте другой. Разные методы могут лучше работать на разных операционных системах.
{{< /note >}}

## Установка

### 1. Установка `boot-to-talos`

-   Используйте установочный скрипт:

    ```bash
    curl -sSL https://github.com/cozystack/boot-to-talos/raw/refs/heads/main/hack/install.sh | sh -s
    ```

-   Скачайте бинарный файл со [страницы релизов GitHub](https://github.com/cozystack/boot-to-talos/releases/latest):

    ```bash
    wget https://github.com/cozystack/boot-to-talos/releases/latest/download/boot-to-talos-linux-amd64.tar.gz
    ```

### 2. Запуск установки Talos

Запустите `boot-to-talos` и укажите значения конфигурации.
Обязательно используйте собственную сборку Talos от Cozystack, доступную по адресу [ghcr.io/cozystack/cozystack/talos](https://github.com/cozystack/cozystack/pkgs/container/cozystack%2Ftalos).


```console
Mode:
  1. boot – extract the kernel and initrd from the Talos installer and boot them directly using the kexec mechanism.
  2. install – prepare the environment, run the Talos installer, and then overwrite the system disk with the installed image.
Mode [1]: 2
Target disk [/dev/sda]:
Talos installer image [ghcr.io/cozystack/cozystack/talos:v1.11.6]: ghcr.io/cozystack/cozystack/talos:v1.12.6
Add networking configuration? [yes]:
Interface [eth0]:
IP address [10.0.2.15]:
Netmask [255.255.255.0]:
Gateway (or 'none') [10.0.2.2]:
Configure serial console? (or 'no') [ttyS0]:

Summary:
  Image: ghcr.io/cozystack/cozystack/talos:v1.12.6
  Disk:  /dev/sda
  Extra kernel args: ip=10.0.2.15::10.0.2.2:255.255.255.0::eth0::::: console=ttyS0

WARNING: ALL DATA ON /dev/sda WILL BE ERASED!

Continue? [yes]:

2025/08/03 00:11:03 created temporary directory /tmp/installer-3221603450
2025/08/03 00:11:03 pulling image ghcr.io/cozystack/cozystack/talos:v1.12.6
2025/08/03 00:11:03 extracting image layers
2025/08/03 00:11:07 creating raw disk /tmp/installer-3221603450/image.raw (2 GiB)
2025/08/03 00:11:07 attached /tmp/installer-3221603450/image.raw to /dev/loop0
2025/08/03 00:11:07 starting Talos installer
2025/08/03 00:11:07 running Talos installer v1.12.6
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
2025/08/03 00:11:08 installation of v1.12.6 complete
2025/08/03 00:11:08 Talos installer finished successfully
2025/08/03 00:11:08 remounting all filesystems read-only
2025/08/03 00:11:08 copy /tmp/installer-3221603450/image.raw → /dev/sda
2025/08/03 00:11:19 installation image copied to /dev/sda
2025/08/03 00:11:19 rebooting system
```

## О приложении

`boot-to-talos` — это open source проект, размещенный на [github.com/cozystack/boot-to-talos](https://github.com/cozystack/boot-to-talos).
Он включает CLI, написанный на Go, и установочный скрипт на Bash.
Доступны сборки для нескольких архитектур:

- `linux-amd64`
- `linux-arm64`
- `linux-i386`

### Как это работает

Понимать эти шаги для установки Talos Linux необязательно.

Рабочий процесс зависит от выбранного режима:

#### Режим boot

При использовании режима **boot** `boot-to-talos` выполняет следующие шаги:

1.  **Распаковывает Talos installer в RAM**<br>
    Извлекает слои из контейнера Talos installer во временный `tmpfs`.
    Обратите внимание, что Docker на этом шаге не нужен.
2.  **Извлекает kernel и initrd**<br>
    Извлекает kernel (`vmlinuz`) и initial ramdisk (`initramfs.xz`) из образа Talos installer.
3.  **Загружает kernel через kexec**<br>
    Использует системный вызов `kexec`, чтобы загрузить kernel Talos и initrd в память с переданными параметрами командной строки kernel.
4.  **Перезагружает в Talos**<br>
    Выполняет `kexec --exec`, чтобы переключиться на kernel Talos без физической перезагрузки. После загрузки можно применить конфигурацию Talos и завершить установку.

#### Режим install

При использовании режима **install** `boot-to-talos` выполняет следующие шаги:

1.  **Распаковывает Talos installer в RAM**<br>
    Извлекает слои из контейнера Talos installer во временный `tmpfs`.
    Обратите внимание, что Docker на этом шаге не нужен.
2.  **Собирает системный образ**<br>
    Создает sparse-файл `image.raw`, подключенный через loop device, и выполняет Talos *installer* внутри chroot.
    Затем installer размечает диск, форматирует разделы и размещает GRUB и системные файлы.
3.  **Записывает поток на диск**<br>
    Копирует `image.raw` на выбранное блочное устройство блоками по 4 MiB и выполняет `fsync` после каждой записи, чтобы данные были полностью сохранены до перезагрузки.
4.  **Перезагружает систему**<br>
    Команда `echo b > /proc/sysrq-trigger` выполняет немедленную перезагрузку в только что установленный Talos Linux.

## Следующие шаги

После установки Talos перейдите к [установке и инициализации кластера Kubernetes]({{% ref "/docs/v1.2/install/kubernetes" %}}).
