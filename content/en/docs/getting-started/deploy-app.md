---
title: "Deploy your application"
linkTitle: "Deploy your application"
description: "Learn how to deploy an example application in Cozystack tenant"
weight: 50
---

In this guide we will deploy an application (that is not a part of Cozystack) in the tenant.

We will reach the following goals:

* Create a Kubernetes cluster.
* Create a managed database and managed cache.
* Get credentials and deploy a sample application as a usual Kubernetes deployment, in the tenant cluster.

We will deploy an imaginary application `instaphoto` that uses a PostgreSQL database and Redis cache. The application
itself is Kubernetes-native (i.e., has a Helm chart) and is not a part of Cozystack.

## Prerequisites

We will need a running Cozystack installation. You can use
the [installation guide]({{% ref "/docs/getting-started/first-deployment" %}}) to install it.

The Cozystack dashboard should be accessible. You can also use `kubectl` instead, but using the dashboard is the easiest
way to learn about the Cozystack platform features.

Client credentials are required to access the dashboard and/or tenant namespace of the main Kubernetes cluster.

Credentials could come in two flavors: OIDC or kubeconfig. The OIDC credentials are used to access the dashboard and
main Kubernetes cluster after authentication with Keycloak service (a part of Cozystack platform). The kubeconfig file
is a plain Kubernetes config file with static token. It's less secure, but simpler to use with automation tools.

Both types of credentials provide the same roles and permissions set.

The DNS name is required to test the application. For dev environments, it's easiest to use wildcard DNS record, as all
subdomains will be landed to the same IP by default.

## Access the dashboard

Open the link to the dashboard in your browser. The link usually looks like `https://dashboard.<cozystack_domain>`.
Depending on the authentication method, either login form or OIDC Login button appears.

{{< tabs name="access_dashboard" >}}
{{% tab name="OIDC" %}}
Click the `OIDC Login` button. The Keycloak login page will open. Enter your credentials and click `Login`. If
everything is fine, you will be logged in and redirected back to the dashboard.
{{% /tab %}}
{{% tab name="kubeconfig" %}}
Non-OIDC login form does not have the `username` field. Only the token is required. Token is a very long string and can
be found in the kubeconfig file. Paste it whole into the form field and click `Submit`. Ensure that you copied it from
the kubeconfig without newlines and extra spaces.
{{% /tab %}}
{{< /tabs >}}

As a result, you should see the dashboard with your tenant context selected. Only own tenant can be accessed with client
credentials. You will immediately see applications like "ingress", "monitoring" if they were enabled by the
administrator. Such kind of applications could not be installed as user as they must be configured with admin rights.

## Create a database

The Cozystack framework includes a managed database system. It allows you to create a database in the hardware layer for
maximum performance. The database is created in the tenant namespace and is accessible from the nested Kubernetes
cluster. This resembles the behavior of a managed database service like AWS RDS or GCP Cloud SQL.

{{< tabs name="create_database" >}}
{{% tab name="in Dashboard" %}}

1. Open the dashboard.
2. Click on the `Catalog` tab in the left menu.
3. Search for `Postgres` application badge and click on it. Application builtin documentation will open.
4. Read the documentation and click on the `Deploy` button. Application parameters page will open.
5. Parameters are pre-filled with sane and minimal defaults. You can change them in a Visual editor or in YAML editor.
   YAML editor contains full commentaries. You can also switch between editors back and forth. Do not worry if unsure
   for right parameters. It can be changed later. The only mandatory parameter is `name`. It should be unique in this
   tenant. Name is the only thing you can't change later.
6. When finished with parameters, click the `Deploy` button again. The application will be installed in the client
   tenant namespace.
{{% /tab %}}

{{% tab name="with kubectl" %}}
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

and apply it:

```bash
kubectl apply -f postgres.yaml
```

The contents of manifest can be copied from the resource that was created in the dashboard and then edited.
{{% /tab %}}
{{< /tabs >}}

After an application is installed and ready, the "Application Resources" section will be filled with connect
credentials.

The "Secrets" tab will contain the database password for each user defined.

The "Services" tab will contain the service addresses. Use the `postgres-<name>-ro` service name to connect to the
readonly replica, and the `postgres-<name>-rw` service name to connect to the master instance of the database. These
names are resolvable from the nested Kubernetes cluster.

If you need to have access to the database from outside the cluster, update the `external` parameter to `true`. After
that, the `postgres-<name>-external-write` service will be created with an external IP. You can use it to connect to the
database using CLI or GUI from anywhere in the internet.

Do not allow external access to the database if you do not need it.

## Create a cache service

From this point we will use the tenant credentials to access the platform. Use the tenant's kubeconfig for kubectl and
token from it to access the dashboard.

{{< tabs name="create_redis" >}}
{{% tab name="in Dashboard" %}}

1. Open the dashboard.
2. Follow the same steps as with postgresql.
3. The redis application has `authEnabled` parameter that will create us a default user. That's enough for our
   application.
4. When finished with parameters, click the `Deploy` button. The application will be installed in the `team1` tenant.

{{% /tab %}}

{{% tab name="with kubectl" %}}

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
{{% tab name="in Dashboard" %}}

1. Open the dashboard as a tenant-team1 user.
2. Click on the `Applications` tab in the left menu.
3. Find the `redis-instaphoto` application and click on it.
4. The password is shown in the `Secrets` section. There are the show/copy buttons next to it.

{{% /tab %}}

{{% tab name="with kubectl" %}}

```bash
# Use the tenant kubeconfig
export KUBECONFIG=./kubeconfig-tenant-team1
# Get the password
kubectl -n tenant-team1 get secret redis-instaphoto-auth
```

{{% /tab %}}
{{< /tabs >}}

## Deploy the nested Kubernetes cluster

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

## Update DNS and access the cluster

The nested Kubernetes cluster will take one of the floating IPs from the main cluster. You can check the actual dns name
and taken IP address on the Application page in the dashboard, or by checking the ingress status with kubectl. Update
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

## Deploy an application with helm

The rest of journey is the same as with any other Kubernetes cluster. You can use `kubectl` or `helm` or your CI/CD
system to deploy kubernetes-native applications. Fill the credentials to the database and cache in the application helm
chart values. Then run `helm upgrade --install` as usual. Service names do not need to have any dns suffixes, as if they
existed in the same namespace.
