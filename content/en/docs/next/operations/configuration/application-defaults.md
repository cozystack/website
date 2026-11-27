---
title: "Application Defaults"
linkTitle: "Application defaults"
description: "Choose the values every new application of a kind starts from, and see how they merge with what a user submits."
weight: 33
---

Application defaults let an administrator choose values that every new application of a kind starts from, without changing its chart: a storage class and disk size for databases, an image factory and registry mirrors for Kubernetes worker pools. They are set once in the platform Package under `applicationDefaults`, and the Cozystack API merges them into an application's spec when the application is created. Applications that already exist are never changed by them.

## Configure

`applicationDefaults` is a map keyed by the plural name of an application kind. Each entry is a partial spec of that kind. Example under `spec.components.platform.values`:

```yaml
applicationDefaults:
  postgreses:
    storageClass: replicated
    size: 20Gi
  kubernetesnodeses:
    talos:
      imageFactoryURL: https://factory.example.org
      registryMirrors:
        ghcr.io:
          endpoints:
            - https://registry.example.org
```

The keys are the `plural` of each ApplicationDefinition, which is not always a regular English plural (`postgreses`, `kubernetesnodeses`). A key that matches no application does nothing and gives no message, so check the spelling against the plurals the cluster serves:

```bash
kubectl get applicationdefinitions --output custom-columns=NAME:.metadata.name,PLURAL:.spec.application.plural
```

An entry for a kind that is not installed yet is kept and applies once that kind appears, so entries for external catalogs can be written in advance.

Do not put credentials or other secrets in an entry. The values end up in the spec of every application created with them, where anyone who can read the application can see them.

## When defaults apply

Defaults are applied when an application is created through the Cozystack API, and only then. That covers `kubectl create`, `kubectl apply` of an application that does not exist yet, the dashboard, Terraform and any other client, and a server-side dry-run of a create. The merged values are saved in the application's HelmRelease, so they stay with the application from then on.

Defaults are not applied when an application is updated, patched, or applied again while it exists, and they are not read when an application is displayed or rendered. Changing or deleting an entry therefore affects only the applications created after the change. To change an existing application, edit its spec. HelmReleases that a controller writes directly, without going through the API, get no defaults either.

When a field is set in more than one place, the order is:

1. the value the user submitted;
2. the application default from `applicationDefaults`;
3. the default of the application chart itself.

## How an entry merges into a spec

The API fills in what the user left out and keeps everything the user wrote:

- A field the request leaves out is taken from the entry.
- A field the request sets is kept, whatever its value. `{}`, `[]`, `""`, `0`, `false` and `null` all count as set and win over the entry. An empty object `{}` therefore turns off defaults for everything inside it.
- An object whose schema declares its properties is merged field by field: the user's fields stay, and the missing ones come from the entry.
- Arrays, dictionaries (`additionalProperties`), free-form objects and objects marked `x-kubernetes-map-type: atomic` are taken whole. When the user sets one, the entry adds nothing to it. A worker pool that lists its own `registryMirrors` gets none of the mirrors from the entry.
- An object is marked atomic when its children are alternatives the chart accepts one at a time. In the built-in applications those are `osImage` of KubernetesNodes, `source` of VMDisk, and `oidc.customConfig` of Kubernetes and of Monitoring. A user who picks one alternative writes it in full: a default for a field inside the same alternative is not filled in. A default for `osImage.factory.imageFactoryURL`, for example, does not reach a pool that sets `osImage.factory.version`. Such a pool takes its factory from `talos.imageFactoryURL`, which is not atomic and is filled from the entry.

The API tells a field the user left out from one the user set by whether its key is in the request. A client that sends every field, with a zero value for the ones nobody chose, sets them all, and its application gets no defaults for those fields. Clients built on the generated Go types in the Cozystack repository do that for fields such as `storageClass`, `size` and `replicas`, and the Terraform provider sends every attribute it models, with its own default when the configuration sets none, so installation defaults do not reach those fields of resources made by Terraform yet ([cozystack/terraform-provider-cozystack#93](https://github.com/cozystack/terraform-provider-cozystack/issues/93)). Values that a client sends always win over the entry.

### Merge cases

Each row is a case from the merge test of the Cozystack API: the user spec is created with the entry configured, and the last column is what the application stores. The Schema column describes the schema of the case. "No declared properties" is a spec root that takes arbitrary keys: its fields are filled from the entry, and nothing is merged into them.

| # | Case | Schema | User spec | Installation entry | Stored spec |
| --- | --- | --- | --- | --- | --- |
| 1 | Omitted fields receive installation values | no declared properties | `{}` | `{"size": "20Gi", "nested": {"enabled": true}}` | `{"size": "20Gi", "nested": {"enabled": true}}` |
| 2 | Explicit empty values win | no declared properties | `{"object": {}, "array": [], "flag": false, "number": 0, "text": "", "nullable": null}` | `{"object": {"enabled": true}, "array": [1], "flag": true, "number": 3, "text": "default", "nullable": "default"}` | `{"object": {}, "array": [], "flag": false, "number": 0, "text": "", "nullable": null}` |
| 3 | An explicit null wins over an installation object | no declared properties | `{"object": null}` | `{"object": {"enabled": true}}` | `{"object": null}` |
| 4 | Nonempty objects with declared properties merge recursively | `nested` and `nested.child` declare properties | `{"nested": {"child": {"user": true}}}` | `{"nested": {"child": {"user": false, "default": true}, "sibling": 1}}` | `{"nested": {"child": {"user": true, "default": true}, "sibling": 1}}` |
| 5 | An empty nested object stops recursion | `nested` and `nested.child` declare properties | `{"nested": {"child": {}}}` | `{"nested": {"child": {"default": true}, "sibling": 1}}` | `{"nested": {"child": {}, "sibling": 1}}` |
| 6 | Typed dictionaries are replaced as a whole | `mirrors` is a dictionary (`additionalProperties` with an object schema) | `{"mirrors": {"docker.io": {"endpoints": ["https://mine"]}}}` | `{"mirrors": {"docker.io": {"endpoints": ["https://platform"], "skipFallback": true}, "ghcr.io": {"endpoints": ["https://platform"]}}}` | `{"mirrors": {"docker.io": {"endpoints": ["https://mine"]}}}` |
| 7 | Free-form objects are replaced as a whole | `values` preserves unknown fields | `{"values": {"a": 1}}` | `{"values": {"a": 2, "b": 3}}` | `{"values": {"a": 1}}` |
| 8 | Objects that also declare a dictionary are replaced as a whole | `options` declares `known` and `additionalProperties` | `{"options": {"extra": "user"}}` | `{"options": {"known": "platform", "platformKey": "injected"}}` | `{"options": {"extra": "user"}}` |
| 9 | Objects that also preserve unknown fields are replaced as a whole | `options` declares `known` and preserves unknown fields | `{"options": {"extra": "user"}}` | `{"options": {"known": "platform", "platformKey": "injected"}}` | `{"options": {"extra": "user"}}` |
| 10 | Closed objects still merge recursively | `options` declares properties, `additionalProperties: false` | `{"options": {"known": "user"}}` | `{"options": {"known": "platform", "other": "platform"}}` | `{"options": {"known": "user", "other": "platform"}}` |
| 11 | An omitted dictionary is copied whole | `mirrors` is a dictionary | `{}` | `{"mirrors": {"docker.io": {"endpoints": ["https://platform"]}}}` | `{"mirrors": {"docker.io": {"endpoints": ["https://platform"]}}}` |
| 12 | Arrays are whole replacement values | no declared properties | `{"rows": [{"name": "user", "nested": {}}]}` | `{"rows": [{"name": "default", "extra": true}]}` | `{"rows": [{"name": "user", "nested": {}}]}` |
| 13 | User scalars and objects retain their type | no declared properties | `{"scalar": "user", "object": {"user": true}}` | `{"scalar": {"default": true}, "object": "default"}` | `{"scalar": "user", "object": {"user": true}}` |
| 14 | Installation nulls and empty objects are copied | no declared properties | `{"user": true}` | `{"object": {}, "nullable": null, "array": []}` | `{"user": true, "object": {}, "nullable": null, "array": []}` |
| 15 | An omitted atomic object is copied whole | `osImage` is atomic | `{}` | `{"osImage": {"builtin": {}}}` | `{"osImage": {"builtin": {}}}` |
| 16 | An atomic object the user fills is not completed from the installation | `osImage` is atomic | `{"osImage": {"factory": {"version": "v1.13.0"}}}` | `{"osImage": {"builtin": {}}}` | `{"osImage": {"factory": {"version": "v1.13.0"}}}` |
| 17 | An atomic object the user fills with an empty child is not completed either | `osImage` is atomic | `{"osImage": {"factory": {}}}` | `{"osImage": {"builtin": {}}}` | `{"osImage": {"factory": {}}}` |
| 18 | An explicit empty atomic object wins | `osImage` is atomic | `{"osImage": {}}` | `{"osImage": {"builtin": {}}}` | `{"osImage": {}}` |
| 19 | Granular objects still merge recursively | `nested` declares properties, `x-kubernetes-map-type: granular` | `{"nested": {"a": 1}}` | `{"nested": {"a": 9, "b": 2}}` | `{"nested": {"a": 1, "b": 2}}` |
| 20 | A default for a sibling field inside the alternative a user chose is not filled in | `atomicMap` is atomic, its children declare properties | `{"atomicMap": {"mutuallyExclusiveKey1": {"value1": "userValue1"}}}` | `{"atomicMap": {"mutuallyExclusiveKey1": {"value1": "defaultValue1", "value2": "defaultValue2"}}}` | `{"atomicMap": {"mutuallyExclusiveKey1": {"value1": "userValue1"}}}` |
| 21 | The same object without the atomic marker is completed field by field | `atomicMap` and its children declare properties, no marker | `{"atomicMap": {"mutuallyExclusiveKey1": {"value1": "userValue1"}}}` | `{"atomicMap": {"mutuallyExclusiveKey1": {"value1": "defaultValue1", "value2": "defaultValue2"}}}` | `{"atomicMap": {"mutuallyExclusiveKey1": {"value1": "userValue1", "value2": "defaultValue2"}}}` |
| 22 | An atomic object nested in a merged object stops the merge only at itself | `pool` declares properties, `pool.osImage` is atomic | `{"pool": {"osImage": {"factory": {"version": "v1.13.0"}}}}` | `{"pool": {"size": "20Gi", "osImage": {"factory": {"imageFactoryURL": "https://factory.example.org"}}}}` | `{"pool": {"size": "20Gi", "osImage": {"factory": {"version": "v1.13.0"}}}}` |
| 23 | Objects that also take arbitrary keys are replaced as a whole | `options` declares `known`, `additionalProperties: true` | `{"options": {"extra": "user"}}` | `{"options": {"known": "platform", "platformKey": "injected"}}` | `{"options": {"extra": "user"}}` |

Rows 20 to 22 show the atomic rule on the shape of a real schema: in row 20 the user's choice is kept as written, in row 21 the same object without the marker is completed, and in row 22 the merge stops at the atomic object while `pool.size` next to it is still filled.

## Dashboard

When the order page of an application opens, the dashboard asks the API for a dry-run create and starts the form and the YAML editor from the spec the API returns, so the form already shows the defaults. Deploy sends what the form shows, and the application stores those values. One exception: when an entry sets `null` for a field that also has a chart default, kubectl and Terraform store `null`, but the form shows the chart default and stores that.

Clearing a text or number field in the form leaves its key out of the request, so the default for that field comes back on Deploy. Two cases work differently: clearing the last field of a nested object sends `{}` for that object, which turns off defaults for the whole object, and a cleared sensitive field, such as a password, is sent as `""` and stays empty. To store an empty value instead, set it in the YAML tab, for example `""` or `0`. Switching from the YAML tab back to the form fills an empty dropdown with its default option again, a dropdown set to None included, so deploy from the YAML tab when such a field has to stay empty.

If the preview fails or takes longer than 8 seconds, the form opens without defaults and shows a notice with a Retry button, and Deploy still works: the API applies the defaults to every field the request leaves out.

Write quantities in an entry as strings, for example `cpu: "2"`. The API accepts a number there, but the dashboard form validates integer-or-string fields as strings and rejects it.

## Checking an entry

Before the merge, the API checks the entry for the kind being created against that application's schema. Unknown fields and values of the wrong type are refused. An object that the merge completes may leave out required fields, because the user or the chart can supply them. Anything that is stored whole, such as array rows, dictionary values and atomic objects, has to be complete on its own.

Saving the Package does not check the entries. Check one with a server-side dry-run of a create, using a name that is not in use in the namespace:

```bash
kubectl create --dry-run=server --output yaml --filename app.yaml
```

Repeat the check after upgrading an application: its new schema may no longer accept a value in the entry.

## When defaults cannot be applied

A broken entry does not block creation. If the API cannot read the defaults, cannot parse them, or the entry for the kind does not pass the schema check, it creates the application with the spec as submitted and returns a warning: `Installation defaults could not be applied; continuing without them`. `kubectl` prints the warning; the dashboard does not show it yet. The reason is in the log of the `cozystack-api` pods.

How far a problem reaches depends on where it is:

- An entry that the schema of its kind refuses turns off defaults for that kind only.
- Invalid JSON, an entry that is not an object, or a top-level field starting with `_` in any entry turns off defaults for every kind until it is fixed.
- No `applicationDefaults` at all means no defaults and no warning.

## Limits

Application defaults are a starting point, not a policy. Users can override every value, and updates never consult the entries. To require a value, use a ValidatingAdmissionPolicy or a validating webhook on the application resource: validating admission runs on the merged spec, so it sees the defaults too. A mutating webhook runs before the defaults are applied and does not see them.

Some charts check two fields together, for example the TLS settings of RabbitMQ or the backup settings of the database applications. A default for one of those fields combined with a user's value for the other can produce a spec the chart refuses. The create succeeds, and the HelmRelease of that application then reports the chart's error. Keep such pairs out of the entry, or make sure users who set one field of a pair also set the other.
