---
title: "Create tenant and get access to it"
linkTitle: "Create tenant"
description: "Learn how to create a tenant and get credentials for users to access it"
weight: 40
---

In short, tenants are the isolation feature of Cozystack. They are used to separate clients, teams or environments.
Tenants also may have quotes set to prevent overuse of resources. Each tenant has its own set of applications and one or
more nested Kubernetes. Tenant users have full access to their Kubernetes.

## Prerequisites

We will need a running Cozystack installation. You can use
the [installation guide]({{% ref "/docs/getting-started/first-deployment" %}}) to install it.

While installing Talos for Cozystack you should have get the `KUBECONFIG` for you new cluster. This config file was
required to bootstrap the framework. It may also be useful later for system troubleshooting if something goes wrong.
But for day-to-day operations you must create the user credentials.

Ensure you can access the dashboard as described in
the [installation guide]({{% ref "/docs/getting-started/first-deployment#cozystack-dashboard" %}}).

If using OIDC, users and roles must be configured, see the [OIDC guide]({{% ref "/docs/operations/oidc" %}}) for more
details how to work with built-in OIDC server.

## Create a tenant

Tenants are created using the Cozystack application named `Tenant`. After Cozystack installation, there is a built-in
tenant `tenant-root`. It must be used by platform administrators only, and should be used to create child tenants only.
It's technically possible to install applications in the root tenant, but it's not recommended for production use.

{{< tabs name="redis_password" >}}
{{% tab name="in Dashboard" %}}

1. Open the dashboard as a tenant-root user.
2. Ensure current context is `tenant-root`. Switch context and reload the page if needed.
3. Click on the `Catalog` tab in the left menu.
4. Search for `Tenant` application badge and click on it. Application builtin documentation will open.
5. Read the documentation and click on the `Deploy` button. Application parameters page will open.
6. The only required parameter is `name`. The domain specified in the `host` must exist. Ensure that tenant user has
   enough control over it to set up DNS records. When left blank, domain will be formed by adding `name`
   subdomain to the main Cozystack domain. All parameters except `name` may be changed later.
7. The checkboxes `etcd`/`monitoring`/`ingress`/`seaweedfs` refer to applications that user will be not able to install
   or uninstall with their credentials. Only administrators can do this.
8. The `etcd` checkbox is required for nested kubernetes cluster. It must be enabled before installation of the
   "Kubernetes" application in the client tenant. Only disable it if you are sure that the client tenant will not be
   used for nested Kubernetes.
9. The `isolated` checkbox controls if sibling tenants can access each other over the network. This is not the same as
   visibility in the dashboard. In most cases, it should be enabled (isolated).
10. Resource quotas are empty by default, this means no limits. You can set them to prevent overuse of resources.
11. Click the `Deploy <version>` button again. The tenant application will be installed in the root tenant.
    {{% /tab %}}

{{% tab name="with kubectl" %}}

Create the tenant HelmRelease manifest (use the one created via dashboard as an example):

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

And apply it:

```bash
# Use the kubeconfig for the root tenant
export KUBECONFIG=./kubeconfig-tenant-root
# Get the password
kubectl -n tenant-root apply -f hr-tenant-team1.yaml
```

{{% /tab %}}
{{< /tabs >}}

It's possible to assist tenant users with installation of database applications and nested Kubernetes clusters. As
administrator, you can switch context in the dashboard to get into the tenant. Tenant users can access only their
tenant and downwards.

### Get tenant kubeconfig with OIDC enabled

Retrieve the kubeconfig file from the dashboard as described
in [OIDC guide]({{% ref "/docs/operations/oidc/enable_oidc#step-4-retrieve-kubeconfig" %}}).

### Get tenant kubeconfig with OIDC disabled

As an administrator, get the service account token secret in the tenant namespace. The secret name is the same as the
tenant name. You actually only need the token from there.

Example of command to retrieve the token for tenant `team1`:

```bash
$ kubectl -n tenant-team1 get secret tenant-team1 -o json | jq -r '.data.token | @base64d'
eyJhbG....
```

Then fill this token into the kubeconfig template, and save it as `kubeconfig-tenant-<name>.yaml` file. The namespace
should be also set to the tenant name, otherwise many GUI clients will complain about missing permissions.

The same token should be used by the tenant user to access the dashboard if OIDC is disabled.

### Get nested Kubernetes kubeconfig

In general case, administrators should not do that. The nested Kubernetes cluster is installed in the tenant namespace
by the tenant user. Tenant users have full control over their nested Kubernetes clusters. The nested Kubernetes cluster
kubeconfig can be downloaded from the corresponding application page in the dashboard.
