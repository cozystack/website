---
title: "OIDC authentication for Grafana"
linkTitle: "OIDC authentication"
description: "Give tenant users per-identity Grafana access with per-instance audience isolation and tenant-membership gating."
weight: 5
---

Cozystack Grafana instances can authenticate users through OIDC instead of the shared `admin_user` / `admin_password` Secret. Each user then has their own identity, per-user audit, and a role that can be revoked by removing them from `spec.oidc.users` on the `Monitoring` CR.

The identity model is deliberately **per-instance** rather than per-tenant: every Monitoring instance (one inner `monitoring-system` release per namespace — each tenant's own, plus the platform's in `tenant-root`) gets its own OIDC audience, and a token minted for instance A is rejected by instance B's Grafana. Cross-tenant sign-in is additionally blocked by a `allowed_groups` gate on the release's namespace-scoped `<ns>-{view,use,admin,super-admin}` groups (chart-owned in the tenant chart; the platform-managed `groups` scope in the `cozy` realm makes them visible on every token). The full rationale is in the [design proposal](https://github.com/cozystack/community/pull/24). The tenant kube-apiserver's Phase 1 ([cozystack/cozystack#3044](https://github.com/cozystack/cozystack/pull/3044)) uses the same shape; this Grafana integration is the Phase-1 follow-up called out in that PR's body.

{{% alert color="info" %}}
The `grafana-admin-password` Secret in the release namespace stays available as a break-glass path regardless of whether OIDC is enabled. `disable_login_form` is not flipped by the selector.
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
    users:
      - email: alice@acme.example
        role: Admin
      - email: bob@acme.example
        role: Editor
      - email: carol@acme.example
        role: Viewer
  # ...
```

Cozystack provisions the following. Every derived identifier below uses `<release>`, the name of the inner HelmRelease that actually carries the OIDC templates. A `Monitoring` CR's release name is forced to `monitoring` (`check-release-name.yaml` rejects any other name), and its inner release is always `<release-name>-system`, so `<release>` is literally `monitoring-system` in every namespace — `tenant-acme-monitoring-system` for the CR above. Instances are told apart by namespace, not by release name:

- A per-instance **`KeycloakClient`** in the `cozy` realm with `clientId` set to `<namespace>-<release>` (for the CR above: `tenant-acme-monitoring-system`). Confidential (`clientAuthenticatorType: client-secret`), `secret` sourced from a chart-owned Kubernetes Secret. `redirectUris` locked to `https://grafana.<host>/login/generic_oauth`.
- A per-instance **`KeycloakClientScope`** whose audience mapper pins the token's `aud` claim to that same `clientId` — the isolation primitive.
- A persistent Kubernetes **Secret** carrying the confidential `client-secret` (random on first install, preserved on upgrades).
- A chart-owned **users-reconcile Job** (`<release>-oidc-users`) that syncs `spec.oidc.users[]` into the Grafana instance on every reconcile: creates missing Grafana accounts, patches roles, and prunes stale org members. Runs as a post-install / post-upgrade hook when `users[]` is non-empty; omitted otherwise (BYO-IdP-friendly).
- An **`auth.generic_oauth`** entry under the Grafana CR's **`spec.config`** (a single ini-section key literally named `auth.generic_oauth`, so it is addressed as `spec.config["auth.generic_oauth"]`, not a two-level `auth` / `generic_oauth` nesting), wired to the cozy realm issuer, per-instance audience scope, and the tenant-membership gate:

  ```ini
  allowed_groups        = <namespace>-view <namespace>-use <namespace>-admin <namespace>-super-admin
  groups_attribute_path = groups
  ```

  `groups_attribute_path` is REQUIRED alongside `allowed_groups` on Grafana v11.x+: without it Grafana leaves the extracted `user.Groups` slice empty regardless of what the userinfo endpoint returns, and the gate rejects every login with "user not a member of one of the required groups" even when the token carries the correct claim. The JMESPath expression `groups` reads the top-level `groups` array from userinfo — the shape Keycloak's `oidc-group-membership-mapper` emits.

  When `spec.oidc.users[]` is non-empty the chart additionally forces:

  ```ini
  skip_org_role_sync                = true
  oauth_allow_insecure_email_lookup = true
  allow_sign_up                     = false
  ```

  `skip_org_role_sync=true` keeps a login from overwriting the users-Job's role assignments; `oauth_allow_insecure_email_lookup=true` lets Grafana attach the OIDC identity to the pre-provisioned local account by email; `allow_sign_up=false` is the isolation lever — without it, Grafana's default `allow_sign_up=true` combined with `skip_org_role_sync=true` would mint a Viewer account for every `cozy`-realm identity that hits the login flow.

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
        enabled: "true"
        client_id: my-grafana
        client_secret: xxxxxxxx
        auth_url: https://idp.acme.example/protocol/openid-connect/auth
        token_url: https://idp.acme.example/protocol/openid-connect/token
        api_url: https://idp.acme.example/protocol/openid-connect/userinfo
        scopes: openid email profile groups
    users:
      - email: alice@acme.example
        role: Admin
```

...or via a pre-existing Secret in the tenant namespace holding a ready-made `[auth.generic_oauth]` ini fragment in the `auth.ini` key:

```yaml
spec:
  oidc:
    mode: CustomConfig
    customConfig:
      secretRef:
        name: acme-byo-grafana-auth
```

Setting both `config` and `secretRef.name` (or neither) fails the render. In `CustomConfig` mode no Keycloak objects are provisioned in `cozy`; the Grafana instance trusts the operator-supplied issuer directly.

The `secretRef` path is authoritative — the chart does not overlay any keys onto the operator-supplied ini fragment. If you use `secretRef`, `spec.oidc.users[]` MUST be empty (the chart fails the render otherwise) because the users-Job cannot reason about a config it cannot see.

On the `inline config` path, when `users[]` is non-empty the chart-forced users-map contract (`skip_org_role_sync=true`, `oauth_allow_insecure_email_lookup=true`, `allow_sign_up=false`) is merged *over* your map and wins every conflict: the chart renders `merge $chartForced $yourConfig`, and Helm's `merge` keeps the left-hand (chart) values and only fills in keys your map is missing — so you cannot override those three. Unlike `System` mode, `CustomConfig` does not set `enabled` for you: your `config` MUST include `enabled: "true"` or Grafana leaves `auth.generic_oauth` disabled and no sign-in button appears. If your BYO IdP does not emit `groups` in the shape Grafana expects, add `groups_attribute_path` to your inline map to point at the right JMESPath.

## Assigning roles

Roles are driven by **`spec.oidc.users[]`**, not by group membership: each entry has an `email` (matched against the OIDC `email` claim on login) and a `role` (Grafana org-level: `Admin`, `Editor`, or `Viewer`). The users-Job creates or updates the local Grafana account on every reconcile and prunes stale members. Removing a user from the list revokes their access on the next chart apply — the users-Job removes them from the Grafana org (`DELETE /api/orgs/1/users/<id>`), an org-membership change rather than deletion of the underlying Grafana account; adding a user re-provisions them.

Login authorization is separate: the token owner MUST be a member of one of the release's tenant-scoped `cozy`-realm groups (`<namespace>-view`, `<namespace>-use`, `<namespace>-admin`, `<namespace>-super-admin`) for `allowed_groups` to accept the login. That gate is unconditional in `System` mode, independent of `users[]`.

Add a user to the appropriate tenant-scoped group in `cozy` — via the Keycloak UI or with a `KeycloakRealmUser` CR:

```yaml
apiVersion: v1.edp.epam.com/v1
kind: KeycloakRealmUser
metadata:
  name: alice-acme
  namespace: cozy-keycloak
spec:
  realmRef:
    name: keycloakrealm-cozy
    kind: ClusterKeycloakRealm
  username: alice@acme.example
  email: alice@acme.example
  emailVerified: true
  passwordSecret:
    name: alice-acme-password
    key: password
  groups:
    - tenant-acme-admin
```

The `cozy` realm is a cluster-scoped `ClusterKeycloakRealm` named `keycloakrealm-cozy`, so `spec.realmRef` (not `spec.realm`) is required, with `kind: ClusterKeycloakRealm`. `spec.passwordSecret` points at a Secret in the same namespace holding the initial password (`kubectl create secret generic alice-acme-password --namespace cozy-keycloak --from-literal=password=...`); the CRD also accepts an inline `spec.password`, but it is deprecated in favour of `passwordSecret`.

## Sign in

Open `https://grafana.<host>` and press "Sign in with Keycloak" under the login form. Grafana runs the OAuth Authorization Code flow against `cozy`, receives a token whose `aud` matches this Monitoring instance's clientId, checks the `groups` claim against `allowed_groups`, then looks up the pre-provisioned Grafana account by email and grants the users-Job-assigned role.

The `admin_user` / `admin_password` field on the form stays wired to `grafana-admin-password` and continues to work.

## Prerequisites and gotchas

- **`emailVerified: true` on Keycloak users.** `email_verified` is not enforced by Grafana: its `auth.generic_oauth` provider has no claim-validation option (claim handling is JMESPath only, and `role_attribute_path` is unused here because the users-Job drives roles). Enforce it on the Keycloak side instead: set `emailVerified: true` on the `KeycloakRealmUser` (or add the `VERIFY_EMAIL` required action / complete the email-verify flow in the Keycloak UI) so the identity holding a given email is guaranteed authentic. The `cozy` realm's default `duplicateEmails: false` additionally prevents a second account from claiming an already-registered address.
- **`groups_attribute_path` is not optional on Grafana v11.x+.** The chart wires it automatically for `System` mode; in `CustomConfig` inline the operator must add it explicitly (`groups_attribute_path: groups`) if their IdP emits a top-level `groups` array. Otherwise `allowed_groups` becomes a silent no-op and every login fails.
- **BYO issuer with a self-signed CA.** In `CustomConfig` mode the `secretRef` path is the way to ship a CA bundle alongside the `[auth.generic_oauth]` block — you package `auth.ini` and any `ca-cert` files into the Secret and mount both under `/etc/grafana/oidc`. Placing the file is not enough on its own: point `tls_client_ca` at it from inside your `auth.ini` so Grafana actually trusts the issuer's certificate.
- **`admin_user` stays a break-glass path.** Even under `mode: System` the login form and the `grafana-admin-password` Secret remain wired. Locking the form off is a follow-up hardening.
- **Mode toggle is non-destructive.** The users-Job renders only when `spec.oidc.mode` is not `None` *and* `spec.oidc.users[]` is non-empty. Flipping `spec.oidc.mode` from `System` to `None` therefore runs no reconcile and no prune pass: the Grafana accounts the Job provisioned survive untouched, and OIDC login is simply no longer offered on the form. Flipping back to `System` resumes reconciliation of `spec.oidc.users[]` against those existing accounts.

## What's out of scope for this feature

- **Per-tenant Keycloak realms.** Managed multi-tenant identity is a separate proposal, evaluated against Keycloak Organizations. Track it in the [community proposal](https://github.com/cozystack/community/pull/24).
- **Federating an external IdP into the platform `cozy` realm.** BYO-for-Cozystack-itself is a distinct problem — this feature is BYO-for-a-managed-service.
- **Full-logout through Keycloak's end-session endpoint.** Native `auth.generic_oauth` covers the OAuth part; `backend-logout-url` wiring is a follow-up.
- **Server-level `GrafanaAdmin` promotion.** All Grafana instances — platform and tenant — cap at org-level `Admin`; `allow_assign_grafana_admin` is not wired and the `Monitoring` CR exposes no field to opt in.
- **Role granularity beyond Admin/Editor/Viewer.** Grafana org roles are the assignment surface; team memberships / dashboard-level permissions stay out-of-band.
