---
title: "DORA on Kubernetes: ICT Third-Party Risk and Resilience"
linkTitle: "DORA"
description: "DORA on Kubernetes: how Cozystack supports digital operational resilience — backup and restore, incident evidence, ICT third-party risk and exit strategy."
date: 2026-08-18
type: "page"
weight: 25
---

**For the chapter of DORA that decides most platform conversations — dependence on a single
ICT provider — Cozystack is about as good an answer as infrastructure gets.** It is
open-source software under Apache 2.0, it runs on your own hardware, and leaving it means
moving standard Kubernetes objects and virtual machines rather than unwinding a proprietary
format. An exit strategy you can rehearse beats a clause promising cooperation.

The resilience side is solid too: replicated storage across nodes, live migration between
them, declared state that the platform continuously restores, multi-datacenter topologies as
a normal deployment shape, backups encrypted by default. This page goes through all of it,
and marks the handful of places where you need to configure something rather than inherit it.

What the platform cannot do is hold the obligation. The Digital Operational Resilience Act —
Regulation (EU) 2022/2554 — has applied since 17 January 2025 and binds the categories of
financial entity listed in Article 2: banks, insurers, investment firms, payment and e-money
institutions, crypto-asset service providers and others. ICT third-party service providers
are not in scope directly; a small number are designated critical by the European Supervisory
Authorities under Article 31 and placed under an EU Oversight Framework with a Lead Overseer,
which is a different regime from the competent-authority supervision financial entities face.

## ICT third-party risk: the part that depends on the platform

DORA devotes a whole chapter to ICT third-party risk: register of information, contractual
requirements, concentration risk, exit strategies, and the right to audit. Regulators care
about it because a financial entity that cannot leave a provider has no real control over its
own resilience.

Three properties matter here. None is a feature you enable; each follows from how the
platform is built and licensed.

**The source is open, under Apache 2.0.** Contractual continuity does not depend on one
vendor's survival, and the code can be audited by you or by a third party without asking
permission.

**It runs on your own hardware.** No control plane in someone else's account, no vendor with
standing access required for the platform to function, no dependency on an external service
being up. What you host, you control.

**Exit is possible in practice, not only on paper.** Workloads are Kubernetes objects and
virtual machines in standard formats; there is no proprietary encapsulation to unwind. An exit
plan you can rehearse is worth more to a regulator than a clause promising cooperation.

None of this exempts you from maintaining the register of information required by Article
28(3), from holding an exit strategy under Article 28(8), or from contracts carrying the key
provisions of Article 30 of DORA — a different Article 30 from the GDPR one. It makes those
documents easier to write truthfully.

## Resilience: what the platform provides

DORA expects ICT systems to withstand and recover from disruption, and to be tested against
that expectation rather than assumed to meet it.

**Replicated storage, where the StorageClass asks for it.** LINSTOR places volumes with DRBD
replication across nodes, so a replicated volume survives the loss of a node holding one of
its copies. Replication is a property of the StorageClass rather than of the platform — local,
non-replicated classes exist and are the right choice for some workloads — so check which
class each critical or important function actually uses. No separate storage array is required
either way.

**Live migration.** Virtual machines move between nodes without shutdown, which turns planned
maintenance from an outage into an operation.

**Declared state, continuously reconciled.** Machines and services are described as
manifests, and the platform works to keep reality matching the description. Kill a workload
directly and it comes back, because the description did not change.

**Stretched clusters across locations.** Multi-datacenter topologies are a normal deployment
shape rather than an exotic one, which matters when your resilience requirements name
geographic separation.

Be precise about what is *not* provided. There is no automated virtual machine failover after
unplanned node loss of the kind a dedicated HA product gives you. Node health handling and
restart policies exist and can be combined into a failover procedure, but that is
configuration and rehearsal work, not a switch.

## Backup, restore and the evidence that they work

Velero ships with the platform for scheduled backups, volume snapshots, virtual machine
backups and cluster state, and backup data is encrypted in object storage by default through
the kopia uploader.

Where those backups land needs a decision before an assessment, not after. Platform-managed
backups default to a shared `cozy-backups` bucket in `tenant-root`, separated between tenants
by object path. Article 12(2) expects restoration to run on systems physically and logically
segregated from the source, and Article 12(3) expects backup systems not to be directly
connected to the primary one — a bucket inside the cluster being protected meets neither.
Point the BackupClass at storage outside the cluster, with its own credentials and its own
key, and say so in the backup policy Article 12(1) asks you to write.

The regulation's emphasis is not on having backups but on being able to restore. Rehearse the
restore against a defined recovery time and recovery point objective, record what you actually
achieved, and keep that record. A restore time you measured is evidence; an estimate is not.

## Detection, logging and incident evidence

DORA requires incidents to be detected, classified and — for major ones — reported to the
competent authority on a short clock. That works only if the underlying record exists.

The platform ships metrics collection, log aggregation, alerting and dashboards, and the
Kubernetes API server writes an audit log under a policy you supply. Set two things
deliberately. Retention first: the default on the cluster examined here is thirty days, shorter than a
financial supervisor will expect for records touching critical or important functions. Then the audit policy, resource by resource — do not raise everything to full request
and response capture, which writes secrets and personal data into the log and buys a GDPR
problem to settle a DORA one.

Security advisories for the platform are published openly, including assessments of
vulnerabilities that turn out not to affect it. That public record is directly usable in the
threat-intelligence and vulnerability-management parts of an ICT risk framework.

## Testing resilience without touching production

DORA expects a program of digital operational resilience testing under Chapter IV, and
threat-led penetration testing under Article 26 for those entities their competent authority
identifies as in scope for it — a designation based on risk profile and systemic importance,
not a category you can read off your own balance sheet.

Two properties of the platform help the general program. A tenant gives you an isolated place
to run destructive tests against a realistic copy. And because environments are described as
manifests, the environment under test can be recreated exactly, which is what makes a test
result meaningful the second time.

TLPT is a different exercise, and the distinction matters: Article 26 tests run against live
production systems supporting critical or important functions, so a tenant copy does not
substitute for one. Where the platform is operated for you, or supports a critical or
important function, the ICT third-party service providers involved are drawn into the scope of
that test and have to be arranged with in advance.

The [CIS Benchmark](/compliance/cis-benchmark/) page shows one such test executed against a
live cluster, together with the reasoning that turns a raw report into something an assessor
can use.

## What stays with you

Governance sits with the management body and cannot be delegated to a supplier: the ICT risk
framework, the register of information, incident classification and reporting within the
regulation's deadlines, the digital operational resilience testing program, contractual
arrangements with providers, and the exit strategy itself.

A platform can make each of those cheaper to satisfy. It cannot hold them.

## Frequently asked questions

### Is Cozystack DORA compliant?

The question does not apply to a platform. Financial entities are subject to DORA; platforms
are part of the ICT estate those entities manage. Cozystack contributes replication, live
migration, backup and restore, observability, audit logging and — most usefully for Chapter V
— an architecture with no vendor dependency to unwind.

### Does running on our own hardware remove ICT third-party risk?

Self-hosting removes the platform vendor from the critical path — often the largest single
component of that risk. Hardware suppliers, datacenter operators and any integrator you
contract remain third parties and belong in the register of information.

### Does Cozystack go into our register of information?

The register under Article 28(3) records *contractual arrangements* for the use of ICT
services. Downloading and self-hosting Apache 2.0 software creates no contractual arrangement,
so there is no counterparty to name and nothing about the project itself to register. The
moment you buy support, hosting or integration around it, that supplier is an ICT third-party
service provider under Article 3(19) and belongs in the register, with the function it
supports and whether that function is critical or important. Confirm the treatment with your
own competent authority — supervisory practice on open-source components is not uniform.

### What about the right to audit?

Article 30(3)(e) is a contractual right of access, inspection and audit for you and for your
competent authority, exercised against a provider. With no provider in the path there is no
contract to carry it, and inspecting the platform means reading public source and running
checks against your own cluster. Where you contract an operator, those access and audit rights
— and the Article 30(3)(f) exit and transition provisions — belong in that contract rather
than in a claim about the software.

### Can we test failure scenarios safely?

Yes. Run them in a dedicated tenant, isolated by network policy from everything else, and
recreate the environment from manifests between runs.

## Notes

This page describes Cozystack v1.6 as observed on a reference cluster in August 2026 and is
informational. It is not legal advice, not an assessment, and not a statement that any
configuration satisfies a competent authority. Regulation (EU) 2022/2554 applies to defined
categories of financial entity and their critical ICT providers; whether it applies to you,
and in what capacity, is a question for your own counsel.
