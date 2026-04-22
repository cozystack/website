---
title: Установка Talos Linux с помощью PXE
linkTitle: PXE
description: "Как установить Talos Linux с помощью временных DHCP- и PXE-серверов, запущенных в Docker-контейнерах."
weight: 15
aliases:
  - /docs/v1.2/talos/installation/pxe
  - /docs/v1.2/talos/install/pxe
  - /docs/v1.2/operations/talos/installation/pxe
---

В этом руководстве описано, как установить Talos Linux на bare-metal серверы или виртуальные машины
с помощью временных DHCP- и PXE-серверов, запущенных в Docker-контейнерах.
Этот метод требует дополнительной управляющей машины, но позволяет устанавливать систему сразу на несколько хостов.

Обратите внимание, что Cozystack предоставляет собственные сборки Talos, протестированные и оптимизированные для запуска кластера Cozystack.

## Зависимости

Для установки Talos этим способом на управляющем хосте потребуются следующие зависимости:

- `docker`
- `kubectl`

## Обзор инфраструктуры

![Cozystack deployment](/img/cozystack-deployment.png)

## Установка

Запустите matchbox с готовым образом Talos для Cozystack:

```bash
sudo docker run --name=matchbox -d --net=host ghcr.io/cozystack/cozystack/matchbox:v0.30.0 \
  -address=:8080 \
  -log-level=debug
```

Запустите DHCP-сервер:
```bash
sudo docker run --name=dnsmasq -d --cap-add=NET_ADMIN --net=host quay.io/poseidon/dnsmasq:v0.5.0-32-g4327d60-amd64 \
  -d -q -p0 \
  --dhcp-range=192.168.100.3,192.168.100.199 \
  --dhcp-option=option:router,192.168.100.1 \
  --enable-tftp \
  --tftp-root=/var/lib/tftpboot \
  --dhcp-match=set:bios,option:client-arch,0 \
  --dhcp-boot=tag:bios,undionly.kpxe \
  --dhcp-match=set:efi32,option:client-arch,6 \
  --dhcp-boot=tag:efi32,ipxe.efi \
  --dhcp-match=set:efibc,option:client-arch,7 \
  --dhcp-boot=tag:efibc,ipxe.efi \
  --dhcp-match=set:efi64,option:client-arch,9 \
  --dhcp-boot=tag:efi64,ipxe.efi \
  --dhcp-userclass=set:ipxe,iPXE \
  --dhcp-boot=tag:ipxe,http://192.168.100.254:8080/boot.ipxe \
  --log-queries \
  --log-dhcp
```

Для установки в изолированной среде добавьте NTP- и DNS-серверы:
```bash
  --dhcp-option=option:ntp-server,10.100.1.1 \
  --dhcp-option=option:dns-server,10.100.25.253,10.100.25.254 \
```

Где:
- `192.168.100.3,192.168.100.199` — диапазон для выделения IP-адресов
- `192.168.100.1` — ваш gateway
- `192.168.100.254` — адрес вашего управляющего сервера

Проверьте состояние контейнеров:

```
docker ps
```

пример вывода:

```console
CONTAINER ID   IMAGE                                               COMMAND                  CREATED          STATUS          PORTS     NAMES
06115f09e689   quay.io/poseidon/dnsmasq:v0.5.0-32-g4327d60-amd64   "/usr/sbin/dnsmasq -…"   47 seconds ago   Up 46 seconds             dnsmasq
6bf638f0808e   ghcr.io/cozystack/cozystack/matchbox:v0.30.0        "/matchbox -address=…"   3 minutes ago    Up 3 minutes              matchbox
```

Запустите серверы.
Теперь они должны автоматически загрузиться с вашего PXE-сервера.

## Следующие шаги

После установки Talos перейдите к [установке и инициализации кластера Kubernetes]({{% ref "/docs/v1.2/install/kubernetes" %}}).
