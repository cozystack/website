---
title: "PCI DSS Compliance on Kubernetes with Cozystack"
linkTitle: "PCI DSS"
description: "Which PCI DSS 4.0.1 requirements Cozystack covers by default on Kubernetes, which are opt-in, and which stay yours — with commands to verify each."
date: 2026-08-18
type: "page"
weight: 10
---

**Cozystack is not "PCI DSS certified" — no infrastructure platform can be — but it provides
most of the technical controls a PCI DSS 4.0.1 assessment depends on, and several of them are
active on a fresh install.** Cozystack is an open-source cloud platform built on Kubernetes,
KubeVirt and Talos Linux that runs on your own bare metal. Tenant network isolation,
privilege restrictions on workloads, automatic TLS for published services and encrypted
backups need no configuration. Single sign-on, volume encryption, restricted egress, encrypted
east-west traffic and longer audit retention are shipped but not switched on, because most
clusters do not need them: each is a configuration option, not a development project. This
page says which is which, requirement by requirement.

*Will this pass our audit?* The question comes up in the first meeting, every time a
cardholder data environment (CDE) moves to a new platform. No platform passes an audit.
A Qualified Security Assessor certifies a scoped environment — your systems, your
processes, your evidence. What a platform can do is provide the technical controls the
assessment depends on, and make them easy to demonstrate.

Finding out during an assessment that a control was never switched on is expensive, so every
opt-in item below is marked as one.

## Which PCI DSS 4.0.1 requirements Cozystack covers

The table below maps all twelve PCI DSS v4.0.1 requirements to what Cozystack provides.
"Default" means the control is active on a fresh installation. "Built in, off by default"
means the platform ships it and you turn it on — configuration, not development.

| PCI DSS v4.0.1 requirement | Cozystack coverage | Notes |
|---|---|---|
| 1 — Network security controls | **Default** | Tenants are isolated from each other by Cilium policies created with the tenant |
| 2 — Secure configurations | **Default** | Immutable OS with no SSH; privileged containers rejected by admission |
| 3 — Protect stored data | **Default + one option** | Secrets encrypted in etcd, backups encrypted by Velero; volume encryption is a StorageClass away |
| 4 — Encrypt data in transit | **Default + one option** | cert-manager issues and renews TLS for published services; Cilium adds transparent east-west encryption when you enable it |
| 5 — Protect against malware | **Yours** | Malware controls belong to the workloads you run, not to the platform |
| 6 — Secure systems and software | **Shared** | Components pinned to immutable digests; patching cadence is yours |
| 7 — Restrict access by need to know | **Default** | Tenant-scoped RBAC; a tenant user cannot read cluster secrets |
| 8 — Identify and authenticate users | **Built in, off by default** | Anonymous API access is disabled; SSO requires enabling the Keycloak OIDC integration — a default install authenticates with a cluster token |
| 9 — Restrict physical access | **Yours** | Cozystack installs on your own hardware, in your own facility |
| 10 — Log and monitor access | **Default, retention is a setting** | API audit log and centralized log storage ship with the platform |
| 11 — Test security regularly | **Shared** | Nothing blocks scanning or penetration testing; scheduling and scope are yours |
| 11.5 — Intrusion and change detection | **Yours** | No IDS or file-integrity monitoring ships with the platform; nothing prevents running one |
| 12 — Organizational policy | **Yours** | No infrastructure product can supply this |

## What you switch on for a cardholder environment

Nothing in this list needs custom development or a support contract. Each item is a setting,
and each belongs at design time rather than after the environment carries card data.

| Control | How it is enabled |
|---|---|
| Single sign-on with MFA | Enable the Keycloak OIDC integration at install time; MFA and password policy are Keycloak settings |
| Volume encryption at rest | Create a StorageClass with the LUKS layer, after setting a LINSTOR passphrase |
| Restricted outbound traffic | A `SecurityGroup`, or a `CiliumNetworkPolicy` egress allow-list, on the tenant |
| Encrypted east-west traffic | Turn on Cilium transparent encryption — WireGuard or IPsec |
| Twelve-month audit retention | Raise the audit log retention and point the archive at storage you control |
| `restricted` Pod Security | Label the tenant namespace; the admission plugin is already running |
| Internal time source | Set `machine.time` in the Talos machine configuration |
| Column-level encryption for identity data | Enable the Keycloak database encryption proxy, with a static key or Vault Transit |

## Migrating a PCI DSS scope from VMware

Teams replacing VMware vSphere usually have a cardholder data environment already scoped
around clusters, VLANs and vCenter roles, and the first question is what the equivalent
boundary looks like afterwards. The virtual machines keep running — KubeVirt runs them as
Kubernetes workloads — and the scoping boundary becomes the tenant. Segmentation moves from
VLANs and distributed firewall rules to Cilium network policies created together with the
tenant; vCenter roles and permissions move to Keycloak groups mapped onto tenant-scoped
RBAC. The requirements below are the same ones your assessor evaluated against vSphere.

## Requirement 1: cardholder data environment segmentation

Segmentation is where most platform evaluations begin, because it sets the size of your
audit scope. Putting the CDE in its own tenant gives you a defensible segmentation
boundary, but it does not by itself take the rest of the cluster out of scope: the control
plane, Cilium, LINSTOR, Keycloak and the nodes are shared services supporting the CDE, and
assessors normally treat them as in scope. Segmentation limits which *workloads* are in
scope, not which *platform components* are.

In Cozystack a [tenant](/docs/v1.6/guides/tenants/) is not a naming convention. Creating one provisions a set of Cilium
network policies alongside it, and those policies deny traffic from other tenants by
default. Nothing to write by hand, nothing to remember.

You can verify this yourself in about a minute. Start a pod in one tenant, then try to reach
it from another:

```bash
kubectl -n tenant-a run target --image=nginx:alpine --restart=Never
kubectl -n tenant-a wait --for=condition=Ready pod/target --timeout=60s
TARGET_IP=$(kubectl -n tenant-a get pod target -o jsonpath='{.status.podIP}')

# positive control: reachable from inside the same tenant
kubectl -n tenant-a run probe --rm -i --restart=Never --image=curlimages/curl:8.11.1 -- \
  curl -s -m 5 -o /dev/null -w '%{http_code}\n' "http://${TARGET_IP}/"

# the actual test: blocked from another tenant
kubectl -n tenant-b run probe --rm -i --restart=Never --image=curlimages/curl:8.11.1 -- \
  curl -s -m 5 -o /dev/null -w '%{http_code}\n' "http://${TARGET_IP}/"
```

The probe returns `000`. Run the same probe from inside `tenant-a` as a positive control: it
must return `200`, which proves the target is serving and the `000` came from policy rather
than from a pod that was never ready.

Note what the default policies do *not* do. Outbound traffic from a tenant to the internet
is not restricted, while Requirement 1.3.2 expects outbound from the CDE to be limited to
what is necessary. A cardholder environment therefore needs explicit egress rules — a
`SecurityGroup`, or a `CiliumNetworkPolicy` with an egress allow-list — on top of the tenant
defaults.

Cozystack v1.6 adds a tenant-facing [`SecurityGroup` API](/blog/2026/08/cozystack-1-6-talos-workers-tenant-sso-security-groups-hierarchical-quotas/) for teams that need finer rules
inside their own tenant without asking a platform administrator.

## Requirement 2: secure configuration and no vendor defaults

Cozystack nodes run [Talos Linux](https://www.talos.dev/), an immutable operating system with
no shell, no SSH daemon and no package manager. Configuration arrives through an API and is
declared, not typed. A whole family of findings — stale local accounts, drifted configuration, someone's
forgotten debugging change — becomes far harder to produce, because changes go through a
declarative API instead of a shell. Node-level access still exists through the Talos API,
and it deserves the same treatment as any other administrative interface.

Cozystack is a container platform, and the container-specific requirement here is that
workloads cannot escalate privileges. Pod Security admission *enforces* `baseline` and only
*warns* at `restricted`. Baseline rejects the obvious escapes — privileged containers, host
namespaces, hostPath — but still permits running as root and does not require a seccomp
profile. Hardening benchmarks an assessor is likely to cite expect `restricted`, so label
the namespaces holding the cardholder environment accordingly:

```bash
kubectl label namespace tenant-cde \
  pod-security.kubernetes.io/enforce=restricted --overwrite
```

At the default `baseline` level, a workload that asks for privileges is refused at the door:

```
Error from server (Forbidden): violates PodSecurity "baseline:latest":
host namespaces (hostNetwork=true, hostPID=true), privileged
```

Anonymous API access is disabled and the profiling endpoint is off.

## Requirement 3: encrypting stored data — secrets yes, volumes not by default

Two layers matter here, and they behave differently.

**Kubernetes secrets** are encrypted in etcd when the API server runs with
`--encryption-provider-config`. That flag, like `--anonymous-auth=false`, the audit policy
and `--profiling=false`, comes from the Talos machine configuration supplied at install
time rather than from Cozystack itself — so verify it on your own cluster instead of
assuming it. Note the limits of the control, too: it protects etcd data on disk and in etcd
backups, does nothing against a principal who can read the Secret through the API, and
buys little if the encryption key sits on the same control-plane node as etcd.

**Volumes** — the disks behind virtual machines and databases — are not encrypted unless
you ask. LINSTOR supports at-rest encryption with LUKS: set a passphrase, then create a
StorageClass that includes the LUKS layer:

```yaml
# local (non-replicated)
parameters:
  linstor.csi.linbit.com/layerList: "luks storage"
  linstor.csi.linbit.com/encryption: "true"

# replicated — the DRBD layer comes first
parameters:
  linstor.csi.linbit.com/layerList: "drbd luks storage"
  linstor.csi.linbit.com/encryption: "true"
```

Two operational consequences to plan for. The passphrase must be entered by hand after every
LINSTOR Controller restart (`linstor encryption enter-passphrase`); encrypted volumes do not
come back on their own. And the mechanism is a single shared passphrase with no rotation
procedure, no split knowledge and no dual control, so Requirements 3.6 and 3.7 have to be
met by the key-management process you build around it.

The full procedure is in [Creating Encrypted Storage on LINSTOR](/docs/v1.6/storage/disk-encryption/).
Decide this before the environment is built: converting a populated volume later means
migrating the data.

### Backups

Velero is the platform's backup layer and uses the kopia uploader, so backup data is
encrypted in the object store with a repository key held in the cluster. That covers the
copies, but it does not answer where they live: platform-managed backups land in a shared
`cozy-backups` bucket in `tenant-root`, separated between tenants by object path. If
cardholder data is backed up, agree with your assessor whether that bucket falls inside your
scope, and consider pointing the BackupClass at storage with its own key management.

For personal data held by the identity layer, v1.6 introduced an encrypting proxy in front
of the Keycloak database, backed by a static key or Vault Transit. It is off until you
enable it.

## Requirement 4: encrypting data in transit with TLS

cert-manager is part of the platform, with issuers configured for Let's Encrypt or your own
authority. Certificates are requested and renewed automatically, which removes the most
common cause of a transit-encryption finding: an expired certificate nobody owned.

From v1.6 an operator-provided wildcard certificate propagates to every tenant termination
point, so tenants inherit valid TLS instead of arranging it themselves.

Requirement 4 is about open public networks, but assessors ask about the internal path too,
and two flows are unencrypted until you act on them: pod-to-pod traffic inside the cluster,
for which Cilium offers transparent WireGuard or IPsec encryption that is off by default,
and DRBD replication between storage nodes. If the network carrying either one is not fully
under your control, turn on transparent encryption and put replication on its own isolated
network.

## Requirements 7 and 8: tenant RBAC and Keycloak single sign-on

Authentication can be centralized in Keycloak, and this is not the default. A fresh
cluster authenticates with a static cluster credential — a shared account, which
Requirement 8.2.2 does not allow. [Enabling OIDC](/docs/v1.6/operations/oidc/) is an installation-time step, and it belongs
before the environment carries cardholder data. Multi-factor authentication, password policy
and idle-session timeout are then Keycloak configuration rather than development work. Once enabled, the API server accepts OIDC tokens and reads group membership from the token,
so joiners and leavers are handled in one place, and the directory you already run stays the
source of truth.

Authorization is scoped to the tenant. This is stricter than teams expect: a tenant user can
create databases and virtual machines through the platform API, yet the tenant role carries no
`get secrets` verb, so credentials are not readable straight from a kubeconfig — they are
shown in the dashboard, under the tenant's own identity. Treat that as least privilege at
the API surface rather than as a confidentiality boundary: anyone who can schedule workloads
in a namespace can mount that namespace's secrets into a pod. Where it matters, restrict
workload creation as well.

Quotas are hierarchical, so a sub-tenant cannot exceed its parent's budget — useful when a
CDE must be capped as well as isolated.

## Requirement 10: Kubernetes audit logging and log retention

The API server writes an audit log to a file on the control-plane node, governed by a policy
you supply, and rotates it by age. Centralized log collection and metrics storage ship with
the platform for workloads — but shipping the API audit log into them is not wired up by
default, and Requirement 10.3.3 expects audit logs to reach a separate, centrally managed
server promptly.

Two more things to check rather than assume. The contents of the audit policy. A `Metadata`-level
policy will not produce the per-event detail Requirement 10.2.1 expects — but raising
everything to `RequestResponse` is the wrong correction, because request bodies carry Secret
values and personal data, and the audit log then becomes another store of the data you are
protecting. Split it by resource: `RequestResponse` for role bindings and admission
configuration, `Metadata` for Secrets. And protection of the trail itself: 10.3.2
through 10.3.4 require the log to be unmodifiable and watched by a change-detection
mechanism, neither of which the platform provides.

One number needs your attention. Requirement 10.5.1 expects twelve months of audit history,
three of them immediately available. The default audit retention in Cozystack is thirty days.
Raise it during design and point the archive at storage you control.

### Time synchronization

Requirement 10.6 is easy to miss and cheap to satisfy. Talos synchronizes node time through
`machine.time`, and the default is a public NTP pool. For a cardholder environment, point
every node at the same designated internal source that itself syncs to an accepted external
reference, keep the setting under configuration management so nobody can change it on a live
node, and confirm that changes to it land in the audit trail.

## Requirements 6 and 11: patching and security testing

Platform component images are pinned to immutable digests, so a release is reproducible and
what you tested is what you run. Releases are frequent and changelogs name every bumped
component, so you can show an assessor exactly what changed and when. Security advisories are published the same way, including [exposure assessments for CVEs that turn out not to affect the platform](/blog/2026/07/cve-2026-43499-ghostlock-cozystack-exposure-assessment/).

The rest is yours: scanning schedules, penetration testing, and the review cadence your
assessor expects. A container registry with built-in scanning is available from the
catalog.

## Is Cozystack PCI DSS certified?

No — and no infrastructure platform is. PCI DSS certification applies to a cardholder data
environment, is scoped by the entity that owns it, and is signed by a Qualified Security
Assessor. A vendor advertising a "PCI DSS certified platform" is describing something that
does not exist.

What we do say is narrower and verifiable: the infrastructure controls an assessment leans
on — segmentation, hardened configuration, encryption, centralized identity, audit logging —
are present, and most of them are on before you touch anything. Every control listed here can be checked against your own cluster with the commands on this
page, and the source is public.

This page is informational. It is not legal advice, not an assessment, not a certification,
and not a warranty that any configuration will satisfy a Qualified Security Assessor.
Statements describe Cozystack v1.6 as observed on a reference cluster; your installation may
differ. Support during an assessment is a commercial arrangement with individual vendors,
not something the project itself provides.

## Frequently asked questions

### How does Cozystack affect PCI DSS audit scope?
That is what segmentation is for, and here the isolation is enforced, not just declared.
Whether your assessor accepts a given boundary depends on your architecture, so agree on
the scope with them early and use the verification above as evidence.

### Does Cozystack encrypt cardholder data at rest by default?
For Kubernetes secrets, yes. For volumes, no — it is a supported option you enable per
StorageClass, and the decision belongs at design time.

### Can we use our own certificate authority and identity provider?
Yes. cert-manager works with an internal authority, and Keycloak federates with corporate
directories and external identity providers.

### Can Cozystack run on our own hardware for PCI DSS scope?
Yes. Cozystack [installs on bare metal](/docs/v1.6/install/) in your own facility, which keeps data residency and
physical security under your control — both of which an assessor will ask about.

## Getting help with a PCI DSS assessment

Cozystack is Apache 2.0 licensed and its source is public, so nothing above has to be taken
on trust. If you are preparing for an assessment and want the control mapping reviewed
against your scope, [enterprise support](/support/) is available from several vendors.
