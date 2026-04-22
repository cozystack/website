---
title: "Собственная платформа (BYOP)"
linkTitle: "Собственная платформа"
description: "Соберите собственную платформу с Cozystack, устанавливая только нужные компоненты с помощью CLI-инструмента cozypkg."
weight: 20
---

## Обзор

Cozystack можно использовать в режиме BYOP (Build Your Own Platform) — примерно так же, как дистрибутивы Linux позволяют устанавливать только нужные пакеты.
Вместо развертывания полной платформы со всеми компонентами вы выборочно устанавливаете из package repository Cozystack только то, что вам нужно.

Такой подход полезен, когда:

-   У вас уже есть кластер Kubernetes, и вам нужны только отдельные компоненты (например, Postgres operator или monitoring).
-   В вашем кластере уже настроены networking (CNI) и storage, и вы не хотите, чтобы Cozystack управлял ими.
-   Вам нужен полный контроль над тем, какие компоненты установлены и как они настроены.

Рабочий процесс опирается на два ресурса Kubernetes, управляемых Cozystack Operator:

-   **PackageSource** — описывает package repository и доступные variants для каждого package.
-   **Package** — объявляет, что конкретный package должен быть установлен в выбранном variant, опционально с пользовательскими values.

CLI-инструмент `cozypkg` предоставляет удобный интерфейс для работы с этими ресурсами: просмотра доступных packages, разрешения зависимостей и интерактивной установки packages.


## 1. Установка Cozystack Operator

Установите Cozystack operator с помощью Helm из OCI registry:

```bash
helm upgrade --install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version X.Y.Z \
  --namespace cozy-system \
  --create-namespace
```

Замените `X.Y.Z` на нужную версию Cozystack.
Доступные версии можно найти на [странице релизов Cozystack](https://github.com/cozystack/cozystack/releases).

Если установка выполняется на Kubernetes-дистрибутив без Talos (k3s, kubeadm, RKE2 и т. д.), укажите variant operator:

```bash
helm upgrade --install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version X.Y.Z \
  --namespace cozy-system \
  --create-namespace \
  --set cozystackOperator.variant=generic \
  --set cozystack.apiServerHost=<YOUR_API_SERVER_IP> \
  --set cozystack.apiServerPort=6443
```

Operator устанавливает FluxCD (в all-in-one mode, работающем без CNI) и создает начальный PackageSource `cozystack.cozystack-platform`.

На этом этапе существует только один PackageSource:

```bash
kubectl get packagesource
```

```console
NAME                           VARIANTS                      READY   STATUS
cozystack.cozystack-platform   default,isp-full,isp-full...  True    ...
```


## 2. Установка cozypkg

Установите CLI-инструмент `cozypkg` с помощью Homebrew:

```bash
brew tap cozystack/tap
brew install cozypkg
```

Готовые бинарные файлы для других платформ доступны на [странице релизов GitHub](https://github.com/cozystack/cozystack/releases).


## 3. Установка Platform Package

Первый шаг — установить package `cozystack-platform` с variant `default`.
Этот variant не устанавливает компоненты — он только регистрирует PackageSources для всех packages, доступных в репозитории Cozystack.

```bash
cozypkg add cozystack.cozystack-platform
```

Инструмент предложит выбрать variant. Выберите `default`:

```console
PackageSource: cozystack.cozystack-platform
Available variants:
  1. default
  2. isp-full
  3. isp-full-generic
  4. isp-hosted
Select variant (1-4): 1
```

После установки platform package станут доступны все остальные PackageSources:

```bash
cozypkg list
```

```console
NAME                                VARIANTS                      READY   STATUS
cozystack.cert-manager              default                       True    ...
cozystack.cozystack-platform        default,isp-full,isp-full...  True    ...
cozystack.ingress-nginx             default                       True    ...
cozystack.linstor                   default                       True    ...
cozystack.metallb                   default                       True    ...
cozystack.monitoring                default                       True    ...
cozystack.networking                noop,cilium,cilium-kilo,...   True    ...
cozystack.postgres-operator         default                       True    ...
...
```


## 4. Установка packages

Используйте `cozypkg add`, чтобы установить любой доступный package. Инструмент автоматически разрешает зависимости и предлагает выбрать variant для каждого package, который нужно установить.

```bash
cozypkg add <package-name>
```

Например, при установке package, зависящего от networking, `cozypkg` обнаружит зависимость, покажет уже установленные packages и предложит выбрать variant для каждой отсутствующей зависимости.

### Variants networking

Package `cozystack.networking` имеет несколько variants для разных окружений:

| Variant | Описание |
|:--------|:------------|
| `noop` | Ничего не устанавливает. Используйте, если networking уже настроен в кластере (например, существующие CNI и kube-proxy). |
| `cilium` | Cilium CNI для кластеров Talos Linux. |
| `cilium-generic` | Cilium CNI для generic-дистрибутивов Kubernetes (k3s, kubeadm, RKE2). |
| `kubeovn-cilium` | Cilium + KubeOVN для Talos Linux. Требуется для полноценной виртуализации (live migration). |
| `kubeovn-cilium-generic` | Cilium + KubeOVN для generic-дистрибутивов Kubernetes. |
| `cilium-kilo` | Cilium + Kilo для cluster mesh на базе WireGuard. |

Если в вашем кластере уже настроен CNI-плагин, выберите `noop`.
Поскольку networking является зависимостью большинства других packages, variant `noop` удовлетворяет зависимость, ничего не устанавливая.

### Просмотр установленных packages

Чтобы увидеть, какие packages сейчас установлены и какие у них variants:

```bash
cozypkg list --installed
```

```console
NAME                           VARIANT   READY   STATUS
cozystack.cozystack-platform   default   True    ...
cozystack.networking           noop      True    ...
cozystack.cert-manager         default   True    ...
```


## 5. Переопределение values компонентов

Каждый package состоит из одного или нескольких компонентов (Helm charts). Values для конкретных компонентов можно переопределить, напрямую отредактировав ресурс Package.

Spec Package поддерживает map `components`, где можно указать values для каждого компонента:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.metallb
spec:
  variant: default
  components:
    metallb:
      values:
        metallb:
          frrk8s:
            enabled: true
```

Примените ресурс:

```bash
kubectl apply -f metallb-package.yaml
```

Доступные values для компонента смотрите в соответствующем `values.yaml` в [репозитории Cozystack](https://github.com/cozystack/cozystack/tree/main/packages/system).

Также можно включать или отключать отдельные компоненты внутри package:

```yaml
spec:
  components:
    some-component:
      enabled: false
```


## 6. Удаление packages

Чтобы удалить установленный package:

```bash
cozypkg del <package-name>
```

Инструмент проверяет обратные зависимости: если другие установленные packages зависят от удаляемого, он перечислит их и запросит подтверждение перед удалением всех затронутых packages.


## Следующие шаги

-   Узнайте о [variants Cozystack]({{% ref "/docs/v1.2/operations/configuration/variants" %}}) и о том, как они определяют состав packages.
-   Подробности о переопределении параметров компонентов см. в [справочнике Components]({{% ref "/docs/v1.2/operations/configuration/components" %}}).
-   Для установки полной платформы см. [руководство по установке Platform]({{% ref "./platform" %}}).
