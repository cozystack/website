---
title: ApplicationDefinition reference
linkTitle: ApplicationDefinition
description: How ApplicationDefinition resources describe application types and how to look them up from client code
weight: 15
---

## Overview

`ApplicationDefinition` (`applicationdefinitions.cozystack.io/v1alpha1`) is a
cluster-scoped CRD that describes every application type the platform
exposes. Each definition declares the Kubernetes kind that tenants use in
the aggregated API (`spec.application.kind`), the OpenAPI schema used to
render the dashboard form and validate user input
(`spec.application.openAPISchema`), and dashboard metadata such as
category, icon, and display names (`spec.dashboard`).

The aggregated API server (`cozystack-api`) lists every `ApplicationDefinition`
**once at startup** and registers a matching resource under
`apps.cozystack.io/v1alpha1`. The set of tenant-facing kinds does not change
while the API server is running — adding, removing, or renaming an
`ApplicationDefinition` takes effect only after `cozystack-api` restarts.

A dedicated controller (`applicationdefinition-controller`, shipped with
Cozystack) watches `ApplicationDefinition` and triggers that restart
automatically: on any change to the set it computes a SHA-256 checksum over
the sorted definitions and writes it to the `cozystack.io/config-hash`
annotation on the `cozy-system/cozystack-api` Deployment's pod template,
which Kubernetes then reconciles as a rolling restart. Events are debounced
over a short window, and if the checksum is unchanged the restart is
skipped. Operators do not need to `kubectl rollout restart` by hand.

When a user creates a `Postgres` CR through the dashboard, `kubectl`, or a Go
client, the aggregated layer translates it into a Flux `HelmRelease` that uses
the chart referenced by the definition.

## Naming convention

`ApplicationDefinition` uses two independent naming styles. Each definition
sets them explicitly, and the relationship between them is **not derivable
by any string transform**:

| Field | Style | Example (HTTP cache) | Example (VM disk) | Example (TCP balancer) |
| --- | --- | --- | --- | --- |
| `metadata.name` | lowercase-with-hyphens | `http-cache` | `vm-disk` | `tcp-balancer` |
| `spec.application.kind` | CamelCase, preserves acronyms | `HTTPCache` | `VMDisk` | `TCPBalancer` |
| `spec.application.singular` | lowercase, no hyphens | `httpcache` | `vmdisk` | `tcpbalancer` |
| `spec.application.plural` | lowercase, no hyphens | `httpcaches` | `vmdisks` | `tcpbalancers` |

Note that `metadata.name` is not a function of `spec.application.kind`. The
hyphen positions (`tcp-balancer`, `vm-disk`, `http-cache`) and the absence of
hyphens in `singular`/`plural` (`tcpbalancer`, `vmdisk`, `httpcache`) are
conventions chosen per application, not outputs of a shared algorithm.
`strings.ToLower(kind)` yields `httpcache`, which matches
`spec.application.singular` but **not** `metadata.name`. A direct lookup by
the lowercased kind therefore fails:

```bash
# The aggregated API resource uses the lowercased plural:
$ kubectl get httpcaches --namespace tenant-demo
NAME       READY   AGE   VERSION
frontend   True    2m    1.2.0

# But the ApplicationDefinition that backs it is stored under a different name:
$ kubectl get applicationdefinition httpcache
Error from server (NotFound): applicationdefinitions.cozystack.io "httpcache" not found

$ kubectl get applicationdefinition http-cache
NAME         AGE
http-cache   14d
```

Acronyms make this more visible: `TCPBalancer`, `HTTPCache`, and `VMDisk` all
lose their capitalisation in the aggregated resource name (`tcpbalancers`,
`httpcaches`, `vmdisks`) but keep hyphens in the CRD name (`tcp-balancer`,
`http-cache`, `vm-disk`).

## Recommended lookup pattern

Client code that needs to resolve a Cozystack kind — for example a dashboard
that receives `HTTPCache` from a HelmRelease label and wants to render the
matching form — should **list all `ApplicationDefinition`s and filter by
`spec.application.kind`** instead of attempting a direct `Get` by the lowercased
kind. The set of definitions is small (tens of items) and changes rarely, so
this pattern is cheap and stable. Return the whole matched object so that
downstream callers can read `spec.application.openAPISchema`,
`spec.dashboard`, or any other field without issuing a second API request.

Before relying on the group and resource names below, confirm them against
your cluster with:

```bash
$ kubectl api-resources | grep applicationdefinition
applicationdefinitions                                cozystack.io/v1alpha1                  false        ApplicationDefinition
```

The row should list `applicationdefinitions` in the `NAME` column,
`cozystack.io/v1alpha1` in the `APIVERSION` column, `false` under
`NAMESPACED` (the resource is cluster-scoped), and `ApplicationDefinition`
in the `KIND` column. If the group differs on your cluster, adjust
`GroupVersionResource` in the example accordingly.

```go
import (
    "context"
    "fmt"

    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
    "k8s.io/apimachinery/pkg/runtime/schema"
    "k8s.io/client-go/dynamic"
)

// findByKind returns the ApplicationDefinition whose spec.application.kind
// matches the requested kind, or an error if no match is found. The caller
// gets the full object, so fields such as spec.application.openAPISchema
// are available without a second API round trip.
func findByKind(ctx context.Context, client dynamic.Interface, kind string) (*unstructured.Unstructured, error) {
    if kind == "" {
        return nil, fmt.Errorf("kind must not be empty")
    }

    gvr := schema.GroupVersionResource{
        Group:    "cozystack.io",
        Version:  "v1alpha1",
        Resource: "applicationdefinitions",
    }

    // The set of ApplicationDefinitions on a Cozystack cluster is small
    // (on the order of tens), so a single unpaginated List is sufficient.
    // If you adapt this helper for a larger catalog, set ListOptions.Limit
    // and loop on the continue token to avoid silent truncation.
    list, err := client.Resource(gvr).List(ctx, metav1.ListOptions{})
    if err != nil {
        return nil, fmt.Errorf("list %s/%s/%s: %w",
            gvr.Group, gvr.Version, gvr.Resource, err)
    }
    for i := range list.Items {
        specKind, found, err := unstructured.NestedString(
            list.Items[i].Object, "spec", "application", "kind")
        if err != nil || !found {
            // Skip definitions with missing or non-string kind so the
            // iteration does not match a malformed entry.
            continue
        }
        if specKind == kind {
            return &list.Items[i], nil
        }
    }
    // Include the GVR in the error so a wrong group (for example after a
    // CRD rename) is distinguishable from a genuine "no such kind".
    return nil, fmt.Errorf("no ApplicationDefinition with spec.application.kind %q found under %s/%s/%s",
        kind, gvr.Group, gvr.Version, gvr.Resource)
}
```

The set of `ApplicationDefinition`s served via the aggregated API is frozen
at `cozystack-api` startup (see [Overview](#overview)), but the backing
CRDs can still be edited at runtime: an administrator can tweak
`spec.application.openAPISchema` or `spec.dashboard` on an existing
definition, or add a new kind — `applicationdefinition-controller` then
triggers a rolling restart of `cozystack-api` so the change becomes
reachable through the aggregated API without manual intervention. How
aggressively a client should cache therefore depends on its own lifetime:

- **Short-lived processes** (CLI tools, one-shot scripts, serverless
  functions) can safely cache the result of `findByKind` for the entire
  process lifetime.
- **Long-running processes** (dashboards, controllers, operators) should
  re-list `ApplicationDefinition`s on a cadence that matches how often
  their operators edit schemas — once every few minutes is usually
  enough. Definitions change rarely, so a watch is not worth the
  complexity. A new `ApplicationDefinition` will become reachable through
  the aggregated API shortly after it is created, once the controller-
  driven rolling restart of `cozystack-api` completes.

{{% alert color="info" %}}
The lowercased plural (`httpcaches`, `vmdisks`) **is** the correct name for
tenant-facing resources under `apps.cozystack.io/v1alpha1`. It is only the
`applicationdefinitions.cozystack.io` CRD that uses the hyphenated form.
{{% /alert %}}

## See also

- [Cozystack API overview]({{% ref "/docs/next/cozystack-api" %}}) — kubectl,
  Terraform, and Go client usage for tenant-facing resources.
- [Go Types]({{% ref "/docs/next/cozystack-api/go-types" %}}) — typed Go clients
  for `apps.cozystack.io/v1alpha1` resources.
