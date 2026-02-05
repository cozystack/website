---
title: How to configure Google as an Identity Provider
linkTitle: Google
description: "How to configure Google as an Identity Provider"
weight: 30
aliases:
  - /docs/oidc/identity_providers/google
---

## Configure Google

- Head over to [Google Console](https://console.cloud.google.com/apis/dashboard), login in to the console using Google account and you will see Google Developer Console. Once logged in, head over the top left drop-down to create new project.
![1](/img/oidc/identity_providers/google/1.jpeg)

- Click on "New Project" to proceed.
![2](/img/oidc/identity_providers/google/2.jpeg)

- Enter the project name of your choice and select the Organisation if you have multiple organisations. Once done click on "Create"
![3](/img/oidc/identity_providers/google/3.jpeg)

- Once the project is created you will get a pop-up suggesting to configure the consent screen. If not then head over to the Dashboard and head over to "Explore and enable APIs" options. Then Click on "Credentials" > "Configure Consent Screen" and head over to the next step.
![4](/img/oidc/identity_providers/google/4.jpeg)

- Click on "External" as we want to allow any Google account to be able to sign in to our application and hit "Create".
![5](/img/oidc/identity_providers/google/5.jpeg)

- After this, we will be redirected to pages where we will have to configure different things
    - Application type: Public
    - Application name: Your application name
    - Authorised domains: Your application top-level domain name
    - Application Homepage link: Your application homepage
    - Application Privacy Policy link: Your application privacy policy link

- Now head over to the Create Credentials option in the navbar and click on "OAuth Client ID".
![6](/img/oidc/identity_providers/google/6.jpeg)

- Select Application type as a "Web application" and name the application according to your choice. Next, Add the link provided in the Keycloak tab under "Authorized Redirect URIs" and click "Create". The link should look something like this
```bash
https://YOUR_KEYCLOAK_DOMAIN/auth/realms/cozy/broker/google/endpoint
```
![7](/img/oidc/identity_providers/google/7.jpeg)

- As it is done, you will see a pop up with the information required in the next step. You will need to "Client ID" and "Client secret" in next step so make sure you make a safe copy of it.
![8](/img/oidc/identity_providers/google/8.jpeg)

## Configure Keycloak Identity Provider
Create a `KeycloakRealmIdentityProvider` resource with the following configuration:

```yaml
apiVersion: v1.edp.epam.com/v1
kind: KeycloakRealmIdentityProvider
metadata:
  name: google
spec:
  realmRef:
    name: keycloakrealm-cozy
    kind: ClusterKeycloakRealm
  alias: google
  authenticateByDefault: false
  enabled: true
  providerId: "google"
  config:
    clientId: "YOUR GOOGLE APP ID"
    clientSecret: "YOUR GOOGLE APP SECRET"
    syncMode: "IMPORT"
  mappers:
    - name: "username"
      identityProviderMapper: "oidc-username-idp-mapper"
      identityProviderAlias: "google"
      config:
        target: "LOCAL"
        syncMode: "INHERIT"
        template: "${ALIAS}---${CLAIM.email}"
```
