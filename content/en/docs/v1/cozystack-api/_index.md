---
title: Cozystack API
description: Cozystack API
weight: 70
aliases:
- /docs/development/cozystack-api
---

## Cozystack API

Cozystack provides a powerful API that allows you to deploy services using various tools.

**The best way to learn the Cozystack API is to:**

1. Use the dashboard to deploy an application.
2. Examine the deployed resource in the Cozystack API and use it as a reference.
3. Parameterize and replicate the example resource to create your own resources through the API.

You can list all available resources using `kubectl`:

```bash
# kubectl api-resources | grep cozystack
buckets            apps.cozystack.io/v1alpha1      true    Bucket
clickhouses        apps.cozystack.io/v1alpha1      true    ClickHouse
etcds              apps.cozystack.io/v1alpha1      true    Etcd
ferretdb           apps.cozystack.io/v1alpha1      true    FerretDB
httpcaches         apps.cozystack.io/v1alpha1      true    HTTPCache
ingresses          apps.cozystack.io/v1alpha1      true    Ingress
kafkas             apps.cozystack.io/v1alpha1      true    Kafka
kuberneteses       apps.cozystack.io/v1alpha1      true    Kubernetes
monitorings        apps.cozystack.io/v1alpha1      true    Monitoring
mysqls             apps.cozystack.io/v1alpha1      true    MySQL
natses             apps.cozystack.io/v1alpha1      true    NATS
postgreses         apps.cozystack.io/v1alpha1      true    Postgres
rabbitmqs          apps.cozystack.io/v1alpha1      true    RabbitMQ
redises            apps.cozystack.io/v1alpha1      true    Redis
seaweedfses        apps.cozystack.io/v1alpha1      true    SeaweedFS
tcpbalancers       apps.cozystack.io/v1alpha1      true    TCPBalancer
tenants            apps.cozystack.io/v1alpha1      true    Tenant
virtualmachines    apps.cozystack.io/v1alpha1      true    VirtualMachine
vmdisks            apps.cozystack.io/v1alpha1      true    VMDisk
vminstances        apps.cozystack.io/v1alpha1      true    VMInstance
vpns               apps.cozystack.io/v1alpha1      true    VPN
```

Next, request a specific resource type in your tenant namespace:

```bash
# kubectl get postgreses -n tenant-test
NAME   READY   AGE   VERSION
test   True    46s   0.7.1
```

To view the YAML output:

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
kubectl create -f postgres.yaml
```

#### Using Terraform with the Cozystack API

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
