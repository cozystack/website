---
title: Использование talosctl для инициализации кластера Cozystack
linkTitle: talosctl
description: "`talosctl` — стандартный CLI Talos Linux: он требует больше boilerplate-кода, но дает полную гибкость настройки."
weight: 15
aliases:
  - /docs/v1.2/talos/bootstrap/talosctl
  - /docs/v1.2/talos/configuration/talosctl
  - /docs/v1.2/operations/talos/configuration/talosctl
---

В этом руководстве описано, как подготовить кластер Talos Linux к развертыванию Cozystack с помощью `talosctl` —
специализированного CLI-инструмента для управления Talos.

## Предварительные требования

К началу работы с этим руководством Talos OS должна быть загружена с ISO на нескольких узлах, но еще не инициализирована (bootstrapped).
Эти узлы должны находиться в одной подсети или иметь публичные IP-адреса.

В руководстве используется пример, где узлы кластера находятся в подсети `192.168.123.0/24` и имеют следующие IP-адреса:

- `192.168.123.11`
- `192.168.123.12`
- `192.168.123.13`

IP `192.168.123.10` — внутренний адрес, который не принадлежит ни одному из этих узлов, но создается Talos.
Он используется как VIP.

{{% alert color="info" %}}
Если вы используете DHCP, вы можете не знать IP-адреса, назначенные узлам.
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
{{% /alert %}}

## 1. Подготовка конфигурационных файлов

1.  Начните с создания каталога конфигурации для нового кластера:

    ```bash
    mkdir -p cluster1
    cd cluster1
    ```

1.  Сгенерируйте файл secrets.
    Эти secrets позже будут внедрены в конфигурацию и использованы для установки аутентифицированных соединений с узлами Talos:

    ```bash
    talosctl gen secrets
    ```

1.  Создайте файл конфигурационного patch `patch.yaml`:

    ```yaml
    machine:
      kubelet:
        nodeIP:
          validSubnets:
          - 192.168.123.0/24
        extraConfig:
          maxPods: 512
      sysctls:
        net.ipv4.neigh.default.gc_thresh1: "4096"
        net.ipv4.neigh.default.gc_thresh2: "8192"
        net.ipv4.neigh.default.gc_thresh3: "16384"
      kernel:
        modules:
        - name: openvswitch
        - name: drbd
          parameters:
            - usermode_helper=disabled
        - name: zfs
        - name: spl
        - name: vfio_pci
        - name: vfio_iommu_type1
      install:
        image: ghcr.io/cozystack/cozystack/talos:v1.10.3
      registries:
        mirrors:
          docker.io:
            endpoints:
            - https://mirror.gcr.io
      files:
      - content: |
          [plugins]
            [plugins."io.containerd.cri.v1.runtime"]
              device_ownership_from_security_context = true
        path: /etc/cri/conf.d/20-customization.part
        op: create
      - op: overwrite
        path: /etc/lvm/lvm.conf
        permissions: 0o644
        content: |
          backup {
            backup = 0
            archive = 0
          }
          devices {
            global_filter = [ "r|^/dev/drbd.*|", "r|^/dev/dm-.*|", "r|^/dev/zd.*|" ]
          }

    cluster:
      apiServer:
        extraArgs:
          oidc-issuer-url: "https://keycloak.example.org/realms/cozy"
          oidc-client-id: "kubernetes"
          oidc-username-claim: "preferred_username"
          oidc-groups-claim: "groups"
      network:
        cni:
          name: none
        dnsDomain: cozy.local
        podSubnets:
        - 10.244.0.0/16
        serviceSubnets:
        - 10.96.0.0/16
    ```

1.  Создайте еще один файл конфигурационного patch `patch-controlplane.yaml` с настройками только для узлов control plane:

    Обратите внимание, что VIP-адрес используется в `machine.network.interfaces[0].vip.ip`:

    ```yaml
    machine:
      nodeLabels:
        node.kubernetes.io/exclude-from-external-load-balancers:
          $patch: delete
      network:
        interfaces:
        - interface: eth0
          vip:
            ip: 192.168.123.10
    cluster:
      allowSchedulingOnControlPlanes: true
      controllerManager:
        extraArgs:
          bind-address: 0.0.0.0
      scheduler:
        extraArgs:
          bind-address: 0.0.0.0
      apiServer:
        certSANs:
        - 127.0.0.1
      proxy:
        disabled: true
      discovery:
        enabled: false
      etcd:
        advertisedSubnets:
        - 192.168.123.0/24
    ```


## 2. Генерация конфигурационных файлов узлов

Когда patch-файлы будут готовы, сгенерируйте конфигурационные файлы для каждого узла.
Обратите внимание, что используются три файла, созданные на предыдущем шаге: `secrets.yaml`, `patch.yaml` и `patch-controlplane.yaml`.

URL `192.168.123.10:6443` использует тот же VIP, который упоминался выше, а порт `6443` — стандартный порт Kubernetes API.

```bash
talosctl gen config \
    cozystack https://192.168.123.10:6443 \
    --with-secrets secrets.yaml \
    --config-patch=@patch.yaml \
    --config-patch-control-plane @patch-controlplane.yaml
export TALOSCONFIG=$PWD/talosconfig
```

`192.168.123.11`, `192.168.123.12` и `192.168.123.13` — это узлы.
В этой конфигурации все узлы являются управляющими.

## 3. Применение конфигурации узлов

Примените конфигурацию ко всем узлам, а не только к управляющим.

```
talosctl apply -f controlplane.yaml -n 192.168.123.11 -e 192.168.123.11 -i
talosctl apply -f controlplane.yaml -n 192.168.123.12 -e 192.168.123.12 -i
talosctl apply -f controlplane.yaml -n 192.168.123.13 -e 192.168.123.13 -i
```

Также можно использовать следующие опции:

- `--dry-run` - dry run mode покажет diff с существующей конфигурацией.
- `-m try` - try mode откатит конфигурацию через 1 минуту.

### 3.1. Ожидание перезагрузки узлов

Дождитесь, пока все узлы перезагрузятся.
Извлеките установочный носитель (например, USB-накопитель), чтобы узлы загрузились с внутреннего диска.

Готовые узлы будут открывать порт 50000; это признак того, что узел завершил настройку Talos и перезагрузился.

Если нужно дождаться готовности узлов в скрипте, используйте такой пример:

```bash
timeout 60 sh -c 'until nc -nzv 192.168.123.11 50000 && \
  nc -nzv 192.168.123.12 50000 && \
  nc -nzv 192.168.123.13 50000; \
  do sleep 1; done'
```

## 4. Инициализация и доступ к кластеру

Запустите `talosctl bootstrap` на одном узле control plane — этого достаточно для инициализации всего кластера:

```bash
talosctl bootstrap -n 192.168.123.11 -e 192.168.123.11
```

Для доступа к кластеру сгенерируйте административный `kubeconfig`:

```bash
talosctl kubeconfig -n 192.168.123.11 -e 192.168.123.11 kubeconfig
```

Настройте `kubectl` на использование новой конфигурации, экспортировав переменную `KUBECONFIG`:

```bash
export KUBECONFIG=$PWD/kubeconfig
```

{{% alert color="info" %}}
Чтобы сделать этот `kubeconfig` постоянно доступным, можно сделать его конфигурацией по умолчанию (`~/.kube/config`),
использовать `kubectl config use-context` или применить другие методы.
См. [документацию Kubernetes о доступе к кластеру](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/).
{{% /alert %}}

Проверьте, что кластер доступен с новым `kubeconfig`:

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

{{% alert color="info" %}}
:warning: Все узлы будут отображаться как `READY: False`, и на этом этапе это нормально.
Так происходит потому, что на предыдущем шаге стандартный CNI-плагин был отключен, чтобы Cozystack мог установить собственный CNI-плагин.
{{% /alert %}}


## Следующие шаги

Теперь у вас есть инициализированный кластер Kubernetes, готовый к установке Cozystack.
Чтобы завершить установку, следуйте руководству по развертыванию, начиная с раздела
[Установка Cozystack]({{% ref "/docs/v1.2/getting-started/install-cozystack" %}}).
