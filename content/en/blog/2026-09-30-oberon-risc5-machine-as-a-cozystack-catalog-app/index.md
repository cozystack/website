---
title: "A community catalog brings Niklaus Wirth's Oberon machine to Cozystack as an installable app"
slug: "oberon-risc5-machine-as-a-cozystack-catalog-app"
date: 2026-09-30
author: "Cozystack Team"
description: "A community member added Niklaus Wirth's RISC5 Oberon workstation to Cozystack as a one-click app — using the pluggable-catalog and KubeVirt sidecar mechanisms, with no fork of Cozystack or KubeVirt."
images:
  - "oberon-cozystack-catalog.jpg"
article_types:
  - "news"
topics:
  - "kubevirt"
  - "virtualization"
  - "platform"
  - "community"
---

{{< figure src="oberon-cozystack-catalog.jpg" alt="The Paleocomputing section in the Cozystack application catalog" width="720" >}}

A community contributor has published a pluggable Cozystack catalog that does something Cozystack was never built to do: it runs Niklaus Wirth's RISC5 processor — the tiny teaching CPU Wirth designed for the 2013 edition of Project Oberon — as an ordinary cloud VM. From a tenant's point of view, the 1980s Oberon workstation installs like any other app in the catalog: a short form, or a single `OberonVM` resource, and the machine boots on a VNC console next to the PostgreSQL and Kubernetes instances. The whole thing is open source under Apache 2.0; the QEMU processor model, like QEMU itself, is under the GPL.

What makes it interesting for the platform is that it adds a brand-new machine architecture **without forking either Cozystack or KubeVirt**. It leans entirely on extension points that already exist. A KubeVirt sidecar handler intercepts a perfectly ordinary VM definition and reshapes it into Wirth's machine — swapping the architecture, the emulator, the bootloader and the disk image. libvirt, which won't take an unknown architecture on the machine definition alone, needed a ten-line patch in five places, written so that the list of architectures comes from a data file rather than new code. And the shared virt-launcher image that carries the patched libvirt is applied by a small reconciling component that watches the KubeVirt configuration and backs its change out cleanly if anything looks wrong.

{{< figure src="oberon-in-cozystack-vnc.png" alt="Wirth's Oberon system running as a VM in Cozystack, viewed over VNC" width="720" >}}

The catalog is delivered through the community `cozymarketplace` mechanism (from the design proposals in [cozystack/community](https://github.com/cozystack/community)): a tenant-facing part with the machine, a browser lab and a handbook installs with an ordinary `cozypkg tap` / `cozypkg add`, while the two parts that touch the whole cluster — the boot images and the launcher patch — install only with the administrator's explicit consent. It runs on the two latest KubeVirt releases and on both Intel and Arm servers.

One finding from the write-up is worth flagging for any operator, because it is a property of Cozystack's defaults rather than of this project. Changing the shared virt-launcher image is a cluster-wide action, and with automatic workload updates enabled by default, doing it on a live cluster will trigger a live migration of **every** VM in the cluster. The author hit exactly this — a swap that, sixteen seconds later, began migrating the whole cluster. The catalog component now refuses to make the change while auto-update is on and waits for an explicit opt-in, but the underlying behavior is a good reminder to check `workloadUpdateStrategy` before touching KubeVirt-wide settings anywhere.

This is a community experiment, not part of the standard Cozystack application set, and it is a fine demonstration of how far the pluggable catalog and the KubeVirt sidecar can be pushed. The full technical write-up — nine days of running Wirth's processor in a browser, in QEMU, and in Kubernetes, and measuring what array-bounds checking actually costs — is on the project site at [tym83.github.io/paleocomputing](https://tym83.github.io/paleocomputing/), with all sources in [github.com/tym83/paleocomputing](https://github.com/tym83/paleocomputing).
