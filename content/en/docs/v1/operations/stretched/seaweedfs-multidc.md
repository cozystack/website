---
title: "SeaweedFS Multi-DC Configuration"
linkTitle: "SeaweedFS Multi-DC"
description: "How to deploy SeaweedFS across multiple data-centres"
weight: 175
---

This guide explains how to deploy SeaweedFS over several data centers ("multi-DC").
Multi-zone configuration for SeaweedFS is available since Cozystack v0.34.0.

## SeaweedFS Multi-DC Configuration

To span SeaweedFS over several DCs, create a new cluster in multi-DC mode.

By default, SeaweedFS runs in a single data centre (DC), and a running single-DC deployment cannot be switched to multi-DC mode.
If you need to change the topology, delete the current SeaweedFS instance and create a new one with the desired mode.

A convenient workflow is:

1. Deploy a tenant with `seaweedfs: false`.
2. Create a new SeaweedFS instance in the tenant’s namespace, using the required topology.
3. Patch the tenant with `seaweedfs: true`.

### 1. Create a Tenant without SeaweedFS

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Tenant
metadata:
  name: dev
  namespace: tenant-root
spec:
  etcd: false
  host: ""
  ingress: false
  isolated: true
  monitoring: false
  seaweedfs: false
```

### 2. Deploy SeaweedFS in Multi-Zone Mode

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: SeaweedFS
metadata:
  name: seaweedfs
  namespace: tenant-dev
spec:
  host: dev.s3.example.org
  replicas: 4
  size: 100Gi
  topology: MultiZone
  zones:
    dc1: {}
    dc2: {}
    dc3: {}
```

In this example, SeaweedFS starts 12 volume servers (4 replicas × 3 zones).

Parameter `zones` lists each data-centre.
Any setting omitted inside a zone inherits the top-level values (replicas, size, etc.).

### 3. Enable SeaweedFS in the tenant

After the SeaweedFS instance is ready, enable it in the tenant.
Apply the following updated resource definition:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: Tenant
metadata:
  name: dev
  namespace: tenant-root
spec:
  etcd: false
  host: ""
  ingress: false
  isolated: true
  monitoring: false
  seaweedfs: true
```

Bucket creation is now available for everything under this tenant tree.

## Using a Remote SeaweedFS Instance

You can expose one SeaweedFS deployment to other CozyStack clusters and let them connect in Client mode.

### 1. Export SeaweedFS

Set the filer's gRPC endpoint and whitelist the networks that may connect:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: SeaweedFS
metadata:
  name: seaweedfs
  namespace: tenant-dev
spec:
  host: dev.s3.example.org
  replicas: 4
  size: 100Gi
  topology: MultiZone
  zones:
    dc1: {}
    dc2: {}
    dc3: {}
  filer:
    grpcHost: filer-dev.s3.example.org
    whitelist:
      - 0.0.0.0/0   # expose to all networks (adjust for production)
```

### 2. Configure Remote SeaweedFS

Consume the remote SeaweedFS instance from another cluster:

```yaml
apiVersion: apps.cozystack.io/v1alpha1
kind: SeaweedFS
metadata:
  name: seaweedfs
spec:
  host: dev.s3.example.org
  topology: Client
  filer:
    grpcHost: filer-dev.s3.example.org
```

### 3. Enable Access to Remote SeaweedFS

To let your local cluster authenticate to the remote SeaweedFS filer, export the `seaweedfs-client-cert` secret from the remote cluster:

```bash
kubectl get secret seaweedfs-client-cert -n tenant-dev -o yaml \
  > seaweedfs-client-cert.yaml
```

Open `seaweedfs-client-cert.yaml` and delete the `namespace`, `labels`, and `annotations` fields.
They belong to the remote cluster and must not be re-applied locally. 
After cleanup the manifest should look roughly like this:

```yaml
apiVersion: v1
kind: Secret
type: kubernetes.io/tls
metadata:
  name: seaweedfs-client-cert
data:
  tls.crt: ...
  tls.key: ...
```

Apply the secret to the target namespace in your local cluster:

```bash
kubectl apply -f seaweedfs-client-cert.yaml -n tenant-root
```

> **Note:**
> In Client mode the cluster creates no volume servers; it simply re-uses the remote SeaweedFS instance for all bucket operations.
