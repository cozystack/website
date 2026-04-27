---
title: Установка Talos Linux с помощью ISO
linkTitle: ISO
description: "Как установить Talos Linux с помощью ISO"
weight: 20
aliases:
  - /docs/v1.2/talos/installation/iso
  - /docs/v1.2/talos/install/iso
  - /docs/v1.2/operations/talos/installation/iso
---

В этом руководстве описано, как установить Talos Linux на bare-metal серверы или виртуальные машины.
Обратите внимание, что Cozystack предоставляет собственные сборки Talos, протестированные и оптимизированные для запуска кластера Cozystack.

## Установка

1.  Скачайте артефакт Talos Linux со [страницы релизов](https://github.com/cozystack/cozystack/releases) Cozystack.

    ```bash
    wget https://github.com/cozystack/cozystack/releases/latest/download/metal-amd64.iso
    ```

1.  Загрузите машину с подключенным ISO.

1.  Нажмите **<F3>** и заполните сетевые настройки:

    ![Cozystack for private cloud](/img/talos-network-configuration.png)

## Следующие шаги

После установки Talos перейдите к [установке и инициализации кластера Kubernetes]({{% ref "/docs/v1.2/install/kubernetes" %}}).
