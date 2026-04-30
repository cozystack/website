---
title: "Running VMs with GPU Passthrough or vGPU"
linkTitle: "GPU Passthrough and vGPU"
description: "Running VMs with GPU Passthrough or NVIDIA vGPU on Cozystack"
weight: 40
aliases:
  - /docs/v1.2/operations/virtualization/gpu
---

This section demonstrates how to deliver GPU access to virtual machines (VMs) on Cozystack. It covers two flows: **GPU passthrough** (one whole physical GPU bound to a single VM via `vfio-pci`) and **NVIDIA vGPU** (one physical GPU sliced into multiple virtual GPUs via SR-IOV, with each VF passed to a different VM). The passthrough flow comes first; jump to [GPU Sharing for Virtual Machines (vGPU)](#gpu-sharing-for-virtual-machines-vgpu) for the vGPU walk-through.

By default, to provision a GPU Passthrough, the GPU Operator will deploy the following components:

- **VFIO Manager** to bind `vfio-pci` driver to all GPUs on the node.
- **Sandbox Device Plugin** to discover and advertise the passthrough GPUs to kubelet.
- **Sandbox Validator** to validate the other operands.

## Prerequisites

- A Cozystack cluster with at least one GPU-enabled node.
- kubectl installed and cluster access credentials configured.

## 1. Install the GPU Operator

Follow these steps:

1.  Label the worker node explicitly for GPU passthrough workloads:

    ```bash
    kubectl label node <node-name> --overwrite nvidia.com/gpu.workload.config=vm-passthrough
    ```

2.  Enable the GPU Operator in your Platform Package by adding it to the enabled packages list:

    ```bash
    kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=json \
      -p '[{"op": "add", "path": "/spec/components/platform/values/bundles/enabledPackages/-", "value": "cozystack.gpu-operator"}]'
    ```

    This will deploy the components (operands).

3.  Ensure all pods are in a running state and all validations succeed with the sandbox-validator component:

    ```bash
    kubectl get pods -n cozy-gpu-operator
    ```

    Example output (your pod names may vary):

    ```console
    NAME                                            READY   STATUS    RESTARTS   AGE
    ...
    nvidia-sandbox-device-plugin-daemonset-4mxsc    1/1     Running   0          40s
    nvidia-sandbox-validator-vxj7t                  1/1     Running   0          40s
    nvidia-vfio-manager-thfwf                       1/1     Running   0          78s
    ```

To verify the GPU binding, access the node using `kubectl node-shell -n cozy-system -x` or `kubectl debug node` and run:

```bash
lspci -nnk -d 10de:
```

The vfio-manager pod will bind all GPUs on the node to the vfio-pci driver. Example output:

```console
3b:00.0 3D controller [0302]: NVIDIA Corporation Device [10de:2236] (rev a1)
       Subsystem: NVIDIA Corporation Device [10de:1482]
       Kernel driver in use: vfio-pci
86:00.0 3D controller [0302]: NVIDIA Corporation Device [10de:2236] (rev a1)
       Subsystem: NVIDIA Corporation Device [10de:1482]
       Kernel driver in use: vfio-pci
```

The sandbox-device-plugin will discover and advertise these resources to kubelet.
In this example, the node shows two A10 GPUs as available resources:

```bash
kubectl describe node <node-name>
```

Example output:

```console
...
Capacity:
  ...
  nvidia.com/GA102GL_A10:         2
  ...
Allocatable:
  ...
  nvidia.com/GA102GL_A10:         2
...
```

{{% alert color="info" %}}
**Note:** Resource names are constructed by combining the `device` and `device_name` columns from the [PCI IDs database](https://pci-ids.ucw.cz/v2.2/pci.ids).
For example, the database entry for A10 reads `2236  GA102GL [A10]`, which results in a resource name `nvidia.com/GA102GL_A10`.
{{% /alert %}}

## 2. Update the KubeVirt Custom Resource

Next, we will update the KubeVirt Custom Resource, as documented in the
[KubeVirt user guide](https://kubevirt.io/user-guide/virtual_machines/host-devices/#listing-permitted-devices),
so that the passthrough GPUs are permitted and can be requested by a KubeVirt VM.

Adjust the `pciVendorSelector` and `resourceName` values to match your specific GPU model.
Setting `externalResourceProvider=true` indicates that this resource is provided by an external device plugin,
in this case the `sandbox-device-plugin` which is deployed by the Operator.

```bash
kubectl edit kubevirt -n cozy-kubevirt
```
example config:
```yaml
  ...
  spec:
    configuration:
      permittedHostDevices:
        pciHostDevices:
        - externalResourceProvider: true
          pciVendorSelector: 10DE:2236
          resourceName: nvidia.com/GA102GL_A10
  ...
```

## 3. Create a Virtual Machine

We are now ready to create a VM.

1.  Create a sample virtual machine using the following VMI specification that requests the `nvidia.com/GA102GL_A10` resource.

    **vmi-gpu.yaml**:

    ```yaml
    ---
    apiVersion: apps.cozystack.io/v1alpha1
    kind: VMInstance
    metadata:
      name: gpu
      namespace: tenant-example
    spec:
      running: true
      instanceProfile: ubuntu
      instanceType: u1.medium
      systemDisk:
        image: ubuntu
        storage: 5Gi
        storageClass: replicated
      gpus:
      - name: nvidia.com/GA102GL_A10
      cloudInit: |
        #cloud-config
        password: ubuntu
        chpasswd: { expire: False }
    ```

    ```bash
    kubectl apply -f vmi-gpu.yaml
    ```

    Example output:
    ```console
    virtualmachines.apps.cozystack.io/gpu created
    ```

2.  Verify the VM status:

    ```bash
    kubectl get vmi
    ```

    ```console
    NAME                       AGE   PHASE     IP             NODENAME        READY
    virtual-machine-gpu        73m   Running   10.244.3.191   luc-csxhk-002   True
    ```

3.  Log in to the VM and confirm that it has access to GPU:

    ```bash
    virtctl console virtual-machine-gpu
    ```

    Example output:
    ```console
    Successfully connected to vmi-gpu console. The escape sequence is ^]

    vmi-gpu login: ubuntu
    Password:

    ubuntu@virtual-machine-gpu:~$ lspci -nnk -d 10de:
    08:00.0 3D controller [0302]: NVIDIA Corporation GA102GL [A10] [10de:2236] (rev a1)
            Subsystem: NVIDIA Corporation GA102GL [A10] [10de:1851]
            Kernel driver in use: nvidia
            Kernel modules: nvidiafb, nvidia_drm, nvidia
    ```

## GPU Sharing for Virtual Machines (vGPU)

GPU passthrough assigns an entire physical GPU to a single VM. To share one GPU between multiple VMs, you can use **NVIDIA vGPU**, which slices a single physical GPU into multiple virtual GPUs that VMs consume independently.

{{% alert color="warning" %}}
**This entire workflow depends on upstream components that are not yet released.** Two foundational pieces are required and neither is in a Cozystack release as of this writing:

- The `vgpu` variant of the `gpu-operator` package — tracked in [cozystack/cozystack#2323](https://github.com/cozystack/cozystack/pull/2323); until that lands the `vgpu` variant is unavailable in released Cozystack versions.
- KubeVirt's SR-IOV vGPU support ([kubevirt/kubevirt#16890](https://github.com/kubevirt/kubevirt/pull/16890)) — `main`-only. See the [Prerequisites](#prerequisites) section below for the full version story.

Treat this guide as forward-looking documentation. If you follow it on a current Cozystack release the variant CR will be rejected and the `kubectl edit kubevirt` patch will not produce allocatable resources.
{{% /alert %}}

{{% alert color="info" %}}
**Why not MIG?** MIG (Multi-Instance GPU) partitions a GPU into isolated instances, but these are logical divisions within a single PCIe device. VFIO cannot pass them to VMs — MIG only works with containers. To use MIG with VMs, you need vGPU on top of MIG partitions (still requires a vGPU license).
{{% /alert %}}

{{% alert color="info" %}}
**Two driver models.** NVIDIA's vGPU driver uses two different host-side mechanisms:

- **SR-IOV with per-VF NVIDIA sysfs** — Ada Lovelace (L4, L40, L40S, …) and Blackwell (B100, …) on the **vGPU 20.x driver branch** (driver `595.x`). KubeVirt advertises VFs via `permittedHostDevices.pciHostDevices`. **This guide focuses on this path** — it is what NVIDIA ships for current data-centre GPUs. vGPU 17.x supports the same hardware via SR-IOV but pre-dates KubeVirt's `pciHostDevices` integration ([kubevirt#16890](https://github.com/kubevirt/kubevirt/pull/16890)) and is out of scope here.
- **Mediated devices (mdev)** — Pascal / Volta / Turing / Ampere up to A100 / A30. KubeVirt advertises them via `permittedHostDevices.mediatedDevices`. For these GPUs follow the [upstream NVIDIA GPU Operator docs](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/install-gpu-operator-vgpu.html) — the configuration shown below does not apply.
{{% /alert %}}

### Prerequisites

- An Ada Lovelace (or newer) NVIDIA GPU that supports SR-IOV vGPU (L4, L40, L40S, etc.).
- Ubuntu 24.04 host OS. Older Ubuntu releases also work if NVIDIA's `gpu-driver-container` repository ships a matching `vgpu-manager/<release>/Dockerfile`.
- **Talos Linux is not recommended** for the vGPU path. NVIDIA does not publicly distribute the vGPU guest driver — it requires NVIDIA Enterprise Portal access — and Sidero [closed siderolabs/extensions#461](https://github.com/siderolabs/extensions/issues/461) noting that they cannot support vGPU "unless NVIDIA changes their licensing terms or provides us a way to obtain, test, and distribute the software". Passthrough on Talos is fine; only vGPU is affected.
- KubeVirt with [kubevirt/kubevirt#16890](https://github.com/kubevirt/kubevirt/pull/16890) ("vGPU: SRIOV support", merged to `main` 2026-04-10). Targeted at the next minor release (v1.9.0); track the PR for the actual release tag. Released tags up to and including v1.8.x do not advertise SR-IOV VFs as PCI host devices, and backports are not planned. If you need vGPU before v1.9.0 lands you have to run a `main`-based nightly build of `virt-handler`; the rest of the operator can stay on the latest released tag.
- An NVIDIA vGPU Software / NVIDIA AI Enterprise subscription.
- A reachable NVIDIA Delegated License Service (DLS) instance and a matching `client_configuration_token.tok` file.

{{% alert color="warning" %}}
The vGPU Manager driver is proprietary software distributed by NVIDIA under a commercial license. Cozystack does not include or redistribute this driver. You must obtain it directly from NVIDIA and build the container image yourself.
{{% /alert %}}

### 1. Build the vGPU Manager Image

The GPU Operator expects a pre-built driver container image — it does not install the driver from a raw `.run` file at runtime.

1. Download the vGPU Manager driver from the [NVIDIA Licensing Portal](https://ui.licensing.nvidia.com) (Software Downloads → NVIDIA AI Enterprise → Linux KVM, **not** the Ubuntu KVM `.deb` — that ships pre-built modules for stock kernels only).
2. Build the driver container image from NVIDIA's upstream repository (the older `gitlab.com/nvidia/container-images/driver` is archived). Replace `registry.example.com` with your private registry hostname:

```bash
git clone https://github.com/NVIDIA/gpu-driver-container.git
cd gpu-driver-container/vgpu-manager/ubuntu24.04

# Place the downloaded .run alongside the Dockerfile (do not commit it)
cp /path/to/NVIDIA-Linux-x86_64-<driver-version>-vgpu-kvm.run .

# --platform linux/amd64 is mandatory on Apple Silicon / arm64 build
# hosts: GPU nodes are amd64 and the kubelet pull will fail with
# 'no matching manifest' if the image was built native on arm64.
docker build \
  --platform linux/amd64 \
  --build-arg DRIVER_VERSION=<driver-version> \
  -t registry.example.com/nvidia/vgpu-manager:<driver-version>-ubuntu24.04 .

# docker login first if your registry needs auth
docker push registry.example.com/nvidia/vgpu-manager:<driver-version>-ubuntu24.04
```

{{% alert color="info" %}}
The container's entrypoint downloads kernel headers at pod start time and compiles `nvidia.ko` against the running kernel, so a single image works across kernel patch versions for the same Ubuntu release.
{{% /alert %}}

{{% alert color="warning" %}}
Uploading the vGPU driver to a publicly available registry is a violation of the NVIDIA vGPU EULA. Always use a private registry — Cozystack's in-cluster Harbor (as a non-proxy project) is a good fit.
{{% /alert %}}

### 2. Install the GPU Operator with vGPU Variant

{{% alert color="warning" %}}
**The vgpu variant is experimental.** NVIDIA's `vgpu-device-manager` walks `/sys/class/mdev_bus/`, which does not exist on Ada Lovelace or Blackwell — the DaemonSet errors with "no parent devices found" and is therefore disabled by default. Profile assignment is currently an out-of-band step (`echo <id> > /sys/.../current_vgpu_type` per VF) that must be re-applied after every node reboot. Without it, `permittedHostDevices.pciHostDevices` reports zero allocatable resources. **Do not deploy the variant in production until you have an automated profile-assignment mechanism in place** — typically a small DaemonSet that reads a ConfigMap (`<bus-id> = <profile-id>`) and writes the corresponding `current_vgpu_type` files at boot.
{{% /alert %}}

The GPU Operator's `vgpu` variant enables the vGPU Manager DaemonSet, sets `sandboxWorkloads.defaultWorkload: vm-vgpu` so unlabelled GPU nodes activate the variant, and disables the pod-side driver, device plugin, and `vgpu-device-manager` DaemonSets. Flip `vgpuDeviceManager.enabled: true` only when running an mdev-era GPU (Pascal–Ampere).

1. Label the worker node for vGPU workloads:

    ```bash
    kubectl label node <node-name> --overwrite nvidia.com/gpu.workload.config=vm-vgpu
    ```

2. Create the GPU Operator Package with the `vgpu` variant, providing your vGPU Manager image coordinates:

    Replace `<driver-version>` with the version you built (it must match the tag you pushed in step 1). If your registry requires authentication, create a docker-registry Secret in the `cozy-gpu-operator` namespace first and uncomment the `imagePullSecrets` block. The chart reads `imagePullSecrets` per-component (`vgpuManager`, `driver`, `validator`, …) as a list of strings — not `[{name: ...}]`:

    ```yaml
    apiVersion: cozystack.io/v1alpha1
    kind: Package
    metadata:
      name: cozystack.gpu-operator
    spec:
      variant: vgpu
      components:
        gpu-operator:
          values:
            gpu-operator:
              vgpuManager:
                repository: registry.example.com/nvidia
                image: vgpu-manager
                version: "<driver-version>-ubuntu24.04"
                # Uncomment if your registry needs auth:
                # imagePullSecrets:
                # - nvidia-registry-secret
    ```

3. Verify the DaemonSet is running and `nvidia.ko` loads on every GPU node:

    ```bash
    kubectl get pods -n cozy-gpu-operator -l app=nvidia-vgpu-manager-daemonset
    kubectl exec -n cozy-gpu-operator <vgpu-manager-pod> -- nvidia-smi
    ```

    `nvidia-smi` should enumerate the physical GPUs and report `Host VGPU Mode : SR-IOV`. The driver enables SR-IOV automatically; the maximum VF count is hardware-dependent and the configured profile size further reduces it (for example an L40S exposes up to 16 VFs at `-1Q` but only 2 at `-24Q` — total framebuffer divided by per-profile framebuffer).

### 3. Assign vGPU Profiles to SR-IOV VFs

Each VF needs a vGPU profile written to its NVIDIA sysfs before it can be allocated to a VM. Profile IDs come from the driver and can be enumerated per VF:

```bash
kubectl exec -n cozy-gpu-operator <vgpu-manager-pod> -- \
  cat /sys/bus/pci/devices/0000:02:00.5/nvidia/creatable_vgpu_types
```

Write the chosen profile — substitute `<profile-id>` with the numeric ID for the desired profile from the `creatable_vgpu_types` listing above. **Numeric IDs come from the driver and are not guaranteed stable across driver versions** — always derive them from sysfs on the actual hardware rather than copy-pasting from external references:

```bash
kubectl exec -n cozy-gpu-operator <vgpu-manager-pod> -- \
  sh -c 'echo <profile-id> > /sys/bus/pci/devices/0000:02:00.5/nvidia/current_vgpu_type'
```

{{% alert color="info" %}}
Profile assignment is currently out-of-band — there is no first-class operator for the SR-IOV path yet. Manual `kubectl exec` is fine for a proof-of-concept cluster. For anything longer-lived, a small DaemonSet that re-applies the assignment periodically is the typical pattern. The skeleton below is a starting point — production-grade implementations will want richer error reporting, MIG awareness, and explicit ConfigMap reload handling. **Side-effect to be aware of:** while this DaemonSet runs, manual `kubectl exec` changes to `current_vgpu_type` are reverted within 60 s. Edit the ConfigMap rather than the sysfs file directly.
{{% /alert %}}

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vgpu-profiles
  namespace: cozy-gpu-operator
data:
  # One <bus-id>=<profile-id> per line. Profile IDs are
  # driver-version-dependent — read them from
  # /sys/bus/pci/devices/<VF>/nvidia/creatable_vgpu_types.
  profiles: |
    0000:02:00.4=<profile-id>
    0000:02:00.5=<profile-id>
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: vgpu-profile-loader
  namespace: cozy-gpu-operator
spec:
  selector:
    matchLabels:
      app: vgpu-profile-loader
  template:
    metadata:
      labels:
        app: vgpu-profile-loader
    spec:
      nodeSelector:
        nvidia.com/gpu.workload.config: vm-vgpu
      containers:
      - name: loader
        image: alpine:3.20
        securityContext:
          privileged: true
        volumeMounts:
        - { name: sys, mountPath: /sys }
        - { name: profiles, mountPath: /etc/vgpu-profiles, readOnly: true }
        command:
        - sh
        - -c
        - |
          set -u
          # exit cleanly on SIGTERM so kubelet does not need to SIGKILL
          # after terminationGracePeriodSeconds on rolling updates.
          trap 'exit 0' TERM INT
          while true; do
            while IFS= read -r line; do
              # strip leading/trailing whitespace and any trailing comment
              line=$(printf '%s' "$line" | sed 's/[[:space:]]*#.*$//;s/^[[:space:]]*//;s/[[:space:]]*$//')
              [ -z "$line" ] && continue
              bus=${line%%=*}; profile=${line#*=}
              [ "$bus" = "$line" ] && { echo "skip malformed line: $line"; continue; }
              path="/sys/bus/pci/devices/$bus/nvidia/current_vgpu_type"
              [ -w "$path" ] || { echo "skip $bus (no $path)"; continue; }
              # read-before-write: skip if the profile already matches
              # so manual out-of-band changes are visible in the log
              # only when the loader actually overrides them, and so
              # the kernel does not reject writes while a VM holds the VF.
              current=$(cat "$path" 2>/dev/null || printf '')
              if [ "$current" = "$profile" ]; then
                continue
              fi
              # printf '%s' avoids a trailing newline that some driver
              # versions reject as 'invalid argument'.
              if printf '%s' "$profile" > "$path" 2>/dev/null; then
                echo "set $bus -> $profile (was $current)"
              else
                # Likely refcount > 0 (VM holds the VF). Suppress the
                # noisy retry; the next pass will pick it up after the
                # VM releases.
                :
              fi
            done < /etc/vgpu-profiles/profiles
            sleep 60 &
            wait $!   # wait so the trap fires immediately on SIGTERM
          done
      volumes:
      - { name: sys, hostPath: { path: /sys } }
      - { name: profiles, configMap: { name: vgpu-profiles } }
```

### 4. Configure the NVIDIA License Service (DLS)

vGPU 17 / 20 uses the NVIDIA Delegated License Service. The legacy `ServerAddress=` / `ServerPort=7070` lines in `gridd.conf` are no longer authoritative — `nvidia-gridd` (running **inside the guest**) reads the DLS endpoint from the ClientConfigToken file directly.

The host vGPU Manager DaemonSet does not request a license — it only enables SR-IOV and loads `nvidia.ko`. Licensing is consumed entirely by the guest. The gpu-operator chart's `driver.licensingConfig.secretName` would mount the Secret into the **driver pod on the host**, where it has no effect for SR-IOV vGPU; do not wire the licensing Secret through it.

Instead, deliver the token and `gridd.conf` to the guest via cloud-init or a containerDisk overlay so they land at `/etc/nvidia/ClientConfigToken/client_configuration_token.tok` and `/etc/nvidia/gridd.conf`:

```yaml
# inside the VirtualMachine cloudInitNoCloud userData
write_files:
- path: /etc/nvidia/ClientConfigToken/client_configuration_token.tok
  # 0744 follows NVIDIA's recommendation in the Licensing User Guide
  # so nvidia-gridd (which does not necessarily run as the file owner)
  # can read it.
  permissions: '0744'
  encoding: b64
  content: <base64 token>
- path: /etc/nvidia/gridd.conf
  permissions: '0644'
  content: |
    # FeatureType selects which vGPU Software license the guest requests:
    #   0 — unlicensed state (no license requested; Q profiles run in
    #       reduced mode after the grace period)
    #   1 — NVIDIA vGPU; the driver auto-selects the correct license type
    #       from the configured vGPU profile (Q → vWS, B → vPC,
    #       A → vCS / Compute). Use this for SR-IOV vGPU profiles.
    #   2 — explicitly NVIDIA RTX Virtual Workstation
    #   4 — explicitly NVIDIA Virtual Compute Server
    FeatureType=1
```

Verify activation inside the guest:

```bash
nvidia-smi -q | grep 'License Status'
# License Status   : Licensed
```

If the guest reports `Unlicensed (Unrestricted)` for more than a couple of minutes, check `journalctl _COMM=nvidia-gridd` inside the guest for handshake errors against the DLS endpoint baked into the token.

{{% alert color="info" %}}
**Migrating from older GPU Operator versions (passthrough only).** The upstream chart deprecated `driver.licensingConfig.configMapName` in favour of `driver.licensingConfig.secretName`. The old key still works but is marked deprecated in the CRD. If you previously wired licensing through `configMapName` for passthrough deployments, switch to `secretName` on the next upgrade — the Secret content (`gridd.conf` and the ClientConfigToken) does not need to change. SR-IOV vGPU operators can ignore this; the host-side licensing knob is unused on the vGPU path (token consumption happens in the guest, see above).
{{% /alert %}}

### 5. Update the KubeVirt Custom Resource

After [kubevirt/kubevirt#16890](https://github.com/kubevirt/kubevirt/pull/16890), `virt-handler` recognises SR-IOV VFs bound to the `nvidia` driver as candidates whenever a vGPU profile is configured (`current_vgpu_type` ≠ 0). PFs are skipped automatically.

`kubectl edit kubevirt -n cozy-kubevirt` opens the live object — **merge** the entry below into the existing `permittedHostDevices.pciHostDevices` list (the passthrough section above adds its own entries; do not overwrite them):

```yaml
spec:
  configuration:
    permittedHostDevices:
      pciHostDevices:
      - pciVendorSelector: "10DE:26B9"   # L40S — same tuple for PF and VF
        resourceName: nvidia.com/L40S-24Q
```

`pciVendorSelector` is the `vendor:device` tuple of the GPU; on L40S (and other Ada-Lovelace cards) the SR-IOV VFs report the same tuple as the PF — `lspci -nn -d 10de:` on the host shows both as `[10de:26b9]`. `virt-handler` distinguishes them by "is-VF + has-vGPU-profile", so a single `pciVendorSelector` matches the right set. Verify on your specific GPU with `lspci -nn -d 10de:` before assuming this — some generations split PF/VF tuples.

Match `resourceName` to the profile you wrote into `current_vgpu_type`. **Do not** set `externalResourceProvider: true` here — the device plugin lives inside `virt-handler` itself for SR-IOV vGPU; no external sandbox device plugin advertises this resource.

Verify allocatable capacity:

```bash
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.status.allocatable.nvidia\.com/L40S-24Q}{"\n"}{end}'
```

### 6. Create a Virtual Machine with vGPU

KubeVirt accepts the vGPU resource under either `hostDevices:` or `gpus:`. The two structs differ only in that `gpus:` carries an optional `virtualGPUOptions` field whose `display.enabled` defaults to `true` (provisioning a vGPU console output); `hostDevices:` has no such field. For a headless compute VM `hostDevices:` is the natural choice. The example uses the upstream `kubevirt.io/v1` `VirtualMachine` kind directly rather than the Cozystack `apps.cozystack.io/v1alpha1` `VMInstance` wrapper used in the passthrough section above — the wrapper's `gpus:` field passes the resource name straight through to KubeVirt, which works for the passthrough case, but the wrapper has not been exercised end-to-end against an SR-IOV vGPU resource and lacks an explicit `hostDevices:` surface for headless setups. Until the wrapper grows a tested SR-IOV vGPU path, raw KubeVirt is the safe option. Tenants need permission to create raw KubeVirt resources in their namespace; if your tenant policy disallows this, wait for wrapper support.

{{% alert color="warning" %}}
**Do not use a stock containerDisk root volume for in-VM driver install.** The Ubuntu containerDisk image gives the guest a ~2.4 GiB root filesystem (qcow2 overlay on the immutable container layer). Kernel headers + `build-essential` + DKMS sources + `libnvidia-*.so` libraries together overflow the rootfs and `nvidia-installer` aborts mid-install (we observed `SIGBUS` from a write into an mmap of a file the kernel could no longer extend). Use a CDI `DataVolume` of 20 GiB or larger for the root disk in any non-throwaway test, or pre-bake the GRID driver into a custom containerDisk image.
{{% /alert %}}

The example below uses a `DataVolume` so the root has room for the driver install, and a `cloudInitNoCloud` disk that drops the licensing token, `gridd.conf`, an SSH key for `virtctl ssh`, and the build dependencies. `<base64 token>` and `<your ssh public key>` are placeholders the operator fills in. Note that the field name for "keep this VM running" differs from the passthrough section above: raw `kubevirt.io/v1` uses `runStrategy: Always`; the Cozystack `apps.cozystack.io/v1alpha1` wrapper uses `running: true`. Both mean the same thing:

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: vgpu-smoke
  namespace: tenant-example
spec:
  runStrategy: Always
  dataVolumeTemplates:
  - metadata:
      name: vgpu-smoke-root
    spec:
      storage:
        # adjust storageClassName to a class that exists on your cluster;
        # 'replicated' is the same StorageClass used by the passthrough
        # example above on a stock Cozystack tenant.
        storageClassName: replicated
        resources:
          requests:
            storage: 20Gi
      source:
        registry:
          url: docker://quay.io/containerdisks/ubuntu:24.04
  template:
    spec:
      domain:
        cpu:
          cores: 4
        memory:
          guest: 8Gi
        devices:
          disks:
          - name: rootdisk
            disk:
              bus: virtio
          - name: cloudinitdisk
            disk:
              bus: virtio
          interfaces:
          - name: default
            masquerade: {}
          hostDevices:
          - name: gpu0
            deviceName: nvidia.com/L40S-24Q
      networks:
      - name: default
        pod: {}
      volumes:
      - name: rootdisk
        dataVolume:
          name: vgpu-smoke-root
      - name: cloudinitdisk
        cloudInitNoCloud:
          userData: |
            #cloud-config
            # The containerDisks/ubuntu image already provisions an
            # `ubuntu` user; do not redefine it via users: (cloud-init
            # silently no-ops a user redefinition and the SSH key is
            # ignored). Top-level ssh_authorized_keys is added to the
            # default user.
            ssh_authorized_keys:
            - <your ssh public key>
            packages:
            - build-essential
            - dkms
            - linux-headers-generic
            - pkg-config
            write_files:
            - path: /etc/nvidia/ClientConfigToken/client_configuration_token.tok
              # 0744 follows NVIDIA's recommendation in the Licensing
              # User Guide so nvidia-gridd (which does not necessarily
              # run as the file owner) can read it.
              permissions: '0744'
              encoding: b64
              content: <base64 token>
            - path: /etc/nvidia/gridd.conf
              permissions: '0644'
              content: |
                FeatureType=1
```

```bash
kubectl apply -f vgpu-smoke.yaml
```

Once the VM is running and cloud-init has settled, install the **guest** GRID driver from the corresponding `.run` (the `linux-grid` variant, distinct from the host `vgpu-kvm` package — and use the version that currently ships on the NVIDIA Licensing Portal):

```bash
# transfer the .run from the workstation that downloaded it from
# the Licensing Portal — virtctl scp uses the same SSH path as
# virtctl ssh, so it goes through the cluster API server
virtctl scp --namespace tenant-example \
  NVIDIA-Linux-x86_64-<driver-version>-grid.run \
  ubuntu@vm/vgpu-smoke:/tmp/

virtctl ssh --namespace tenant-example ubuntu@vm/vgpu-smoke -- \
  sudo sh /tmp/NVIDIA-Linux-x86_64-<driver-version>-grid.run --dkms --silent

# the .run installs the nvidia-gridd systemd unit but does not
# necessarily start it on first boot; enable it explicitly so the
# license handshake runs without a guest reboot
virtctl ssh --namespace tenant-example ubuntu@vm/vgpu-smoke -- \
  sudo systemctl enable --now nvidia-gridd.service
```

The `--dkms` flag asks the installer to register kernel module sources with DKMS so future kernel updates re-build them automatically. `virtctl scp` and `virtctl ssh` need the VM's namespace explicitly — they default to `default`, not the VM's namespace.

Verify the vGPU is visible:

```console
ubuntu@vgpu-smoke:~$ nvidia-smi
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 595.58.03              Driver Version: 595.58.03      CUDA Version: N/A      |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
|=========================================+========================+======================|
|   0  NVIDIA L40S-24Q                Off |   00000000:0E:00.0 Off |                    0 |
| N/A   N/A    P0            N/A  /  N/A  |      17MiB /  24576MiB |      0%      Default |
+-----------------------------------------+------------------------+----------------------+
```

```bash
nvidia-smi -q | grep 'License Status'
# License Status   : Licensed
```

If the License Status remains `Unlicensed (Unrestricted)` for more than a couple of minutes after `nvidia-gridd` starts, see step 4 above for troubleshooting.

### vGPU Profiles

Each GPU model supports one or more profile families that determine which workload class the partition is licensed for: **`-Q`** (NVIDIA RTX Virtual Workstation, vWS — graphics workloads), **`-A`** (NVIDIA Virtual Compute Server / Compute — CUDA without display), **`-B`** (NVIDIA Virtual PC, vPC — basic VDI). The suffix selects the license type the guest will request; partition sizes vary per GPU and per family — not all combinations are available on all GPUs. The table below lists the `Q` family for NVIDIA L40S; consult NVIDIA's documentation for the full per-GPU matrix:

| Profile | Frame Buffer | Max Instances | Use Case |
| --- | --- | --- | --- |
| L40S-1Q | 1 GB | 48 | Light 3D / VDI |
| L40S-2Q | 2 GB | 24 | Medium 3D / VDI |
| L40S-4Q | 4 GB | 12 | Heavy 3D / VDI |
| L40S-6Q | 6 GB | 8 | Professional 3D |
| L40S-8Q | 8 GB | 6 | AI / ML inference |
| L40S-12Q | 12 GB | 4 | AI / ML training |
| L40S-24Q | 24 GB | 2 | Large AI workloads |
| L40S-48Q | 48 GB | 1 | Full GPU equivalent |

Other GPU families have analogous tables — consult the [NVIDIA Virtual GPU Software Documentation](https://docs.nvidia.com/grid/latest/grid-vgpu-user-guide/) for the full list and the vPC / vCS / Compute variants.

### Open-Source vGPU (Experimental)

NVIDIA is developing open-source vGPU support for the Linux kernel. Once merged, this could enable GPU sharing without a commercial license.

- Status: RFC stage, not merged into mainline kernel
- Supports Ada Lovelace and newer (L4, L40, etc.)
- References: [Phoronix announcement](https://www.phoronix.com/news/NVIDIA-Open-GPU-Virtualization), [kernel patches](https://lore.kernel.org/all/20240922124951.1946072-1-zhiw@nvidia.com/)
