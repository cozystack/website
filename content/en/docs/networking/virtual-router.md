---
title: "Virtual Routers"
linkTitle: "Virtual Routers"
description: "Deploy a virtual router in a VM"
weight: 40
aliases:
  - /docs/operations/virtualization/virtual-router
---

Starting with version [v0.27.0](https://github.com/cozystack/cozystack/releases/tag/v0.27.0),
Cozystack can deploy virtual routers (also known as "router appliances" or "middlebox appliances").
This feature allows you to create a virtual router based on a virtual machine instance.
The virtual router can route traffic between different networks.

## Creating a Virtual Router

Creating a virtual router requires a Cozystack administrator account.

1.  **Create a VM Instance**<br/>
    Use the standard `vm-instance` and `virtual-machine` packages to create a virtual machine instance.

1.  **Disable Anti-Spoofing Protection**<br/>
    To act as a virtual router, the VM instance should have anti-spoofing protection disabled:

    ```bash
    kubectl patch virtualmachines.kubevirt.io virtual-machine-example --type=merge \
        -p '{"spec":{"template":{"metadata":{"annotations":{"ovn.kubernetes.io/port_security": "false"}}}}}'
    ```

1.  **Restart the Virtual Machine**

    ```bash
    virtctl stop virtual-machine-example
    virtctl start virtual-machine-example
    ```

1.  **Retrieve the IP Address of the VM**

    ```bash
    kubectl get vmi
    ```

    The output will have a line with the new VM's IP address:

    ```console
    NAME                      AGE     PHASE     IP            NODENAME        READY
    virtual-machine-example   3d4h    Running   10.244.8.56   gld-csxhk-003   True
    ```

1.  **Configure Custom Routes for a Tenant**<br/>
    Edit the tenant namespace:

    ```bash
    kubectl edit namespace tenant-example
    ```

    Add the following annotation using the router IP you found earlier as `gw`
    and the subnet mask for the router to handle as `dst`:

    ```yaml
    ovn.kubernetes.io/routes: |
      [{
        "gw": "10.244.8.56",
        "dst": "10.10.13.0/24"
      }]
    ```

These custom routes will now be applied to all pods within the tenant namespace.
