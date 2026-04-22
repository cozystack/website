---
title: "3. Установка и настройка Cozystack"
linkTitle: "3. Установка Cozystack"
description: "Установите Cozystack, получите административный доступ, выполните базовую настройку и включите UI-дашборд."
weight: 20
---

## Цели

{{% alert color="info" %}}
Это руководство описывает установку Cozystack как **готовой к использованию платформы**.
Если вы хотите собрать собственную платформу, устанавливая только нужные компоненты,
см. [руководство BYOP (Build Your Own Platform)]({{% ref "/docs/v1.2/install/cozystack/kubernetes-distribution" %}}).
{{% /alert %}}

На этом шаге мы установим Cozystack поверх [Kubernetes-кластера, подготовленного на предыдущем шаге]({{% ref "./install-kubernetes" %}}).

Руководство проведёт вас через следующие этапы:

1.  Установка оператора Cozystack
1.  Подготовка файла конфигурации Cozystack и его применение
1.  Настройка хранилища
1.  Настройка сети
1.  Развёртывание etcd, ingress и стека мониторинга в корневом tenant'е
1.  Завершение развёртывания и вход в дашборд Cozystack

## 1. Установка оператора Cozystack

Установите оператор Cozystack с помощью Helm chart из OCI-реестра.
Оператор управляет всеми компонентами Cozystack и отвечает за жизненный цикл Platform Package.

```bash
helm upgrade --install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version X.Y.Z \
  --namespace cozy-system \
  --create-namespace
```

Замените `X.Y.Z` на нужную версию Cozystack.
Доступные версии перечислены на [странице релизов Cozystack](https://github.com/cozystack/cozystack/releases).

{{% alert color="info" %}}
**Если установка прерывается из-за того, что `cozy-system` уже существует.**
Helm отказывается забирать себе namespace, который создал не он, и выводит
ошибку `invalid ownership metadata` (или `namespaces "cozy-system" already exists`
в зависимости от версии Helm), если `cozy-system` остался после ранее прерванной
установки или был создан вручную для этой цели.

Если namespace **не** управляется другим инструментом (Terraform, Argo CD,
другим Helm release и т. д.), повторите команду с `--take-ownership`
(требуется Helm 3.17+), чтобы Helm смог принять его под управление:

```bash
helm upgrade --install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --version X.Y.Z \
  --namespace cozy-system \
  --create-namespace \
  --take-ownership
```

Не используйте `--take-ownership`, если `cozy-system` уже принадлежит другой системе —
Helm незаметно станет новым владельцем, а последующие обновления или удаление
релиза Cozystack могут изменить или удалить namespace (и всё, что было принято
под управление этим флагом) вопреки ожиданиям этой системы.
{{% /alert %}}

## 2. Подготовка и применение Platform Package

### 2.1. Подготовьте файл конфигурации

Теперь, когда оператор запущен, подготовим для него файл конфигурации.
Возьмите пример ниже и сохраните его в файл **cozystack-platform.yaml**:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full
  components:
    platform:
      values:
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://api.example.org:443"
          exposedServices:
            - dashboard
            - api
        networking:
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
```

Что нужно сделать:

1.  Замените `example.org` в `publishing.host` и `publishing.apiServerEndpoint` на маршрутизируемое полное доменное имя (FQDN), которым вы управляете.
    Если у вас есть только публичный IP, но нет FQDN, используйте [nip.io](https://nip.io/) с dash-нотацией.
2.  Используйте для `networking.*` те же значения, что и на предыдущем шаге, где вы выполняли bootstrap Kubernetes-кластера через Talm или `talosctl`.
    Значения из примера — это разумные значения по умолчанию, которые подходят для большинства случаев.

В этой конфигурации есть и другие значения, которые в рамках руководства менять не требуется.
Тем не менее, кратко разберём каждое из них:

-   `metadata.name` должен быть равен `cozystack.cozystack-platform`, чтобы совпасть с PackageSource, созданным установщиком.
-   `publishing.host` используется как основной домен для всех сервисов, создаваемых в Cozystack, например дашборда, Grafana, Keycloak и т. д.
-   `publishing.apiServerEndpoint` — это endpoint Cluster API. Он используется для генерации kubeconfig-файлов для пользователей. Рекомендуется использовать маршрутизируемые IP-адреса, а не локальные.
-   `spec.variant: "isp-full"` означает, что используется наиболее полный набор компонентов Cozystack.
    Подробнее о вариантах см. в [справочнике по вариантам Cozystack]({{% ref "/docs/v1.2/operations/configuration/variants" %}}).
-   `publishing.exposedServices` перечисляет сервисы, которые должны быть доступны пользователям — здесь это дашборд (UI) и API.
-   `networking.*` — это внутренняя сетевая конфигурация базового Kubernetes-кластера:
    -   `networking.podCIDR` — диапазон CIDR, из которого Kube-OVN выделяет IP-адреса pod'ам. Он не должен пересекаться
        ни с одной сетью, которую уже маршрутизируют ваши узлы.
    -   `networking.podGateway` — адрес шлюза, который Kube-OVN назначает подсети pod'ов по умолчанию. Используйте
        адрес `.1` сети `podCIDR` (например, `10.244.0.1` для `10.244.0.0/16`).
    -   `networking.serviceCIDR` — диапазон CIDR для сервисов `ClusterIP`. Он **обязательно** должен совпадать со значением
        `cluster.network.serviceSubnets`, которое вы использовали при bootstrap Kubernetes-кластера:
        это значение вшивается в kube-apiserver во время bootstrap и не может быть изменено без
        пересборки кластера, поэтому несоответствие здесь незаметно ломает DNS и маршрутизацию сервисов.
    -   `networking.joinCIDR` — диапазон CIDR для *join* подсети Kube-OVN, внутренней сети, которая переносит
        трафик между узлами кластера и pod'ами. Значение по умолчанию `100.64.0.0/16` входит в
        общее адресное пространство [RFC 6598](https://datatracker.ietf.org/doc/html/rfc6598) (`100.64.0.0/10`),
        зарезервированное для такого внутреннего использования. Меняйте его только если оно пересекается с сетью,
        которую уже маршрутизируют ваши узлы; подробности см. в
        [справочнике по Kube-OVN join subnet](https://kubeovn.github.io/docs/stable/en/guide/subnet/#join-subnet).

Подробнее об этом файле конфигурации см. в [справочнике Platform Package]({{% ref "/docs/v1.2/operations/configuration/platform-package" %}}).

{{% alert color="info" %}}
По умолчанию Cozystack собирает анонимную статистику использования. Подробнее о том, какие данные собираются и как отказаться от этой функции, см. в [документации по телеметрии]({{% ref "/docs/v1.2/operations/configuration/telemetry" %}}).
{{% /alert %}}


### 2.2. Примените Platform Package

Примените файл конфигурации:

```bash
kubectl apply -f cozystack-platform.yaml
```

Во время установки можно следить за логами оператора:

```bash
kubectl logs -n cozy-system deploy/cozystack-operator -f
```


### 2.3. Проверьте статус установки

Подождите немного, затем проверьте статус установки:

```bash
kubectl get hr -A
```

Повторяйте проверку, пока во всех строках не появится `True`, как в этом примере:

```console
NAMESPACE                        NAME                        AGE    READY   STATUS
cozy-cert-manager                cert-manager                4m1s   True    Release reconciliation succeeded
cozy-cert-manager                cert-manager-issuers        4m1s   True    Release reconciliation succeeded
cozy-cilium                      cilium                      4m1s   True    Release reconciliation succeeded
cozy-cluster-api                 capi-operator               4m1s   True    Release reconciliation succeeded
cozy-cluster-api                 capi-providers              4m1s   True    Release reconciliation succeeded
cozy-dashboard                   dashboard                   4m1s   True    Release reconciliation succeeded
cozy-grafana-operator            grafana-operator            4m1s   True    Release reconciliation succeeded
cozy-kamaji                      kamaji                      4m1s   True    Release reconciliation succeeded
cozy-kubeovn                     kubeovn                     4m1s   True    Release reconciliation succeeded
cozy-kubevirt-cdi                kubevirt-cdi                4m1s   True    Release reconciliation succeeded
cozy-kubevirt-cdi                kubevirt-cdi-operator       4m1s   True    Release reconciliation succeeded
cozy-kubevirt                    kubevirt                    4m1s   True    Release reconciliation succeeded
cozy-kubevirt                    kubevirt-operator           4m1s   True    Release reconciliation succeeded
cozy-linstor                     linstor                     4m1s   True    Release reconciliation succeeded
cozy-linstor                     piraeus-operator            4m1s   True    Release reconciliation succeeded
cozy-mariadb-operator            mariadb-operator            4m1s   True    Release reconciliation succeeded
cozy-metallb                     metallb                     4m1s   True    Release reconciliation succeeded
cozy-monitoring                  monitoring                  4m1s   True    Release reconciliation succeeded
cozy-postgres-operator           postgres-operator           4m1s   True    Release reconciliation succeeded
cozy-rabbitmq-operator           rabbitmq-operator           4m1s   True    Release reconciliation succeeded
cozy-redis-operator              redis-operator              4m1s   True    Release reconciliation succeeded
cozy-telepresence                telepresence                4m1s   True    Release reconciliation succeeded
cozy-victoria-metrics-operator   victoria-metrics-operator   4m1s   True    Release reconciliation succeeded
tenant-root                      tenant-root                 4m1s   True    Release reconciliation succeeded
```

Список компонентов в вашей установке может отличаться от приведённого выше,
так как он зависит от вашей конфигурации и версии Cozystack.

Когда у всех компонентов появится `READY: True`, можно переходить к настройке подсистем.


## 3. Настройка хранилища

Kubernetes нужен слой хранилища для предоставления persistent volumes приложениям, но собственного такого механизма у него нет.
В качестве подсистемы хранения Cozystack использует [LINSTOR](https://github.com/LINBIT/linstor-server).

Далее мы получим доступ к интерфейсу LINSTOR, создадим storage pool'ы и определим storage class'ы.


### 3.1. Проверьте устройства хранения

1.  Настройте alias для доступа к LINSTOR:

    ```bash
    alias linstor='kubectl exec -n cozy-linstor deploy/linstor-controller -- linstor'
    ```

1.  Выведите список узлов и проверьте их готовность:

    ```bash
    linstor node list
    ```

    В примере ниже показаны имена узлов и их состояние:

    ```console
    +-------------------------------------------------------+
    | Node | NodeType  | Addresses                 | State  |
    |=======================================================|
    | srv1 | SATELLITE | 192.168.100.11:3367 (SSL) | Online |
    | srv2 | SATELLITE | 192.168.100.12:3367 (SSL) | Online |
    | srv3 | SATELLITE | 192.168.100.13:3367 (SSL) | Online |
    +-------------------------------------------------------+
    ```

1.  Выведите список доступных пустых устройств:

    ```bash
    linstor physical-storage list
    ```

    В примере ниже отображаются те же имена узлов:

    ```console
    +--------------------------------------------+
    | Size         | Rotational | Nodes          |
    |============================================|
    | 107374182400 | True       | srv3[/dev/sdb] |
    |              |            | srv1[/dev/sdb] |
    |              |            | srv2[/dev/sdb] |
    +--------------------------------------------+
    ```

### 3.2. Создайте storage pool'ы

1.  Создайте storage pool'ы на основе ZFS:

    ```bash
    linstor ps cdp zfs srv1 /dev/sdb --pool-name data --storage-pool data
    linstor ps cdp zfs srv2 /dev/sdb --pool-name data --storage-pool data
    linstor ps cdp zfs srv3 /dev/sdb --pool-name data --storage-pool data
    ```

    [Рекомендуется](https://github.com/LINBIT/linstor-server/issues/463#issuecomment-3401472020)
    установить для ZFS storage pool'ов `failmode=continue`, чтобы обработкой отказов диска занимался DRBD, а не ZFS.

    ```bash
    kubectl exec -ti -n cozy-linstor ds/linstor-satellite.srv1 -- zpool set failmode=continue data
    kubectl exec -ti -n cozy-linstor ds/linstor-satellite.srv2 -- zpool set failmode=continue data
    kubectl exec -ti -n cozy-linstor ds/linstor-satellite.srv3 -- zpool set failmode=continue data
    ```

1.  Проверьте результат, выведя список storage pool'ов:

    ```bash
    linstor sp l
    ```

    Пример вывода:

    ```console
    +-------------------------------------------------------------------------------------------------------------------------------------+
    | StoragePool          | Node | Driver   | PoolName | FreeCapacity | TotalCapacity | CanSnapshots | State | SharedName                |
    |=====================================================================================================================================|
    | DfltDisklessStorPool | srv1 | DISKLESS |          |              |               | False        | Ok    | srv1;DfltDisklessStorPool |
    | DfltDisklessStorPool | srv2 | DISKLESS |          |              |               | False        | Ok    | srv2;DfltDisklessStorPool |
    | DfltDisklessStorPool | srv3 | DISKLESS |          |              |               | False        | Ok    | srv3;DfltDisklessStorPool |
    | data                 | srv1 | ZFS      | data     |    96.41 GiB |     99.50 GiB | True         | Ok    | srv1;data                 |
    | data                 | srv2 | ZFS      | data     |    96.41 GiB |     99.50 GiB | True         | Ok    | srv2;data                 |
    | data                 | srv3 | ZFS      | data     |    96.41 GiB |     99.50 GiB | True         | Ok    | srv3;data                 |
    +-------------------------------------------------------------------------------------------------------------------------------------+
    ```

### 3.3. Создайте storage class'ы

Наконец, можно создать несколько storage class'ов, один из которых будет классом по умолчанию.


1.  Создайте файл с описанием storage class'ов.
    Ниже приведён разумный пример по умолчанию с двумя классами: `local` (по умолчанию) и `replicated`.

    **storageclasses.yaml:**

    ```yaml
    ---
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: local
      annotations:
        storageclass.kubernetes.io/is-default-class: "true"
    provisioner: linstor.csi.linbit.com
    parameters:
      linstor.csi.linbit.com/storagePool: "data"
      linstor.csi.linbit.com/layerList: "storage"
      linstor.csi.linbit.com/allowRemoteVolumeAccess: "false"
    volumeBindingMode: WaitForFirstConsumer
    allowVolumeExpansion: true
    ---
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: replicated
    provisioner: linstor.csi.linbit.com
    parameters:
      linstor.csi.linbit.com/storagePool: "data"
      linstor.csi.linbit.com/autoPlace: "3"
      linstor.csi.linbit.com/layerList: "drbd storage"
      linstor.csi.linbit.com/allowRemoteVolumeAccess: "true"
      property.linstor.csi.linbit.com/DrbdOptions/auto-quorum: suspend-io
      property.linstor.csi.linbit.com/DrbdOptions/Resource/on-no-data-accessible: suspend-io
      property.linstor.csi.linbit.com/DrbdOptions/Resource/on-suspended-primary-outdated: force-secondary
      property.linstor.csi.linbit.com/DrbdOptions/Net/rr-conflict: retry-connect
    volumeBindingMode: Immediate
    allowVolumeExpansion: true
    ```

1.  Примените конфигурацию storage class'ов

    ```bash
    kubectl apply -f storageclasses.yaml
    ```

1.  Убедитесь, что storage class'ы были успешно созданы:

    ```bash
    kubectl get storageclasses
    ```

    Пример вывода:

    ```console
    NAME              PROVISIONER              RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
    local (default)   linstor.csi.linbit.com   Delete          WaitForFirstConsumer   true                   11m
    replicated        linstor.csi.linbit.com   Delete          Immediate              true                   11m
    ```


## 4. Настройка сети

Далее мы настроим способ доступа к кластеру Cozystack.
На этом шаге есть два варианта в зависимости от доступной инфраструктуры:

-   Для собственного bare metal или self-hosted ВМ выбирайте вариант с MetalLB.
    MetalLB — это балансировщик нагрузки по умолчанию в Cozystack.
-   Для ВМ и выделенных серверов у облачных провайдеров выбирайте настройку через публичные IP.
    [Большинство облачных провайдеров не поддерживают MetalLB](https://metallb.universe.tf/installation/clouds/).

    Загляните в раздел [provider-specific installation]({{% ref "/docs/v1.2/install/providers" %}}).
    Возможно, там уже есть инструкции для вашего провайдера, подходящие для развёртывания production-ready кластера.

### 4.a Настройка MetalLB

В Cozystack используются три типа IP-адресов:

-   IP-адреса узлов: постоянные и действуют только внутри кластера.
-   Виртуальный floating IP: используется для доступа к одному из узлов кластера и также действует только внутри кластера.
-   IP-адреса внешнего доступа: используются LoadBalancer'ами для публикации сервисов за пределами кластера.

Сервисы с внешними IP могут публиковаться в двух режимах: L2 и BGP.
Режим L2 проще, но требует, чтобы узлы находились в одном L2-домене, и хуже подходит для балансировки нагрузки.
Режим BGP настраивается сложнее: нужны BGP peer'ы, готовые принимать анонсы, зато он позволяет организовать корректную балансировку и даёт больше гибкости при выборе диапазонов IP-адресов.

Выберите диапазон неиспользуемых IP-адресов для сервисов; в примере используется диапазон `192.168.100.200-192.168.100.250`.
Если вы используете режим L2, эти IP должны либо принадлежать той же сети, что и узлы, либо до них должны существовать все необходимые маршруты.

Для режима BGP также потребуются IP-адреса BGP peer'ов и локальные и удалённые номера AS. В примере используются `192.168.20.254` как IP peer'а и номера AS 65000 и 65001 как локальный и удалённый соответственно.

Создайте и примените файл с описанием пула адресов.

**metallb-ip-address-pool.yml**
```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: cozystack
  namespace: cozy-metallb
spec:
  addresses:
    # используется для публикации сервисов за пределами кластера
    - 192.168.100.200-192.168.100.250
  autoAssign: true
  avoidBuggyIPs: false
```

```bash
kubectl apply -f metallb-ip-address-pool.yml
```

Создайте и примените ресурсы, необходимые для L2- или BGP-анонса.

{{< tabs name="metallb_announce" >}}
{{% tab name="L2 mode" %}}
L2Advertisement использует имя ресурса IPAddressPool, который мы создали на предыдущем шаге.

**metallb-l2-advertisement.yml**
```yaml
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: cozystack
  namespace: cozy-metallb
spec:
  ipAddressPools:
    - cozystack
```
<br/>

Примените изменения.

```bash
kubectl apply -f metallb-l2-advertisement.yml
```
{{% /tab %}}
{{% tab name="BGP mode" %}}
Сначала создайте отдельный ресурс BGPPeer для **каждого** peer'а.

**metallb-bgp-peer.yml**
```yaml
apiVersion: metallb.io/v1beta2
kind: BGPPeer
metadata:
  name: peer1
  namespace: cozy-metallb
spec:
  myASN: 65000
  peerASN: 65001
  peerAddress: 192.168.20.254
```
<br/>

Затем создайте один ресурс BGPAdvertisement.

**metallb-bgp-advertisement.yml**
```yaml
apiVersion: metallb.io/v1beta1
kind: BGPAdvertisement
metadata:
  name: cozystack
  namespace: cozy-metallb
spec:
  ipAddressPools:
  - cozystack
```
<br/>
Примените изменения.

```bash
kubectl apply -f metallb-bgp-peer.yml
kubectl apply -f metallb-bgp-advertisement.yml
```
{{% /tab %}}
{{< /tabs >}}
<br/>

Теперь, когда MetalLB настроен, включите `ingress` в `tenant-root`:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '
{"spec":{
  "ingress": true
}}'
```

Чтобы убедиться, что всё настроено корректно, проверьте HelmRelease'ы `ingress` и `ingress-nginx-system`:

```bash
kubectl -n tenant-root get hr ingress ingress-nginx-system
```

Пример корректного вывода:
```console
NAME                   AGE   READY   STATUS
ingress                47m   True    Helm upgrade succeeded for release tenant-root/ingress.v3 with chart ingress@1.8.0
ingress-nginx-system   47m   True    Helm upgrade succeeded for release tenant-root/ingress-nginx-system.v2 with chart cozy-ingress-nginx@0.35.1
```

Затем проверьте состояние сервиса `root-ingress-controller`:

```bash
kubectl -n tenant-root get svc root-ingress-controller
```

Сервис должен быть развёрнут как `TYPE: LoadBalancer` и иметь корректный внешний IP:

```console
NAME                      TYPE           CLUSTER-IP      EXTERNAL-IP       PORT(S)          AGE
root-ingress-controller   LoadBalancer   10.96.91.83     192.168.100.200   80/TCP,443/TCP   48m
```

### 4.b. Настройка публичных IP узлов

Если ваш облачный провайдер не поддерживает MetalLB, вы можете опубликовать ingress controller через внешние IP-адреса ваших узлов.

Если публичные IP привязаны непосредственно к узлам, укажите их.
Если публичные IP предоставляются через 1:1 NAT, как у некоторых облачных провайдеров, используйте IP-адреса **внешних** сетевых интерфейсов.

В примере используются `192.168.100.11`, `192.168.100.12` и `192.168.100.13`.

Сначала добавьте внешние IP в Platform Package:

```bash
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=merge -p '{
  "spec": {
    "components": {
      "platform": {
        "values": {
          "publishing": {
            "externalIPs": [
              "192.168.100.11",
              "192.168.100.12",
              "192.168.100.13"
            ]
          }
        }
      }
    }
  }
}'
```

Затем включите `ingress` для корневого tenant'а:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '{
  "spec":{
    "ingress": true
  }
}'
```

Наконец, добавьте внешние IP-адреса в список `externalIPs` в конфигурации Ingress:

```bash
kubectl patch -n tenant-root ingresses.apps.cozystack.io ingress --type=merge -p '{
  "spec":{
    "externalIPs": [
      "192.168.100.11",
      "192.168.100.12",
      "192.168.100.13"
    ]
  }
}'
```

После этого ваш Ingress будет доступен по указанным IP-адресам.
Проверьте это так:

```bash
kubectl get svc -n tenant-root root-ingress-controller
```

Сервис должен быть развёрнут как `TYPE: ClusterIP` и содержать полный список внешних IP:

```console
NAME                     TYPE       CLUSTER-IP   EXTERNAL-IP                                   PORT(S)         AGE
root-ingress-controller  ClusterIP  10.96.91.83  192.168.100.11,192.168.100.12,192.168.100.13  80/TCP,443/TCP  48m
```

## 5. Завершение установки

### 5.1. Настройте сервисы корневого tenant'а

Включите `etcd` и `monitoring` для корневого tenant'а:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '
{"spec":{
  "monitoring": true,
  "etcd": true
}}'
```

### 5.2. Проверьте состояние и состав кластера

Проверьте созданные persistent volume'ы:

```bash
kubectl get pvc -n tenant-root
```

Пример вывода:

```console
NAME                                     STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
data-etcd-0                              Bound    pvc-4cbd29cc-a29f-453d-b412-451647cd04bf   10Gi       RWO            local          <unset>                 2m10s
data-etcd-1                              Bound    pvc-1579f95a-a69d-4a26-bcc2-b15ccdbede0d   10Gi       RWO            local          <unset>                 115s
data-etcd-2                              Bound    pvc-907009e5-88bf-4d18-91e7-b56b0dbfb97e   10Gi       RWO            local          <unset>                 91s
grafana-db-1                             Bound    pvc-7b3f4e23-228a-46fd-b820-d033ef4679af   10Gi       RWO            local          <unset>                 2m41s
grafana-db-2                             Bound    pvc-ac9b72a4-f40e-47e8-ad24-f50d843b55e4   10Gi       RWO            local          <unset>                 113s
vmselect-cachedir-vmselect-longterm-0    Bound    pvc-622fa398-2104-459f-8744-565eee0a13f1   2Gi        RWO            local          <unset>                 2m21s
vmselect-cachedir-vmselect-longterm-1    Bound    pvc-fc9349f5-02b2-4e25-8bef-6cbc5cc6d690   2Gi        RWO            local          <unset>                 2m21s
vmselect-cachedir-vmselect-shortterm-0   Bound    pvc-7acc7ff6-6b9b-4676-bd1f-6867ea7165e2   2Gi        RWO            local          <unset>                 2m41s
vmselect-cachedir-vmselect-shortterm-1   Bound    pvc-e514f12b-f1f6-40ff-9838-a6bda3580eb7   2Gi        RWO            local          <unset>                 2m40s
vmstorage-db-vmstorage-longterm-0        Bound    pvc-e8ac7fc3-df0d-4692-aebf-9f66f72f9fef   10Gi       RWO            local          <unset>                 2m21s
vmstorage-db-vmstorage-longterm-1        Bound    pvc-68b5ceaf-3ed1-4e5a-9568-6b95911c7c3a   10Gi       RWO            local          <unset>                 2m21s
vmstorage-db-vmstorage-shortterm-0       Bound    pvc-cee3a2a4-5680-4880-bc2a-85c14dba9380   10Gi       RWO            local          <unset>                 2m41s
vmstorage-db-vmstorage-shortterm-1       Bound    pvc-d55c235d-cada-4c4a-8299-e5fc3f161789   10Gi       RWO            local          <unset>                 2m41s
```

Убедитесь, что все pod'ы запущены:

```bash
kubectl get pod -n tenant-root
```

пример вывода:
```console
NAME                                           READY   STATUS    RESTARTS       AGE
etcd-0                                         1/1     Running   0              2m1s
etcd-1                                         1/1     Running   0              106s
etcd-2                                         1/1     Running   0              82s
grafana-db-1                                   1/1     Running   0              119s
grafana-db-2                                   1/1     Running   0              13s
grafana-deployment-74b5656d6-5dcvn             1/1     Running   0              90s
grafana-deployment-74b5656d6-q5589             1/1     Running   1 (105s ago)   111s
root-ingress-controller-6ccf55bc6d-pg79l       2/2     Running   0              2m27s
root-ingress-controller-6ccf55bc6d-xbs6x       2/2     Running   0              2m29s
root-ingress-defaultbackend-686bcbbd6c-5zbvp   1/1     Running   0              2m29s
vmalert-vmalert-644986d5c-7hvwk                2/2     Running   0              2m30s
vmalertmanager-alertmanager-0                  2/2     Running   0              2m32s
vmalertmanager-alertmanager-1                  2/2     Running   0              2m31s
vminsert-longterm-75789465f-hc6cz              1/1     Running   0              2m10s
vminsert-longterm-75789465f-m2v4t              1/1     Running   0              2m12s
vminsert-shortterm-78456f8fd9-wlwww            1/1     Running   0              2m29s
vminsert-shortterm-78456f8fd9-xg7cw            1/1     Running   0              2m28s
vmselect-longterm-0                            1/1     Running   0              2m12s
vmselect-longterm-1                            1/1     Running   0              2m12s
vmselect-shortterm-0                           1/1     Running   0              2m31s
vmselect-shortterm-1                           1/1     Running   0              2m30s
vmstorage-longterm-0                           1/1     Running   0              2m12s
vmstorage-longterm-1                           1/1     Running   0              2m12s
vmstorage-shortterm-0                          1/1     Running   0              2m32s
vmstorage-shortterm-1                          1/1     Running   0              2m31s
```

Получите публичный IP ingress controller:

```bash
kubectl get svc -n tenant-root root-ingress-controller
```

Пример вывода:

```console
NAME                      TYPE           CLUSTER-IP     EXTERNAL-IP       PORT(S)                      AGE
root-ingress-controller   LoadBalancer   10.96.16.141   192.168.100.200   80:31632/TCP,443:30113/TCP   3m33s
```

### 5.3 Доступ к дашборду Cozystack

Если вы включили `dashboard` в список `publishing.exposedServices` вашего Platform Package (как показано на шаге 2), дашборд Cozystack уже доступен.

Если в исходной конфигурации его не было, обновите Platform Package:

```bash
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=json \
  -p '[{"op": "add", "path": "/spec/components/platform/values/publishing/exposedServices/-", "value": "dashboard"}]'
```

Откройте `dashboard.example.org`, чтобы перейти в системный дашборд, где `example.org` — домен, указанный вами для `tenant-root`.
Там вы увидите окно входа, ожидающее токен аутентификации.

Получите токен аутентификации для `tenant-root`:

```bash
kubectl get secret -n tenant-root tenant-root -o go-template='{{ printf "%s\n" (index .data "token" | base64decode) }}'
```

Войдите с этим токеном.
Теперь вы можете пользоваться дашбордом как администратор.

Дальше вы сможете:

-   Настроить OIDC и использовать его вместо токенов для аутентификации.
-   Создавать пользовательские tenant'ы и выдавать пользователям доступ через токены или OIDC.

### 5.4 Доступ к метрикам в Grafana

Используйте `grafana.example.org` для доступа к системному мониторингу, где `example.org` — домен, указанный для `tenant-root`.
В этом примере `grafana.example.org` доступен по адресу 192.168.100.200.

-   логин: `admin`
-   получите пароль:

    ```bash
    kubectl get secret -n tenant-root grafana-admin-password -o go-template='{{ printf "%s\n" (index .data "password" | base64decode) }}'
    ```

## Следующий шаг

Продолжите руководство по Cozystack и [создайте пользовательский tenant]({{% ref "./create-tenant" %}}).
