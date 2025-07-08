---
title: "Running MikroTik RouterOS in Cozystack"
linkTitle: "MikroTik"
description: "Deploying MikroTik RouterOS (CHR) as a virtual appliance on Cozystack"
weight: 60
----------

## Prerequisites

* MikroTik RouterOS ISO (CHR or NPK install image), e.g. `mikrotik-7.19.3.iso`.
* A free static IP or DHCP on the connected tenant network.
* `virtctl` installed and configured for your tenant‘s namespace.

---

## Installation

### Prepare disks

You need **two disks**:

1. **Installation ISO** – optical.
2. **System disk** – non‑optical.

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VMDisk
metadata:
  name: mikrotik-iso
spec:
  source:
    http:
      url: https://download.mikrotik.com/routeros/7.19.3/mikrotik-7.19.3.iso
  optical: true
  storage: 1Gi
  storageClass: replicated
---
apiVersion: apps.cozystack.io/v1alpha1
kind: VMDisk
metadata:
  name: mikrotik-system
spec:
  optical: false
  storage: 1Gi
  storageClass: replicated
```

### Create the VMInstance

RouterOS does not require a special instance profile. Use a lightweight Linux profile (e.g. `ubuntu`) plus a small instance type such as `u1.medium`:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: VMInstance
metadata:
  name: mikrotik-demo
spec:
  running: true
  instanceType: "u1.medium"
  instanceProfile: ubuntu
  disks:
    - name: mikrotik-system
      bus: sata
    - name: mikrotik-iso
      bus: sata
```

### 3. Install RouterOS

1. Launch a console:

   ```bash
   virtctl vnc mikrotik-demo -n tenant-test
   ```

2. When prompted for package selection, choose the desired bundle (usually *system*, *routing*, *security*). Confirm formatting the system disk.

3. After installation completes, remove the installation ISO

### 5. Adjust MTU (optional)

Cozystack’s virtual network interfaces default to **MTU 1400**. RouterOS respects this automatically on Virtio‑Net adapters, but you can verify or change it:

```bash
/interface ethernet print detail
/interface ethernet set [find default-name~"ether1"] mtu=1400
```

Avoid legacy e1000/vmxnet drivers; they ignore non‑1500 MTUs and may drop large packets.
