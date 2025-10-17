---
title: "What’s New in Cozystack v0.17"
slug: what-s-new-in-cozystack-v0-17
date: 2024-10-24
author: "Timur Tukaev"
description: "This update mainly focuses on enhancing the platform’s virtualization features, while also introducing several other improvements."
---

### What’s New in Cozystack v0.17: Windows on VMs, VM image upload app, and web interface for S3 buckets

This update mainly focuses on enhancing the platform’s virtualization features, while also introducing several other improvements.

> Today marks the release of an updated version of the free PaaS system, Cozystack. Built on Kubernetes, Cozystack consists of numerous open technologies and provides all the essential tools for running managed services on your own hardware. The platform is distributed under the Apache 2.0 license.

> Cozystack leverages **Talos Linux** as its foundation, **LINSTOR** for storage, **KubeVirt** for virtualization, and **Cilium + KubeOVN** for networking.

![](https://cdn-images-1.medium.com/max/800/0*TPCZ3Zpt6v38RauU)

#### **Virtualization Enhancements**

The old Virtual Machine app has been split into two separate apps: `vm-disk` and `vm-instance`.

- **vm-disk (Virtual Machine Disk)** has been separated from the virtual machine application, now supporting image uploads from HTTP or local sources. When creating a disk, you can specify the source and type of image — CD-ROM or classic.
- **vm-instance (Virtual Machine Instance)** allows you to launch a virtual machine from created disks.

This new structure enables the creation of virtual machines with multiple disks, installation from CD-ROMs, and the ability to switch disks between different VMs. This approach allows for more flexible disk and virtual machine configuration management.

The old **Virtual Machine** app has been retained for compatibility and to offer a simpler way of launching virtual machines in Cozystack.

In addition to the virtualization enhancements, the latest release introduces several other important features.

#### **InstanceType and InstanceProfile Options**

New `instanceType` and `instanceProfile` options have been added, along with a default set of instances and profiles for Ubuntu, RHEL, Alpine, and Windows. You can now configure virtual machines with optimal parameters (e.g., enable TPM, use virtio devices, or tablet-pointer) depending on the operating system. Instead of manually specifying resources for a VM, you can use standardized instances designed for specific workloads.

These instance types also extend to **Kubernetes**, allowing for better planning of your node groups.

#### **CDI Upload Proxy**

An option for enabling proxying for image uploads from local machines has been added to the ingress, and the CDI (Containerized Data Importer) has been updated for better compatibility with block devices. Previously, image uploads for LINSTOR using the `virtctl` utility were unavailable, but we have resolved this issue and contributed a patch upstream to LINSTOR.

#### Windows Virtual Machine Support

With the new `vm-disk` and `vm-instance` features, we tested the installation of Windows 10 and Windows Server 2025 from ISO, followed by switching to VirtIO drivers. Everything works smoothly.

#### **Web Interface for S3 Buckets**

When ordering S3 buckets, a web interface is now automatically deployed for accessing them. You can upload and delete files, as well as generate temporary links for public access.

This interface is built on [s3manager](https://github.com/cloudlena/s3manager) (Apache 2.0).

![](https://cdn-images-1.medium.com/max/800/0*HVZdxOcTtif8O84i)

#### **Alert System Improvements**

New alerts for FluxCD have been added, providing real-time status updates on releases. Alerts are now more structured and categorized, making it easier to navigate and identify issues. Additionally, the **Resource** field now displays the specific problematic resource, allowing for faster troubleshooting and resolution.

![](https://cdn-images-1.medium.com/max/800/0*8TbubaCWTABDevO1)

#### **Telegram Alert Integration**

A new feature allows the delivery of alerts directly to Telegram, including deduplication to prevent alert spam. Alerts now come with actionable buttons, enabling you to manage the lifecycle of each alert (e.g., acknowledge, resolve) directly within the Telegram interface.

![](https://cdn-images-1.medium.com/max/800/0*3lsWgkyGJes-L0-D)

#### MachineHealthChecks Controller for Kubernetes

`MachineHealthChecks` controller has been integrated into Cluster API to monitor the health of nodes in Kubernetes clusters. In case of any issues, the affected nodes will be automatically reprovisioned.

#### Added External-DNS Component

The external-dns component now allows automatic configuration of DNS records in Cloudflare. Additionally, the API can be used to order certificates via the DNS method with Cloudflare.

#### External-Secrets-Operator

A new feature has been added to synchronize secrets with external systems using the external-secrets-operator.

#### Optional Components

Some components in bundles are now disabled by default. You can enable them by passing the bundle-enable option in the Cozystack configuration.

#### Improved Initialization Jobs for Postgres and FerretDB

The initialization jobs now wait until the database is fully ready before making any configuration changes.

#### Increased Stability of Kube-OVN

NetworkManager communication has been disabled, resolving an issue where, on some systems, this blocked the OVN controllers from starting.

#### Log Configuration for Clickhouse

Logs can now be moved to a separate volume, and log rotation can be configured.

#### Component Updates:

- LINSTOR updated to v1.29.1
- Talos Linux updated to v1.8.1
- Cilium updated to v1.16.3

### Acknowledgments

We extend our thanks to community contributors who submitted PRs for this release: [kingdonb](https://github.com/kingdonb), [mrkhachaturov](https://github.com/mrkhachaturov), [klinch0](https://github.com/klinch0).

Join the platform developer community via [Telegram chat](https://t.me/cozystack).

We also hold weekly community meetings every Thursday, where we openly discuss platform development. Subscribe to the calendar of events via [the link provided](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t).