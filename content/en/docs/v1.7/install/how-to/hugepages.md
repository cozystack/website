---
title: "How to enable Hugepages"
linkTitle: "Enable Hugepages"
description: "How to enable Hugepages"
weight: 130
---

Enabling Hugepages for Cozystack can be done both on initial installation and at any time after it.
Applying this configuration after installation will require a full node reboot.

Read more in the Linux Kernel documentation: [HugeTLB Pages](https://docs.kernel.org/admin-guide/mm/hugetlbpage.html).


## Using Talm

Requires Talm `v0.16.0` or later.

1.  Add the following lines to `values.yaml`:

    ```yaml
    ...
    certSANs: []
    nr_hugepages: 3000
    ```
    
    `vm.nr_hugepages` is the count of pages per 2Mi.

1.  Apply the configuration:

    ```bash
    talm apply -f nodes/node0.yaml
    ```

1.  Finally, reboot the nodes:

    ```bash
    talm -f nodes/node0.yaml reboot
    ```

## Using talosctl

1.  Add the following lines to your node template:

    ```yaml
    machine:
      sysctls:
        vm.nr_hugepages: "3000"
    ```
    
    `vm.nr_hugepages` is the count of pages per 2Mi.

1.  Apply the configuration:

    ```bash
    talosctl apply -f nodetemplate.yaml -n 192.168.123.11 -e 192.168.123.11
    ```

1.  Reboot the nodes:

    ```bash
    talosctl reboot -n 192.168.123.11 -e 192.168.123.11
    ```
