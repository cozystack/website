---
title: "Migrating Virtual Machines from VMware vSphere"
linkTitle: "VMware Migration"
description: "Migrating virtual machines from VMware vSphere into Cozystack tenants with the VM import API"
weight: 64
---

This guide describes how to migrate virtual machines from VMware vSphere into a Cozystack tenant using the `forklift.cozystack.io` import API. The migration is driven by the cluster rather than by hand: you register a connection to vCenter, name the machines you want, and the platform transfers each disk and turns it into a Cozystack `VMDisk` and `VMInstance`.

{{< note >}}
The transfer is a **cold migration**: the source VM is powered off before its disks are read, and stays off until you start it again in vSphere. Plan a maintenance window, and never point an import at a machine you cannot afford to stop.
{{< /note >}}

The engine underneath is [Konveyor Forklift](https://github.com/kubev2v/forklift). You do not interact with it directly — Cozystack owns the tenant-facing API and drives Forklift on your behalf.

## Prerequisites

**Packages.** VM import is opt-in. Add all three to the platform configuration:

```yaml
bundles:
  enabledPackages:
  - cozystack.forklift-operator
  - cozystack.forklift
  - cozystack.migration-controller
```

**The VDDK image.** VMware's Virtual Disk Development Kit is proprietary and Cozystack can neither ship nor mirror it. An operator who holds a licence builds the image once, pushes it somewhere the cluster can pull from, and names it at the platform level — see [Building the VDDK image](#building-the-vddk-image).

```yaml
vmImport:
  vddkImage: registry.example.com/vddk:8.0.3
```

Leaving it empty is a supported state: a vSphere import source then reports `Ready=False` with reason `VDDKNotConfigured` the moment it is created, rather than failing halfway through a transfer.

**A vCenter account.** The account needs read access to the inventory and the privileges Forklift uses to snapshot and read disks. Note that vCenter silently ignores an unknown privilege name, so a typo produces a role that looks correct and is quietly incomplete.

## Building the VDDK image

This is an administrator task, done once per cluster. It exists because the Virtual Disk Development Kit is licensed software: VMware distributes it to registered users only, and no one may redistribute it — which is why Cozystack ships no image and cannot mirror one for you.

{{< note >}}
Read the VDDK licence before you start. It permits an internal build for your own use; it does not permit publishing the resulting image to a registry other people can pull from. Push it to a private registry, not Docker Hub.
{{< /note >}}

### Download the kit

Sign in to the [Broadcom support portal](https://support.broadcom.com/) and download the **Virtual Disk Development Kit** for **Linux**, matching your vSphere version — a 8.0.x kit for vSphere 8, 7.0.x for vSphere 7. The file is named like `VMware-vix-disklib-8.0.3-24091160.x86_64.tar.gz`.

Matching matters: a kit older than the vCenter it talks to may fail to open disks, and the error appears at transfer time rather than at connection time.

### Build

The image is a plain filesystem carrying the kit at `/vddk-lib` — the engine mounts it into its transfer pod and reads the libraries from there. There is nothing to run inside it, so a scratch-like base is enough:

```dockerfile
FROM registry.access.redhat.com/ubi9/ubi-minimal
USER 1001
COPY vmware-vix-disklib-distrib /vddk-lib
ENTRYPOINT ["/bin/bash"]
```

```bash
tar -xzf VMware-vix-disklib-8.0.3-24091160.x86_64.tar.gz
podman build -t registry.example.com/vddk:8.0.3 .
podman push registry.example.com/vddk:8.0.3
```

Build for **linux/amd64**: the transfer pod runs on the cluster's worker nodes, and an image built on an arm64 laptop without an explicit platform will be pulled and then fail to execute. With `podman` or `docker buildx`, pass `--platform linux/amd64`.

### Make the cluster able to pull it

A private registry needs credentials in the namespaces that pull the image — the Forklift namespace and every tenant namespace an import runs in. Create the pull secret and reference it from the service account, or use whatever registry-credential mechanism your cluster already has.

An image the cluster cannot pull produces a transfer that never starts, with the reason on the pod rather than on the import task, so it is worth confirming the pull works before the first migration:

```bash
kubectl -n cozy-forklift run vddk-pull-check --rm -it --restart=Never \
  --image=registry.example.com/vddk:8.0.3 --command -- ls /vddk-lib
```

### Point the platform at it

```yaml
vmImport:
  vddkImage: registry.example.com/vddk:8.0.3
```

Only the reference travels to the controller — never a credential. The value is not a tenant setting and does not appear on any tenant-facing object: naming an image the cluster will run is an operator's decision.

When the kit is upgraded, change the tag here and the next import uses it. Running imports are unaffected, since the transfer pod already holds its copy.

## Before the first import

Four checks. Each of them, skipped, produces a failure that appears late and names something other than its cause.

### The storage class must bind Immediate

An import populates a volume before anything consumes it, so a `WaitForFirstConsumer` class deadlocks: the claim waits for a consumer that never arrives. The import task refuses such a class up front, but the **cluster default is frequently `WaitForFirstConsumer`**, so name the class explicitly:

```bash
kubectl get storageclass
```

Pick one whose `VOLUMEBINDINGMODE` is `Immediate` and put it in `spec.storageClass`.

### The ESXi hosts must be reachable from the cluster

Disk data does not travel through vCenter. The VDDK opens its connection straight to the ESXi host holding the VM, at whatever address vCenter advertises for that host.

That address must be routable from the worker nodes and — this is the one that catches people — **must not fall inside the cluster's Service CIDR**. An address in that range is claimed by Kubernetes service routing: the packets never leave the node, and the transfer dies after validation has already passed.

```bash
# The cluster's service network, via the address of the kubernetes service
kubectl get svc -n default kubernetes -o jsonpath='{.spec.clusterIP}'
```

Compare it with the addresses your ESXi hosts are advertised at. If they overlap, or the advertised address is simply unreachable, redirect the transfer with `spec.hosts` — see [Redirecting the transfer](#redirecting-the-transfer) below.

### The vCenter username needs its domain

vCenter expects the SSO domain: `migration@vsphere.local`, not `migration`. Given a bare account name it answers *"Cannot complete login due to an incorrect user name or password"* — the same message it uses for a wrong password, which sends you looking in the wrong place.

### The engine's certificates must be current

Forklift rotates its own serving certificates and updates the secret, but does not restart its pods. A long-lived deployment can therefore serve a certificate that its own published CA no longer matches, and the import controller — which verifies that CA — will refuse the connection. If a source will not become ready and the logs mention `certificate signed by unknown authority`:

```bash
kubectl -n cozy-forklift rollout restart deploy/forklift-controller
```

## Step 1: Register the source

A `VMImportSource` is a long-lived connection, reusable across many imports. Credentials go on the spec — tenants cannot create Secrets in Cozystack, so the controller materializes one for the engine to consume:

```yaml
apiVersion: forklift.cozystack.io/v1alpha1
kind: VMImportSource
metadata:
  name: vcenter-prod
  namespace: tenant-example
spec:
  type: vsphere
  url: https://vcenter.example.com/sdk
  credentials:
    username: migration@vsphere.local
    password: "..."
    caCert: |
      -----BEGIN CERTIFICATE-----
      ...
      -----END CERTIFICATE-----
```

Either `caCert` or `insecureSkipVerify: true` must be set. A SHA-1 **thumbprint does not work here**: a thumbprint is what the engine wants for a direct ESXi host connection, and supplying one in place of a CA leaves the source stuck reporting `SecretNotValid`.

Wait for the connection to be tested:

```bash
kubectl -n tenant-example get vmimportsource
```

```console
NAME           TYPE      URL                                READY   AGE
vcenter-prod   vsphere   https://vcenter.example.com/sdk    True    45s
```

### Redirecting the transfer

When vCenter advertises an ESXi address the cluster cannot use, add an override. Each entry carries its own credentials because the ESXi host authenticates the transfer connection itself rather than honouring the vCenter session:

```yaml
spec:
  hosts:
  - id: host-10               # the host's managed-object id
    address: 10.0.30.29       # an address the cluster can actually reach
    credentials:
      username: root
      password: "..."
      insecureSkipVerify: true
```

The host id is the one the VM's inventory record names, not the hostname.

## Step 2: Find the VMs to migrate

Machines are named by their vSphere managed-object reference — `vm-1234`, not the display name. The reference appears in the vSphere client URL when the VM is selected, and `govc ls -i` prints it:

```bash
govc ls -i /DC/vm/web-01
```

## Step 3: Run the import

A `VMImportTask` is a one-shot operation. It names a source, the machines, and the storage class every disk lands on:

```yaml
apiVersion: forklift.cozystack.io/v1alpha1
kind: VMImportTask
metadata:
  name: import-web-tier
  namespace: tenant-example
spec:
  sourceRef:
    name: vcenter-prod
  storageClass: replicated
  vms:
  - id: vm-1234
    name: web-01
  - id: vm-1235
    name: web-02
```

Watch it:

```bash
kubectl -n tenant-example get vmimporttask -w
```

```console
NAME              SOURCE         PHASE          AGE
import-web-tier   vcenter-prod   Validating     20s
import-web-tier   vcenter-prod   Transferring   1m
import-web-tier   vcenter-prod   Succeeded      6m
```

Per-VM progress, including the percentage of each disk transferred, is on `status.vms`:

```bash
kubectl -n tenant-example get vmimporttask import-web-tier -o jsonpath='{.status.vms}'
```

Each VM in a task is independent: one that fails does not stop its siblings.

## Step 4: What you get

The import produces ordinary Cozystack objects — one `VMDisk` per source disk and one `VMInstance` over them:

```bash
kubectl -n tenant-example get vmdisk,vminstance
```

Three properties are worth knowing:

**Nothing is copied twice.** The transferred volume is re-pointed into the disk the `VMInstance` expects, rather than cloned into it. A 16 GiB machine occupies 16 GiB when the import finishes.

**The imported VM starts `Halted`.** A freshly imported guest usually needs its network reviewed before it runs, and starting it automatically would put a second copy of a machine on the network. Start it when you are ready:

```bash
kubectl -n tenant-example patch vminstance web-01 --type merge -p '{"spec":{"runStrategy":"Always"}}'
```

**The results outlive the task.** Deleting the `VMImportTask` removes the migration machinery and leaves the disks and instances untouched — they carry no owner reference back to it. Deleting the source deregisters the connection and touches nothing already imported.

CPU topology, memory and firmware are carried across from the source: a UEFI guest is imported as a UEFI guest, with Secure Boot preserved.

## Migration checklist

- [ ] The three packages are enabled and `vmImport.vddkImage` is set
- [ ] A storage class with `volumeBindingMode: Immediate` is chosen
- [ ] ESXi transfer addresses are reachable and do not overlap the Service CIDR
- [ ] The vCenter username includes its SSO domain
- [ ] The source reports `Ready=True`
- [ ] A maintenance window exists: the source VM is powered off during transfer
- [ ] The tenant has quota for the imported disks
- [ ] After import: network reviewed, then the VM started

## Troubleshooting

### The source stays `Ready=False` with an authentication error

Check the username first. vCenter reports a missing SSO domain with the same message it uses for a wrong password. If the account is correct, confirm that `caCert` holds a CA certificate rather than a thumbprint.

### The task reaches `Transferring` and then fails with an NBD error

```console
Unable to connect to vddk data source: nbd_connect_uri: the server has no export named ''
```

This sounds like a missing disk and is almost always an unreachable ESXi host: the VDDK could not open its data connection to the address vCenter advertised. Check the address against your Service CIDR and add a `spec.hosts` override.

### Progress sits at 0 for a long time

A stalled transfer is not reported as an error on the migration objects. Look at the events on the target namespace's claims — a VDDK failure to reach the host surfaces there and nowhere else.

### The task fails with `no imported VM was found`

Something removed the machine the engine built before the platform could adopt it. The usual cause is a second controller acting on the same objects — for instance an older VM adoption controller left running from a previous Cozystack version. Ensure only one is active.

### An import failed and something is still transferring

A failed transfer can leave the engine's own `DataVolume` behind, retrying indefinitely. Look for one whose labels name the plan of the failed import and remove it:

```bash
kubectl -n tenant-example get dv -l vmID=vm-1234
```

## Limitations

The first version of this API is deliberately narrow:

- **vSphere only.** Other providers the engine already supports — oVirt, OpenStack, OVA, Hyper-V — arrive additively.
- **Cold migration only.** Warm, change-block-tracking migration is not offered; the source is powered off for the transfer.
- **One storage class per task.** Disks are not split across classes by source datastore.
- **Pod networking.** The imported `VMInstance` attaches to the pod network; richer placement arrives with the network-placement design.
- **Guest conversion is not offered.** Disks are copied as-is: the guest arrives with exactly the drivers it had under VMware. Imported disks are therefore attached to the SATA bus, which every distribution's initramfs and Windows itself can read without help — see [Disk bus](#disk-bus) for what to do once the machine is up.

## Disk bus

Imported disks are attached to the **SATA** bus, not virtio.

This is not a performance preference, it is what makes the machine boot at all. A guest copied out of VMware carries the drivers it had there — typically `vmw_pvscsi` — and no virtio. On a virtio disk such a guest does not fail the import; it imports successfully and then does not boot. Linux stops in its initramfs waiting for a root device that never appears, and Windows stops with `INACCESSIBLE_BOOT_DEVICE` (0x7B). SATA's controller is present in essentially every initramfs and inbox in Windows, so the machine comes up as it did before.

Once the guest is running, switching to virtio is worth doing — it is meaningfully faster — but only after the drivers are in place:

- **Linux:** make sure `virtio_blk` (and `virtio_pci`) are in the initramfs, then rebuild it. On RHEL-family guests that is `dracut --regenerate-all --force`; on Debian-family, `update-initramfs -u -k all`.
- **Windows:** install the [virtio-win](https://github.com/virtio-win/virtio-win-pkg-scripts) drivers before changing anything.

Then edit the `VMInstance` and set `bus: virtio` on the disk. Change one machine first and confirm it boots before doing the rest.

A machine with more than six disks is the one exception: the SATA controller offers six ports, so disks past the sixth are attached to virtio from the start. Only the boot disk has to be readable before the guest's own drivers load, so Linux picks the rest up normally once it is running; on Windows they appear after virtio-win is installed.

## Planning notes

An import needs roughly **twice the disk size in free space** while it runs: the transfer target plus scratch space. A 16 GiB machine transfers in a few minutes on a local network; plan larger machines proportionally, and remember the source is unavailable for that whole window.
