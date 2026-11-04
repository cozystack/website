---
title: "vGPU guest licensing"
description: "Prepare platform-licensed Linux and Windows guests, connect them to NVIDIA licensing, and plan rotation."
weight: 45
---

This guide describes the unreleased GPU class license-delivery contract and reference guest assets. It does not establish that a particular guest image, GPU, driver or license server has passed hardware validation. Complete the [acceptance checklist](#guest-acceptance-checklist) for the versions you deploy.

## Choose the licensing mode

A hoster-licensed vGPU class has a `license`: the name of the hoster's source Secret and a `featureType` of `1` (default) or `4`. The GPU controller copies its token into entitled tenant namespaces. The VMI webhook attaches the class's copy as a disk labelled `GPULICENSE`. The disk contains `client_configuration_token.tok` and `gridd.conf`; it is not a boot disk.

A BYOL class has no `license`. Its tenant configures licensing inside the guest and still needs vGPU entitlement. **Do not install the reference unit or startup task in a BYOL image.** Without the platform disk, Linux selects an empty managed token directory and Windows clears the default token folder. These references do not support switching one image between platform licensing and BYOL.

The hoster's NVIDIA entitlement is the default for licensed classes. Before distributing an image containing an NVIDIA driver, check the applicable distribution terms and restrict access where those terms require it. These downloads contain no NVIDIA driver, proprietary binary or token.

## Platform preparation

1. Enable root entitlement with platform `gpu.vgpu: true`; it defaults to `false`. Grant `gpu.vgpu` on each child Tenant through its parent's administrator. Every ancestor must be entitled. The effective namespace label is `namespace.cozystack.io/vgpu: "true"`. Entitlement is separate from GPU quota.
2. Define the hoster's `GPUClass` catalog and source license Secrets. Use class entries in VMInstance or KubernetesNodes to select a licensed offer. Raw `name` entries remain the compatibility path; they do not opt into class-based licensing.
3. Configure platform `gpu.resourceNames` for GPU resource names in the deployment. See the [platform reference]({{% ref "/docs/next/operations/configuration/platform-package" %}}).
4. Confirm that the controller created `gpuclass-<class>-license` in the entitled namespace. Inspect names, keys and conditions, not Secret payloads. The class reports `LicenseSecretMissing` if its source Secret is missing or lacks the token key; existing copies are retained in that case. A zero-length token is not useful guest media.

A class-based vGPU start without effective entitlement is refused. When a required license copy does not exist, the launcher waits in `ContainerCreating` with a `FailedMount` event naming the missing Secret and the VM shows `Starting`; it does not deliberately boot without that copy. Check the class condition and source Secret first. Neither a pending launcher nor the presence of the disk proves that the guest has obtained an NVIDIA license.

The delivery contract is [gpudevice §6](https://github.com/cozystack/community/blob/026c4190c9c1d8d0e458e2d60bb621c2b4ecd6b9/design-proposals/gpudevice/README.md#6-vgpu-entitlement-and-license-delivery), with [decision 0018](https://github.com/cozystack/community/blob/026c4190c9c1d8d0e458e2d60bb621c2b4ecd6b9/design-proposals/gpudevice/decisions/0018-a-vgpu-license-reaches-each-vm-as-a-secret-volume.md). Guest responsibilities follow the accepted [vGPU VM licensing design](https://github.com/cozystack/community/blob/024d8b9133520a17e6610271bed7ad78b0b3edfa/design-proposals/vgpu-vms/README.md).

## Download one reference revision

| Asset | Download |
| --- | --- |
| Linux script | [cozystack-vgpu-license.sh](/examples/vgpu-guest/v1/linux/cozystack-vgpu-license.sh) |
| Linux oneshot | [cozystack-vgpu-license.service](/examples/vgpu-guest/v1/linux/cozystack-vgpu-license.service) |
| NVIDIA client drop-in | [cozystack-vgpu-license.conf](/examples/vgpu-guest/v1/linux/nvidia-gridd.service.d/cozystack-vgpu-license.conf) |
| Windows script | [Set-CozystackVgpuLicense.ps1](/examples/vgpu-guest/v1/windows/Set-CozystackVgpuLicense.ps1) |
| Checksums | [SHA256SUMS](/examples/vgpu-guest/v1/SHA256SUMS) |

`v1` names the reference contract, not a Cozystack release or an immutable file revision. For reproducible installation, select a reviewed **full website commit SHA** and fetch every file and its checksum manifest from that same commit. Review and authenticate the selected commit through your image-build process; downloading a checksum beside a file is not independent authentication. Do not pipe downloads into a shell.

On the Linux image-build machine, in a new empty directory:

```bash
REV='<FULL_REVIEWED_WEBSITE_COMMIT_SHA>'
BASE="https://raw.githubusercontent.com/cozystack/website/${REV}/static/examples/vgpu-guest/v1"
for FILE in linux/cozystack-vgpu-license.sh linux/cozystack-vgpu-license.service linux/nvidia-gridd.service.d/cozystack-vgpu-license.conf windows/Set-CozystackVgpuLicense.ps1 SHA256SUMS; do
    mkdir --parents "$(dirname "$FILE")"
    curl --fail --show-error --location --output "$FILE" "${BASE}/${FILE}"
done
sha256sum --check SHA256SUMS
```

For a Windows build, download the same revision's script and manifest before installation. Verify the Windows entry without executing the script:

```powershell
$Revision = '<FULL_REVIEWED_WEBSITE_COMMIT_SHA>'
$Base = "https://raw.githubusercontent.com/cozystack/website/$Revision/static/examples/vgpu-guest/v1"
Invoke-WebRequest -Uri "$Base/windows/Set-CozystackVgpuLicense.ps1" -OutFile './Set-CozystackVgpuLicense.ps1'
Invoke-WebRequest -Uri "$Base/SHA256SUMS" -OutFile './SHA256SUMS'
$Entry = @(Get-Content -LiteralPath './SHA256SUMS' | Where-Object { $_ -match '^[a-f0-9]{64}  windows/Set-CozystackVgpuLicense.ps1$' })
if ($Entry.Count -ne 1) { throw 'Missing or ambiguous checksum' }
$Expected = $Entry[0].Substring(0, 64)
if ((Get-FileHash -LiteralPath './Set-CozystackVgpuLicense.ps1' -Algorithm SHA256).Hash -ne $Expected) { throw 'Checksum mismatch' }
```

## Linux image installation

Use a systemd-based image with the NVIDIA guest driver and its `nvidia-gridd.service` installed. Runtime prerequisites are POSIX `/bin/sh`, `id`, `find`, `mkdir`, `rmdir`, `rm`, `cp`, `mv`, `chmod`, `od` and `awk`; util-linux `lsblk`, `blkid`, `findmnt`, `mount` and `umount`; and systemd's `udevadm`. Python is an offline test dependency only. The script uses POSIX utility syntax where no portable long option exists and util-linux long options for block and mount operations; BusyBox compatibility is not claimed. Verify the selected executables and option support in the actual guest image, including `findmnt`'s `ID` and `MAJ:MIN` columns.

`/run/cozystack-vgpu-license/token` and its private sibling `.stage` must share one `tmpfs` or `ramfs` mount. The script verifies the actual token filesystem and staging mount identity, not just `/run`'s usual backing. Configuration staging is private and on the same mount as `/etc/nvidia/gridd.conf`. The config directory must be writable at client startup, including on immutable images. Configure these paths in the image; the script does not install packages or create a memory mount.

Execution is serialized by systemd, with root-owned directories that are not writable by other users. Do not invoke the script manually alongside the unit or another root config writer. Path checks and rename do not protect against concurrent root pathname or mount replacement. Token and config publication each use a completed same-filesystem rename; they are not a two-file transaction. The required service dependency keeps the client from reading intermediate state.

Run these commands as root in the image build, from the verified download directory, with the client stopped:

```bash
systemctl stop nvidia-gridd.service
install --mode=0755 linux/cozystack-vgpu-license.sh /usr/local/sbin/cozystack-vgpu-license
install --mode=0644 linux/cozystack-vgpu-license.service /etc/systemd/system/cozystack-vgpu-license.service
install --directory --mode=0755 /etc/systemd/system/nvidia-gridd.service.d
install --mode=0644 linux/nvidia-gridd.service.d/cozystack-vgpu-license.conf /etc/systemd/system/nvidia-gridd.service.d/cozystack-vgpu-license.conf
systemctl daemon-reload
systemctl enable nvidia-gridd.service
```

The oneshot is pulled in by the client's `Requires=` and `After=` drop-in; it has no boot-target enablement. Do not add a `RequiredBy=` boot target. A failed preparation blocks **the licensing client, not VM boot**. Installing these files into an already-running licensed VM does not demonstrate first-boot ordering. Stop the client before installation and validate a fresh boot of the resulting image.

At each client start or restart the script first removes old files only from its managed token directory, then sets `ClientConfigTokenPath=/run/cozystack-vgpu-license/token`. It waits up to 10 seconds for queued udev events with `udevadm settle`, then enumerates labels with `lsblk`. This requires a working udev database and complete block-device visibility in the guest. A successful inventory without a candidate or label link is the reference's no-media case: preparation succeeds with an empty directory and preserves `FeatureType`. Blank or encrypted data disks with other labels do not prevent this. A discovery timeout or command failure, stale label link, multiple candidates, or a failed fresh `blkid --probe` of a candidate is an explicit error, not no-media. In particular, probe exit status 2 does not prove absence. This is ordinary systemd/udev discovery, not an independent scan proving that every raw superblock lacks the label.

With one confirmed `GPULICENSE`, the script mounts read-only with `nodev,nosuid,noexec` and verifies the exact mountpoint and source device identity. It validates a single `FeatureType=1` or `FeatureType=4` and copies only the nonempty regular, single-link token file. Media `gridd.conf` must be ASCII text with LF or CRLF records; duplicate active `FeatureType` assignments, even identical ones, fail. The parser never executes configuration, trusts a media-supplied token path, or interprets the token format: token bytes are copied unchanged, including binary bytes. Structural checks cannot establish NVIDIA token validity.

The class-based VMI integration permits vGPUs from one class per VM and attaches one license disk, including when requesting multiple GPUs of that class. The guest reference rejects multiple `GPULICENSE` devices instead of choosing a token arbitrarily.

Missing, empty, symlinked, nonregular or ambiguous media fails explicitly after stale managed-token cleanup. Unrelated local `gridd.conf` records, including UTF-8 comments, retain their bytes under `LC_ALL=C`; a missing final newline is added. Local text may contain tabs and LF/CRLF line endings but not NUL or other control bytes. Active exact managed-key assignments are replaced when importing a profile, without changing similarly named keys. The default `/etc/nvidia/ClientConfigToken` directory is not deleted or used. Existing configuration permissions are preserved; a new config is `0644`, runtime directories are root-owned `0755`, private staging is `0700` and the token is root-owned `0744`, following NVIDIA's documented mode. The token directory holds no config or lock file. The guest administrator and the licensing service can read the token; this is not root-only storage.

The script unmounts only media it mounted. An occupied mountpoint, unsafe managed path, cleanup failure, non-memory backing, copy failure or unmount failure is an error. It never deliberately writes token bytes to the root disk or a disk-backed temporary file. Memory-backed does not mean that bytes can never reach persistent storage: [tmpfs can swap](https://docs.kernel.org/filesystems/tmpfs.html), and hibernation, core dumps and memory snapshots can capture them. A strict no-disk guarantee requires a separately verified image/operator policy for all those mechanisms; the script does not disable them. It also cannot prevent a guest administrator from copying a token.

## Windows image installation

Use the NVIDIA default token directory; custom registry token paths are outside this reference. The script does not import the disk's `gridd.conf` or write `FeatureType` into the registry. Confirm that your driver, licensing settings and certificate trust are valid before preparing the image.

Install the verified script as an administrator, with a root-owned equivalent Windows ACL: SYSTEM and Administrators may modify it; ordinary users may not. Configure script signing and execution policy through your image's normal policy. Do not weaken execution policy to run this reference. For example, after placing the verified script at `C:\ProgramData\Cozystack\Set-CozystackVgpuLicense.ps1` and applying the required signature and ACL:

```powershell
$Script = 'C:\ProgramData\Cozystack\Set-CozystackVgpuLicense.ps1'
$PowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument "-NoProfile -NonInteractive -File `"$Script`""
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName 'Cozystack-vGPU-License' -Action $Action -Trigger $Trigger -Principal $Principal -Force
```

The task uses the Windows PowerShell executable supplied with Windows; PowerShell 7 is not a guest prerequisite.

**An AtStartup task does not guarantee execution before `NvDisplayContainer`.** The service may already have read a persistent token before cleanup. Replacing the named task is idempotent and needs no user logon, but neither registration nor mock tests prove real boot ordering or revocation. This reference makes no Linux-equivalent startup guarantee on Windows.

On every invocation, including without media, the script clears the contents of `%SystemDrive%\Program Files\NVIDIA Corporation\vGPU Licensing\ClientConfigToken`. It creates a missing directory, rejects unsafe directory/reparse entries, optionally copies the single media token, and restarts `NvDisplayContainer`. Invalid media or a failed copy leaves no new token after successful cleanup, restarts the client and then reports failure. Cleanup failures and service failures are errors, not successful licensing. Monitor the task's result through your image operations; do not record token payloads in transcripts or error reports.

## License server connectivity and driver compatibility

The hoster chooses CLS or DLS and DLS placement, including a management cluster. From the guest, verify DNS resolution, routing, TLS trust and access to the endpoints named by its token. Check the actual DLS deployment's listening ports and the client's requirements in NLS §2.4; do not use a remembered port list as an allow-list. An in-cluster DLS may need explicit tenant network-policy exceptions under the installed CNI. Current isolation defaults are not an architectural prohibition on that placement.

If acquisition or renewal fails, check the guest client logs, available licenses, endpoint reachability and guest configuration. Inspect `nvidia-smi -q` for license status with the product's enforcement mode in mind: it is not independently a server-side lease audit. A connectivity fix may need a client restart; a platform token change needs a new VMI. NVIDIA's release-specific grace and degradation rules apply. A recovered guest can regain full capability, although applications started while degraded may require restarting.

Before upgrading host vGPU Manager, check every guest driver against the applicable release's compatibility table. NVIDIA AI Enterprise and NVIDIA vGPU software have different release lines; do not compare their version numbers as if they were one product. An entitled tenant can update a compatible driver **inside the guest**. Recreating the VM from an updated image is an alternative, not a requirement. Confirm NVIDIA support for the actual host/guest/compute combination and distribution rights before offering driver-bearing images.

## Usage, rotation and revocation

Platform usage records describe GPU use per tenant while launcher pods exist. They are not active license counts: Cozystack does not query the license server. A stopped VM can retain a lease until expiry, and an Offline Lease can survive a clean shutdown. Reconcile tenant usage and server leases in the hoster's billing process.

The accepted rotation procedure moves to a new allocation or license server instance, replaces the source Secret token and restarts each VMI. An OS reboot inside the same VMI does not refresh its Secret disk. Do not assume that editing a Secret updates a running guest. Plan spare capacity on the new allocation, a restart deadline, and when to disable leasing on the old allocation. Check the configured maximum lease duration: disabling leasing does not immediately erase existing leases.

A token's expiry is distinct from a lease's expiry. NLS 4.0.0 documents a default token expiry of 12 years and a DLS no-expiry option (§4.4); choose an explicit lifetime compatible with deployed drivers. Generating a replacement token alone is not revocation. The guide documents no method to revoke an individual token before expiry. Before recommending same-instance DLS allocation rotation operationally, verify that disabling the old allocation prevents its token from obtaining a new license; that live check is not supplied by these scripts.

Manual release frees a lease, not the ability to request another one with a still-served token. NLS §4.9 documents release limits; check the limit shown by your actual CLS/DLS before use rather than relying on a fixed number here. Clearing platform entitlement blocks subsequent class-based starts and removes namespace copies; running guests keep running and may renew while their allocation serves them. Immediate cut-off also requires stopping the affected vGPU VMs and addressing copied-token reuse through the server-side rotation procedure. One class token is shared across entitled namespaces, not a per-tenant revocation mechanism.

## Security

Do not put platform tokens in golden images, cloud-init, bootstrap data, chart values, examples, CI fixtures or diagnostic bundles. Build from a token-free source image: installing this reference does not scrub old tokens from a previous image, cloud-init data or snapshots. Treat previously distributed tokens as exposed and include them in the rotation plan. An entitled guest administrator can read and retain its token by design. Memory-backed Linux placement limits ordinary root-disk persistence, not deliberate copying or memory capture.

On Windows the token persists on the system disk and can enter snapshots, clones and exports. The licensing service may use a previous token before the startup task runs. Cleanup and restart prove neither immediate lease release nor token revocation, and they do not provide Linux-equivalent stale-token protection. BYOL credentials remain tenant-owned and must not be exposed to these cleanup references.

## Guest acceptance checklist

Offline tests execute the canonical Linux script in a synthetic filesystem with stubbed OS commands, check Linux unit dependency structure, and exercise the Windows script under Pester with mocked volume and service calls. They do not access a GPU, NVIDIA binary, cluster, real token or DLS/CLS. Windows mocks do not prove loaded-token removal, licensing state or real boot order.

Run each checklist separately on disposable guests with permission to use the driver, GPU and license. Record the reference commit, guest OS, systemd/Windows, driver and license-server versions, sanitized operation order and observed license state. Never save token bytes, Secret dumps, private endpoints or raw transcripts. Keep timestamps with their source timezone and the operator's local timezone.

### Linux

- [ ] First boot with media: confirm a valid NVIDIA lease, memory backing, token-only directory and modes, merged vendor config, and journal ordering before the real licensing client.
- [ ] New VMI without media: confirm empty managed storage, no default-path fallback and an otherwise bootable VM.
- [ ] Malformed media: confirm an explicit preparation error and a blocked client, without blocking VM boot.
- [ ] Rotate synthetic-labelled token A to token B through a new VMI and observe actual lease behaviour without exporting token contents.
- [ ] Test unreachable endpoint and recovery, then a denied class-based start without entitlement.
- [ ] Check guest root disk, swap and snapshot policy for unintended token persistence.

### Windows

- [ ] First boot with media: observe the scheduled task, folder contents and real licensing result.
- [ ] New VMI without media and a stale-token fixture: observe cleanup and the real task/service timeline, including a service that already started. Do not infer pre-service ordering.
- [ ] Malformed media and copy/cleanup/restart failures: observe reported errors and resulting folder/service state.
- [ ] Rotate A to B through a new VMI; observe actual lease lifecycle, unreachable endpoint and recovery, and denied starts without entitlement.
- [ ] Review snapshots, clones and exports for persistent token exposure.

Claims about immediate revocation require additional real-server observations: release/renewal, old-token reuse, configured expiry and maximum-lease boundaries. A successful script run or client restart is insufficient evidence.

## Sources and version context

Vendor client operations were checked on 9 November 2026 against the [NVIDIA License System User Guide](https://docs.nvidia.com/license-system/latest/nvidia-license-system-user-guide/index.html), whose page metadata identifies **NLS 4.0.0**, last updated 19 October 2026. Sections §5.1.1, §5.1.2 and §5.1.3.2 document the Windows directory/service, Linux token mode, custom token directory and token-only requirement. The `latest` URL moves; recheck these facts when changing deployed versions.

For product-specific enforcement and compatibility, use the deployed release's [NVIDIA vGPU licensing guide](https://docs.nvidia.com/vgpu/latest/grid-licensing-user-guide/), [Linux/KVM release notes](https://docs.nvidia.com/vgpu/latest/grid-vgpu-release-notes-generic-linux-kvm/), and [NVIDIA AI Enterprise documentation](https://docs.nvidia.com/ai-enterprise/). This reference does not substitute an old product's grace-period numbers or compatibility table for the release you run.
