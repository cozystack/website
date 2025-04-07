---
title: How to configure GitLab as an Identity Provider
linkTitle: Gitlab
description: "How to configure GitLab as an Identity Provider"
weight: 30
---

You can use Gitlab identity provider for Keycloak

### Overview

## Create Application in Gitlab

- Open `https://gitlab.com/groups/<YOUR_GROUP>/-/settings/applications`
- Click `Add new application`
- Name: cozy, Redirect URI: `https://keycloak.<root-host>/realms/cozy/broker/gitlab/endpoint`
- Enable Confidential, api, read_api, read_user, openid, profile, email
- Copy and save Secret


## Configure Keycloak Identity Provider
Create a `KeycloakRealmIdentityProvider` resource with the following configuration:

```yaml
apiVersion: v1.edp.epam.com/v1
kind: KeycloakRealmIdentityProvider
metadata:
  name: gitlab
spec:
  realmRef:
    name: keycloakrealm-cozy
    kind: ClusterKeycloakRealm
  alias: gitlab
  authenticateByDefault: false
  enabled: true
  providerId: "gitlab"
  config:
    clientId: "YOUR GITLAB APP ID"
    clientSecret: "YOUR GITLAB APP SECRET"
    syncMode: "IMPORT"
  mappers:
    - name: "username"
      identityProviderMapper: "oidc-username-idp-mapper"
      identityProviderAlias: "gitlab"
      config:
        target: "LOCAL"
        syncMode: "INHERIT"
        template: "${ALIAS}---${CLAIM.preferred_username}"
```
