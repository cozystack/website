---
title: "Deploy a sample application in Cozystack"
linkTitle: "Deploy Sample Application"
description: "Learn how to deploy an example application to a kubernetes cluster, using PostgreSQL and cache — all managed by Cozystack and conveniently isolated in a tenant."
weight: 50
---

## Introduction

This guide will walk you through deploying a sample web application with a couple of dependencies—PostgreSQL and Redis—on Cozystack, a Kubernetes-based PaaS framework.
The app is not part of Cozystack itself; it's a typical containerized service you'd deploy in any cloud-native setup.

In this tutorial you will learn to:

- Deploy managed applications: a PostgreSQL database and Redis cache.
- Create a managed Kubernetes cluster.
- Deploy a containerized application to this Kubernetes cluster and connect it to the services.

Our example app is called `instaphoto`.
It’s a simple web app that uses a PostgreSQL database to store data and a Redis cache for performance.
You don’t need to know Kubernetes internals to follow this tutorial.
Most steps are done through the Cozystack web interface.
For the final deployment of the app, we’ll briefly switch to the command line, and guide you step-by-step.

This is your fast track to a successful deployment on Cozystack.
Once you’ve completed it, you’ll have a working example to build upon and something to show your team.

## Prerequisites

Before you begin:

-   **Cozystack cluster** should already be [installed and running]({{% ref "/docs/getting-started/first-deployment" %}}).
    You won’t need to install or configure anything on the infrastructure level—this
    guide assumes that part is already done, possibly by you or someone else on your team.
-   **Credentials:** You must have access to your tenant in Cozystack.
    This can be either through a `kubeconfig` file or OIDC login for the dashboard.
    If you don’t have access, ask your Ops team or refer to the guide on creating a tenant.
-   **DNS for dev/testing:** To access the deployed app over HTTPS you need a DNS record set up.
    A wildcard DNS record is preferred, as it's more convenient to use.

> 🛠️ **CLI is optional.** 
> You don’t need to use `kubectl` or `helm` unless you want to. 
> All major steps (like creating the cluster and managed services) can be done entirely in the Cozystack Dashboard. 
> The only point where you’ll need the CLI is when deploying the app itself—and we’ll walk you through that part when the time comes.

## 1. Access the Cozystack Dashboard

Open the Cozystack dashboard in your browser.
The link usually looks like `https://dashboard.<cozystack_domain>`.

Depending on how authentication is configured in your Cozystack cluster, you'll see one of the following:

- An **OIDC login screen** with a button that redirects you to Keycloak.
- A **Token login screen**, where you manually paste a token from your kubeconfig file.

Choose your login method below:

{{< tabs name="access_dashboard" >}}
{{% tab name="OIDC" %}}
Click the `OIDC Login` button.  
This will take you to the Keycloak login page.

Enter your credentials and click `Login`.  
If everything is configured correctly, you'll be logged in and redirected back to the dashboard.
{{% /tab %}}

{{% tab name="kubeconfig" %}}
This login form doesn’t have a `username` field—only a `token` input.
You can get this token from your kubeconfig file.

1.  Open your kubeconfig file and copy the token value (it’s a long string).
    Make sure you copy it without extra spaces or line breaks.
1.  Paste it into the form and click `Submit`.

{{% /tab %}}
{{< /tabs >}}

Once you're logged in, the dashboard will automatically show your tenant context.

You may see system-level applications like `ingress` or `monitoring` already running—these are managed by your cluster admin.
As a tenant user, you can’t install or modify them, but your own apps will run alongside them in your isolated tenant environment.

## 2. Create a Managed PostgreSQL

Cozystack lets you provision managed databases directly on the hardware layer for maximum performance.  
Each database is created inside your tenant namespace and is automatically accessible from your nested Kubernetes cluster.

If you're familiar with services like AWS RDS or GCP Cloud SQL, the experience is similar—  
except it's fully integrated with Cozystack and isolated within your own tenant.

> Throughout this tutorial, you’ll have the option to use either the Cozystack dashboard (UI) or `kubectl`:
>
> - **Cozystack Dashboard** offers the quickest and most straightforward experience—recommended if this is your first time using Cozystack.
> - **`kubectl`** provides deeper visibility into how managed services are deployed behind the scenes.
> 
> While neither approach reflects how services are typically deployed in production,
> both are well-suited for learning and experimentation—making them ideal for this tutorial.

### 2.1 Deploy PostgresSQL

{{< tabs name="create_database" >}}
{{% tab name="Cozystack Dashboard" %}}

1. Open the Cozystack dashboard and go to the **Catalog** tab.
2. Search for the **Postgres** application badge and click it to open its built-in documentation.
3. Click the **Deploy** button to open the deployment configuration page.
4. Fill in `instaphoto-postgres` in the **`name`** field. Application name must be unique within your tenant and **cannot be changed after deployment**.
4. Review the other parameters. They come pre-filled with sensible defaults, so you can keep them unchanged.
    - Try using both the **Visual editor** and the **YAML editor**. You can switch between editors at any time.
    - The YAML editor includes inline comments to guide you.
    - Don’t worry if you’re unsure about some settings. Most of them can be updated later.
6. Click **Deploy** again. The database will be installed in your tenant’s namespace.

![Postgres deployment values](deploy-postgresql.png)

{{% /tab %}}

{{% tab name="kubectl" %}}
Create a manifest `postgres.yaml` with the following content:

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: postgres-instaphoto-dev
  namespace: tenant-team1
spec:
  chart:
    spec:
      chart: postgres
      reconcileStrategy: Revision
      sourceRef:
        kind: HelmRepository
        name: cozystack-apps
        namespace: cozy-public
      version: 0.10.0
  interval: 0s
  values:
    databases:
      myapp:
        roles:
          admin:
            - user1
    external: true
    replicas: 2
    resourcesPreset: nano
    size: 5Gi
    users:
      user1:
        password: strongpassword
```

Apply the manifest using:

```bash
kubectl apply -f postgres.yaml
```

> 💡 Tip: You can generate a similar manifest by deploying the Postgres app through the dashboard first.
> Then, export the configuration and edit it as needed.
> It's useful if you’re trying to reproduce or automate the setup.

{{% /tab %}}
{{< /tabs >}}


### 2.2 Get the Connection Credentials

Navigate to the **Applications** tab, then find and open the `instaphoto-postgres` application.  
Once the application is installed and ready, you’ll find connection details in the **Application Resources** section of the dashboard.

- The **Secrets** tab contains the database password for each user you defined.
- The **Services** tab lists the internal service endpoints:
  - Use `postgres-<name>-ro` to connect to the **read-only replica**.
  - Use `postgres-<name>-rw` to connect to the **primary (read-write)** instance.

These service names are resolvable from within the nested Kubernetes cluster and can be used in your app’s configuration.

If you need to connect to the database from outside the cluster, you can expose it externally by setting the `external` parameter to `true`.
This will create a service named `postgres-<name>-external-write` with a public IP address.

> ⚠️ **Only enable external access if absolutely necessary.** Exposing databases to the internet introduces security risks and should be avoided in most cases.

## 3. Create a cache service

From this point we will use the tenant credentials to access the platform. Use the tenant's kubeconfig for kubectl and
token from it to access the dashboard.

{{< tabs name="create_redis" >}}
{{% tab name="Cozystack Dashboard" %}}

1. Open the dashboard.
2. Follow the same steps as with PostgreSQL.
3. The redis application has `authEnabled` parameter that will create us a default user. That's enough for our
   application.
4. When finished with parameters, click the `Deploy` button. The application will be installed in the `team1` tenant.

{{% /tab %}}

{{% tab name="kubectl" %}}

Create a manifest `redis.yaml` with the following content:

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: redis-instaphoto
  namespace: tenant-team1
spec:
  chart:
    spec:
      chart: redis
      reconcileStrategy: Revision
      sourceRef:
        kind: HelmRepository
        name: cozystack-apps
        namespace: cozy-public
      version: 0.6.0
  interval: 0s
  values:
    authEnabled: true
    external: false
    replicas: 2
    resources: {}
    resourcesPreset: nano
    size: 1Gi
```

and apply it:

```bash
kubectl apply -f redis.yaml
```

{{% /tab %}}
{{< /tabs >}}

After a while, the redis application will be installed in the `team1` tenant. The generated password could be found in
the dashboard.

{{< tabs name="redis_password" >}}
{{% tab name="Cozystack Dashboard" %}}

1. Open the dashboard as a tenant-team1 user.
2. Click on the `Applications` tab in the left menu.
3. Find the `redis-instaphoto` application and click on it.
4. The password is shown in the `Secrets` section. There are the show/copy buttons next to it.

{{% /tab %}}

{{% tab name="kubectl" %}}

```bash
# Use the tenant kubeconfig
export KUBECONFIG=./kubeconfig-tenant-team1
# Get the password
kubectl -n tenant-team1 get secret redis-instaphoto-auth
```

{{% /tab %}}
{{< /tabs >}}

## 4. Deploy a nested Kubernetes cluster

The nested Kubernetes cluster is created in the same way as the database and cache. Here are additional points to get
attention:

* The `etcd` application must be enabled for the tenant. It is required for nested Kubernetes cluster. And it can be
  enabled only by the
  administrator.
* Ensure the quota is sufficient.
* Do not try to set Kubernetes instances preset too low. The Kubernetes node itself consumes around 2.5GB of RAM per
  node. So, if you choose the 4GB RAM preset, only 1.5GB will be available for the actual workload. 4GB will work for a
  test, but it's always better to get less amount of machines with more RAM than many machines with less RAM.
* If you develop web applications, most probably you will need the ingress and cert-manager. Both of them can be
  installed with a checkbox in the Cozystack application configuration.

When the nested Kubernetes cluster is ready, the `Secrets` tab will be available in the application page in the
dashboard. It contains the secrets with kubeconfig file for the nested Kubernetes cluster, in four flavors.

* admin.conf - The first kubeconfig to access your new cluster. You can also create another Kubernetes users using this
  config.
* admin.svc - The same token, but Kubernetes API server is set to the internal service name. This is useful for apps
  that work with Kubernetes API from inside the cluster.
* super-admin.conf - The same as admin, but with slightly more permissions. It can be used for
  troubleshooting.
* super-admin.svc - The same as super-admin, but with internal service name.

## 5. Update DNS and access the cluster

The nested Kubernetes cluster will take one of the floating IPs from the main cluster. You can check the actual dns name
and taken IP address on the Application page in the dashboard, or by checking the ingress status with `kubectl`. Update
DNS settings to match the ingress name and IP address.

When DNS records are updated, you can access the nested Kubernetes cluster using the downloaded kubeconfig file.

Example of how to access the Kubernetes with it:

```bash
cat > ~/.kube/kubeconfig-team1.example.org
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: LS0tL....
# (paste secret-admin.conf here)
$ export KUBECONFIG=~/.kube/kubeconfig-team1.example.org
$ kubectl get nodes
NAME                             STATUS   ROLES           AGE   VERSION
kubernetes-dev-md0-vn8dh-jjbm9   Ready    ingress-nginx   29m   v1.30.11
kubernetes-dev-md0-vn8dh-xhsvl   Ready    ingress-nginx   25m   v1.30.11
```

## 6. Deploy an application with helm

The rest of journey is the same as with any other Kubernetes cluster. You can use `kubectl` or `helm` or your CI/CD
system to deploy kubernetes-native applications. Fill the credentials to the database and cache in the application helm
chart values. Then run `helm upgrade --install` as usual. Service names do not need to have any dns suffixes, as if they
existed in the same namespace.
