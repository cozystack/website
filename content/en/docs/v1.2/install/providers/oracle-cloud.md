---
title: Как установить Cozystack в Oracle Cloud Infrastructure
linkTitle: Oracle Cloud
description: "Как установить Cozystack в Oracle Cloud Infrastructure"
weight: 25
aliases:
  - /docs/v1.2/operations/talos/installation/oracle-cloud
  - /docs/v1.2/talos/install/oracle-cloud
---

## Введение

В этом руководстве описано, как установить Talos в Oracle Cloud Infrastructure и развернуть кластер Kubernetes, готовый для Cozystack.
После выполнения руководства можно перейти к
[установке самого Cozystack]({{% ref "/docs/v1.2/getting-started/install-cozystack" %}}).

{{% alert color="info" %}}
Это руководство создано для поддержки развертывания development-кластеров командой Cozystack.
Если при прохождении руководства возникнут проблемы, создайте issue в [cozystack/website](https://github.com/cozystack/website/issues)
или поделитесь опытом в [сообществе Cozystack](https://t.me/cozystack).
{{% /alert %}}

## 1. Загрузка образа Talos в Oracle Cloud

Первый шаг — сделать установочный образ Talos Linux доступным в Oracle Cloud как custom image.

1.  Скачайте архив образа Talos Linux со [страницы релизов Cozystack](https://github.com/cozystack/cozystack/releases/latest/) и распакуйте его:

    ```bash
    wget https://github.com/cozystack/cozystack/releases/latest/download/metal-amd64.raw.xz
    xz -d metal-amd64.raw.xz
    ```

    В результате вы получите файл `metal-amd64.raw`, который затем можно загрузить в OCI.

1.  Следуйте документации OCI, чтобы [загрузить образ в bucket в OCI Object Storage](https://docs.oracle.com/iaas/Content/Object/Tasks/managingobjects_topic-To_upload_objects_to_a_bucket.htm).

1.  Затем следуйте документации, чтобы [импортировать этот образ как custom image](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/importingcustomimagelinux.htm#linux).
    Используйте следующие настройки:

-   **Image type**: QCOW2
-   **Launch mode**: Paravirtualized mode

1.  Затем получите [OCID](https://docs.oracle.com/en-us/iaas/Content/libraries/glossary/ocid.htm) образа и сохраните его для следующих шагов.

## 2. Создание инфраструктуры

Цель этого шага — подготовить инфраструктуру согласно
[требованиям к кластеру Cozystack]({{% ref "/docs/v1.2/install/hardware-requirements" %}}).

Это можно сделать вручную через Oracle Cloud dashboard или с помощью Terraform.

### 2.1 Подготовка конфигурации Terraform

Если вы используете Terraform, первый шаг — подготовить конфигурацию.

{{% alert color="info" %}}
См. [полный пример конфигурации Terraform](https://github.com/cozystack/examples/tree/main/001-deploy-cozystack-oci)
для развертывания нескольких узлов Talos в Oracle Cloud Infrastructure.
{{% /alert %}}

Ниже приведен сокращенный пример конфигурации Terraform, создающей три виртуальные машины со следующими private IP:

- `192.168.1.11`
- `192.168.1.12`
- `192.168.1.13`

Эти ВМ также будут иметь VLAN-интерфейс с подсетью `192.168.100.0/24`, используемой для внутреннего взаимодействия кластера.

Обратите внимание на часть, которая ссылается на OCID образа Talos с предыдущего шага:

```hcl
  source_details {
    source_type = "image"
    source_id   = var.talos_image_id
  }
```

Полный пример конфигурации:

```hcl
terraform {
  backend "local" {}
  required_providers {
    oci = { source = "oracle/oci", version = "~> 6.35" }
  }
}

resource "oci_core_vcn" "cozy_dev1" {
  display_name = "cozy-dev1"
  cidr_blocks = ["192.168.0.0/16"]
  compartment_id = var.compartment_id
}

resource "oci_core_network_security_group" "cozy_dev1_allow_all" {
  display_name = "allow-all"
  compartment_id = var.compartment_id
  vcn_id = oci_core_vcn.cozy_dev1.id
}

resource "oci_core_subnet" "test_subnet" {
  display_name = "cozy-dev1"
  cidr_block = "192.168.1.0/24"
  compartment_id = var.compartment_id
  vcn_id = oci_core_vcn.cozy_dev1.id
}

resource "oci_core_network_security_group_security_rule" "cozy_dev1_ingress" {
  network_security_group_id = oci_core_network_security_group.cozy_dev1_allow_all.id
  direction = "INGRESS"
  protocol = "all"
  source = "0.0.0.0/0"
  source_type = "CIDR_BLOCK"
}

resource "oci_core_network_security_group_security_rule" "cozy_dev1_egress" {
  network_security_group_id = oci_core_network_security_group.cozy_dev1_allow_all.id
  direction = "EGRESS"
  protocol = "all"
  destination = "0.0.0.0/0"
  destination_type = "CIDR_BLOCK"
}

resource "oci_core_internet_gateway" "cozy_dev1" {
  display_name = "cozy-dev1"
  compartment_id = var.compartment_id
  vcn_id = oci_core_vcn.cozy_dev1.id
}

resource "oci_core_default_route_table" "cozy_dev1_default_rt" {
  manage_default_resource_id = oci_core_vcn.cozy_dev1.default_route_table_id

  compartment_id = var.compartment_id
  display_name   = "cozy‑dev1‑default"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.cozy_dev1.id
  }
}

resource "oci_core_vlan" "cozy_dev1_vlan" {
  display_name       = "cozy-dev1-vlan"
  compartment_id     = var.compartment_id
  vcn_id             = oci_core_vcn.cozy_dev1.id

  cidr_block         = "192.168.100.0/24"
  nsg_ids = [oci_core_network_security_group.cozy_dev1_allow_all.id]
}

variable "node_private_ips" {
  type    = list(string)
  default = ["192.168.1.11", "192.168.1.12", "192.168.1.13"]
}

variable "compartment_id" {
  description = "OCID of the OCI compartment"
  type        = string
}

variable "availability_domain" {
  description = "Availability domain for the instances"
  type        = string
}

variable "talos_image_id" {
  description = "OCID of the imported Talos Linux image"
  type        = string
}

resource "oci_core_instance" "cozy_dev1_nodes" {
  count               = length(var.node_private_ips)
  display_name        = "cozy-dev1-node-${count.index + 1}"
  compartment_id      = var.compartment_id
  availability_domain = var.availability_domain
  shape               = "VM.Standard3.Flex"
  preserve_boot_volume                        = false
  preserve_data_volumes_created_at_launch     = false

  create_vnic_details {
    subnet_id   = oci_core_subnet.test_subnet.id
    nsg_ids     = [oci_core_network_security_group.cozy_dev1_allow_all.id]
    private_ip  = var.node_private_ips[count.index]
  }

  source_details {
    source_type = "image"
    source_id   = var.talos_image_id
  }

  launch_volume_attachments {
    display_name = "cozy-dev1-node${count.index + 1}-data"
    launch_create_volume_details {
      display_name       = "cozy-dev1-node${count.index + 1}-data"
      compartment_id     = var.compartment_id
      size_in_gbs        = "512"
      volume_creation_type = "ATTRIBUTES"
      vpus_per_gb        = "10"
    }
    type = "paravirtualized"
  }

  shape_config {
    memory_in_gbs = "32"
    ocpus         = "4"
  }
}

resource "oci_core_vnic_attachment" "cozy_dev1_vlan_vnic" {
  count       = length(var.node_private_ips)
  instance_id = oci_core_instance.cozy_dev1_nodes[count.index].id

  create_vnic_details {
    vlan_id = oci_core_vlan.cozy_dev1_vlan.id
  }
}
```

### 2.2 Применение конфигурации

Когда конфигурация будет готова, аутентифицируйтесь в OCI и примените ее с Terraform:

```bash
oci session authenticate --region us-ashburn-1 --profile-name=DEFAULT
terraform init
terraform apply
```

В результате этих команд виртуальные машины будут развернуты и настроены.

Сохраните public IP-адреса, назначенные ВМ, для следующего шага. В этом примере адреса такие:

- `1.2.3.4`
- `1.2.3.5`
- `1.2.3.6`

## 3. Настройка Talos и инициализация кластера Kubernetes

Следующий шаг — применить конфигурации и установить Talos Linux.
Это можно сделать несколькими способами.

В этом руководстве используется [Talm](https://github.com/cozystack/talm) — CLI-инструмент для декларативного управления Talos Linux.
В Talm есть шаблоны конфигурации, специализированные для развертывания Cozystack, поэтому мы используем его.

Если Talm не установлен, [скачайте последний binary](https://github.com/cozystack/talm/releases/latest) для вашей ОС и архитектуры.
Сделайте его исполняемым и сохраните в `/usr/local/bin/talm`:

```bash
# выберите нужную архитектуру из release artifacts
wget -O talm https://github.com/cozystack/talm/releases/latest/download/talm-darwin-arm64
chmod +x talm
mv talm /usr/local/bin/talm
```

### 3.1 Подготовка конфигурации Talm

1.  Создайте каталог для конфигурационных файлов нового кластера:
    ```bash
    mkdir -p cozystack-cluster
    cd cozystack-cluster
    ```

1.  Инициализируйте конфигурацию Talm для Cozystack:

    ```bash
    talm init --preset cozystack --name mycluster
    ```

1.  Сгенерируйте шаблон конфигурации для каждого узла, указав IP-адрес узла:

    ```bash
    # Используйте public IP узла, назначенный OCI
    talm template \
      --nodes 1.2.3.4 \
      --endpoints 1.2.3.4 \
      --template templates/controlplane.yaml \
      --insecure \
      > nodes/node0.yaml
    ```

    Повторите то же для каждого узла, используя его public IP:

    ```bash
    talm template ... > nodes/node1.yaml
    talm template ... > nodes/node2.yaml
    ```

    Использование `templates/controlplane.yaml` означает, что узел будет работать одновременно как control plane и worker.
    Три совмещенных узла — предпочтительная конфигурация для небольшого PoC-кластера.

    Параметр `--insecure` (`-i`) нужен потому, что Talm должен получить конфигурационные данные с узла, который еще не инициализирован и поэтому не может принять аутентифицированное соединение.
    Узел будет инициализирован несколькими шагами позже с помощью `talm apply`.

    Public IP узла должен быть указан и в параметре `--nodes` (`-n`), и в `--endpoints` (`-e`).
    Подробнее о конфигурации узлов Talos и endpoints см. в
    [документации Talos](https://www.talos.dev/v1.10/learn-more/talosctl/#endpoints-and-nodes)

1.  При необходимости отредактируйте конфигурационный файл узла.

-   Обновите `hostname` на нужное имя:

        ```yaml
        machine:
          network:
            hostname: node1
        ```

-   Добавьте конфигурацию private interface в раздел `machine.network.interfaces` и перенесите `vip` в эту конфигурацию.
        Эта часть конфигурации не генерируется автоматически, поэтому значения нужно заполнить вручную:

-    `interface`: берется из "Discovered interfaces" путем сопоставления параметров private interface.
-    `addresses`: используйте адрес, указанный для Layer 2 (L2).

        Пример:

        ```yaml
        machine:
          network:
            interfaces:
              - interface: eth0
                addresses:
                  - 1.2.3.4/29
                routes:
                  - network: 0.0.0.0/0
                    gateway: 1.2.3.1
              - interface: eth1
                addresses:
                  - 192.168.100.11/24
                vip:
                  ip: 192.168.100.10
        ```

После этих шагов конфигурационные файлы узлов готовы к применению.

### 3.2 Инициализация Talos и запуск кластера Kubernetes

Следующий этап — инициализировать узлы Talos и выполнить bootstrap кластера Kubernetes.

1.  Выполните `talm apply` для всех узлов, чтобы применить конфигурации:

    ```bash
    talm apply -f nodes/node0.yaml --insecure
    talm apply -f nodes/node1.yaml --insecure
    talm apply -f nodes/node2.yaml --insecure
    ```

    Узлы перезагрузятся, и Talos будет установлен на диск.
    Параметр `--insecure` (`-i`) нужен при первом запуске `talm apply` на каждом узле.

1.  Выполните `talm bootstrap` на первом узле кластера. Например:
    ```bash
    talm bootstrap -f nodes/node0.yaml
    ```

1.  Получите `kubeconfig` с любого узла control plane с помощью Talm. В этом примере все три узла являются control-plane узлами:

    ```bash
    talm kubeconfig -f nodes/node0.yaml
    ```

1.  Отредактируйте `kubeconfig`, указав IP-адрес server как один из узлов control plane, например:
    ```yaml
    server: https://1.2.3.4:6443
    ```

1.  Экспортируйте переменную `KUBECONFIG`, чтобы использовать kubeconfig, и проверьте подключение к кластеру:
    ```bash
    export KUBECONFIG=${PWD}/kubeconfig
    kubectl get nodes
    ```

    Вы должны увидеть, что узлы доступны и находятся в состоянии `NotReady`, что ожидаемо на этом этапе:

    ```console
    NAME    STATUS     ROLES           AGE     VERSION
    node0   NotReady   control-plane   2m21s   v1.32.0
    node1   NotReady   control-plane   1m47s   v1.32.0
    node2   NotReady   control-plane   1m43s   v1.32.0
    ```

Теперь у вас есть кластер Kubernetes, подготовленный к установке Cozystack.
Чтобы завершить установку, следуйте руководству по развертыванию, начиная с раздела
[Установка Cozystack]({{% ref "/docs/v1.2/getting-started/install-cozystack" %}}).
