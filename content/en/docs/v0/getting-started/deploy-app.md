---
title: "5. Deploy Managed Applications, VMs, and tenant Kubernetes cluster"
linkTitle: "5. Deploy Applications"
description: "Start using Cozystack: deploy a virtual machine, managed application, and a tenant Kubernetes cluster."
weight: 50
---

## Objectives

This guide will walk you through setting up the environment needed to run a typical web application with common service
dependencies—PostgreSQL and Redis—on Cozystack, a Kubernetes-based PaaS framework.

You’ll learn how to:

-   Deploy managed applications in your tenant: a PostgreSQL database and Redis cache.
-   Create a managed Kubernetes cluster, configure DNS, and access the cluster.
-   Deploy a containerized application to the new cluster.

You don’t need in-depth Kubernetes knowledge to complete this tutorial—most steps are done through the Cozystack web interface.

This is your fast track to a successful first deployment on Cozystack.
Once you're done, you’ll have a working setup ready for your own applications—and a solid foundation to build upon and showcase to your team.

## Prerequisites

Before you begin:

-   **Cozystack cluster** should already be [installed and running]({{% ref "/docs/getting-started/install-cozystack" %}}).
    You won’t need to install or configure anything on the infrastructure level—this
    guide assumes that part is already done, possibly by you or someone else on your team.
-   **Tenant and credentials:** You must have access to your tenant in Cozystack.
    This can be either through a `kubeconfig` file or OIDC login for the dashboard.
    If you don’t have access, ask your Ops team or refer to the guide on creating a tenant.
-   **DNS for dev/testing:** To access the deployed app over HTTPS you need a DNS record set up.
    A wildcard DNS record is preferred, as it's more convenient to use.

> 🛠️ **CLI is optional.**
> You don’t need to use `kubectl` or `helm` unless you want to.
> All major steps (like creating the Kubernetes cluster and managed services) can be done entirely in the Cozystack Dashboard.
> The only point where you’ll need the CLI is when deploying the app to a Kubernetes cluster.

## 1. Access the Cozystack Dashboard

Open the Cozystack dashboard in your browser.
The link usually looks like `https://dashboard.<cozystack_domain>`.

Depending on how authentication is configured in your Cozystack cluster, you'll see one of the following:

-   An **OIDC login screen** with a button that redirects you to Keycloak.
-   A **Token login screen**, where you manually paste a token from your kubeconfig file.

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
> -   **Cozystack Dashboard** offers the quickest and most straightforward experience—recommended if this is your first time using Cozystack.
> -   **`kubectl`** provides in-depth visibility into how managed services are deployed behind the scenes.
>
> While neither approach reflects how services are typically deployed in production,
> both are well-suited for learning and experimentation—making them ideal for this tutorial.

### 2.1 Deploy PostgresSQL

{{< tabs name="create_database" >}}
{{% tab name="Cozystack Dashboard" %}}

1.  Open the Cozystack dashboard and go to the **Catalog** tab.
1.  Search for the **Postgres** application badge and click it to open its built-in documentation.
1.  Click the **Deploy** button to open the deployment configuration page.
1.  Fill in `instaphoto-postgres` in the **`name`** field. Application name must be unique within your tenant and **cannot be changed after deployment**.
1.  Review the other parameters. They come pre-filled with sensible defaults, so you can keep them unchanged.
    -    Try using both the **Visual editor** and the **YAML editor**. You can switch between editors at any time.
    -    The YAML editor includes inline comments to guide you.
    -    Don’t worry if you’re unsure about some settings. Most of them can be updated later.
1.  Click **Deploy** again. The database will be installed in your tenant’s namespace.


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

-   The **Secrets** tab contains the database password for each user you defined.
-   The **Services** tab lists the internal service endpoints:
    -   Use `postgres-<name>-ro` to connect to the **read-only replica**.
    -   Use `postgres-<name>-rw` to connect to the **primary (read-write)** instance.

These service names are resolvable from within the nested Kubernetes cluster and can be used in your app’s configuration.

If you need to connect to the database from outside the cluster, you can expose it externally by setting the `external` parameter to `true`.
This will create a service named `postgres-<name>-external-write` with a public IP address.

> ⚠️ **Only enable external access if absolutely necessary.** Exposing databases to the internet introduces security risks and should be avoided in most cases.

## 3. Create a Cache Service

From this point on, you'll use your tenant credentials to access the platform.
Use the tenant's kubeconfig for `kubectl`, and the token from it to access the dashboard.

{{< tabs name="create_redis" >}}
{{% tab name="Cozystack Dashboard" %}}

1.  Open the dashboard.
1.  Follow the same steps as with PostgreSQL, but for Redis application.
1.  The Redis application has an `authEnabled` parameter, which will create a default user. That’s sufficient for our application.
1.  Once you're done configuring the parameters, click the **Deploy** button. The application will be installed in your tenant.

{{% /tab %}}
{{% tab name="kubectl" %}}

Create a manifest file named `redis.yaml` with the following content:

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

Then apply it:

```bash
kubectl apply -f redis.yaml
```
{{% /tab %}}
{{< /tabs >}}

After a short time, the Redis application will be installed in the `team1` tenant.
The generated password can be found in the dashboard.

{{< tabs name="redis_password" >}}
{{% tab name="Cozystack Dashboard" %}}

1.  Open the dashboard as the `tenant-team1` user.
1.  Click on the **Applications** tab in the left menu.
1.  Find the `redis-instaphoto` application and click on it.
1.  The password is shown in the **Secrets** section, with buttons to copy or reveal it.

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

## 4. Deploy a Nested Kubernetes Cluster

The nested Kubernetes cluster is created in the same way as the database and cache.
However, there are a few important additional points to consider:

-   **`etcd` must be enabled in the tenant**<br/>
    The `etcd` service is required to run a nested Kubernetes cluster and can only be enabled by a Cozystack administrator.
-   **Verify your quota.**<br/>
    Ensure your tenant has enough CPU, RAM, and disk resources to create and run a cluster.
-   **Choose an appropriate instance preset.**<br/>
    Avoid selecting presets that are too small. A Kubernetes node consumes approximately 2.5 GB of RAM just for system components.
    For example, if you select a 4 GB RAM preset, only about 1.5 GB will be available for your actual workloads.
    4 GB is sufficient for testing, but in general, it’s better to provision **fewer nodes with more RAM** than many nodes with minimal RAM.
-   **Enable `ingress` and `cert-manager` if needed.**<br/>
    If you're deploying web applications, you will likely need ingress and certificate management.
    Both can be enabled with a checkbox when configuring the nested Kubernetes application in Cozystack.

Once the nested Kubernetes cluster is ready, you'll find its kubeconfig files in the **Secrets** tab of the application page in the dashboard.
Several options are provided:

-   **`admin.conf`** — The standard kubeconfig for accessing your new cluster.
    You can create additional Kubernetes users using this configuration.
-   **`admin.svc`** — Same token as `admin.conf`, but with the API server address set to the internal service name.
    Use it for applications running inside the cluster that need API access.
-   **`super-admin.conf`** — Similar to `admin.conf`, but with extended administrative permissions.
    Intended for troubleshooting and cluster maintenance tasks.
-   **`super-admin.svc`** — Same as `super-admin.conf`, but pointing to the internal API server address.

## 5. Update DNS and Access the Cluster

After deployment, the nested Kubernetes cluster will automatically claim one of the floating IP addresses from the main cluster.

You can find the assigned DNS name and IP address in one of two ways:
- Open the application page for the cluster in the dashboard.
- Check the ingress status using `kubectl`.

Once you have the correct DNS name and IP address, update your DNS settings to point your domain or subdomain to the assigned IP.

After the DNS records are updated and propagated, you can access your nested Kubernetes cluster using the downloaded kubeconfig file.

Here’s an example of how to configure and use it:

1.  Save the contents of `admin.conf` in a file, for example, `~/.kube/kubeconfig-team1.example.org`:

    ```console
    $ cat ~/.kube/kubeconfig-team1.example.org
    apiVersion: v1
    clusters:
    - cluster:
        certificate-authority-data: LS0tL
        ...
    ```

1.  Set up `KUBECONFIG` env variable to this file and check that the nodes are ready:

    ```console
    $ export KUBECONFIG=~/.kube/kubeconfig-team1.example.org
    $ kubectl get nodes
    NAME                             STATUS   ROLES           AGE   VERSION
    kubernetes-dev-md0-vn8dh-jjbm9   Ready    ingress-nginx   29m   v1.30.11
    kubernetes-dev-md0-vn8dh-xhsvl   Ready    ingress-nginx   25m   v1.30.11
    ```

## 6. Deploy an Application with Helm

From this point, working with your cluster is the same as working with any standard Kubernetes environment.

You can use `kubectl`, `helm`, or your CI/CD pipeline to deploy Kubernetes-native applications.

To deploy your application:

1.  Update your Helm chart values to include the correct credentials for the database and cache.
1.  Run a standard Helm deployment command, for example:

    ```bash
    helm upgrade --install <release-name> <chart-path> -f values.yaml
    ```

Service names such as the database and cache do not need DNS suffixes.
They are accessible within the same namespace by their service names.