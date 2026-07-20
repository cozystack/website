---
title: "Customizer — Declarative Cluster Customizations"
linkTitle: "Customizer"
description: "Manage cluster customizations from a git repo you own, using Cozystack's built-in Flux."
weight: 15
---

The **customizer** is an opt-in system package (`cozystack.customizer`) that turns an admin-owned git repo into the source of truth for cluster customizations: Package CR overrides (OIDC enable, MetalLB options), in-house HelmReleases, Keycloak realm imports, NetworkPolicies, and additional `PackageSource`s pointing at the admin's own chart registries.

It's the supported alternative to running `kubectl patch packages.cozystack.io …` interactively. Same end-state, but every change is a commit in a repo the admin owns — with audit trail, code review, rollback, and DR replay.

## When to use it

- Enabling OIDC on the host control plane
- Overriding a system-component value (`metallb.frrk8s.enabled: true`, ingress-nginx config keys, etc.)
- Declaring Keycloak realms / clients as `KeycloakRealmImport` CRs
- Shipping in-house HelmReleases (internal portal, monitoring sidecar) into a namespace the admin owns
- Registering an additional OCI chart registry + `PackageSource` so the admin's own charts get the same Package-CR lifecycle as platform packages
- Cluster-scoped resources the admin needs that the platform doesn't manage (NetworkPolicies, RBAC for ops teams)

## How it works

Cozystack runs its own GitOps loop — the platform chart and its child packages reconcile from a fixed OCI/Git source. The customizer adds a **second, parallel loop** scoped to the admin's repo:

```
                     cozy-system
                     ┌────────────────────────────────────────────────────┐
   cozystack OCI ─►  │ PackageSource cozystack.*                          │
   (chart-managed)   │ Package cozystack.*       ◄── helm-controller SSA  │
                     │     └─► HelmRelease (owned, hard-Updated)          │
                     └────────────────────────────────────────────────────┘
                                       ▲
                                       │ SSA patch to spec.components.*.values
                                       │
   admin git repo ──►  GitRepository cozystack-customizer-config
                              │
                              ▼
                    Kustomization cozystack-customizer
                       serviceAccountName: cozystack-customizer
                              │
                              ├─► Package CR patches  (Server-Side Apply)
                              ├─► resources in cozy-customizer/  (own & prune)
                              ├─► extra PackageSources           (own & prune)
                              └─► extra HelmReleases in admin namespaces
```

Two field managers (`helm-controller` and `kustomize-controller`) coexist on the same Package CR. helm-controller writes only the chart-rendered fields; kustomize-controller writes only what the admin's repo declares. SSA tracks ownership per field.

## Read next

- **[Setup guide]({{< relref "setup.md" >}})** — step-by-step: prerequisites, enable the package, first commit, verify reconciliation.
- **[Repo layout and worked examples]({{< relref "repo-layout.md" >}})** — recommended directory tree plus three end-to-end examples (enable OIDC, override a MetalLB option, ship an in-house HelmRelease).
- **[Field ownership, RBAC, limitations]({{< relref "field-ownership.md" >}})** — what the customizer SA can and can't do; which fields on Package CRs are chart-owned vs admin-owned; the SSA contract.
