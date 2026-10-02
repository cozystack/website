---
title: "LINSTOR GUI"
linkTitle: "LINSTOR GUI"
description: "Enable and access the optional LINSTOR web console for managing storage nodes, resources, and volumes."
weight: 40
aliases:
  - /docs/next/operations/storage/linstor-gui
---

The `linstor-gui` package deploys [LINBIT's LINSTOR GUI](https://github.com/LINBIT/linstor-gui) — a web console
for browsing and managing LINSTOR nodes, resource definitions, volumes, storage pools, and snapshots.
The UI proxies the LINSTOR controller REST API in-cluster using mTLS, so no credentials are ever exposed in the browser.

The package is **opt-in**. The CLI workflow is unchanged — enabling the GUI does not affect any LINSTOR behaviour.

## Enable the package

Add `cozystack.linstor-gui` to `bundles.enabledPackages` in the [Platform Package]({{% ref "/docs/next/operations/configuration/platform-package" %}}):

```bash
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=json \
  -p '[{"op": "add", "path": "/spec/components/platform/values/bundles/enabledPackages/-", "value": "cozystack.linstor-gui"}]'
```

Wait a minute for the platform chart to reconcile, then verify the HelmRelease has been created:

```bash
kubectl get helmrelease --namespace cozy-linstor linstor-gui
```

## Access the UI

### Option 1 — Keycloak-protected Ingress (recommended)

When [OIDC authentication]({{% ref "/docs/next/operations/oidc" %}}) is enabled, you can publish the UI at
`https://linstor-gui.<root-host>` behind the cluster Keycloak realm.
Add `linstor-gui` to `publishing.exposedServices` in the Platform Package:

```bash
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=json \
  -p '[{"op": "add", "path": "/spec/components/platform/values/publishing/exposedServices/-", "value": "linstor-gui"}]'
```

{{% alert color="info" %}}
The Ingress is only created when both conditions are met: `linstor-gui` is listed in `publishing.exposedServices`
**and** OIDC is enabled (`authentication.oidc.enabled: true`). Without Keycloak there is no authentication
layer in front of the LINSTOR REST API proxy, so the chart deliberately skips the Ingress.
{{% /alert %}}

Access is restricted to members of the `cozystack-cluster-admin` Keycloak group — the same group that grants
cluster-admin RBAC on the host cluster. Once enabled, open `https://linstor-gui.<root-host>` in your browser
and log in with your Keycloak credentials.

### Option 2 — Port-forward

For ad-hoc access without Keycloak, forward the `ClusterIP` service:

```bash
kubectl -n cozy-linstor port-forward svc/linstor-gui 3373:80
```

Then open <http://localhost:3373>.
