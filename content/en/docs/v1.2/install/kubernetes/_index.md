---
title: "Установка и настройка кластера Kubernetes"
linkTitle: "2. Установка Kubernetes"
description: "Шаг 2: установка и настройка кластера Kubernetes, готового к установке Cozystack."
weight: 20
aliases:
  - /docs/v1.2/operations/talos/configuration
  - /docs/v1.2/talos/bootstrap
  - /docs/v1.2/talos/configuration
---


**Второй шаг** развертывания кластера Cozystack — установка и настройка кластера Kubernetes.
В результате вы получите установленный и настроенный кластер Kubernetes, готовый к установке Cozystack.

Если вы устанавливаете Cozystack впервые, [начните с руководства по Cozystack]({{% ref "/docs/v1.2/getting-started" %}}).

## Варианты установки

### Talos Linux (рекомендуется)

Для production-развертываний Cozystack рекомендует использовать [Talos Linux]({{% ref "/docs/v1.2/guides/talos" %}}) в качестве базовой операционной системы.
Предварительное условие для этих методов — [установленный Talos Linux]({{% ref "/docs/v1.2/install/talos" %}}).

Есть несколько способов настроить узлы Talos и инициализировать кластер Kubernetes:

-   **Рекомендуется**: [использование Talm]({{% ref "./talm" %}}) — декларативного CLI-инструмента с готовыми пресетами для Cozystack, который использует возможности Talos API.
-   [Использование `talos-bootstrap`]({{% ref "./talos-bootstrap" %}}) — интерактивного скрипта для инициализации кластеров Kubernetes на Talos OS.
-   [Использование talosctl]({{% ref "./talosctl" %}}) — специализированного CLI-инструмента для управления Talos.
-   [Установка в изолированной среде]({{% ref "./air-gapped" %}}) возможна с Talm или talosctl.

### Generic Kubernetes

Cozystack также можно развернуть на других дистрибутивах Kubernetes:

-   [Generic Kubernetes]({{% ref "./generic" %}}) — развертывание Cozystack на k3s, kubeadm, RKE2 или других дистрибутивах.

Если при установке возникнут проблемы, см. [раздел Troubleshooting]({{% ref "./troubleshooting" %}}).

## Следующие шаги

-   После установки и настройки кластера Kubernetes можно
    [установить и настроить Cozystack]({{% ref "/docs/v1.2/install/cozystack" %}}).
