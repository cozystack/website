---
title: "Blockstor: a LINSTOR-compatible storage system for Kubernetes, written from scratch in Go"
slug: "blockstor-linstor-compatible-storage-for-kubernetes"
date: 2026-08-04
author: "Cozystack Team"
description: "The Cozystack team has open-sourced Blockstor: LVM and ZFS backends, DRBD replication, and a LINSTOR-compatible REST API, so existing client tooling keeps working unchanged."
images:
  - "blockstor-announcement.png"
article_types:
  - "announcement"
topics:
  - "storage"
  - "linstor"
  - "drbd"
  - "platform"
---

{{< figure src="blockstor-announcement.png" alt="Blockstor — a free software-defined storage system based on Kubernetes" width="720" >}}

The Cozystack team has open-sourced Blockstor, a control plane for block storage in Kubernetes: LVM and ZFS as backends, replication over DRBD, and a LINSTOR-compatible REST API. The project lives in the cozystack organization and is developed as part of Cozystack, a platform accepted into the CNCF Sandbox. The license is Apache 2.0.

The main thing that makes it worth a look: it is not a fork, and it is not a wrapper. Blockstor is written from scratch in Go, but it speaks the same REST API as LINSTOR — so all the client tooling you already run keeps working without a single change: the `linstor` CLI, linstor-csi, piraeus-operator, and the golinstor library.

## Why Blockstor takes a different approach

LINSTOR is a mature system, and it ran in production in Cozystack for years. We did not hit a functionality ceiling — we hit the model.

The original controller is request-based: for most API calls it goes out to the nodes in real time and polls their state to assemble a response. That has two consequences. First, this design scales poorly. Second, with no reconciliation loop, automatic recovery from failures has to be bolted on from the outside.

Blockstor is built the way Kubernetes operators are normally built: the desired state lives in CRDs, and a set of reconcilers on controller-runtime drives the cluster toward it. Three practical consequences follow:

- No external database to back up and worry about
- No in-memory state to lose when the controller restarts
- No controller-side polling of nodes that can fall behind reality

The satellites watch the API themselves and write the observed state back through Server-Side Apply, using separate field managers. Spec belongs to the controller, Status to the satellite, and that split is enforced strictly.

## What it is made of

Three components, all of them ordinary Kubernetes workloads:

| Component | Role |
|---|---|
| `blockstor-controller` | A Deployment running the controller-runtime reconcilers |
| `blockstor-apiserver` | A stateless, LINSTOR-compatible REST front end, backed by CRDs. This is what `linstor`, CSI, and Piraeus talk to |
| `blockstor-satellite` | A DaemonSet: it brings up the DRBD, LUKS, and STORAGE layers on the node and calls `drbdadm`, `lvs`, `zfs`, and `cryptsetup` |

The objects live in the `blockstor.cozystack.io/v1alpha1` group: Node, StoragePool, ResourceGroup, ResourceDefinition, Resource, Snapshot, PhysicalDevice, and ControllerConfig. The CRDs are designed as a public integration point, with schema-level validation and a safe multi-writer model for Status, so that GitOps tooling and monitoring can work with them directly.

## What already works

- Replicated DRBD volumes on top of LVM, LVM-thin, ZFS, ZFS-thin, and file backends
- A DRBD-free mode — a single replica, diskful or diskless
- LUKS encryption at the volume level; the layers stack as DRBD → LUKS → STORAGE
- Auto-placement with constraints: zones, node properties, and replica spreading
- TieBreaker and quorum policies — one of the most heavily tested parts of the system
- Snapshots: create, roll back, clone, and restore into a new resource
- Snapshot shipping within the cluster using `zfs send/recv` and thin-send-recv
- Online volume resize. Shrinking is disabled by default and requires an explicit `force=true` — here we are deliberately stricter than the original
- Creating pools from physical disks
- Replica rebalancing and migration: automatic evacuation from a departing node, automatic promotion to diskful, and recovery after split-brain
- Skipping the initial sync when a replica is added, by seeding the Generation Identifier. Adding a third replica to a multi-terabyte volume does not turn into a multi-hour resync
- mTLS on the API with hot certificate reload, Prometheus metrics, and images for amd64 and arm64
- RWX — verified by an end-to-end test through linstor-csi and NFS-Ganesha

## What is not there yet

We would rather put this in the announcement than have you discover it on day three.

The following are not implemented, and they return an honest `501 Not Implemented` rather than a silent 404: cross-cluster snapshot shipping, backups and the backup queue, schedules, remote backends such as S3, and the SPDK, NVMe-oF, OpenFlex, and Exos drivers. There is no Helm chart — installation goes through plain manifests. The version is still 0.x.

The list of CLI behaviour differences from the original is maintained in public, along with a register of known issues and a write-up of the csi-sanity tests that fail. Put plainly: the project itself publishes the list of its own gaps.

## Why you can trust this

A storage control plane rewritten from scratch is a claim that needs proof, not promises. Our answer is tests.

The implementation is 94,000 lines. The tests are 170,000 lines of Go and another 46,000 lines of shell. And these are not only unit tests:

- 108 integration tests run the real `linstor` Python client against envtest on every PR
- Contract tests run real `drbdmeta` and `drbdadm` in Docker on top of loopback devices
- 89 end-to-end scenarios run on a Talos and QEMU rig with real DRBD
- 91 CLI matrix cells and 74 replay scenarios cover operator workflows
- A parity harness compares Blockstor's responses against a live upstream LINSTOR and fails CI on any divergence that is not on the accepted list

Release v0.1.11 deserves a separate mention: it reproduced and closed 48 edge cases pulled from the linstor-server bug tracker itself — on a live rig, with the disputed cases settled by checking against a running upstream.

## Compatibility and the legal side

Blockstor returns `1.33.2+git=blockstor` for `linstor controller version` and implements the endpoints that linstor-csi and piraeus-operator actually call. Piraeus connects in external-controller mode — point it at the address of the Blockstor apiserver, and linstor-csi keeps working untouched.

LINSTOR is distributed under the GPL and Blockstor under Apache 2.0, so no sources from the original were used. The project is a clean-room implementation: the compatibility types come from golinstor, an Apache 2.0 library, and no code is copied or generated from GPL sources. This is not a declaration but a checkable rule: on every PR, a license gate runs in CI that keeps GPL, AGPL, LGPL, and SSPL out of the runtime graph — including code generated from a GPL-licensed specification.

And to be direct: LINSTOR, LINBIT, and DRBD are trademarks of LINBIT. Blockstor is an independent project, not affiliated with, endorsed by, or sponsored by LINBIT. We are grateful to LINBIT and to the DRBD, LINSTOR, and Piraeus communities: Blockstor speaks the LINSTOR API deliberately, precisely so that the ecosystem the community built keeps working.

## How to try it

One nice detail for anyone already living on LINSTOR: you can install Blockstor on the same nodes, next to a running LINSTOR. The TCP port ranges and the DRBD minor-number ranges are deliberately kept clear of the upstream ones, so you can try it without shutting anything down.

The hosts need the DRBD 9 kernel module, drbd-utils, lvm2, and cryptsetup; for ZFS, the module and zfsutils-linux. On Talos those are the `siderolabs/drbd` and `siderolabs/zfs` extensions.

```bash
kubectl apply -f config/crd/bases/

# then the manifests from stand/: controller, apiserver, satellite

kubectl -n blockstor-system rollout status deploy/blockstor-controller
kubectl -n blockstor-system rollout status deploy/blockstor-apiserver
kubectl -n blockstor-system rollout status daemonset/blockstor-satellite
```

From there on, it is the ordinary `linstor`, unchanged:

```bash
kubectl -n blockstor-system port-forward deploy/blockstor-apiserver 3370:3370
export LS_CONTROLLERS=http://localhost:3370

linstor node create worker-1 10.0.0.11
linstor physical-storage create-device-pool --pool-name data --storage-pool data zfs worker-1 /dev/sdb
linstor resource-group create mygroup --place-count 3 --storage-pool data
linstor volume-group create mygroup
linstor resource-group spawn mygroup myvolume 10G
linstor resource list
```

In the output you will see two UpToDate diskful replicas and one TieBreaker.

## What is next, and where we would welcome help

Blockstor has already been through the Cozystack end-to-end suite on a three-node rig: PVCs are served through an untouched CSI and untouched StorageClasses, including three-way DRBD replication. But the integration is still a proof of concept — it has proven substitutability, not the default.

A tool for migrating an existing LINSTOR cluster in place is in the works: it moves the metadata into CRDs and adopts existing zvols, LVs, and running DRBD devices with no data copying and no resync, preserving minor numbers, node IDs, ports, and the DRBD shared secret. Where something cannot be carried over without guesswork, the tool refuses to guess and reports it.

The project is young and was written mostly by one person — and that is exactly where outside hands help. These are the areas where help would matter most right now:

- Testing outside Talos — Ubuntu and other distributions have not been checked yet
- A Helm chart — there is not one
- Verifying the pairing with ha-controller — compatibility is claimed but not covered by a test
- Grafana dashboards and alerts for Blockstor metrics
- The hardest and most valuable area — the DRBD kernel layer: filesystem assembly and attachment on the satellite, split-brain, and real synchronization. The project itself names this as its main remaining risk

If you run DRBD in production, the most useful contribution starts with installing Blockstor alongside it and telling us what broke.

Questions, bug reports, and "it doesn't work for me" belong in the repository issues or the chats below. A report on what did not work is worth more right now than a star on GitHub.

## Join the community

- [Blockstor on GitHub](https://github.com/cozystack/blockstor)
- [Cozystack on GitHub](https://github.com/cozystack/cozystack)
- Telegram [group](https://t.me/cozystack)
- Slack [group](https://kubernetes.slack.com/archives/C06L3CPRVN1) (Get invite at [https://slack.kubernetes.io](https://slack.kubernetes.io))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
