---
title: Использование скрипта talos-bootstrap для инициализации кластера Cozystack
linkTitle: talos-bootstrap
description: "`talos-bootstrap` — CLI для пошаговой инициализации кластера, созданный разработчиками Cozystack.<br> Рекомендуется для первых развертываний."
weight: 10
aliases:
  - /docs/v1.2/talos/bootstrap/talos-bootstrap
  - /docs/v1.2/talos/configuration/talos-bootstrap
  - /docs/v1.2/operations/talos/configuration/talos-bootstrap
---

[talos-bootstrap](https://github.com/cozystack/talos-bootstrap/) — интерактивный скрипт для инициализации кластеров Kubernetes на Talos OS.

Он был создан разработчиками Cozystack, чтобы упростить установку Talos Linux на bare-metal узлы и сделать ее удобнее.

## 1. Установка зависимостей

Установите следующие зависимости:

- `talosctl`
- `dialog`
- `nmap`

Скачайте последнюю версию `talos-bootstrap` со [страницы релизов](https://github.com/cozystack/talos-bootstrap/releases) или напрямую из trunk:

```bash
curl -fsSL -o /usr/local/bin/talos-bootstrap \
    https://github.com/cozystack/talos-bootstrap/raw/master/talos-bootstrap
chmod +x /usr/local/bin/talos-bootstrap
talos-bootstrap --help
```

## 2. Подготовка конфигурационных файлов

1.  Начните с создания каталога конфигурации для нового кластера:

    ```bash
    mkdir -p cluster1
    cd cluster1
    ```

1.  Создайте файл конфигурационного patch `patch.yaml` с общими настройками узлов, используя следующий пример:

    ```yaml
    machine:
      kubelet:
        nodeIP:
          validSubnets:
          - 192.168.100.0/24
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
            [plugins."io.containerd.grpc.v1.cri"]
              device_ownership_from_security_context = true
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
      network:
        cni:
          name: none
        dnsDomain: cozy.local
        podSubnets:
        - 10.244.0.0/16
        serviceSubnets:
        - 10.96.0.0/16
    ```

1.  Создайте еще один файл конфигурационного patch `patch-controlplane.yaml` с настройками, которые относятся только к узлам control plane:

    ```yaml
    machine:
      nodeLabels:
        node.kubernetes.io/exclude-from-external-load-balancers:
          $patch: delete
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
        - 192.168.100.0/24
    ```

1.  Чтобы настроить Keycloak как OIDC-провайдера, добавьте следующий раздел в `patch-controlplane.yaml`, заменив `example.com` на свой домен:

    ```yaml
    cluster:
      apiServer:
        extraArgs:
        oidc-issuer-url: "https://keycloak.example.com/realms/cozy"
        oidc-client-id: "kubernetes"
        oidc-username-claim: "preferred_username"
        oidc-groups-claim: "groups"
    ```

## 3. Инициализация и доступ к кластеру

Когда конфигурационные файлы будут готовы, запустите `talos-bootstrap` на каждом узле кластера:

```bash
# в каталоге конфигурации кластера
talos-bootstrap install
```

{{% alert color="warning" %}}
:warning: Если узлы работают во внешней сети, каждый узел нужно явно указать в аргументе:
```bash
talos-bootstrap install -n 1.2.3.4
```

Где `1.2.3.4` — IP-адрес удаленного узла.
{{% /alert %}}

{{% alert color="info" %}}
`talos-bootstrap` включит bootstrap на первом настроенном узле кластера.
Если нужно повторно выполнить bootstrap кластера etcd, удалите строку `BOOTSTRAP_ETCD=false` из файла `cluster.conf`.
{{% /alert %}}

Повторите этот шаг для остальных узлов кластера.

После завершения команды `install` `talos-bootstrap` сохранит конфигурацию кластера как `./kubeconfig`.

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
