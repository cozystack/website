---
title: "OIDC authentication for Grafana"
linkTitle: "OIDC authentication"
description: "Give tenant users per-identity Grafana access with per-instance audience isolation."
weight: 5
---

Cozystack Grafana instances can authenticate users through OIDC instead of the shared `admin_user` / `admin_password` Secret. Each user then has their own identity, per-user audit, and a role that can be revoked by removing them from a Keycloak group.

The identity model is deliberately **per-instance** rather than per-tenant: each Monitoring release (per-tenant `monitoring`, plus the platform's `monitoring-system`) gets its own OIDC audience, and a token minted for instance A is rejected by instance B's Grafana. That gives cross-tenant isolation without provisioning a Keycloak realm per tenant. The full rationale (why per-cluster audience and not per-tenant realm; how it relates to Keycloak Organizations; what BYO-OIDC looks like) is in the [design proposal](https://github.com/cozystack/community/pull/24). The tenant kube-apiserver's Phase 1 ([cozystack/cozystack#3044](https://github.com/cozystack/cozystack/pull/3044)) uses the same shape; this Grafana integration is the Phase-1 follow-up called out in that PR's body.

{{% alert color="info" %}}
The `grafana-admin-password` Secret in the tenant namespace stays available as a break-glass path regardless of whether OIDC is enabled. `disable_login_form` is not flipped by the selector.
{{% /alert %}}

## Modes

`spec.oidc.mode` picks the identity source on the `Monitoring` CR:

- **`None`** — the default. No OIDC; only the `admin_user` / `admin_password` Secret works. Existing instances render identically to before.
- **`System`** — trust the platform `cozy` Keycloak realm via a per-instance confidential client and audience binding. Users are the ones a Cozystack platform admin already provisioned in `cozy`; the tenant does not manage a directory of its own.
- **`CustomConfig`** — trust a tenant-supplied issuer directly (BYO IdP: Okta, Auth0, a customer's own Keycloak). `cozy` is not in the path.

## Enable OIDC — `System` mode

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Monitoring
metadata:
  name: monitoring
  namespace: tenant-acme
spec:
  oidc:
    mode: System
  # ...
```

Cozystack provisions:

- A per-instance `KeycloakClient` in the `cozy` realm with `clientId` set to `<namespace>-<release>` (for the CR above: `tenant-acme-monitoring`). `public: false`, `directAccess: false`, `secret` sourced from a chart-owned Kubernetes Secret. `redirectUris` locked to `https://grafana.<host>/login/generic_oauth`.
- A per-instance `KeycloakClientScope` whose audience mapper pins the token's `aud` claim to that same `clientId` — the isolation primitive.
- Three `KeycloakRealmGroup` objects — `<namespace>-<release>-admin`, `-editor`, `-viewer`. The chart owns the groups; membership is managed out-of-band by a Keycloak operator.
- A persistent Kubernetes Secret carrying the confidential `client-secret` (random on first install, preserved on upgrades).
- The Grafana CR's `spec.config.auth.generic_oauth` section wired to the cozy realm issuer, per-instance audience scope, and a `role_attribute_path` that maps the three groups above to Grafana's `Admin` / `Editor` / `Viewer` roles.

The platform Grafana release (`monitoring-system` in the `cozy-monitoring` namespace) additionally gets `allow_assign_grafana_admin: true` so an `Admin`-group member is auto-promoted to server-level `GrafanaAdmin`. Tenant Grafana instances stay at org-level Admin.

### Prerequisite

`System` mode requires the platform-level OIDC feature (`authentication.oidc.enabled` at the Cozystack platform values). If the flag is off, the chart hard-fails the render with a clear message. Ask a Cozystack platform admin to enable it, or use `CustomConfig`.

## Enable OIDC — `CustomConfig` mode

Bring your own issuer. Two supply paths, **mutually exclusive**:

```yaml
spec:
  oidc:
    mode: CustomConfig
    customConfig:
      config:
        client_id: my-grafana
        client_secret: xxxxxxxx
        auth_url: https://idp.acme.example/protocol/openid-connect/auth
        token_url: https://idp.acme.example/protocol/openid-connect/token
        api_url: https://idp.acme.example/protocol/openid-connect/userinfo
        scopes: openid email profile groups
        role_attribute_path: "contains(groups[*], 'grafana-admins') && 'Admin' || 'Viewer'"
```

…or via a pre-existing Secret in the tenant namespace holding a ready-made `[auth.generic_oauth]` ini fragment in the `auth.ini` key:

```yaml
spec:
  oidc:
    mode: CustomConfig
    customConfig:
      secretRef:
        name: acme-byo-grafana-auth
```

Setting both `config` and `secretRef.name` (or neither) fails the render. In `CustomConfig` mode no Keycloak objects are provisioned in `cozy`; the Grafana instance trusts the operator-supplied issuer directly.

## Assigning roles

Grafana has three org-level roles — `Admin`, `Editor`, `Viewer` — and the chart drives them via `role_attribute_path`:

```text
contains(groups[*], '<ns>-<release>-admin')  && 'Admin'  ||
contains(groups[*], '<ns>-<release>-editor') && 'Editor' ||
contains(groups[*], '<ns>-<release>-viewer') && 'Viewer' ||
'Viewer'
```

Authenticated users with none of the three groups default to `Viewer`. To give a user a role, add them to the corresponding `KeycloakRealmGroup` in the `cozy` realm — either through the Keycloak UI or with a `KeycloakRealmUser` CR:

```yaml
apiVersion: v1.edp.epam.com/v1
kind: KeycloakRealmUser
metadata:
  name: alice-acme
  namespace: cozy-keycloak
spec:
  realm: cozy
  username: alice@acme.example
  email: alice@acme.example
  emailVerified: true
  password: "…"
  groups:
    - tenant-acme-monitoring-admin
```

Removing a user from the group demotes them on the next login; deleting them from `cozy` revokes access outright.

## Sign in

Open `https://grafana.<host>` and use the "Sign in with Keycloak" button under the login form. Grafana runs the Authorization Code + PKCE flow against `cozy`, receives a token whose `aud` matches this Monitoring instance's clientId, and creates or updates the local Grafana user on the first successful login with the role from `role_attribute_path`.

The `admin_user` / `admin_password` field on the form stays wired to `grafana-admin-password` and continues to work.

## Prerequisites and gotchas

- **`emailVerified: true` on Keycloak users.** Phase 1 does not add a `claimValidationRules` entry — so `email_verified` is not chart-enforced. Set `emailVerified: true` on the `KeycloakRealmUser` (or complete the email-verify flow through the Keycloak UI) so the identity holding a given email is guaranteed authentic. The `cozy` realm's default `duplicateEmails: false` prevents a second account from claiming an already-registered address. CEL `claimValidationRules` to make this a hard gate is a follow-up hardening path.
- **BYO issuer with a self-signed CA.** In `CustomConfig` mode the `secretRef` path is the way to ship a CA bundle alongside the `[auth.generic_oauth]` block — you package `auth.ini` and any `ca-cert` files into the Secret and mount both under `/etc/grafana/oidc`.
- **`admin_user` stays a break-glass path.** Even under `mode: System` the login form and the `grafana-admin-password` Secret remain wired. Locking the form off is a follow-up hardening.

## What's out of scope for this feature

- **Per-tenant Keycloak realms.** Managed multi-tenant identity is a separate proposal, evaluated against Keycloak Organizations. Track it in the [community proposal](https://github.com/cozystack/community/pull/24).
- **Federating an external IdP into the platform `cozy` realm.** BYO-for-Cozystack-itself is a distinct problem — this feature is BYO-for-a-managed-service.
- **Full-logout through Keycloak's end-session endpoint.** Native `auth.generic_oauth` covers the OAuth part; `backend-logout-url` wiring is a follow-up.
- **CEL `claimValidationRules` for `email_verified`.** Explicit-gate hardening; not required for Phase 1 given the layered guarantees above.
