---
title: Использование Talm для инициализации кластера Cozystack
linkTitle: Talm
description: "`talm` — декларативный CLI-инструмент, созданный разработчиками Cozystack и оптимизированный для развертывания Cozystack.<br> Рекомендуется для infrastructure-as-code и GitOps."
weight: 5
aliases:
  - /docs/v1.2/operations/talos/configuration/talm
  - /docs/v1.2/talos/bootstrap/talm
  - /docs/v1.2/talos/configuration/talm
---

В этом руководстве описано, как установить и настроить Kubernetes в кластере Talos Linux с помощью Talm.
После выполнения этого руководства у вас будет кластер Kubernetes, готовый к установке Cozystack.

[Talm](https://github.com/cozystack/talm) — Helm-подобная утилита для декларативного управления конфигурацией Talos Linux.
Talm был создан Ænix, чтобы сделать конфигурации управления кластером более декларативными и настраиваемыми.
Talm поставляется с готовыми пресетами для Cozystack.

## Предварительные требования

К началу работы с этим руководством [Talos Linux должен быть установлен]({{% ref "/docs/v1.2/install/talos" %}}) на нескольких узлах, но еще не инициализирован (bootstrapped).
Эти узлы должны находиться в одной подсети или иметь публичные IP-адреса.

В руководстве используется пример, где узлы кластера находятся в подсети `192.168.123.0/24` и имеют следующие IP-адреса:

- `node1`: private `192.168.123.11` or public `12.34.56.101`.
- `node2`: private `192.168.123.12` or public `12.34.56.102`.
- `node3`: private `192.168.123.13` or public `12.34.56.103`.

Публичные IP-адреса необязательны.
Для установки с Talm нужен только доступ к узлам: напрямую, через VPN, bastion host или другим способом.
В примерах этого руководства по умолчанию используются private IP, а public IP используются в инструкциях и примерах, относящихся к конфигурации с public IP.

Если вы используете DHCP, вы можете не знать IP-адреса, назначенные узлам в private subnet.
Узлы с Talos Linux [открывают Talos API на порту `50000`](https://www.talos.dev/v1.10/learn-more/talos-network-connectivity/).
Чтобы найти их, можно использовать `nmap`, указав маску сети (`192.168.123.0/24` в примере):

```bash
nmap -Pn -n -p 50000 192.168.123.0/24 -vv | grep 'Discovered'
```

Пример вывода:

```console
Discovered open port 50000/tcp on 192.168.123.11
Discovered open port 50000/tcp on 192.168.123.12
Discovered open port 50000/tcp on 192.168.123.13
```


## 1. Установка зависимостей

Для этого руководства нужно установить несколько инструментов:

-   **Talm**.
    Чтобы установить последнюю сборку для вашей платформы, скачайте и запустите установочный скрипт:
    
    ```bash
    curl -sSL https://github.com/cozystack/talm/raw/refs/heads/main/hack/install.sh | sh -s
    ```
    Для Talm доступны бинарные файлы для Linux, macOS и Windows, как для AMD, так и для ARM.
    Также можно [скачать бинарный файл с GitHub](https://github.com/cozystack/talm/releases)
    или [собрать Talm из исходного кода](https://github.com/cozystack/talm).
    

-   **talosctl** распространяется как brew package:

    ```bash
    brew install siderolabs/tap/talosctl
    ```

    Другие варианты установки см. в [руководстве по установке `talosctl`](https://www.talos.dev/v1.9/talos-guides/install/talosctl/)

## 2. Инициализация конфигурации кластера

Первый шаг — инициализировать шаблоны конфигурации и указать значения для шаблонизации.


### 2.1 Инициализация конфигурации

Начните с инициализации конфигурации для нового кластера, используя preset `cozystack`:

```bash
mkdir -p cozystack-cluster
cd cozystack-cluster
talm init --preset cozystack --name mycluster
```

Структура проекта в основном повторяет обычный Helm chart:

- `charts` - каталог с общим library chart, содержащим функции для запроса информации из Talos Linux.
- `Chart.yaml` - файл с общей информацией о проекте; имя chart используется как имя создаваемого кластера.
- `templates` - каталог для описания шаблонов генерации конфигурации.
- `secrets.yaml` - файл с secrets вашего кластера.
- `values.yaml` - общий values-файл для передачи параметров в шаблоны.
- `nodes` - необязательный каталог для описания и хранения сгенерированной конфигурации узлов.


### 2.2. Редактирование значений конфигурации и шаблонов

Сила Talm — в шаблонизации.
Есть несколько файлов с исходными значениями и шаблонами, которые можно редактировать: `Chart.yaml`, `values.yaml` и `templates/*`.
Talm использует эти значения и шаблоны для генерации конфигурации Talos для всех узлов кластера: и control plane, и workers.

Все часто изменяемые значения конфигурации находятся в `values.yaml`:

```yaml
## Используется для доступа к control plane кластера
endpoint: "https://192.168.100.10:6443"
## Домен кластера Cozystack API — используется сервисами и K8s-кластерами tenant'ов для доступа к управляющему кластеру
clusterDomain: cozy.local
## Floating IP — должен быть неиспользуемым IP-адресом в той же подсети, что и узлы
floatingIP: 192.168.100.10
## Исходный образ Talos: используйте последнюю доступную версию
## https://github.com/cozystack/cozystack/pkgs/container/cozystack%2Ftalos
image: "ghcr.io/cozystack/cozystack/talos:v1.10.5"
## Подсеть Pod'ов — используется для назначения IP-адресов pod'ам
podSubnets:
- 10.244.0.0/16
## Подсеть сервисов — используется для назначения IP-адресов сервисам
serviceSubnets:
- 10.96.0.0/16
## Подсеть с IP-адресами узлов
advertisedSubnets:
- 192.168.100.0/24
## Добавьте URL OIDC issuer, чтобы включить OIDC — см. комментарии ниже.
oidcIssuerUrl: ""
certSANs: []
```

На этом шаге не нужно указывать IP-адреса узлов.
Вы укажете их позже, при генерации конфигураций узлов.


### 2.3 Добавление конфигурации Keycloak

По умолчанию кластер будет доступен только при аутентификации с помощью токена.
Однако можно настроить OIDC-провайдера, чтобы использовать аутентификацию на основе учетных записей.
Эта настройка начинается на данном шаге и продолжается позже, после установки Cozystack.

Чтобы настроить Keycloak как OIDC-провайдера, внесите следующие изменения в шаблоны:

-   Для Talm v0.6.6 или новее: в `./templates/_helpers.tpl` замените `keycloak.example.com` на `keycloak.<your-domain.tld>`.

-   Для Talm старше v0.6.6 обновите `./templates/_helpers.tpl` следующим образом:

    ```yaml
     cluster:
       apiServer:
         extraArgs:
           oidc-issuer-url: "https://keycloak.example.com/realms/cozy"
           oidc-client-id: "kubernetes"
           oidc-username-claim: "preferred_username"
           oidc-groups-claim: "groups"
    ```


## 3. Генерация конфигурационных файлов узлов

Следующий шаг — создать конфигурационные файлы узлов из шаблонов.
Создайте каталог `nodes` и соберите информацию с каждого узла в отдельный файл для этого узла:

```bash
mkdir nodes
talm template -e 192.168.123.11 -n 192.168.123.11 -t templates/controlplane.yaml -i > nodes/node1.yaml
talm template -e 192.168.123.12 -n 192.168.123.12 -t templates/controlplane.yaml -i > nodes/node2.yaml
talm template -e 192.168.123.13 -n 192.168.123.13 -t templates/controlplane.yaml -i > nodes/node3.yaml
```

Параметр `--insecure` (`-i`) нужен потому, что Talm должен получить конфигурационные данные
с узлов Talos, которые еще не инициализированы, находятся в maintenance mode и поэтому не могут принять аутентифицированное соединение.
Узлы будут инициализированы только на следующем шаге с помощью `talm apply`.

Сгенерированные файлы содержат блок комментариев с обнаруженными сетевыми интерфейсами и дисками.
Эти файлы можно отредактировать перед применением, чтобы настроить сетевую конфигурацию.
Например, если нужно настроить network bonding (LACP), см.
[Настройка bonding (LACP)]({{% ref "/docs/v1.2/install/how-to/bonding" %}}).


## 4. Применение конфигурации и инициализация кластера

На этом этапе конфигурационные файлы в `node/*.yaml` готовы к применению на узлах.


### 4.1 Применение конфигурационных файлов

Используйте `talm apply`, чтобы применить конфигурационные файлы к соответствующим узлам:

```bash
talm apply -f nodes/node1.yaml -i
talm apply -f nodes/node2.yaml -i
talm apply -f nodes/node3.yaml -i
```

Эта команда инициализирует узлы и настраивает аутентифицированное соединение, поэтому дальше `-i` (`--insecure`) не потребуется.
Если команда выполнена успешно, она вернет IP узла:

```console
$ talm apply -f nodes/node1.yaml -i
- talm: file=nodes/node1.yaml, nodes=[192.168.123.11], endpoints=[192.168.123.11]
```

Позже с `talm apply` также можно использовать следующие опции:

- `--dry-run` - dry run mode покажет diff с существующей конфигурацией без внесения изменений.
- `-m try` - try mode откатит конфигурацию через 1 минуту.


### 4.2 Ожидание перезагрузки

Дождитесь, пока все узлы перезагрузятся.
Если использовался установочный носитель, например USB-накопитель, извлеките его, чтобы узлы загрузились с внутреннего диска.

Когда узлы будут готовы, они откроют порт `50000`; это признак того, что узел завершил настройку Talos и перезагрузился.
Если нужно автоматизировать проверку готовности узлов, используйте такой пример:

```bash
timeout 60 sh -c 'until \
  nc -nzv 192.168.123.11 50000 && \
  nc -nzv 192.168.123.12 50000 && \
  nc -nzv 192.168.123.13 50000; \
  do sleep 1; done'
```


### 4.3. Инициализация Kubernetes

Инициализируйте кластер Kubernetes, выполнив `talm bootstrap` для одного из узлов control plane:

```bash
talm bootstrap -f nodes/node1.yaml
```


## 5. Доступ к кластеру Kubernetes

На этом этапе кластер Kubernetes готов к установке Cozystack.

До этого шага взаимодействие с кластером выполнялось через Talos API и `talosctl`.
Для следующих шагов нужны Kubernetes API и `kubectl`, которым требуется `kubeconfig`.


### 5.1. Получение kubeconfig

Используйте Talm, чтобы сгенерировать административный `kubeconfig`:

```bash
talm kubeconfig -f nodes/node1.yaml
```

Эта команда создаст файл `kubeconfig` в текущем каталоге.


### 5.2. Изменение URL Cluster API

Теперь в `kubeconfig` URL Cluster API указывает на floating IP (VIP) в private subnet.

Если вместо floatingIP используется public IP, обновите endpoint соответствующим образом.
Отредактируйте `kubeconfig` — замените URL кластера на public IP одного из узлов:

```diff
  apiVersion: v1                                                                                                          
  clusters:                                                                                                               
  - cluster:     
      certificate-authority-data: ...                                                                                                         
-     server: https://10.0.1.101:6443   
+     server: https://12.34.56.101:6443   
```


### 5.3. Активация kubeconfig

Затем настройте переменную `KUBECONFIG` или используйте другие инструменты, чтобы сделать этот kubeconfig
доступным вашему клиенту `kubectl`:

```bash
export KUBECONFIG=$PWD/kubeconfig
```

{{% alert color="info" %}}
Чтобы сделать этот `kubeconfig` постоянно доступным, можно сделать его конфигурацией по умолчанию (`~/.kube/config`),
использовать `kubectl config use-context` или применить другие методы.
См. [документацию Kubernetes о доступе к кластеру](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/).
{{% /alert %}}


### 5.4. Проверка доступности кластера

Проверьте, что кластер доступен:

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

### 5.5. Проверка состояния узлов

Проверьте состояние узлов кластера:

```bash
kubectl get nodes    
```

Вывод показывает состояние узлов и версию Kubernetes:

```console
NAME    STATUS     ROLES           AGE     VERSION
node1   NotReady   control-plane   7m56s   v1.33.1
node2   NotReady   control-plane   7m56s   v1.33.1
node3   NotReady   control-plane   7m56s   v1.33.1
```

Обратите внимание, что все узлы показывают `STATUS: NotReady`, и на этом этапе это нормально.
Так происходит потому, что стандартный [CNI-плагин Kubernetes](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
был отключен в конфигурации Talos, чтобы Cozystack мог установить собственный CNI-плагин.


## Следующие шаги

Теперь у вас есть инициализированный кластер Kubernetes, готовый к установке Cozystack.
Чтобы завершить установку, следуйте руководству по развертыванию, начиная с раздела
[Установка Cozystack]({{% ref "/docs/v1.2/getting-started/install-cozystack" %}}).
