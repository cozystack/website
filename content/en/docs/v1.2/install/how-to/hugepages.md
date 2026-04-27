---
title: "Как включить Hugepages"
linkTitle: "Включение Hugepages"
description: "Как включить Hugepages"
weight: 130
---

Hugepages для Cozystack можно включить как во время первоначальной установки, так и в любой момент после нее.
Применение этой конфигурации после установки потребует полной перезагрузки узла.

Подробнее см. в документации ядра Linux: [HugeTLB Pages](https://docs.kernel.org/admin-guide/mm/hugetlbpage.html).


## Использование Talm

Требуется Talm `v0.16.0` или новее.

1.  Добавьте следующие строки в `values.yaml`:

    ```yaml
    ...
    certSANs: []
    nr_hugepages: 3000
    ```
    
    `vm.nr_hugepages` — это количество страниц на 2Mi.

1.  Примените конфигурацию:

    ```bash
    talm apply -f nodes/node0.yaml
    ```

1.  Затем перезагрузите узлы:

    ```bash
    talm -f nodes/node0.yaml reboot
    ```

## Использование talosctl

1.  Добавьте следующие строки в шаблон узла:

    ```yaml
    machine:
      sysctls:
        vm.nr_hugepages: "3000"
    ```
    
    `vm.nr_hugepages` — это количество страниц на 2Mi.

1.  Примените конфигурацию:

    ```bash
    talosctl apply -f nodetemplate.yaml -n 192.168.123.11 -e 192.168.123.11
    ```

1.  Перезагрузите узлы:

    ```bash
    talosctl reboot -n 192.168.123.11 -e 192.168.123.11
    ```
