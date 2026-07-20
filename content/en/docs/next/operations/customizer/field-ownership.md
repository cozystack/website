---
title: "Field Ownership, RBAC, Limitations"
linkTitle: "Field Ownership & RBAC"
description: "What the customizer ServiceAccount can do, which fields on Package CRs are admin-owned vs chart-owned, and the SSA contract."
weight: 30
---

The customizer Kustomization applies its manifests via Server-Side Apply through a dedicated ServiceAccount with a curated ClusterRole. This page documents what's granted, what isn't, and which fields on Package CRs the customizer is supposed to write.

## RBAC granted to `cozystack-customizer`

Cluster-scoped:

| Resource | Verbs | Notes |
|---|---|---|
| `packages.cozystack.io` | get, list, watch, **patch**, update | No `delete` — disable a Package by adding it to `bundles.disabledPackages` on `cozystack.cozystack-platform` instead. |
| `packagesources.cozystack.io` | full | Customizer authors its own PackageSources. |
| `helmreleases.helm.toolkit.fluxcd.io` (cluster-wide) | get, list, watch | Read-only — chart-managed HelmReleases are off-limits to the customizer. |
| `keycloakrealmimports`, `keycloaks`, `keycloakusers` (`k8s.keycloak.org`) | full | Declarative Keycloak realm management. |
| `*.source.toolkit.fluxcd.io` | full | Additional `GitRepository` / `OCIRepository` / `HelmRepository` / `Bucket` sources. |

Namespace-scoped (inside `customizer.rbac.ownedNamespaces`, default `cozy-customizer`):

- `cluster-admin` role bound — full mutate on every namespaced resource kind. HelmReleases, NetworkPolicies, ConfigMaps, Secrets, Services, Ingresses, etc.

## RBAC explicitly NOT granted

- `delete` on `packages.cozystack.io`
- Anything on `customresourcedefinitions.apiextensions.k8s.io`
- Anything on the `cozystack-controller` Deployment, ServiceAccount, or its cluster-admin binding
- Anything on `mutatingwebhookconfigurations` / `validatingwebhookconfigurations`
- Anything in `kube-system`

If you need any of these from a customizer manifest, the answer is "don't" — either restructure the change to use one of the granted paths, or perform it as an out-of-band administrator action.

## Field ownership on Package CRs

Each Package CR is shared between two field managers:

| Field | Owner | Why |
|---|---|---|
| `metadata.name`, `metadata.annotations["helm.sh/resource-policy"]` | helm-controller (platform chart) | Set by the platform bundle template. |
| `spec.variant` | helm-controller (for child Packages); cozystack-operator (for `cozystack.cozystack-platform`) | Set in the platform chart's `_helpers.tpl`. |
| `spec.components.*.values.*` | **customizer** | This is the entire admin-writable surface area for tuning a platform component. |
| `spec.components.*.enabled: false` | **customizer** | Disable a component within a Package. |
| `spec.ignoreDependencies` | **customizer** | Same. |
| `spec.components.platform.values.bundles.{enabled,disabled}Packages` | **customizer** (on `cozystack.cozystack-platform`) | The documented removal path for whole-package disable. |

The rule of thumb: **patch `spec.components.*.values.*` from the customizer; never write `spec.variant` or chart-rendered metadata.**

## Known limitation — contract is currently advisory

`kustomize-controller` hardcodes `client.ForceOwnership=true` on every Server-Side Apply call. When a customizer manifest declares a chart-owned field (most notably `spec.variant`), kustomize-controller **silently transfers ownership** away from helm-controller. Flux's own SSA conflict detection cannot catch this, because the force-ownership flag bypasses the conflict path.

The planned enforcement is a validating admission webhook on `packages.cozystack.io` that allow-lists which field managers may write the chart-owned fields. Until that ships, this contract is enforced socially, not by the API server.

### Symptoms of a contract violation

If a customizer manifest accidentally claims `spec.variant: <something-the-package-doesn't-have>`:

- The Package's status flips to `Ready=False`, `reason: VariantNotFound`, `message: "Variant <x> not found in PackageSource cozystack.<name>"`.
- helm-controller's `managedFields` entry for `spec.variant` collapses (ownership transferred to kustomize-controller).
- The downstream HelmRelease for that component is not regenerated.

If a customizer manifest accidentally drops `spec.variant` entirely after having claimed it:

- The field is deleted from the CR, no manager reclaims it.
- The reconciler falls back to the `default` variant (functionally benign for most components), but the CR is not pristine.

### Mitigation

Until the webhook lands:

1. **Code review** — treat the field-ownership table above as a PR checklist for customizer changes. Reject manifests that declare `spec.variant` on a chart-managed Package.
2. **Audit after enabling** new patches:
   ```sh
   kubectl get package <name> -o yaml --show-managed-fields | yq '.metadata.managedFields[] | {manager, operation, fields: .fieldsV1}'
   ```
   Confirm `helm-controller` still owns `spec.variant` and `kustomize-controller` owns only `spec.components.*.values.*`.

## Recovery — restore a broken Package CR

Suppose a customizer patch broke `cozystack.metallb` (set `spec.variant: oidc` by mistake, or left orphan `spec.components.metallb.values`).

1. Suspend the customizer Kustomization so it stops re-applying the bad patch:
   ```sh
   kubectl --namespace cozy-system patch kustomization cozystack-customizer \
     --type merge --patch '{"spec":{"suspend":true}}'
   ```
2. Reset the Package CR to a chart-default state:
   ```sh
   kubectl patch package cozystack.metallb \
     --type merge --patch '{"spec":{"variant":"default","components":null}}'
   ```
3. Confirm:
   ```sh
   kubectl get package cozystack.metallb
   ```
   Should show `Ready=True, reason: ReconciliationSucceeded` within a minute.
4. Fix the customizer manifest in your repo, commit, push, and resume:
   ```sh
   kubectl --namespace cozy-system patch kustomization cozystack-customizer \
     --type merge --patch '{"spec":{"suspend":false}}'
   ```

## Disable the customizer entirely

To turn the customizer off but leave the resources it created in place:

```sh
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=merge --patch '{
  "spec": {"components": {"platform": {"values": {"customizer": {"enabled": false}}}}}
}'
```

`helm.sh/resource-policy: keep` on the `cozystack.customizer` Package CR means the existing chart resources (GitRepository, Kustomization, SA, RBAC, owned namespaces) are not auto-removed. To fully uninstall:

```sh
kubectl delete package.cozystack.io cozystack.customizer
helm uninstall customizer --namespace cozy-system
```

## Other limitations

- **Single platform admin per cluster.** One customizer repo, one platform-wide configuration. Per-tenant customizer GitOps is out of scope; it would layer on top of the existing `tenant` Application CRs.
- **No HelmRelease forking for chart-managed components.** Cozystack's Package reconciler uses plain `Update` (not SSA) on its rendered HelmReleases, so a customizer manifest that tries to override a chart-rendered HelmRelease is wiped on the next reconcile. Patch the corresponding Package CR's `spec.components.*.values` instead.
- **Keycloak realm imports only run once unless the spec changes.** Bump a label, annotation, or any field on the `KeycloakRealmImport` to trigger re-import.
- **Keycloak user attributes and sessions are not declarative.** Those genuinely don't fit a GitOps loop; the customizer doesn't try to manage them.
- **No multi-admin authoring model.** The customizer pulls one branch from one repo with one SA. Branch protection and review happen in your git provider, not in the cluster.
