---
title: Cozystack API
description: Cozystack API for managing services and resources
weight: 70
aliases:
  - /docs/v1.3/development/cozystack-api
---

## Cozystack API

Cozystack provides a powerful API that allows you to deploy services using various tools. You can manage resources through kubectl, Terraform, or programmatically using Go.

**The best way to learn the Cozystack API is to:**

1. Use the dashboard to deploy an application.
2. Examine the deployed resource in the Cozystack API and use it as a reference.
3. Parameterize and replicate the example resource to create your own resources through the API.

## Discovering Resources

You can list all available resources using `kubectl`:

```bash
# kubectl api-resources | grep apps.cozystack
buckets           apps.cozystack.io/v1alpha1      true      Bucket
clickhouses       apps.cozystack.io/v1alpha1      true      ClickHouse
etcds             apps.cozystack.io/v1alpha1      true      Etcd
foundationdbs     apps.cozystack.io/v1alpha1      true      FoundationDB
harbors           apps.cozystack.io/v1alpha1      true      Harbor
httpcaches        apps.cozystack.io/v1alpha1      true      HTTPCache
infos             apps.cozystack.io/v1alpha1      true      Info
ingresses         apps.cozystack.io/v1alpha1      true      Ingress
kafkas            apps.cozystack.io/v1alpha1      true      Kafka
kuberneteses      apps.cozystack.io/v1alpha1      true      Kubernetes
mariadbs          apps.cozystack.io/v1alpha1      true      MariaDB
mongodbs          apps.cozystack.io/v1alpha1      true      MongoDB
monitorings       apps.cozystack.io/v1alpha1      true      Monitoring
natses            apps.cozystack.io/v1alpha1      true      NATS
openbaos          apps.cozystack.io/v1alpha1      true      OpenBAO
postgreses        apps.cozystack.io/v1alpha1      true      Postgres
qdrants           apps.cozystack.io/v1alpha1      true      Qdrant
rabbitmqs         apps.cozystack.io/v1alpha1      true      RabbitMQ
redises           apps.cozystack.io/v1alpha1      true      Redis
seaweedfses       apps.cozystack.io/v1alpha1      true      SeaweedFS
tcpbalancers      apps.cozystack.io/v1alpha1      true      TCPBalancer
tenants           apps.cozystack.io/v1alpha1      true      Tenant
virtualprivate    apps.cozystack.io/v1alpha1      true      VirtualPrivateCloud
vmdisks           apps.cozystack.io/v1alpha1      true      VMDisk
vminstances       apps.cozystack.io/v1alpha1      true      VMInstance
vpns              apps.cozystack.io/v1alpha1      true      VPN

```

## Using kubectl

Request a specific resource type in your tenant namespace:

```bash
# kubectl get postgreses -n tenant-test
NAME   READY   AGE   VERSION
test   True    46s   0.7.1
```

View the YAML output:

```yaml
# kubectl get postgreses -n tenant-test test -o yaml
apiVersion: apps.cozystack.io/v1alpha1
appVersion: 0.7.1
kind: Postgres
metadata:
  name: test
  namespace: tenant-test
spec:
  databases: {}
  replicas: 2
  size: 10Gi
  storageClass: ""
  users: {}
status:
  conditions:
  - lastTransitionTime: "2024-12-10T09:53:32Z"
    message: Helm install succeeded for release tenant-test/postgres-test.v1 with chart postgres@0.7.1
    reason: InstallSucceeded
    status: "True"
    type: Ready
  - lastTransitionTime: "2024-12-10T09:53:32Z"
    message: Helm install succeeded for release tenant-test/postgres-test.v1 with chart postgres@0.7.1
    reason: InstallSucceeded
    status: "True"
    type: Released
  version: 0.7.1
```

You can use this resource as an example to create a similar service via the API. Just save the output to a file, update the `name` and any parameters you need, then use `kubectl` to create a new Postgres instance:

```bash
kubectl apply -f postgres.yaml
```

## Using Terraform

Cozystack integrates with Terraform. You can use the default `kubernetes` provider to create resources in the Cozystack API.

**Example:**

```hcl
provider "kubernetes" {
  config_path = "~/.kube/config"
}

resource "kubernetes_manifest" "vm_disk_iso" {
  manifest = {
    "apiVersion" = "apps.cozystack.io/v1alpha1"
    "appVersion" = "0.7.1"
    "kind"       = "Postgres"
    "metadata" = {
      "name"      = "test2"
      "namespace" = "tenant-test"
    }
    "spec" = {
      "replicas" = 2
      "size"     = "10Gi"
    }
  }
}
```

Then run:

```bash
terraform plan
terraform apply
```

Your new Postgres cluster will be deployed.

## Using Go code

Cozystack publishes its custom Kubernetes resource types as a Go module, enabling management of Cozystack resources from any Go code. For details and examples, see the [Go Types]({{< relref "go-types.md" >}}) page.
