---
title: "2. Установка и bootstrap кластера Kubernetes"
linkTitle: "2. Установка Kubernetes"
description: "Используйте Talm CLI, чтобы выполнить bootstrap кластера Kubernetes, готового к установке Cozystack."
weight: 15
---

## Цели

К началу этого шага у нас уже есть [три узла с установленным Talos Linux]({{% ref "./install-talos" %}}).

В результате этого шага у вас будет установленный и настроенный Kubernetes-кластер, готовый к установке Cozystack.
Также вы получите `kubeconfig` для этого кластера и выполните базовые проверки его состояния.

## Установка Kubernetes

Установите и выполните bootstrap кластера Kubernetes с помощью [Talm]({{% ref "/docs/v1.2/install/kubernetes/talm" %}}) — декларативного CLI-инструмента управления конфигурацией с готовыми пресетами для Cozystack.

{{% alert color="info" %}}
Этот фрагмент руководства сейчас перерабатывается.
Здесь появятся упрощённые инструкции по установке Talm без дополнительных опций и редких пограничных случаев, которые описаны в основном руководстве по Talm.
{{% /alert %}}


## Следующий шаг

Продолжите руководство по Cozystack и [установите Cozystack]({{% ref "./install-cozystack" %}}).

Дополнительно:

-   Загляните в [github.com/cozystack/talm](https://github.com/cozystack/talm) и поставьте проекту звезду.
