---
title: "Развертывание Cozystack на Generic Kubernetes"
linkTitle: "Generic Kubernetes"
description: "Как развернуть Cozystack на k3s, kubeadm, RKE2 или других дистрибутивах Kubernetes без Talos Linux"
weight: 50
---

В этом руководстве описано, как развернуть Cozystack на generic-дистрибутивах Kubernetes, таких как k3s, kubeadm или RKE2.
Хотя Talos Linux остается рекомендуемой платформой для production-развертываний, Cozystack поддерживает развертывание на других дистрибутивах Kubernetes с помощью bundle `isp-full-generic`.

## Когда использовать Generic Kubernetes

Рассмотрите использование generic Kubernetes вместо Talos Linux, если:

- У вас уже есть кластер Kubernetes, который вы хотите дополнить Cozystack
- Ваша инфраструктура не поддерживает Talos Linux (некоторые облачные провайдеры, embedded-системы)
- Вам нужны специфические функции или пакеты Linux, недоступные в Talos

Для новых production-развертываний рекомендуется [Talos Linux]({{% ref "/docs/v1.2/guides/talos" %}}) благодаря его преимуществам в безопасности и эксплуатации.

## Предварительные требования

### Поддерживаемые дистрибутивы

Cozystack протестирован на:

- **k3s** v1.32+ (рекомендуется для single-node и edge-развертываний)
- **kubeadm** v1.28+
- **RKE2** v1.28+

### Требования к хостам

- **Операционная система**: Ubuntu 22.04+ или Debian 12+ (kernel 5.x+ с systemd)
- **Архитектура**: amd64 или arm64
- **Оборудование**: см. [требования к оборудованию]({{% ref "/docs/v1.2/install/hardware-requirements" %}})

### Обязательные пакеты

Установите следующие пакеты на всех узлах:

```bash
apt-get update
apt-get install -y nfs-common open-iscsi multipath-tools
```

### Обязательные модули ядра

Загрузите модуль `br_netfilter` (требуется для sysctl-настроек bridge netfilter):

```bash
modprobe br_netfilter
echo "br_netfilter" > /etc/modules-load.d/br_netfilter.conf
```

### Обязательные сервисы

Включите и запустите обязательные сервисы:

```bash
systemctl enable --now iscsid
systemctl enable --now multipathd
```

## Настройка sysctl

{{% alert color="warning" %}}
:warning: **Критично**: приведенные ниже sysctl-настройки обязательны для корректной работы Cozystack.
Без этих настроек компоненты Kubernetes будут завершаться с ошибками из-за недостаточного количества inotify watches.
{{% /alert %}}

Создайте `/etc/sysctl.d/99-cozystack.conf` со следующим содержимым:

```ini
# Inotify limits (critical for Cozystack)
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 8192
fs.inotify.max_queued_events = 65536

# Filesystem limits
fs.file-max = 2097152
fs.aio-max-nr = 1048576

# Network forwarding (required for Kubernetes)
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# VM tuning
vm.swappiness = 1
```

Примените настройки:

```bash
sysctl --system
```

## Настройка Kubernetes

Cozystack самостоятельно управляет сетью (Cilium/KubeOVN), хранилищем (LINSTOR) и ingress (NGINX).
Ваш дистрибутив Kubernetes должен быть настроен так, чтобы **не** устанавливать эти компоненты.

### Обязательная конфигурация

| Компонент | Требование |
| ----------- | ------------- |
| CNI | **Отключен** — Cozystack развертывает Cilium или KubeOVN |
| Ingress Controller | **Отключен** — Cozystack развертывает NGINX |
| Storage Provisioner | **Отключен** — Cozystack развертывает LINSTOR |
| kube-proxy | **Отключен** — его заменяет Cilium |
| Cluster Domain | Должен быть `cozy.local` |

{{< tabs name="kubernetes_distributions" >}}
{{% tab name="k3s" %}}

При установке k3s используйте следующие флаги:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --disable=traefik \
  --disable=servicelb \
  --disable=local-storage \
  --disable=metrics-server \
  --disable-network-policy \
  --disable-kube-proxy \
  --flannel-backend=none \
  --cluster-domain=cozy.local \
  --tls-san=<YOUR_NODE_IP> \
  --kubelet-arg=max-pods=220" sh -
```

Замените `<YOUR_NODE_IP>` на IP-адрес вашего узла.

{{% /tab %}}
{{% tab name="kubeadm" %}}

Создайте конфигурационный файл kubeadm:

```yaml
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
networking:
  podSubnet: "10.244.0.0/16"
  serviceSubnet: "10.96.0.0/16"
  dnsDomain: "cozy.local"
---
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
mode: "none"  # Cilium заменит kube-proxy
```

Инициализируйте кластер без стандартного CNI:

```bash
kubeadm init --config kubeadm-config.yaml --skip-phases=addon/kube-proxy
```

Не устанавливайте CNI-плагин после `kubeadm init` — Cozystack автоматически развернет Kube-OVN и Cilium.

{{% /tab %}}
{{% tab name="RKE2" %}}

Создайте `/etc/rancher/rke2/config.yaml`:

```yaml
cni: none
disable:
  - rke2-ingress-nginx
  - rke2-metrics-server
cluster-domain: cozy.local
disable-kube-proxy: true
```

{{% /tab %}}
{{< /tabs >}}

## Установка Cozystack

### 1. Применение CRD

Скачайте и примените Custom Resource Definitions:

```bash
kubectl apply -f https://github.com/cozystack/cozystack/releases/latest/download/cozystack-crds.yaml
```

### 2. Развертывание Cozystack Operator

Скачайте generic-манифест operator, замените placeholder адреса API server и примените его:

```bash
curl -fsSL https://github.com/cozystack/cozystack/releases/latest/download/cozystack-operator-generic.yaml \
  | sed 's/REPLACE_ME/<YOUR_NODE_IP>/' \
  | kubectl apply -f -
```

Замените `<YOUR_NODE_IP>` на IP-адрес вашего Kubernetes API server (только IP, без протокола и порта).

Манифест включает deployment operator, ConfigMap `cozystack-operator-config` с адресом API server и ресурс `PackageSource`.

### 3. Создание Platform Package

После запуска operator и reconciliation ресурса `PackageSource` создайте ресурс `Package`, чтобы запустить установку платформы.

{{% alert color="warning" %}}
:warning: **Важно**: значения `podCIDR` и `serviceCIDR` **должны совпадать** с конфигурацией вашего кластера Kubernetes.
Разные дистрибутивы используют разные значения по умолчанию:

- **k3s**: `10.42.0.0/16` (pods), `10.43.0.0/16` (services)
- **kubeadm**: `10.244.0.0/16` (pods), `10.96.0.0/16` (services)
- **RKE2**: `10.42.0.0/16` (pods), `10.43.0.0/16` (services)
{{% /alert %}}

Пример для **k3s** (для других дистрибутивов скорректируйте CIDR):

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
  # Package имеет cluster scope — namespace не нужен
spec:
  variant: isp-full-generic
  components:
    platform:
      values:
        publishing:
          host: "example.com"
          apiServerEndpoint: "https://<YOUR_NODE_IP>:6443"
        networking:
          podCIDR: "10.42.0.0/16"
          podGateway: "10.42.0.1"
          serviceCIDR: "10.43.0.0/16"
          joinCIDR: "100.64.0.0/16"
```

Скорректируйте значения:

| Поле | Описание |
| ------- | ------------- |
| `publishing.host` | Ваш домен для сервисов Cozystack |
| `publishing.apiServerEndpoint` | URL Kubernetes API endpoint |
| `networking.podCIDR` | CIDR pod-сети (должен совпадать с вашей k8s-конфигурацией) |
| `networking.podGateway` | Первый IP в pod CIDR (например, `10.42.0.1` для `10.42.0.0/16`) |
| `networking.serviceCIDR` | CIDR service-сети (должен совпадать с вашей k8s-конфигурацией) |
| `networking.joinCIDR` | Сеть для связи с nested-кластерами |

Примените его:

```bash
kubectl apply -f cozystack-platform-package.yaml
```

{{% alert color="info" %}}
Имя Package **должно** совпадать с именем PackageSource (`cozystack.cozystack-platform`).
Проверить доступные PackageSources можно командой `kubectl get packagesource`.
{{% /alert %}}

### 4. Мониторинг установки

Следите за ходом установки:

```bash
kubectl logs -n cozy-system deploy/cozystack-operator -f
```

Проверьте состояние HelmRelease:

```bash
kubectl get hr -A
```

{{% alert color="info" %}}
Во время начального развертывания HelmRelease в первые несколько минут может показывать ошибки вроде `ExternalArtifact not found` или `dependency is not ready`, пока Cilium и другие базовые компоненты проходят reconciliation. Это ожидаемо — подождите несколько минут и проверьте снова.
{{% /alert %}}

Можно убедиться, что Cilium развернут и сеть между узлами настроена, дождавшись, пока узлы перейдут в состояние Ready:

```bash
kubectl wait --for=condition=Ready nodes --all --timeout=300s
```

## Пример: Ansible Playbook

Ниже приведен минимальный Ansible playbook для подготовки узлов и развертывания Cozystack.

Сначала установите необходимые Ansible collections:

```bash
ansible-galaxy collection install ansible.posix community.general kubernetes.core ansible.utils
```

### Playbook подготовки узлов

```yaml
---
- name: Prepare nodes for Cozystack
  hosts: all
  become: true
  tasks:
    - name: Load br_netfilter module
      community.general.modprobe:
        name: br_netfilter
        persistent: present

    - name: Install required packages
      ansible.builtin.apt:
        name:
          - nfs-common
          - open-iscsi
          - multipath-tools
        state: present
        update_cache: true

    - name: Configure sysctl for Cozystack
      ansible.posix.sysctl:
        name: "{{ item.name }}"
        value: "{{ item.value }}"
        sysctl_set: true
        state: present
        reload: true
      loop:
        - { name: fs.inotify.max_user_watches, value: "524288" }
        - { name: fs.inotify.max_user_instances, value: "8192" }
        - { name: fs.inotify.max_queued_events, value: "65536" }
        - { name: fs.file-max, value: "2097152" }
        - { name: fs.aio-max-nr, value: "1048576" }
        - { name: net.ipv4.ip_forward, value: "1" }
        - { name: net.ipv4.conf.all.forwarding, value: "1" }
        - { name: net.bridge.bridge-nf-call-iptables, value: "1" }
        - { name: net.bridge.bridge-nf-call-ip6tables, value: "1" }
        - { name: vm.swappiness, value: "1" }

    - name: Enable iscsid service
      ansible.builtin.systemd:
        name: iscsid
        enabled: true
        state: started

    - name: Enable multipathd service
      ansible.builtin.systemd:
        name: multipathd
        enabled: true
        state: started
```

### Playbook развертывания Cozystack

В этом примере используются CIDR по умолчанию для k3s. Скорректируйте их для kubeadm (`10.244.0.0/16`, `10.96.0.0/16`) или своей пользовательской конфигурации.

```yaml
---
- name: Deploy Cozystack
  hosts: localhost
  connection: local
  vars:
    cozystack_root_host: "example.com"
    cozystack_api_host: "10.0.0.1"
    cozystack_api_port: "6443"
    # k3s defaults - adjust for kubeadm (10.244.0.0/16, 10.96.0.0/16)
    cozystack_pod_cidr: "10.42.0.0/16"
    cozystack_svc_cidr: "10.43.0.0/16"
  tasks:
    - name: Apply Cozystack CRDs
      ansible.builtin.command:
        cmd: kubectl apply -f https://github.com/cozystack/cozystack/releases/latest/download/cozystack-crds.yaml
      changed_when: true

    - name: Download and apply Cozystack operator manifest
      ansible.builtin.shell:
        cmd: >
          curl -fsSL https://github.com/cozystack/cozystack/releases/latest/download/cozystack-operator-generic.yaml
          | sed 's/REPLACE_ME/{{ cozystack_api_host }}/'
          | kubectl apply -f -
      changed_when: true

    - name: Wait for PackageSource to be ready
      kubernetes.core.k8s_info:
        api_version: cozystack.io/v1alpha1
        kind: PackageSource
        name: cozystack.cozystack-platform
      register: pkg_source
      until: >
        pkg_source.resources | length > 0 and
        (
          pkg_source.resources[0].status.conditions
          | selectattr('type', 'equalto', 'Ready')
          | map(attribute='status')
          | first
          | default('False')
        ) == "True"
      retries: 30
      delay: 10

    - name: Create Platform Package
      kubernetes.core.k8s:
        state: present
        definition:
          apiVersion: cozystack.io/v1alpha1
          kind: Package
          metadata:
            name: cozystack.cozystack-platform
          spec:
            variant: isp-full-generic
            components:
              platform:
                values:
                  publishing:
                    host: "{{ cozystack_root_host }}"
                    apiServerEndpoint: "https://{{ cozystack_api_host }}:{{ cozystack_api_port }}"
                  networking:
                    podCIDR: "{{ cozystack_pod_cidr }}"
                    podGateway: "{{ cozystack_pod_cidr | ansible.utils.ipaddr('1') | ansible.utils.ipaddr('address') }}"
                    serviceCIDR: "{{ cozystack_svc_cidr }}"
                    joinCIDR: "100.64.0.0/16"
```

## Troubleshooting

### Некорректный image tag linstor-scheduler

**Симптом**: ошибка `InvalidImageName` для pod linstor-scheduler.

**Причина**: формат версии k3s (например, `v1.35.0+k3s1`) содержит `+`, который недопустим в Docker image tags.

**Решение**: это исправлено в Cozystack v1.0.0+. Убедитесь, что используете последний релиз.

### KubeOVN не планируется

**Симптом**: pods ovn-central остаются в состоянии Pending.

**Причина**: KubeOVN использует Helm `lookup` для поиска узлов control plane, что может не сработать на свежих кластерах.

**Решение**: убедитесь, что ваш Platform Package содержит явную конфигурацию `MASTER_NODES`:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full-generic
  components:
    platform:
      values:
        networking:
          kubeovn:
            MASTER_NODES: "<YOUR_CONTROL_PLANE_IP>"
```

Ключ — `kubeovn` (без дефиса), он соответствует полю в
`packages/core/platform/values.yaml` — см. также
[`networking.kubeovn.MASTER_NODES`]({{% ref "/docs/v1.2/operations/configuration/platform-package" %}})
в справочнике Platform Package.

### Cilium не может подключиться к API server

**Симптом**: pods Cilium находятся в CrashLoopBackOff с ошибками подключения к API.

**Причина**: single-node кластеры или нестандартные API endpoints требуют явной конфигурации.

**Решение**: проверьте, что ваш Platform Package содержит корректные настройки API server:

```yaml
spec:
  components:
    networking:
      values:
        cilium:
          k8sServiceHost: "<YOUR_API_HOST>"
          k8sServicePort: "6443"
```

### Ошибки лимитов inotify

**Симптом**: pods завершаются с ошибками "too many open files" или ошибками inotify.

**Причина**: стандартные лимиты inotify в Linux слишком низкие для Kubernetes.

**Решение**: примените sysctl-настройки из раздела [Настройка sysctl](#sysctl-configuration) и перезагрузите узел.

## Следующие шаги

После завершения установки Cozystack:

1. [Настройте хранилище с LINSTOR]({{% ref "/docs/v1.2/getting-started/install-cozystack#3-configure-storage" %}})
2. [Настройте root tenant]({{% ref "/docs/v1.2/getting-started/install-cozystack#51-setup-root-tenant-services" %}})
3. [Разверните первое приложение]({{% ref "/docs/v1.2/applications" %}})

## Ссылки

- [PR #1939: Non-Talos Kubernetes Support](https://github.com/cozystack/cozystack/pull/1939)
- [Issue #1950: Complete non-Talos Support](https://github.com/cozystack/cozystack/issues/1950)
- [k3s Documentation](https://docs.k3s.io/)
- [kubeadm Documentation](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/)
