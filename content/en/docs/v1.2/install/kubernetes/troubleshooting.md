---
title: Устранение неполадок при установке Kubernetes
linkTitle: Troubleshooting
description: "Инструкции по решению типовых проблем, которые могут возникнуть при установке Kubernetes с помощью `talm`, `talos-bootstrap` или `talosctl`."
weight: 40
aliases:
---

На этой странице приведены инструкции по решению типовых проблем, которые могут возникнуть при установке Kubernetes с помощью `talm`, `talos-bootstrap` или `talosctl`.

## No Talos nodes in maintenance mode found!

Если скрипт `talos-bootstrap` не обнаруживает узлы, выполните следующие шаги для диагностики и устранения проблемы:

1.  Проверьте сетевой сегмент

    Убедитесь, что скрипт запускается в том же сетевом сегменте, что и узлы. Это критически важно, чтобы скрипт мог взаимодействовать с узлами.

1.  Используйте Nmap для обнаружения узлов

    Проверьте, может ли `nmap` обнаружить узел, выполнив следующую команду:

    ```bash
    nmap -Pn -n -p 50000 192.168.0.0/24
    ```
    
    Эта команда сканирует сеть на наличие узлов, которые слушают порт `50000`.
    В выводе должны быть перечислены все узлы в сетевом сегменте, слушающие этот порт; это означает, что они доступны.

1.  Проверьте подключение talosctl

    Затем убедитесь, что `talosctl` может подключиться к конкретному узлу, особенно если узел находится в maintenance mode:
    
    ```bash
    talosctl -e "${node}" -n "${node}" get machinestatus -i
    ```
    
    Ошибка вида ниже обычно означает, что локальный бинарный файл `talosctl` устарел:
    
    ```console
    rpc error: code = Unimplemented desc = unknown service resource.ResourceService
    ```
    
    Обновление `talosctl` до последней версии должно решить проблему.

1.  Запустите talos-bootstrap в debug mode

    Если предыдущие шаги не помогли, запустите `talos-bootstrap` в debug mode, чтобы получить больше диагностической информации.
    
    Выполните скрипт с опцией `-x`, чтобы включить debug mode:
    
    ```bash
    bash -x talos-bootstrap
    ```
    
    Обратите внимание на последнюю команду, показанную перед ошибкой; часто она указывает на команду, которая завершилась неудачно, и помогает в дальнейшей диагностике.

# Исправление ext-lldpd на узлах Talos
Ожидание runtime service в Talos может привести к тому, что узел останется в состоянии booting в консоли Talos. Если вы хотите использовать lldpd, можно применить patch к узлам.
Продолжайте, если у вас есть подключение через `talosctl`.
```bash
cat > lldpd.patch.yaml <<EOF
apiVersion: v1alpha1
kind: ExtensionServiceConfig
name: lldpd
configFiles:
  - content: |
      configure lldp status disabled
    mountPath: /usr/local/etc/lldp/lldpd.conf
EOF
```
Чтобы применить patch к конкретному узлу, выполните:
```bash
talosctl patch mc -p @lldpd.patch.yaml -n <node> -e <node>
```

Проверьте, на каких узлах установлен lldpd:
```bash
node_net='192.168.100.0/24'
nmap -Pn -n -T4 -p50000 --open -oG - $node_net  | awk '/50000\/open/ { system("talosctl get extensions -n "$2" -e "$2" | grep lldpd") }'
```

Если хотите применить patch ко всем узлам:
```bash
nmap -Pn -n -T4 -p50000 --open -oG - $node_net  | awk '/50000\/open/ {print "talosctl patch mc -p @lldpd.patch.yaml -n "$2" -e "$2" "}'
```

Проверьте состояние в консоли Talos:
```bash
talosctl dashboard -n $(nmap -Pn -n -T4 -p50000 --open -oG - $node_net | awk '/50000\/open/ {print $2}' | paste -sd,)
```
