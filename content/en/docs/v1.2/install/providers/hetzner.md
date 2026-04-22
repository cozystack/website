---
title: Как установить Cozystack в Hetzner
linkTitle: Hetzner.com
description: "Как установить Cozystack в Hetzner"
weight: 30
aliases:
  - /docs/v1.2/operations/talos/installation/hetzner
  - /docs/v1.2/talos/installation/hetzner
  - /docs/v1.2/talos/install/hetzner
---

Это руководство поможет установить Cozystack на выделенные серверы [Hetzner](https://www.hetzner.com/).
Процесс состоит из нескольких шагов: подготовки инфраструктуры, установки Talos Linux, настройки cloud-init и инициализации кластера.


## Подготовка инфраструктуры и сети

Установка в Hetzner включает общие [требования к оборудованию]({{% ref "/docs/v1.2/install/hardware-requirements" %}}) с несколькими дополнениями.

### Варианты сети

Есть два варианта сетевой связности между узлами Cozystack в кластере:

-   **Создание подсети с помощью vSwitch.**
    Этот вариант рекомендуется для production-сред.

    Для этого варианта выделенные серверы должны быть развернуты через [Hetzner robot](https://robot.hetzner.com/).
    Также Hetzner требует использовать собственный load balancer RobotLB вместо стандартного для Cozystack MetalLB.
    Cozystack включает RobotLB как optional component начиная с релиза v0.35.0.
    
-   **Использование только public IP выделенных серверов.**
    Этот вариант подходит для proof-of-concept установки, но не рекомендуется для production.


### Настройка подсети с vSwitch

Выполните следующие шаги, чтобы подготовить серверы к установке Cozystack:

1.  Выполните сетевые настройки в Hetzner (только для варианта **vSwitch subnet**).

    Выполните шаги из [раздела Prerequisites](https://github.com/Intreecom/robotlb/blob/master/README.md#prerequisites)
    в README RobotLB:

    1.  Создайте [vSwitch](https://docs.hetzner.com/cloud/networks/connect-dedi-vswitch/).
    2.  Используйте его, чтобы назначить IP вашим выделенным серверам в Hetzner.
    3.  Создайте подсеть, чтобы [подключить выделенные серверы](https://docs.hetzner.com/cloud/networks/connect-dedi-vswitch/).

    Обратите внимание, что RobotLB не нужно развертывать вручную.
    Вместо этого вы настроите Cozystack на установку RobotLB как optional component на шаге "Установка Cozystack" в этом руководстве.

### Отключение Secure Boot

1.  Убедитесь, что Secure Boot отключен.

    Secure Boot сейчас не поддерживается в Talos Linux.
    Если сервер настроен на использование Secure Boot, отключите эту функцию в BIOS.
    Иначе она заблокирует загрузку сервера после установки Talos Linux.

    Проверьте это следующей командой:

    ```console
    # mokutil --sb-state
    SecureBoot disabled
    Platform is in Setup Mode
    ```

В остальной части руководства будем считать, что используется следующая сетевая конфигурация:

- Облачная сеть Hetzner — `10.0.0.0/16`, имя `network-1`.
- vSwitch subnet с выделенными серверами — `10.0.1.0/24`
- VLAN ID vSwitch — `4000`

- Есть три выделенных сервера со следующими public и private IP:
  - `node1`, public IP `12.34.56.101`, IP в vSwitch subnet `10.0.1.101`
  - `node2`, public IP `12.34.56.102`, IP в vSwitch subnet `10.0.1.102`
  - `node3`, public IP `12.34.56.103`, IP в vSwitch subnet `10.0.1.103`

## 1. Установка Talos Linux

Первый этап развертывания Cozystack — установка Talos Linux на выделенные серверы.

Talos — дистрибутив Linux, созданный для максимально безопасного и эффективного запуска Kubernetes.
Чтобы узнать, почему Cozystack использует Talos как основу кластера,
прочитайте [Talos Linux в Cozystack]({{% ref "/docs/v1.2/guides/talos" %}}).

### 1.1 Установка boot-to-talos в Rescue Mode

Talos будет загружен из rescue system Hetzner с помощью утилиты [`boot-to-talos`](https://github.com/cozystack/boot-to-talos).
Позже, при применении конфигурации Talm, Talos будет установлен на диск.
Выполните эти шаги на каждом выделенном сервере.

1.  Переведите сервер в rescue mode и войдите на него по SSH.

1.  Определите диск, который позже будет использоваться для Talos (например, `/dev/nvme0n1`).

1.  Скачайте и установите `boot-to-talos`:

    ```bash
    curl -sSL https://github.com/cozystack/boot-to-talos/raw/refs/heads/main/hack/install.sh | sh -s
    ```

    После этого бинарный файл `boot-to-talos` должен быть доступен в `PATH`:

    ```bash
    boot-to-talos -h
    ```

### 1.2. Установка Talos Linux с boot-to-talos

1.  Запустите installer:

    ```bash
    boot-to-talos
    ```

    При запросе:

-   Выберите режим `1. boot`.
-   Подтвердите или измените образ Talos installer.
        Значение по умолчанию указывает на образ Talos от Cozystack (стандартный образ Cozystack подходит).
-   Укажите сетевые настройки (имя интерфейса, IP-адрес, netmask, gateway), соответствующие подготовленной ранее конфигурации
        (vSwitch subnet или public IP).
-   При необходимости настройте serial console, если используете ее для удаленного доступа.

    Утилита скачает образ Talos installer, извлечет kernel и initramfs и загрузит узел в Talos Linux
    (с помощью механизма kexec), не изменяя диски.

### 1.3. Загрузка в Talos Linux

После завершения `boot-to-talos` сервер автоматически перезагрузится в Talos Linux в maintenance mode.

Повторите ту же процедуру для всех выделенных серверов в кластере.
Когда все узлы загрузятся в Talos, переходите к следующему разделу и настройте их с помощью Talm.

## 2. Установка кластера Kubernetes

Теперь, когда Talos загружен в maintenance mode, он должен получить конфигурацию и настроить кластер Kubernetes.
Есть [несколько вариантов]({{% ref "/docs/v1.2/install/kubernetes" %}}) создания и применения конфигурации Talos.
В этом руководстве используется [Talm](https://github.com/cozystack/talm) — собственный инструмент Cozystack для управления конфигурацией Talos.

Эта часть руководства основана на общем [руководстве по Talm]({{% ref "/docs/v1.2/install/kubernetes/talm" %}}),
но содержит инструкции и примеры, специфичные для Hetzner.

### 2.1. Подготовка конфигурации узлов с Talm

1.  Если Talm еще не установлен, начните с установки последней версии для вашей ОС:

    ```bash
    curl -sSL https://github.com/cozystack/talm/raw/refs/heads/main/hack/install.sh | sh -s
    ```

1.  Создайте каталог для конфигурации кластера и инициализируйте в нем проект Talm.

    Обратите внимание, что в Talm есть встроенный preset для Cozystack, который используется через `--preset cozystack`:

    ```bash
    mkdir -p hetzner-cluster
    cd hetzner-cluster
    talm init --preset cozystack --name hetzner
    ```

    Теперь в каталоге `hetzner-cluster` создан набор файлов.
    Подробнее о роли каждого файла см. в
    [руководстве по Talm]({{% ref "/docs/v1.2/install/kubernetes/talm#2-initialize-cluster-configuration" %}}).

1.  Отредактируйте `values.yaml`, изменив следующие значения:

-   В списке `advertisedSubnets` должна быть vSwitch subnet.
-   `endpoint` и `floatingIP` должны использовать неназначенный IP из этой подсети.
        Этот IP будет использоваться для доступа к cluster API через `talosctl` и `kubectl`.
-   `podSubnets` и `serviceSubnets` должны использовать другие подсети из облачной сети Hetzner,
        которые не пересекаются друг с другом и с vSwitch subnet.

    ```yaml
    endpoint: "https://10.0.1.100:6443"
    clusterDomain: cozy.local
    # floatingIP указывает на primary etcd node
    floatingIP: 10.0.1.100
    image: "ghcr.io/cozystack/cozystack/talos:v1.9.5"
    podSubnets:
    - 10.244.0.0/16
    serviceSubnets:
    - 10.96.0.0/16
    advertisedSubnets:
    # vSwitch subnet
    - 10.0.1.0/24
    oidcIssuerUrl: ""
    certSANs: []
    ```

1.  Создайте конфигурационные файлы узлов из шаблонов и values:
    
    ```bash
    mkdir -p nodes
    talm template -e 12.34.56.101 -n 12.34.56.101 -t templates/controlplane.yaml -i > nodes/node1.yaml
    talm template -e 12.34.56.102 -n 12.34.56.102 -t templates/controlplane.yaml -i > nodes/node2.yaml
    talm template -e 12.34.56.103 -n 12.34.56.103 -t templates/controlplane.yaml -i > nodes/node3.yaml
    ```

    В этом руководстве предполагается, что у вас только три выделенных сервера, поэтому все они должны быть узлами control plane.
    Если серверов больше и вы хотите разделить control plane и worker-узлы, используйте `templates/worker.yaml` для создания worker configs:

    ```bash
    taml template -e 12.34.56.104 -n 12.34.56.104 -t templates/worker.yaml -i > nodes/worker1.yaml
    ```

1.  Отредактируйте конфигурационный файл каждого узла, добавив VLAN configuration.

    Используйте следующий diff как пример и учитывайте, что для каждого узла должен использоваться его IP в subnet:

    ```diff
    machine:
      network:
        interfaces:
          - deviceSelector:
            # ...
    -       vip:
    -         ip: 10.0.1.100
    +       vlans:
    +         - addresses:
    +             # отличается для каждого узла
    +             - 10.0.1.101/24
    +           routes:
    +             - network: 10.0.0.0/16
    +               gateway: 10.0.1.1
    +           vlanId: 4000
    +           vip:
    +             ip: 10.0.1.100
    ```

### 2.2. Применение конфигурации узлов

1.  Когда конфигурационные файлы будут готовы, примените конфигурацию к каждому узлу:

    ```bash
    talm apply -f nodes/node1.yaml -i
    talm apply -f nodes/node2.yaml -i
    talm apply -f nodes/node3.yaml -i
    ```

    Эта команда инициализирует узлы и настраивает аутентифицированное соединение, поэтому дальше `-i` (`--insecure`) не потребуется.
    Если команда выполнена успешно, она вернет IP узла:
    
    ```console
    $ talm apply -f nodes/node1.yaml -i
    - talm: file=nodes/node1.yaml, nodes=[12.34.56.101], endpoints=[12.34.56.101]
    ```

1.  Дождитесь, пока все узлы перезагрузятся, и переходите к следующему шагу.
    Когда узлы будут готовы, они откроют порт `50000`; это признак того, что узел завершил настройку Talos и перезагрузился.

    Если нужно автоматизировать проверку готовности узлов, используйте такой пример:

    ```bash
    timeout 60 sh -c 'until \
      nc -nzv 12.34.56.101 50000 && \
      nc -nzv 12.34.56.102 50000 && \
      nc -nzv 12.34.56.103 50000; \
      do sleep 1; done'
    ```
        
1.  Инициализируйте кластер Kubernetes с одного из узлов control plane:
    
    ```bash
    talm bootstrap -f nodes/node1.yaml
    ```

1.  Сгенерируйте административный `kubeconfig` для доступа к кластеру через тот же узел control plane:

    ```bash
    talm kubeconfig -f nodes/node1.yaml
    ```

1.  Измените URL server в `kubeconfig` на public IP

    ```diff
      apiVersion: v1                                                                                                          
      clusters:                                                                                                               
      - cluster:                                                                                                              
    -     server: https://10.0.1.101:6443   
    +     server: https://12.34.56.101:6443   
    ```
    
1.  Затем настройте переменную `KUBECONFIG` или другие инструменты, чтобы сделать эту конфигурацию
    доступной клиенту `kubectl`:

    ```bash
    export KUBECONFIG=$PWD/kubeconfig
    ```        

1.  Проверьте, что кластер доступен с новым `kubeconfig`:

    ```bash
    kubectl get ns
    ```

    Пример вывода:
    
    ```console
    NAME              STATUS   AGE
    default           Active   7m56s
    kube-node-lease   Active   7m56s
    kube-public       Active   7m56s
    kube-system       Active   7m56s
    ```

На этом этапе у вас есть выделенные серверы с Talos Linux и развернутый на них кластер Kubernetes.
Также у вас есть `kubeconfig`, который будет использоваться для доступа к кластеру через `kubectl` и установки Cozystack.

## 3. Установка Cozystack

Финальный этап развертывания кластера Cozystack в Hetzner — установка Cozystack в подготовленный кластер Kubernetes.

### 3.1. Запуск Cozystack Installer

1.  Установите Cozystack operator:

    ```bash
    helm upgrade --install cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
      --version X.Y.Z \
      --namespace cozy-system \
      --create-namespace
    ```

    Замените `X.Y.Z` на нужную версию Cozystack со [страницы релизов](https://github.com/cozystack/cozystack/releases).

1.  Создайте файл Platform Package, **cozystack-platform.yaml**.

    Обратите внимание, что этот файл повторно использует подсети для pods и services, которые использовались в `values.yaml` перед созданием конфигурации Talos с Talm.
    Также обратите внимание, как стандартный load balancer Cozystack MetalLB заменяется на RobotLB с помощью `disabledPackages` и `enabledPackages`.

    Замените `example.org` на маршрутизируемое fully-qualified domain name (FQDN), которое вы будете использовать для платформы на базе Cozystack.
    Если такого домена нет, можно использовать [nip.io](https://nip.io/) с записью через дефис.

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
            bundles:
              disabledPackages:
                - cozystack.metallb
              enabledPackages:
                - cozystack.hetzner-robotlb
            publishing:
              host: "example.org"
              apiServerEndpoint: "https://api.example.org:443"
              exposedServices:
                - dashboard
                - api
            networking:
              ## podSubnets из конфигурации узлов
              podCIDR: "10.244.0.0/16"
              podGateway: "10.244.0.1"
              ## serviceSubnets из конфигурации узлов
              serviceCIDR: "10.96.0.0/16"
    ```

1.  Примените Platform Package:

    ```bash
    kubectl apply -f cozystack-platform.yaml
    ```

    Operator запустит установку, которая займет некоторое время.
    При необходимости можно отслеживать логи operator:

    ```bash
    kubectl logs -n cozy-system deploy/cozystack-operator -f
    ```

1.  Проверьте состояние установки:
    
    ```bash
    kubectl get hr -A
    ```

    Когда установка завершится, все сервисы перейдут в состояние `READY: True`:
    ```console
    NAMESPACE                        NAME                        AGE    READY   STATUS
    cozy-cert-manager                cert-manager                4m1s   True    Release reconciliation succeeded
    cozy-cert-manager                cert-manager-issuers        4m1s   True    Release reconciliation succeeded
    cozy-cilium                      cilium                      4m1s   True    Release reconciliation succeeded
    ...
    ```

### 3.2 Создание Load Balancer с RobotLB

Hetzner требует использовать собственный RobotLB вместо стандартного MetalLB в Cozystack.
RobotLB уже установлен как компонент Cozystack и работает как сервис внутри него.
Теперь ему нужен token для создания ресурса load balancer в Hetzner.

1.  Создайте Hetzner API token для RobotLB.

    Перейдите в консоль Hetzner, откройте Security и создайте token с разрешениями `Read` и `Write`.

1.  Передайте token в RobotLB, чтобы создать load balancer в Hetzner.

    Используйте Hetzner API token, чтобы создать Kubernetes secret в Cozystack.

-   Если используется **private network** (vSwitch), укажите имя сети:

        ```bash
        export ROBOTLB_HCLOUD_TOKEN="<token>"
        export ROBOTLB_DEFAULT_NETWORK="<network name>"

        kubectl create secret generic hetzner-robotlb-credentials \
          --namespace=cozy-hetzner-robotlb \
          --from-literal=ROBOTLB_HCLOUD_TOKEN="$ROBOTLB_HCLOUD_TOKEN" \
          --from-literal=ROBOTLB_DEFAULT_NETWORK="$ROBOTLB_DEFAULT_NETWORK"
        ```

-   Если используются **только public IP** (без vSwitch), не указывайте `ROBOTLB_DEFAULT_NETWORK`:

        ```bash
        export ROBOTLB_HCLOUD_TOKEN="<token>"

        kubectl create secret generic hetzner-robotlb-credentials \
          --namespace=cozy-hetzner-robotlb \
          --from-literal=ROBOTLB_HCLOUD_TOKEN="$ROBOTLB_HCLOUD_TOKEN"
        ```

        В этом случае RobotLB будет использовать public IP узлов (ExternalIP) как targets load balancer.
        Чтобы это работало, на узлах должны быть настроены адреса ExternalIP.
        Самый простой способ добиться этого — установить [local-ccm](https://github.com/cozystack/local-ccm),
        который автоматически назначает public IP в поле `.status.addresses` узлов.

    После получения token сервис RobotLB в Cozystack создаст load balancer в Hetzner.

### 3.3 Настройка хранилища с LINSTOR

Настройка LINSTOR в Hetzner не отличается от других инфраструктурных конфигураций.
Следуйте [руководству по настройке хранилища]({{% ref "/docs/v1.2/getting-started/install-cozystack#3-configure-storage" %}}) из tutorial по Cozystack.

### 3.4. Запуск сервисов в Root Tenant

Настройте базовые сервисы (`etcd`, `monitoring` и `ingress`) в root tenant:

```bash
kubectl patch -n tenant-root tenants.apps.cozystack.io root --type=merge -p '
{"spec":{
  "ingress": true,
  "monitoring": true,
  "etcd": true
}}'
```

## Примечания и troubleshooting

{{% alert color="warning" %}}
:warning: Если возникают проблемы с загрузкой Talos Linux на узле, это может быть связано с параметрами serial console в конфигурации GRUB:
`console=tty1 console=ttyS0`.
Попробуйте перезагрузиться в rescue mode и удалить эти параметры из конфигурации GRUB на третьем разделе основного системного диска (`$DISK1`).
{{% /alert %}}
