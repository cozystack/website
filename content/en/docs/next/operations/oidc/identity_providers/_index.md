---
title: "Identity providers"
linkTitle: "Identity providers"
description: "Identity providers managment."
weight: 70
aliases:
  - /docs/next/oidc/identity_providers
---

## Linking straight to an identity provider

When an identity provider is configured, Keycloak's login page offers it as a button next to the username and password form. An external portal that signs its users in through that provider can skip the page by sending them to the dashboard's login start and naming the provider's alias:

```
https://dashboard.<root-host>/oauth2/start?rd=/admin/tenants&kc_idp_hint=<alias>
```

`rd` is the dashboard path to land on after the login, and `<alias>` is the `alias` of the `KeycloakRealmIdentityProvider`. The dashboard passes `kc_idp_hint` on to Keycloak only when the alias consists of letters, digits, `.`, `_` and `-`; any other value is dropped and Keycloak shows its login page as usual. A browser that already has a Keycloak session is signed in with that session, and the hint is not used.
