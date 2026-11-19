---
title: "OpenCost"
linkTitle: "OpenCost"
description: "Enable the optional OpenCost package for per-namespace and per-workload cost allocation, and the packages it needs on a slim variant."
weight: 60
---

The `opencost` package deploys [OpenCost](https://github.com/opencost/opencost), which allocates cluster cost to
namespaces, workloads and pods from the usage data in VictoriaMetrics and the node prices.

The package is **opt-in**: an existing cluster is unchanged until it is enabled.

## Enable the package

Add `cozystack.opencost` to `bundles.enabledPackages` in the [Platform Package]({{% ref "/docs/next/operations/configuration/platform-package" %}}):

```bash
kubectl patch packages.cozystack.io cozystack.cozystack-platform --type=json \
  -p '[{"op": "add", "path": "/spec/components/platform/values/bundles/enabledPackages/-", "value": "cozystack.opencost"}]'
```

## What OpenCost needs

OpenCost queries the VictoriaMetrics of the root tenant and allocates from the series `monitoring-agents` collects. It exits
at startup when that endpoint is missing. The operator installs the package only once every package it depends on is Ready,
and `enabledPackages` never pulls a dependency in. The platform therefore refuses to render, naming everything that is missing:

- **A required package is in `bundles.disabledPackages`.** Remove it from there, or drop `cozystack.opencost`. The one exception is
  `cozystack.networking`, which stays allowed so that a CNI managed by hand can be kept.
- **On a slim variant, packages that are opt-in there are not enabled.** List all of them in `bundles.enabledPackages`:
  `cozystack.grafana-operator`, `cozystack.metrics-server`, `cozystack.monitoring-agents`, `cozystack.monitoring-application`,
  `cozystack.vertical-pod-autoscaler`, and, when OIDC is off, `cozystack.postgres-operator`.
- **`monitoring.rootEnabled` is `false`.** The slim variants default to `false`.

The platform HelmRelease reports the message, for example
`cozystack.opencost cannot be installed: on a slim variant it also needs ... in bundles.enabledPackages`.

A full variant already installs these packages, so enabling `cozystack.opencost` is enough there.

{{% alert title="Keep Tenant/root monitoring in sync" color="warning" %}}
`monitoring.rootEnabled` is only a value. The root tenant must also run monitoring (`spec.monitoring: true` on `Tenant/root`),
otherwise there is no VictoriaMetrics for OpenCost to query and it restarts until there is.
{{% /alert %}}

## Verify

```bash
kubectl get helmrelease --namespace cozy-opencost opencost
```
