---
title: "GPU Passthrough Fails on a Host with a Pre-installed NVIDIA Driver"
linkTitle: "GPU Operator: host driver"
description: "Why vfio-manager refuses to bind vfio-pci when the node already has an apt-installed NVIDIA driver, and how to recover the node."
weight: 30
---

The `default` (passthrough) variant of the `cozystack.gpu-operator` package assumes the GPU is **owned by the host kernel's `vfio-pci` driver and nothing else**. On a node that already has the NVIDIA driver installed through the distro package manager, the operator detects it, declines to touch it, and the passthrough setup never completes.

Verified 2026-05-28 against the `gpu-operator` chart v26.3.1 with `nvcr.io/nvidia/cloud-native/k8s-driver-manager:v0.10.0`, on an Ubuntu 24.04 host carrying `nvidia-driver-580-open` 580.82.07.

{{< note >}}

If you want GPUs in **containers** rather than in VMs, you do not need this recovery at all — use the [`container` variant](/docs/next/operations/gpu-container-workloads/), which is designed for exactly this host shape and keeps the host driver in place.

{{< /note >}}

## Symptom

`kubectl get pods -n cozy-gpu-operator` shows `nvidia-vfio-manager-*` stuck in `Init:Error` or `Init:CrashLoopBackOff` — the init container exits non-zero after detecting the host driver, so kubelet keeps restarting it.

Its log shows it skipped the bind step:

```text
Host driver detected: 580.82.07
NVIDIA GPU driver is already pre-installed on the node,
  disabling the containerized driver
Labeling node <NODE> with nvidia.com/gpu.deploy.driver=pre-installed
```

`nvidia-sandbox-validator` then crashloops:

```text
Error: error validating vfio-pci driver installation:
  device not bound to 'vfio-pci'; device: 0000:18:00.0 driver: 'nvidia'
```

`lspci -nnk -d 10de:` still shows `Kernel driver in use: nvidia` on every target GPU, the node carries `nvidia.com/gpu.deploy.driver=pre-installed`, and this reports `{}` — no GPU resource was registered:

```bash
kubectl get node <NODE> -o json | jq '.status.allocatable | with_entries(select(.key | startswith("nvidia.com/")))'
```

## Why it happens

The chart's `vfio-manager` DaemonSet runs the upstream NVIDIA `k8s-driver-manager` init container with the `uninstall_driver` subcommand. That path calls the Go method `(*DriverManager).isHostDriver`, which runs `chroot /host nvidia-smi --query-gpu=driver_version --format=csv,noheader` and treats any non-empty stdout as "host driver present". File existence is not pre-tested — if `nvidia-smi` is missing the chroot exec errors and `isHostDriver` returns false, which is the intended path on a clean host: the operator then proceeds with the uninstall flow and `vfio-manager` binds `vfio-pci` as designed.

On a positive detection the binary logs `Host driver detected: <ver>`, labels the node `nvidia.com/gpu.deploy.driver=pre-installed`, and exits.

**`FORCE_REINSTALL` does not bypass this.** `k8s-driver-manager` v0.10.0 exposes a `FORCE_REINSTALL` / `--force-reinstall` env and flag pair, but it gates a later "same-config already loaded" branch inside `uninstallDriver`, not the `isHostDriver` short-circuit at the top. Operators who set it and expect a bypass will report a false bug. There is currently no opt-out for the `isHostDriver` guard itself.

## Recovery: clean the host

Purge the NVIDIA host stack and blacklist the kernel modules so the host never re-claims the GPU.

Two pitfalls to avoid. `apt autoremove` is dangerous here because the `nvidia-` prefix is shared with NVIDIA DOCA / Mellanox / InfiniBand userspace, so a blanket autoremove can take RDMA out on a converged GPU plus RDMA host. And a hardcoded `apt purge 'nvidia-*' 'cuda-*'` pattern list is fragile — `apt` treats `*` as a cache-wide regex and **aborts the entire transaction, purging nothing**, if any pattern matches nothing in the cache (for example `cuda-*` on a host without NVIDIA's CUDA repo). Build the list from what is actually installed instead:

```bash
# dpkg-query patterns are true globs over INSTALLED packages: no
# zero-match abort (unlike apt's cache-wide regex) and no accidental
# substring over-match. List first, then review before purging.
dpkg-query -W -f '${Package}\n' 'nvidia-*' 'libnvidia-*' 'cuda-*' 2>/dev/null
```

Review the list before purging:

- `nvidia-dkms-*` and `nvidia-kernel-*` are the load-bearing kernel pieces — without removing them DKMS rebuilds `nvidia.ko` on the next reboot and the blacklist below is bypassed by any explicit `modprobe`.
- On a **converged GPU plus RDMA host**, drop any `libnvidia-*` that belong to NVIDIA DOCA / Mellanox OFED — purging those breaks RDMA.
- If the list is **empty**, the driver was installed with NVIDIA's `.run` installer rather than apt — run `sudo nvidia-uninstall` instead of the purge below.

Then purge the reviewed list, blacklist the modules, and rebuild the initramfs:

```bash
# Replace with the packages you kept from the list above.
sudo apt purge nvidia-driver-580-open nvidia-dkms-580-open <...>

sudo tee /etc/modprobe.d/blacklist-nvidia.conf > /dev/null <<'EOF'
blacklist nouveau
blacklist nvidia
blacklist nvidia_drm
blacklist nvidia_modeset
blacklist nvidia_uvm
blacklist nvidia_peermem
EOF

# -k all rebuilds EVERY installed kernel's initramfs (plain -u touches
# only the running kernel), so a just-upgraded kernel also boots with
# the blacklist and cannot re-claim the GPU.
sudo update-initramfs -u -k all
sudo reboot
```

## Confirm the host is clean

The init container exits non-zero after detecting a host driver, so both DaemonSet pods sit in `Init:CrashLoopBackOff` and **will retry on their own** — deleting them just skips the up-to-five-minute backoff window.

```bash
# Should print nothing.
lsmod | grep -E '^(nvidia|nouveau)'

# command -v matches what isHostDriver does (PATH lookup inside the
# chroot), so it also catches /usr/local/bin/nvidia-smi left by a .run
# or CUDA-toolkit install. Prints "ok: gone" on success.
command -v nvidia-smi >/dev/null && echo "STILL PRESENT — purge incomplete" || echo "ok: gone"

# A leftover DKMS module rebuilds nvidia.ko on the next kernel update
# and an explicit modprobe bypasses the blacklist — should print nothing.
dkms status | grep -i nvidia

# Skip the CrashLoopBackOff backoff window by deleting the stuck pods.
# The DaemonSet labels are operator-managed and not stable across
# gpu-operator versions, so delete by name pattern — anchored so the
# match is the two DaemonSets and nothing else.
kubectl -n cozy-gpu-operator get pods -o name \
  | grep -E '^pod/(nvidia-vfio-manager|nvidia-sandbox-validator)-' \
  | xargs -r kubectl -n cozy-gpu-operator delete
```

Within a couple of minutes `vfio-manager` should bind every target GPU to `vfio-pci` and the node's `allocatable` will gain the registered resource:

```bash
lspci -nnk -d 10de: | grep 'Kernel driver in use'
# Kernel driver in use: vfio-pci

kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.status.allocatable}{"\n"}{end}' | grep nvidia.com
```

## Clear the leftover label

One label is **not** cleaned up automatically. The init container set `nvidia.com/gpu.deploy.driver=pre-installed`, and the operator's success path restores only the operand labels — `rescheduleGPUOperatorComponents` in `k8s-driver-manager` v0.10.0 touches the validator, toolkit and device-plugin labels, not `deploy.driver`. So the node keeps `pre-installed` indefinitely: it is the same label the Symptom section uses as evidence, and it would disable the containerized-driver DaemonSet if the node later switches to a container workload.

```bash
# Nothing on the success path resets this label; clear it so it does not
# mislead future debugging or block a later container-workload switch.
kubectl label node <NODE> nvidia.com/gpu.deploy.driver-
```

## Known limitation

The skip-on-pre-installed behaviour lives in the upstream [`NVIDIA/k8s-driver-manager`](https://github.com/NVIDIA/k8s-driver-manager) Go binary at `cmd/driver-manager/main.go`: `(*DriverManager).isHostDriver` is called from `(*DriverManager).uninstallDriver` and has no in-band opt-out in `:v0.10.0`.

Hosts that need to keep the NVIDIA host driver installed for non-Kubernetes workloads therefore cannot share the same GPU with the passthrough variant. Two paths out:

- **Use the [`container` variant](/docs/next/operations/gpu-container-workloads/)** if the workloads can be containers rather than VMs. It targets the apt-installed-driver host shape and exposes GPUs to pods without unbinding the host driver, so no purge is needed.
- **Upstream override** — an env-var override of `isHostDriver` is the only structural fix that would let the passthrough variant coexist with a host driver. Requested in [NVIDIA/k8s-driver-manager#191](https://github.com/NVIDIA/k8s-driver-manager/issues/191), still open.

Talos is unaffected: the Talos image ships only the `vfio-pci` extension and no host NVIDIA stack, so the clean-host check passes trivially. This page applies to distributions where you installed the host driver yourself — typically Ubuntu, Debian or RHEL with `apt install nvidia-driver-*` or the equivalent.
