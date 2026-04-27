---
title: "Как настроить network bonding (LACP)"
linkTitle: "Настройка bonding (LACP)"
description: "Как настроить network bonding LACP (802.3ad) для агрегации каналов и резервирования"
weight: 120
---

Network bonding позволяет объединить несколько физических сетевых интерфейсов в один логический интерфейс.
Это увеличивает пропускную способность и обеспечивает резервирование каналов.

LACP (Link Aggregation Control Protocol, IEEE 802.3ad) — самый распространенный режим bonding,
который динамически согласует агрегацию каналов с сетевым коммутатором.

{{% alert color="warning" %}}
LACP требует настройки и на сервере, и на сетевом коммутаторе.
Убедитесь, что на коммутаторе настроен соответствующий LACP port-channel для портов сервера.
{{% /alert %}}

## Определение сетевых интерфейсов

После выполнения `talm template` сгенерированный конфигурационный файл узла будет содержать
блок комментариев с обнаруженными сетевыми интерфейсами:

```yaml
machine:
  network:
    # -- Discovered interfaces:
    # eno1:
    #   hardwareAddr: aa:bb:cc:dd:ee:f0
    #   busPath: 0000:02:00.0
    #   driver: tg3
    #   vendor: Broadcom Inc. and subsidiaries
    #   product: NetXtreme BCM5719 Gigabit Ethernet PCIe
    # eno2:
    #   hardwareAddr: aa:bb:cc:dd:ee:f1
    #   busPath: 0000:02:00.1
    #   driver: tg3
    #   vendor: Broadcom Inc. and subsidiaries
    #   product: NetXtreme BCM5719 Gigabit Ethernet PCIe
    # eth0:
    #   hardwareAddr: aa:bb:cc:dd:ee:f2
    #   busPath: 0000:04:00.0
    #   driver: bnx2x
    #   vendor: Broadcom Inc. and subsidiaries
    #   product: NetXtreme II BCM57810 10 Gigabit Ethernet
    # eth1:
    #   hardwareAddr: aa:bb:cc:dd:ee:f3
    #   busPath: 0000:04:00.1
    #   driver: bnx2x
    #   vendor: Broadcom Inc. and subsidiaries
    #   product: NetXtreme II BCM57810 10 Gigabit Ethernet
```

Выберите интерфейсы, которые хотите объединить в bond. Обычно это порты одной скорости,
подключенные к одному коммутатору или стеку коммутаторов. Запишите значения `busPath` — они понадобятся далее.

## Настройка bonding

Отредактируйте сгенерированный конфигурационный файл узла (например, `nodes/node1.yaml`) и замените стандартный
раздел `machine.network.interfaces` на конфигурацию bond:

```yaml
machine:
  network:
    interfaces:
      - interface: bond0
        dhcp: false
        bond:
          mode: 802.3ad
          adSelect: bandwidth
          miimon: 100
          updelay: 200
          downdelay: 200
          minLinks: 1
          xmitHashPolicy: encap3+4
          deviceSelectors:
            - busPath: "0000:04:00.0"
            - busPath: "0000:04:00.1"
        addresses:
          - 192.168.100.11/24
        routes:
          - network: 0.0.0.0/0
            gateway: 192.168.100.1
```

### Описание параметров bond

| Параметр | Значение | Описание |
| --- | --- | --- |
| `mode` | `802.3ad` | LACP — динамическая агрегация каналов с согласованием на коммутаторе |
| `adSelect` | `bandwidth` | Выбирает активный агрегатор по наибольшей суммарной пропускной способности |
| `miimon` | `100` | Интервал мониторинга канала в миллисекундах |
| `updelay` | `200` | Задержка (мс) перед переводом восстановленного канала в активное состояние |
| `downdelay` | `200` | Задержка (мс) перед объявлением отказавшего канала отключенным |
| `minLinks` | `1` | Минимальное количество активных каналов, при котором bond остается поднятым |
| `xmitHashPolicy` | `encap3+4` | Хеширование по IP и TCP/UDP-порту для распределения нагрузки между каналами |

### Выбор интерфейсов

Рекомендуемый способ выбора участников bond — по пути PCI-шины с помощью `deviceSelectors`.
Это надежнее, чем имена интерфейсов, которые могут меняться между перезагрузками:

```yaml
bond:
  deviceSelectors:
    - busPath: "0000:04:00.0"
    - busPath: "0000:04:00.1"
```

Также можно выбирать по имени интерфейса:

```yaml
bond:
  interfaces:
    - eth0
    - eth1
```

Или по аппаратному адресу:

```yaml
bond:
  deviceSelectors:
    - hardwareAddr: "aa:bb:cc:dd:ee:f2"
    - hardwareAddr: "aa:bb:cc:dd:ee:f3"
```

## VLAN поверх bond

Поверх bond можно создавать VLAN-интерфейсы.
Это удобно для разделения трафика (например, management, storage, tenant-сетей):

```yaml
machine:
  network:
    interfaces:
      - interface: bond0
        dhcp: false
        bond:
          mode: 802.3ad
          adSelect: bandwidth
          miimon: 100
          updelay: 200
          downdelay: 200
          minLinks: 1
          xmitHashPolicy: encap3+4
          deviceSelectors:
            - busPath: "0000:04:00.0"
            - busPath: "0000:04:00.1"
        addresses:
          - 192.168.100.11/24
        routes:
          - network: 0.0.0.0/0
            gateway: 192.168.100.1
        vlans:
          - vlanId: 100
            addresses:
              - 10.0.0.11/24
```

## Floating IP (VIP) с bonding

Для узлов control plane разместите раздел `vip` на интерфейсе (или VLAN),
который используется для API endpoint кластера:

```yaml
machine:
  network:
    interfaces:
      - interface: bond0
        dhcp: false
        bond:
          mode: 802.3ad
          adSelect: bandwidth
          miimon: 100
          updelay: 200
          downdelay: 200
          minLinks: 1
          xmitHashPolicy: encap3+4
          deviceSelectors:
            - busPath: "0000:04:00.0"
            - busPath: "0000:04:00.1"
        addresses:
          - 192.168.100.11/24
        routes:
          - network: 0.0.0.0/0
            gateway: 192.168.100.1
        vip:
          ip: 192.168.100.10
```

Убедитесь, что floating IP совпадает с адресом, настроенным в `values.yaml`.

## Применение конфигурации

После редактирования всех файлов узлов примените конфигурацию обычным способом:

```bash
talm apply -f nodes/node1.yaml -i
talm apply -f nodes/node2.yaml -i
talm apply -f nodes/node3.yaml -i
```

{{% alert color="info" %}}
Флаг `-i` (`--insecure`) нужен только при первом применении, когда узлы находятся в maintenance mode.
Для уже инициализированных узлов не указывайте этот флаг: `talm apply -f nodes/node1.yaml`.
{{% /alert %}}
