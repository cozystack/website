---
title: "Enable OIDC Server"
linkTitle: "OIDC Server"
description: "How to enable OIDC Server"
weight: 36
---

## Prerequisites

1. **OIDC Configuration**  
   Your API server must be configured to use OIDC. If you are using Talos Linux, your machine configuration should include the following parameters:

   ```yaml
   cluster:
     apiServer:
       extraArgs:
         oidc-issuer-url: "https://keycloak.example.org/realms/cozy"
         oidc-client-id: "kubernetes"
         oidc-username-claim: "preferred_username"
         oidc-groups-claim: "groups"
   ```

2. **Domain Reachability**  
   Ensure that the domain `keycloak.example.org` is accessible from the cluster and resolves to your root ingress controller.

3. **Storage Configuration**  
   Storage must be properly configured.

## Configuration  

If all prerequisites are met, you can proceed with the configuration steps.

### Step 1: Enable OIDC in Cozystack  

Edit your Cozystack ConfigMap to enable OIDC:

```bash
kubectl patch -n cozy-system configmap cozystack --type=merge -p '{"data":{"oidc-enabled": "true"}}'
```

If you need to add extra redirect URLs for the dashboard client (for example, when accessing the dashboard via port-forwarding), edit your Cozystack ConfigMap.
Multiple redirect URLs should be separated by commas.

```bash
kubectl patch -n cozy-system configmap cozystack --type=merge -p '{"data":{"extra-keycloak-redirect-uri-for-dashboard": "http://127.0.0.1:8080/oauth2/callback/*,http://localhost:8080/oauth2/callback/*"}}'
```

Within one minute, CozyStack will reconcile the ConfigMap and create three new `HelmRelease` resources:

```bash
# kubectl get hr -n cozy-keycloak
cozy-keycloak                    keycloak                    26s    Unknown   Running 'install' action with a timeout of 5m0s
cozy-keycloak                    keycloak-configure          26s    False     dependency 'cozy-keycloak/keycloak-operator' is not ready
cozy-keycloak                    keycloak-operator           26s    False     dependency 'cozy-keycloak/keycloak' is not ready
```

### Step 2: Wait for Installation Completion  

Wait until all resources are successfully installed and reach the `Ready` state:

```bash
NAME                 AGE     READY   STATUS
keycloak             2m19s   True    Release reconciliation succeeded
keycloak-configure   2m19s   True    Release reconciliation succeeded
keycloak-operator    2m19s   True    Release reconciliation succeeded
```

<!-- TODO: automate this -->
Reconcile tenants:

```
kubectl annotate -n tenant-root hr/tenant-root reconcile.fluxcd.io/forceAt=$(date +"%Y-%m-%dT%H:%M:%SZ") --overwrite
```

### Step 3: Access Keycloak  

You can now access Keycloak at `https://keycloak.example.org` (replace `example.org` with your infrastructure domain).

To get the Keycloak credentials, run the following command:

```bash
kubectl get secret -o yaml -n cozy-keycloak keycloak-credentials -o go-template='{{ printf "%s\n" (index .data "password" | base64decode) }}'
```

1. **Create a User in the Cozy Realm**  
   Follow the [Keycloak documentation](https://www.keycloak.org/docs/latest/server_admin/index.html#proc-creating-user_server_administration_guide) to create a user in the Cozy realm.
   {{% alert color="info" %}}
   Users must have a verified email address in Keycloak. This is required for proper OIDC authentication.
   To verify an email:
   1. Access the user details in Keycloak admin console
   2. Navigate to the Credentials tab
   3. Use the "Email Verification" action
   {{% /alert %}}

2. **Add User to the `kubeapps-admin` Group**  
   Assign the user to the `kubeapps-admin` group.

### Step 4: Retrieve Kubeconfig

To access the cluster through the Dashboard, download your kubeconfig by selecting the deployed tenant and copying the secret from the resource map.

This kubeconfig will be automatically configured to use OIDC authentication and the namespace dedicated to the tenant.

Setup [kubelogin](https://github.com/int128/kubelogin) which is necessary to use an OIDC-enabled kubeconfig.
```bash
# Homebrew (macOS and Linux)
brew install int128/kubelogin/kubelogin

# Krew (macOS, Linux, Windows and ARM)
kubectl krew install oidc-login

# Chocolatey (Windows)
choco install kubelogin
```
