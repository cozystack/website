---
title: "4. Create a User Tenant and Configure Access"
linkTitle: "4. Create User Tenant"
description: "Create a user tenant, the foundation of RBAC in Cozystack, and get access to it via dashboard and Cozystack API."
weight: 40
---

## Objectives

At this step of the tutorial, you will create a user tenant — a space for users to deploy applications and VMs.
You will also get tenant credentials and log in as a user with access to this tenant.

## Prerequisites

Before you begin:


-   Complete the previous steps of the tutorial to get 
    a [Cozystack cluster]({{% ref "/docs/getting-started/install-cozystack" %}}) running,
    with storage, networking, and management dashboard configured.
    
-   Make sure you can access the dashboard, as described in the
    [previous step of the tutorial]({{% ref "/docs/getting-started/install-cozystack" %}}).
    
-   If you're using OIDC, users and roles must be configured.
    See the [OIDC guide]({{% ref "/docs/operations/oidc" %}}) for details on how to work with the built-in OIDC server.

During [Kubernetes installation]({{% ref "/docs/getting-started/install-kubernetes" %}}) for Cozystack, 
you should have obtained the administrative `kubeconfig` file for your new cluster.
Keep it at hand — it may be useful later for troubleshooting.
However, for day-to-day operations, you'll want to create user-specific credentials.


## Introduction

Tenants are the isolation mechanism in Cozystack.
They are used to separate clients, teams, or environments.
Each tenant has its own set of applications and one or more nested Kubernetes clusters.
Tenant users have full access to their clusters.
Optionally, you can configure quotas for each tenant to limit resource usage and prevent overconsumption.

To learn more about tenants, read the [Core Concepts]({{% ref "/docs/guides/concepts#tenant-system" %}}) guide.


## Create a Tenant

Tenants are created using the Cozystack application named `Tenant`.
After installation, Cozystack includes a built-in tenant called `tenant-root`.
This root tenant is reserved for platform administrators and should only be used to create child tenants.
Although it’s technically possible to install applications in `tenant-root`,
doing so is **not recommended** for production environments.

{{< tabs name="create_tenant" >}}
{{% tab name="Using Dashboard" %}}

1.  Open the dashboard as a `tenant-root` user.
1.  Ensure the current context is set to `tenant-root`.
    Switch context and reload the page if needed.
1.  Navigate to the **Catalog** tab.
1.  Search for the **Tenant** application and open it.
1.  Review the documentation, then click the **Deploy** button to proceed to the parameters page.
1.  Fill in the tenant `name`.
    It is the only parameter that can't be changed later.
1.  (Optional) Fill in the domain name in `host`.
    This domain name must already exist.
    Ensure that the tenant user has enough control over the domain to configure DNS records.
    If left blank, the domain will default to `<name>.<cozystack-domain>`.
1.  Select the checkboxes to install system-level apps: `etcd`, `monitoring`, `ingress`, and `seaweedfs`.
    Tenant users will **not** be able to install or uninstall these apps — only administrators can.

    The `etcd` option is required for nested Kubernetes.
    Select it before installing the **Kubernetes** application in the tenant.
    Only disable it if you're certain the tenant won’t use nested Kubernetes.
1.  The `isolated` option determines whether sibling tenants can communicate over the network.
    This does **not** affect visibility in the dashboard.
    In most cases, it should be enabled (i.e., isolation is on).
1.  By default, no resource quotas are set.
    This means no usage limits.
    You can define quotas to prevent resource overuse.
1.  Click **Deploy <version>** to install the tenant application into the root tenant.

{{% /tab %}}

{{% tab name="Using kubectl" %}}

Create a HelmRelease manifest for the tenant. You can use a manifest created via the dashboard as a starting point:

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: tenant-team1
  namespace: tenant-root
spec:
  chart:
    spec:
      chart: tenant
      reconcileStrategy: Revision
      sourceRef:
        kind: HelmRepository
        name: cozystack-apps
        namespace: cozy-public
      version: 1.9.1
  interval: 0s
  values:
    etcd: true
    host: team1.example.org
    ingress: true
    isolated: true
    monitoring: false
    resourceQuotas: {}
    seaweedfs: false
```

Apply the manifest:

```bash
# Use the kubeconfig for the root tenant
export KUBECONFIG=./kubeconfig-tenant-root
# Apply the manifest
kubectl -n tenant-root apply -f hr-tenant-team1.yaml
```

{{% /tab %}}
{{< /tabs >}}

You can assist tenant users with installing database applications or nested Kubernetes clusters.
As an administrator, you can switch context in the dashboard to access any tenant.
Tenant users, however, can only access their own tenant and any child tenants.


## Get Tenant Kubeconfig

Tenant users need a kubeconfig file to access their Kubernetes cluster.
The method to retrieve it depends on whether OIDC is enabled in your Cozystack setup.

### With OIDC Enabled

You can retrieve the kubeconfig file directly from the dashboard, as described in the
[OIDC guide]({{% ref "/docs/operations/oidc/enable_oidc#step-4-retrieve-kubeconfig" %}}).

### Without OIDC

As an administrator, you'll need to retrieve a service account token from the tenant namespace.
The secret holding the token has the same name as the tenant.

To retrieve the token for a tenant named `team1`, run:

```bash
kubectl -n tenant-team1 get secret tenant-team1 -o json | jq -r '.data.token | @base64d'
```

Next, insert this token into a kubeconfig template, and save the file as `kubeconfig-tenant-<name>.yaml`.

Make sure to also set the default namespace to the tenant name.
Many GUI clients will display permission errors if the namespace is not explicitly defined.

The same token can also be used by the tenant user to log into the Cozystack dashboard if OIDC is disabled.

### Get Nested Kubernetes Kubeconfig

In general, administrators do **not** need to retrieve kubeconfig files for nested Kubernetes clusters.

These clusters are installed by the tenant user, within their own tenant namespace.
Tenant users have full control over their nested Kubernetes environments.

To access a nested Kubernetes cluster, the tenant user can download the kubeconfig file
directly from the corresponding application's page in the dashboard.
