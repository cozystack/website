---
title: "Ubuntu Secure Boot: DRBD prerequisites"
linkTitle: "Ubuntu + Secure Boot"
description: "Prepare Ubuntu LTS hosts with UEFI Secure Boot enabled for Cozystack non-Talos installation by pre-installing drbd-dkms from the LINBIT PPA"
weight: 52
---

This page covers a single prerequisite for installing Cozystack on Ubuntu hosts where UEFI Secure Boot is enabled. If your nodes are Talos Linux, or Ubuntu with Secure Boot disabled, you can skip this page — the default piraeus-operator flow handles those cases.

## Why this is needed

Cozystack uses [LINSTOR](https://linbit.com/linstor/) for replicated block storage, which depends on the DRBD 9.x kernel module. The piraeus-operator that ships with Cozystack defaults to **compiling DRBD from source on each node at runtime** and loading the module via `insmod`.

On hosts where UEFI Secure Boot is enabled, the kernel's lockdown subsystem rejects unsigned modules at load time:

```text
insmod: ERROR: could not insert module ./drbd.ko: Key was rejected by service
```

(A preceding `chcon: can't apply partial context to unlabeled file './drbd.ko'` line may also appear when the loader image sets `LB_SELINUX_AS` — that warning is benign and unrelated to the load failure.)

The compiled `.ko` files are not signed against any key the host trusts, so `init_module()` fails. The linstor satellite Pod never reaches `Ready` and Cozystack storage stays broken.

This is common on bare-metal Ubuntu installs and on cloud SKUs that ship with Secure Boot enabled. Stock cloud-VM images on AWS, GCP, and Azure typically ship without Secure Boot enforcement and the default piraeus-operator flow works as-is.

This guide covers Ubuntu LTS only. Debian 12 has the same DRBD-unsigned-module problem under Secure Boot but LINBIT does not publish a Debian PPA — those operators must use LINBIT's customer-portal apt mirror or build and sign drbd-dkms manually. RHEL/SUSE flows (LINBIT-managed RPM repos with pre-signed kmods) are out of scope here.

## Recommended fix: pre-install drbd-dkms on the host

Install the LINBIT-published `drbd-dkms` package on each node **before** deploying Cozystack, then add a `usermode_helper=disabled` modprobe.d drop-in and mask the host-side `drbd.service`. Minimal Ubuntu cloud images do not ship `add-apt-repository`; install `software-properties-common` first if it is missing. The full flow on each node:

1. Add LINBIT PPA, install `drbd-dkms`. The package goes through Ubuntu's standard `shim-signed` + dkms pipeline:
   - On first dkms install with no existing MOK present, Ubuntu's `shim-signed` postinst generates a per-host signing keypair at `/var/lib/shim-signed/mok/MOK.priv` and `/var/lib/shim-signed/mok/MOK.der` (referenced from `/etc/dkms/framework.conf` as `mok_signing_key` / `mok_certificate`).
   - dkms compiles the module against the running kernel and signs the freshly built `.ko` against that key.
   - During `apt-get install`, debconf prompts the operator for an enrollment password; the matching public key is queued for MOK enrollment via `mokutil --import`. **If the install runs non-interactively** (`DEBIAN_FRONTEND=noninteractive`), the prompt is bypassed and the operator must run `mokutil --import /var/lib/shim-signed/mok/MOK.der` manually after the install.
2. Write `/etc/modprobe.d/cozystack-drbd.conf` with `options drbd usermode_helper=disabled`. piraeus-operator's daemonset sets `LB_FAIL_IF_USERMODE_HELPER_NOT_DISABLED=yes` on the loader, so the loader fails on a host-loaded module without that param (see LINBIT/drbd [`entry.sh` line 332](https://github.com/LINBIT/drbd/blob/8c279459a32823b495a2649fc6dafc9fdfac1c7f/docker/entry.sh#L332) and the env wiring in piraeus-operator's [satellite daemonset](https://github.com/piraeusdatastore/piraeus-operator/blob/3bf3e75a142f69534609a6323c88db29150047a2/pkg/resources/satellite/satellite/daemonset.yaml)).
3. `systemctl mask drbd.service`. `drbd-utils` lands on the host transitively as a hard apt dependency of `drbd-dkms` and ships a `drbd.service` unit that would race piraeus-operator's satellite container if accidentally enabled.
4. Write `/etc/modules-load.d/cozystack-drbd.conf` containing `drbd` so `systemd-modules-load.service` loads the module on every boot. Without this file the host depends on whatever (if any) `modules-load.d` entry the `drbd-utils` package ships, which has varied across releases — making it explicit removes the ambiguity and matches the path the companion Ansible playbook writes.
5. **Reboot each node and confirm MOK enrollment at the shim console** (Enroll MOK → View key → Continue → enter the password set during step 1's debconf prompt or via `mokutil --import`). One reboot per node is required for the operator to walk through shim's MOK Manager. This step cannot be automated — it is the design of UEFI Secure Boot.
6. After enrollment, the kernel trusts the signing key and the dkms-built DRBD module loads with the right param.

Once the host has DRBD 9.x loaded with `usermode_helper=disabled`, piraeus-operator's loader detects the host-loaded module on Pod startup and exits cleanly without attempting its own compile and `insmod`. No operator-side configuration is required.

## Automated path: ansible-cozystack

The [`cozystack/ansible-cozystack`](https://github.com/cozystack/ansible-cozystack) collection is being extended to automate the install side of the dance via [PR #39](https://github.com/cozystack/ansible-cozystack/pull/39). When that PR merges, `examples/ubuntu/prepare-ubuntu.yml` will add the LINBIT PPA, install `drbd-dkms`, write `/etc/modprobe.d/cozystack-drbd.conf` with `options drbd usermode_helper=disabled`, mask the host-side `drbd.service`, and try to load the module immediately. Variables to know once the PR lands:

- `cozystack_enable_drbd_dkms` (default `true`) — set `false` on Talos hosts or where Secure Boot is disabled and you prefer the in-cluster compile path.
- `cozystack_drbd_ppa` (default `ppa:linbit/linbit-drbd9-stack`) — point at a Launchpad mirror of the LINBIT archive.
- `cozystack_drbd_supported_releases` (default `[jammy, noble]`) — extend in inventory once LINBIT publishes for a new Ubuntu series.

Until that PR merges, follow the manual path below. The two flows produce the same end state on the host.

After the playbook (or the manual steps) completes, **reboot each node** and confirm MOK enrollment at the shim console. Then re-run the playbook on the same nodes; the second run should report `changed=0` and the modprobe will succeed.

{{% alert color="warning" %}}
**MOK enrollment is interactive and per-node**. The operator must access the console (physical, IPMI, or KVM) of each node on the next reboot and walk through shim's MOK Manager. There is no Kubernetes-level workaround — kernel module signing under Secure Boot is a host-firmware concern.
{{% /alert %}}

## Manual path

For operators who do not use Ansible, the equivalent steps on each Ubuntu LTS node are:

```bash
# 1. Install add-apt-repository (not present on minimal cloud images).
sudo apt-get update
sudo apt-get install --yes software-properties-common

# 2. Add LINBIT PPA and install drbd-dkms. During the install, debconf
#    prompts for a one-time MOK enrollment password — choose any
#    password you can re-enter at the shim console after reboot.
sudo add-apt-repository --yes ppa:linbit/linbit-drbd9-stack
sudo apt-get install --yes drbd-dkms

# 3. Configure the required module parameter.
sudo tee /etc/modprobe.d/cozystack-drbd.conf <<'EOF'
options drbd usermode_helper=disabled
EOF

# 4. Mask the host drbd.service so it cannot race piraeus-operator.
sudo systemctl mask drbd.service

# 5. Persist the module load on boot. The drbd-utils package's own
#    /lib/modules-load.d/ entry has varied across releases; an explicit
#    /etc/ entry overrides anything in /lib/ and removes the ambiguity.
echo drbd | sudo tee /etc/modules-load.d/cozystack-drbd.conf

# 6. Reboot. At the shim MOK Manager menu, choose:
#    Enroll MOK -> View key -> Continue -> Yes -> enter the password
#    you set at the debconf prompt during step 2.
sudo reboot
```

After the reboot, verify the module loaded with the right param:

```bash
cat /sys/module/drbd/parameters/usermode_helper
# expected: disabled
```

Then deploy Cozystack as usual. The piraeus-operator loader will detect the host-loaded DRBD and exit cleanly.

## What happens at deploy time

When piraeus-operator's satellite Pod starts on a node, its `drbd-module-loader` initContainer runs [LINBIT/drbd's `entry.sh`](https://github.com/LINBIT/drbd/blob/master/docker/entry.sh). Lines 328–339 short-circuit the compile + insmod path when DRBD is already loaded on the host:

```sh
if grep -q '^drbd ' /proc/modules; then
    echo "DRBD module is already loaded"
    [[ $LB_FAIL_IF_USERMODE_HELPER_NOT_DISABLED == yes ]] \
        && ! grep -qw disabled /sys/module/drbd/parameters/usermode_helper \
        && die "..."
    drbd_matches_min_version "$LB_DRBD_MIN_LOADED_VERSION" || die "..."
    exit 0
fi
```

Two preconditions are checked:

1. The module must be loaded with `usermode_helper=disabled`. The modprobe.d drop-in above takes care of this.
2. The loaded version must satisfy `LB_DRBD_MIN_LOADED_VERSION`. piraeus-operator's daemonset sets it to `9`. LINBIT's `drbd-dkms` ships DRBD 9.x, so this is automatic.

Both conditions met → `exit 0` → satellite Pod proceeds. No operator-side change to piraeus-operator or LinstorSatelliteConfiguration is needed.

## Alternatives

- **Talos Linux** ([guide]({{% ref "/docs/v1.5/guides/talos" %}})) ships pre-signed DRBD modules in its system extensions and has none of these problems. Recommended for new deployments where you do not need a custom Linux distro.
- **Disable Secure Boot** in the host's UEFI firmware. The default in-cluster compile path then works without modification. Operationally undesirable for fleets where Secure Boot is part of the security baseline, but a valid escape hatch.
- **Build and sign drbd-dkms manually** against your own enterprise CA. This is what production environments with their own MOK / shim signing infrastructure already do; it is out of scope for this guide.

## Troubleshooting

**`modprobe drbd` returns `Key was rejected by service` after dkms install** — the dkms-generated MOK key is queued but not yet enrolled. Reboot the node and confirm enrollment at the shim console (Enroll MOK → View key → Continue → dkms password). Re-run modprobe.

**`cat /sys/module/drbd/parameters/usermode_helper` is not `disabled`** — the modprobe.d drop-in is missing or the module was loaded before it was written. `sudo rmmod drbd && sudo modprobe drbd` after the drop-in is in place, or reboot.

**piraeus-operator loader Pod logs `Could not load DRBD kernel modules`** even after host install — check `LB_DRBD_MIN_LOADED_VERSION` via `kubectl --namespace cozy-linstor describe pod --selector app.kubernetes.io/component=linstor-satellite` and `cat /proc/drbd` on the host. The host module must be at least the loader's required minimum (`9` per piraeus-operator's daemonset). LINBIT PPA `drbd-dkms` is 9.x so this is rarely the issue.

**Ubuntu 26.04+ or interim releases (Oracular 24.10, Plucky 25.04)** — LINBIT's PPA publishes `drbd-dkms` only for the LTS series LINBIT keeps current. Check [the PPA detail page](https://launchpad.net/~linbit/+archive/ubuntu/linbit-drbd9-stack) for the current series list. On unsupported releases the PPA add fails on a 404 Release file. Build and sign drbd-dkms manually, downgrade to a supported LTS, or wait for LINBIT to publish for your release. Ansible operators can extend `cozystack_drbd_supported_releases` once that happens.
