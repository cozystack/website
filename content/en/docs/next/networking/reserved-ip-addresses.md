---
title: "Reserved IP addresses"
linkTitle: "Reserved IP addresses"
description: "Let tenants reserve an IP address that outlives the Service using it, with the optional address-controller and metallb-iad packages."
weight: 27
---

## What this page covers

How to enable IP addresses as a first-class resource on a Cozystack cluster, how to give tenants a class of addresses to reserve from, how a tenant reserves and attaches one, and what operators need to know about the admission policy, air-gapped installs, teardown and upgrades. The feature is two optional system packages, off by default, added in [cozystack/cozystack#3382](https://github.com/cozystack/cozystack/pull/3382):

- `cozystack.address-controller`, the class-agnostic core ([cozystack/address-controller](https://github.com/cozystack/address-controller)). It serves the `local.sdn.cozystack.io/v1alpha1` API and binds claims to addresses, but never allocates an address itself.
- `cozystack.metallb-iad`, the driver for addresses that MetalLB announces ([cozystack/metallb-iad](https://github.com/cozystack/metallb-iad)). It allocates from a MetalLB pool and pins addresses to Services.

## How it fits together

The API mirrors storage provisioning:

| Storage | Addresses | Scope | Role |
| --- | --- | --- | --- |
| `StorageClass` | `IPAddressClass` | cluster | which pool, which driver, which reclaim policy |
| `PersistentVolume` | `IPAddress` | cluster | the address itself, bound to at most one claim |
| `PersistentVolumeClaim` | `IPAddressClaim` | namespaced | a tenant's request for an address |

A tenant creates an `IPAddressClaim` and reads the address from its status. The address belongs to the claim, not to any Service: deleting the Service that uses it does not release it, and under `reclaimPolicy: Retain` the address outlives the claim too, as a `Released` `IPAddress`.

MetalLB has no reservation concept, so the driver holds each reserved address with a placeholder Service in its own namespace, `cozy-metallb-iad`. MetalLB assigns the address to the placeholder but, with no endpoints behind it, never announces it. When a Service names the claim, the driver releases the placeholder and pins the address to that Service.

## Enabling the packages

Enable both packages together. The driver depends on the core, whose CRDs it needs, and on `cozystack.metallb`:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full
  components:
    platform:
      values:
        bundles:
          enabledPackages:
            - cozystack.address-controller
            - cozystack.metallb-iad
```

The platform emits the driver only where it also emits MetalLB. It does not emit the driver on the `isp-hosted` variants, on a slim variant that has not enabled `cozystack.metallb`, or where `bundles.disabledPackages` names `cozystack.metallb`. The core installs into `cozy-address-controller` and the driver into `cozy-metallb-iad`.

## Creating a class

A class does not describe addresses itself: it names an existing MetalLB `IPAddressPool` in `cozy-metallb`. The admin creates the pool and its advertisement in MetalLB's own terms, so the choice of L2 or BGP, and of which nodes and interfaces announce the range, stays with the admin. The pool must set `autoAssign: false`; otherwise MetalLB would hand its addresses to any Service that asks, and the driver refuses the class.

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: public
  namespace: cozy-metallb
spec:
  addresses:
    - 203.0.113.0/26
  autoAssign: false
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: public
  namespace: cozy-metallb
spec:
  ipAddressPools:
    - public
---
apiVersion: local.sdn.cozystack.io/v1alpha1
kind: IPAddressClass
metadata:
  name: public
  annotations:
    ipaddressclass.local.sdn.cozystack.io/is-default-class: "true"
spec:
  provisioner: metallb.drivers.local.sdn.cozystack.io
  reclaimPolicy: Retain
  releaseDelay: 720h
  parameters:
    pool: public
```

- `is-default-class` makes this the class for claims that name none.
- `reclaimPolicy: Retain` keeps an address `Released` after its claim is deleted. `Delete` returns it to the pool at once.
- `releaseDelay` returns a `Released` address to `Available` after that long. Without it, a `Released` address stays until an admin deletes it or clears its `spec.claimRef`.

The driver reports a refused pool (missing, auto-assigning, or named by another class) as a `PoolRefused` event on the class. A pool that sets `serviceAllocation` must admit `cozy-metallb-iad` and every namespace whose Services name claims of the class; the driver does not check this.

Classes are not scoped per tenant, in the same way that StorageClasses are not: any tenant that can create claims can claim from any class.

### Reserving part of an existing pool

MetalLB rejects overlapping pools, so a range that an auto-assigning pool covers today cannot simply be named by a class. Shrink the existing pool so it no longer covers the part to reserve, create a new pool with `autoAssign: false` for that part, and name the new pool in the class. Check `kubectl get svc -A` first: MetalLB withdraws any assigned address that falls outside the shrunk pool. Adopt those addresses into claims first, or leave them in the shared pool. The [metallb-iad README](https://github.com/cozystack/metallb-iad#reserving-part-of-an-existing-pool) has the procedure, and the [address-controller operating guide](https://github.com/cozystack/address-controller/blob/main/docs/operating.md#adopting-an-address-a-service-already-holds) shows how to adopt an address a Service already holds.

## Reserving and attaching an address

Tenant admins can create, update and delete `IPAddressClaim`s in their own namespace, and every access level from view upward can read them. Tenants get no access to the cluster-scoped `IPAddress` and `IPAddressClass` objects. They read the address they were given from their own claim:

```yaml
apiVersion: local.sdn.cozystack.io/v1alpha1
kind: IPAddressClaim
metadata:
  name: web
  namespace: tenant-example
spec:
  className: public   # optional when a default class exists
  family: IPv4        # IPv4 (default), IPv6 or Dual
```

```sh
kubectl -n tenant-example get ipaddressclaim web -o jsonpath='{.status.addresses[*].address}'
```

A claim is `Pending` until every requested family is bound, then `Bound`.

To attach the address, a `LoadBalancer` Service in the same namespace names the claim with the annotation `local.sdn.cozystack.io/ip-address-claim: web`. Removing the annotation detaches the address again, and the claim keeps it reserved. Tenants do not create Services in their namespace directly. The path that works today is a tenant Kubernetes cluster: its cloud provider copies a guest `LoadBalancer` Service's annotations onto the Service it creates in the tenant namespace, so the annotation goes on the guest Service. Managed applications do not expose the annotation yet.

### Auto-claim

The core can also create a claim for a `LoadBalancer` Service that names none, so that ordinary Services draw reserved, attributable addresses too. It is off until an admin opts in, either by marking one class with `ipaddressclass.local.sdn.cozystack.io/is-auto-claim-class: "true"` or by naming a class on the Service with `local.sdn.cozystack.io/ip-address-class: <class>`. The auto-created claim is named after the Service and owned by it, so deleting the Service deletes the claim and its addresses whatever the class's reclaim policy. Remove the claim's owner reference to keep the address. Services that already name a claim, set `local.sdn.cozystack.io/auto-claim: "false"`, set `spec.loadBalancerClass` or `spec.loadBalancerIP`, carry a MetalLB pool, pin or sharing annotation, or already have an address are skipped.

On a tenant Kubernetes cluster, `local.sdn.cozystack.io/ip-address-class` on a guest Service reaches the host the same way as the claim annotation. This is how a guest Service chooses between classes, for example a public and a private one, now that the admission policy below denies `metallb.io/address-pool` on tenant Services.

## The admission policy

MetalLB pins or selects an address from any writer of a Service, through its `metallb.io/` annotations, their legacy `metallb.universe.tf/` predecessors, and `spec.loadBalancerIP`. A tenant who could set those fields could point MetalLB at an address reserved for someone else. The driver would mark the address `Conflict`, but only after the fact.

The `cozystack.metallb-iad` package therefore enables the driver's `metallb-iad-service-pins` `ValidatingAdmissionPolicy`, in `Deny` mode. It reserves the `loadBalancerIPs`, `address-pool` and `allow-shared-ip` annotations under both prefixes, `spec.loadBalancerIP`, and the driver's own `pinned` marker. Only these principals may set, change or remove those fields:

- the driver's ServiceAccount;
- members of `system:masters`, `kubeadm:cluster-admins` and `cozystack-cluster-admin`, the group Cozystack's OIDC administrators authenticate as.

A write that leaves those fields as they were is always admitted, so the driver's pin on a tenant's Service does not stop the tenant's tooling from updating the rest of that Service. The policy applies only to namespaces labelled `namespace.cozystack.io/host`, which `tenant-root` and every tenant namespace carry and no `cozy-*` namespace does. Platform components that set these fields themselves are unaffected.

Enabling the package changes what tenants can do today:

- A guest Service on a tenant Kubernetes cluster that sets `metallb.io/address-pool` or `spec.loadBalancerIP` is denied on the host. The cloud provider then keeps retrying it. Choose a class with `local.sdn.cozystack.io/ip-address-class` instead, or reserve a claim and name it.
- Removing a pin that an admin wrote by hand also takes an admin.

To see what the policy would deny before enforcing it, switch it to warn and audit through the package's values:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.metallb-iad
spec:
  variant: default
  components:
    metallb-iad:
      values:
        metallb-iad:
          admissionPolicy:
            validationActions: [Warn, Audit]
```

The same block takes `allowedUsernames` and `allowedGroups` to exempt further principals. A values list replaces the default list rather than extending it, so restate the three groups above when adding one.

## Air-gapped and mirrored installs

The two controller images are published by their own projects under `ghcr.io/cozystack/<name>`, outside the `ghcr.io/cozystack/cozystack/` repositories that Cozystack's release tooling retags and mirrors. A cluster that pulls through a mirror must copy them itself. The references shipped with the packages are:

- `ghcr.io/cozystack/address-controller:main-90e65ca@sha256:74e4c7cf63f730ebe61527fdcd2b06e1bca2c383a66522dd4734aab9e66a9331`
- `ghcr.io/cozystack/metallb-iad:main-1faf937@sha256:a2a8b05a887f9f28927d75f8b57e264be40e8770d0177798b4f06a0f69c3e793`

Mirror them by digest, and point the packages at the mirror through the `image` value of each component (`address-controller.image` on `cozystack.address-controller`, `metallb-iad.image` on `cozystack.metallb-iad`).

## Teardown

Claims, addresses and classes carry finalizers that the core removes, and the driver adds its own to the addresses it creates. While those objects exist, deleting them, or deleting a tenant namespace that holds claims, hangs if a controller is not running, for example after its Package has been deleted. Remove the feature in this order:

1. Remove the claim annotation from Services, or delete the Services.
2. Delete every `IPAddressClaim`.
3. Delete the remaining `IPAddress` objects (`Released`, `Available`).
4. Delete the `IPAddressClass` objects.
5. Remove both packages from `bundles.enabledPackages`, then delete the `cozystack.metallb-iad` and `cozystack.address-controller` Packages. The platform does not delete a Package it stops emitting.

A class is held until no `IPAddress` of it is left, in any phase, and reports a `ClassInUse` event naming the addresses that hold it. Deleting a class does not touch MetalLB: the pool and advertisement are the admin's. If the controllers are already gone, the [operating guide](https://github.com/cozystack/address-controller/blob/main/docs/operating.md#removing-the-controllers) has the commands to clear the finalizers by hand. Use the fully qualified kind names in them: `ipaddresses` alone resolves to the Kubernetes `networking.k8s.io` kind.

## Upgrading

The API is `v1alpha1` and has no conversion webhook. The `cozystack.address-controller` package installs its CRDs with `upgradeCRDs: CreateReplace`, so every upgrade replaces them. A field that a later release removes or renames invalidates stored objects that still set it. Read the schema changes of every release before upgrading; the [operating guide](https://github.com/cozystack/address-controller/blob/main/docs/operating.md#upgrading-the-crds) lists them per release.
