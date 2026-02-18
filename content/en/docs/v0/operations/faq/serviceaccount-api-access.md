---
title: "ServiceAccount Tokens for API Access"
linkTitle: "ServiceAccount API Access"
description: "How to retrieve and use ServiceAccount tokens in Cozystack."
weight: 20
aliases:
  - /docs/v0/operations/api-access
  - /docs/operations/api-access
---

## Prerequisites

Before you begin, make sure that:
-   A tenant already exists in Cozystack.
    See [Create a User Tenant]({{% ref "/docs/v0/getting-started/create-tenant" %}}) if you haven't created one yet.
-   You have access to the tenant namespace — either via OIDC credentials or an administrative kubeconfig.
-   `kubectl` is installed and configured.
-   (Optional) `jq` is installed.


## Retrieving the ServiceAccount Token

Each tenant in Cozystack has a Secret that contains a ServiceAccount token.
The Secret has the same name as the tenant and is located in the tenant's namespace.

{{< tabs name="get_token" >}}
{{% tab name="Dashboard" %}}

1.  Log in to the Dashboard as a user with access to the tenant.
1.  Switch context to the target tenant if needed.
1.  On the left sidebar, navigate to the **Administration** → **Info** page and open the **Secrets** tab.
1.  Find the secret named `tenant-<name>` (e.g. `tenant-team1`), where the **Key** is **token**.
1.  Click the eye icon to reveal the **Value** field, then click the revealed data. The text will be copied to the clipboard automatically.

{{% /tab %}}

{{% tab name="kubectl" %}}

Retrieve the token for a tenant named `<name>`:

```bash
kubectl -n tenant-<name> get tenantsecret tenant-<name> -o json | jq -r '.data.token | @base64d'
```

To store the token in a variable for subsequent commands:

```bash
export TOKEN=$(kubectl -n tenant-<name> get tenantsecret tenant-<name> -o json | jq -r '.data.token | @base64d')
```

{{% /tab %}}
{{< /tabs >}}

## Using the Token for API Access

Once you have the token, you can [generate a kubeconfig]({{% ref "/docs/v0/operations/faq/generate-kubeconfig" %}}) for kubectl access, or use it directly with `curl` as shown below.

{{% alert color="warning" %}}
**Token Security**

ServiceAccount tokens in Cozystack **do not expire** by default. Handle them with the same care as passwords.
{{% /alert %}}

### Test the Connection

First, verify your kubectl context points to the correct Cozystack cluster:

```bash
kubectl config current-context
kubectl cluster-info
```

Next, get the API server address:

```bash
export API_SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
```

Then, extract the CA certificate from the tenant secret:

```bash
kubectl -n tenant-<name> get secret tenant-<name> -o jsonpath='{.data.ca\.crt}' | base64 -d > ca.crt
```

Now, test the connection:

```bash
curl --cacert ca.crt -H "Authorization: Bearer ${TOKEN}" ${API_SERVER}/api
```

> You can remove `ca.crt` after testing.
