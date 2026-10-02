---
title: "GDPR Compliance on Kubernetes with Cozystack"
linkTitle: "GDPR"
description: "GDPR on self-hosted Kubernetes: which Article 32 measures Cozystack supplies — data residency, encryption, access control, erasure — and which stay yours."
date: 2026-08-18
type: "page"
weight: 15
---

**Personal data on Cozystack stays where you put it.** The platform is open-source software
built on Kubernetes, KubeVirt and Talos Linux that runs on your own hardware: no control plane
in someone else's cloud, no vendor account, no service to sign up for. On top of that it
brings the measures Article 32 asks about — encryption in transit and for backups, centralized
identity, tenant isolation enforced by network policy, audit logging, backup and restore.

That is a strong starting position, and this page walks through it measure by measure. It also
marks the places where a control is available but off until you enable it, and the two or
three questions a data protection officer will raise that no infrastructure can answer for
you. Better to meet those here than in a meeting.

One framing worth keeping. Compliance belongs to the organization holding the data — why it
holds it, on what legal basis, for how long. A platform supplies measures and makes them
demonstrable; the useful answer to "is Cozystack GDPR compliant" is what follows below, not a
yes that falls apart under the first question.

## Data residency: where the data physically lives

Residency is usually the first question, and the easiest one to answer well.

Cozystack installs on your own hardware, in a facility you choose. There is no control plane
in someone else's cloud, no vendor who needs standing access in order for the platform to
work, and the platform requires no telemetry channel to a vendor in order to run. For Chapter
V — transfers of personal data to third countries — that removes the largest single element
from the analysis.

It does not close it. Under the EDPB's reading, remote access from a third country is itself a
transfer, so support engineers, an integrator's staff, out-of-hours administrators and
anything you connect for observability all still count. The outbound paths the cluster does
use — container registries, certificate authorities, time sources and update channels — are
worth listing once, because they say where the environment reaches even when the personal data
does not. If you operate in several jurisdictions, tenants and node placement let you keep
processing in one of them rather than spreading it across all of them.

## Which Article 32 measures Cozystack covers

### Encryption of personal data

Three layers, and they behave differently.

**Kubernetes secrets** are encrypted in etcd where the API server runs with
`--encryption-provider-config`. That setting comes from the Talos machine configuration
supplied at install time, so confirm it on your own cluster.

**Volumes** — the disks behind databases and virtual machines, which is where personal data
actually sits — are not encrypted unless you ask. LINSTOR supports at-rest encryption with
LUKS, enabled by setting a passphrase and creating a StorageClass that includes the LUKS
layer. See [Creating Encrypted Storage on LINSTOR](/docs/v1.6/storage/disk-encryption/), and
decide it at design time: converting a populated volume later means migrating the data.

Two consequences belong in the same decision, because they cut against Article 32(1)(b) and
(c) rather than for them. The passphrase is a single shared secret with no rotation procedure,
split knowledge or dual control, so key management is a process you build around it. And it
must be entered by hand after every restart of the LINSTOR controller — encrypted volumes do
not come back on their own, which turns an unattended restart into an availability event.

**Backups** are encrypted by default. Velero uses the kopia uploader, so backup data is
written to object storage under a repository key held in the cluster.

For personal data held by the identity layer specifically, Cozystack v1.6 added an optional
encrypting proxy in front of the Keycloak database, giving column-level encryption backed by
a static key or Vault Transit. It is off until you enable it.

### Confidentiality and access control

Authentication can be centralized in Keycloak through OIDC, which puts joiners, leavers,
multi-factor authentication and password policy in one place instead of scattering them
across kubeconfig files. It is not the default — a fresh cluster authenticates with a cluster
credential, which is a shared account and unsuitable for anything holding personal data.
Enable OIDC before the environment carries real data.

Authorization is scoped to the tenant, and more tightly than teams expect: a tenant user can
create databases and virtual machines through the platform API yet cannot read raw Kubernetes
secrets. Check it rather than take it on trust — as the tenant user, against the tenant
namespace:

```bash
kubectl auth can-i --list -n tenant-a
kubectl auth can-i get secrets -n tenant-a
```

The second returns `no`. Read that as least privilege at the API surface rather than as a
confidentiality boundary — a principal who can schedule workloads in a namespace can mount
that namespace's secrets into a pod, so the boundary holds only as far as you also restrict
workload creation.

### Separation of processing

Tenants are isolated from each other at the network layer by Cilium policies created together
with the tenant, and that isolation is enforced rather than declared. You can verify it in a
minute — start a pod in one tenant and try to reach it from another, with a same-tenant probe
as the positive control: the cross-tenant probe returns `000`, the same-tenant one `200`.

Read it for what it is. Network separation is not separation of processing in the sense a data
protection officer means. The control plane, etcd, LINSTOR and the identity layer are shared
services, platform administrators see across every tenant, and platform-managed backups land
in a single `cozy-backups` bucket in `tenant-root` separated between tenants by object path
rather than by credentials or by key. Tenant egress to the internet is not restricted by
default either, so an exfiltration path stays open until you add a `SecurityGroup` or an
egress allow-list. If you process personal data for several controllers, treat the tenant as a
strong first boundary and document the shared components and the administrators who cross
it — that is the part a data protection officer will ask about.

### Integrity of processing systems

Article 32(1)(b) names integrity alongside confidentiality, availability and resilience, and
this is the measure with the largest gap. Immutable node images and digest-pinned platform
components make undetected drift harder, and the audit log records who changed what through
the API. But no intrusion detection, no file-integrity monitoring and no change-detection
mechanism ship with the platform. Nothing prevents you running one, and if your risk
assessment calls for it, that is an addition you make rather than a control you inherit.

### Ability to restore availability after an incident

Article 32(1)(c) asks for the ability to restore access to personal data in a timely manner.
Velero ships with the platform for scheduled backups, volume snapshots and cluster state, and
restores are worth rehearsing rather than assuming — a backup nobody has restored is a hope,
not a measure.

### Regular testing of measures

Article 32(1)(d) asks for a process of testing and evaluating effectiveness. The
[CIS Benchmark](/compliance/cis-benchmark/) page shows one such test run against a live
cluster, with the failures sorted into real deviations and artifacts of the architecture.
Nothing prevents you from running it on your own schedule; the manifest is published there.

## The right to erasure, and where it gets awkward

The right to erasure is where infrastructure and law meet uncomfortably, so it is worth being
concrete rather than reassuring.

Deleting a database row is straightforward. Deleting it from **backups** is not: backups exist
precisely so that deletions can be undone. The commonly used position — one several supervisory
authorities have described as workable, without it being settled across the EEA — is
documented retention: state how long backups live, put the data beyond use in the meantime,
ensure erased data ages out within that window, and do not reintroduce it selectively on
restore. Record the reasoning, tell the data subject when the erasure will complete, and check
the position against your own authority's guidance rather than against this page.
Cozystack does not solve this for you — but it does let you set backup retention deliberately
and point backups at storage you control.

**Audit logs** create a second version of the same problem. Start from the fact that the audit
log is already a store of personal data: at the default `level: Metadata` it records
usernames, groups and source IP addresses, which are personal data about your administrators
regardless of what the requests contained. It needs an entry in your Article 30 records, a
retention period and an access rule of its own — the default retention on the cluster examined
here is thirty days.

The trap sits one level up. Raising the policy to `RequestResponse` to satisfy some other
framework writes request bodies — secret values, and whatever personal data your users put in
annotations — into the same file. Split the policy by resource instead: `RequestResponse`
where knowing what changed is the point, `Metadata` for secrets and for anything carrying
personal data.

## What stays with you

No infrastructure product supplies any of the following: the lawful basis for processing,
records of processing activities under Article 30, data protection impact assessments where
Article 35 requires them, notification of a personal data breach to the supervisory authority
within 72 hours under Article 33, responses to data subject requests, the appointment of a
data protection officer where Article 37 requires one, and the Article 28 agreement with
anyone who processes personal data on your behalf.

The platform is a tool. The obligations sit with whoever determines the purposes and means of
the processing.

## Frequently asked questions

### Is Cozystack GDPR compliant?

The question does not apply to infrastructure. An organization is compliant; a platform
supplies measures. Cozystack supplies encryption, access control, tenant separation, audit
logging, backup and restore, and full control over where data physically resides.

### Does self-hosting Cozystack avoid third-country transfer problems?

Self-hosting removes the platform itself from the Chapter V analysis: Cozystack runs on your
hardware and needs no vendor access to operate. Whether your own architecture moves data
elsewhere is a separate question, about your applications and integrations.

### Is personal data encrypted at rest by default?

For the storage that actually holds personal data — the volumes behind databases and virtual
machines — no. Volume encryption is opt-in per StorageClass and belongs in the design rather
than in a later change. Backups are encrypted by default. Kubernetes secrets are encrypted in
etcd when the API server runs with `--encryption-provider-config`, which comes from the Talos
machine configuration rather than from Cozystack, so verify it on your own cluster — and
secrets hold credentials, not usually the personal data your records of processing describe.

### Does running Cozystack ourselves introduce a processor?

No. Running open-source software on your own hardware adds no third party to the processing:
there is no service, no account and no data leaving your infrastructure, so there is nobody to
appoint under Article 28. Your own role is unchanged — you are the controller for personal
data whose purposes and means you determine, and a processor only where you host on behalf of
another controller. If you contract an integrator to operate the platform, that is a processor
or sub-processor relationship and needs an Article 28 agreement.

## Notes

This page describes Cozystack v1.6 as observed on a reference cluster in August 2026, and is
informational. It is not legal advice, not an assessment, and not a warranty that any
configuration satisfies a supervisory authority. Your installation may differ, particularly in
the Talos machine configuration that supplies several of the settings above.
