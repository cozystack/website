---
title: "SeaweedFS Multi-DC Configuration"
linkTitle: "SeaweedFS Multi-DC"
description: "How to deploy SeaweedFS across multiple data-centres"
weight: 175
---

## SeaweedFS Multi-DC Configuration

> **Warning**  
> Multi-Zone support for SeaweedFS is available starting with CozyStack **v0.34.2**.

By default, SeaweedFS runs in a single data-centre (DC). If you need to span several DCs, you must **create the cluster in Multi-DC mode from the very beginning**—you cannot switch an existing single-DC deployment to Multi-DC (or vice-versa).  
If you need to change the topology, delete the current SeaweedFS instance and create a new one with the desired mode.

A convenient workflow is:

1. Deploy the tenant with `seaweedfs: false`.
2. Create a new SeaweedFS instance in the tenant’s namespace, using the required topology.
3. Patch the tenant to set `seaweedfs: true`.

---

Example: Creating a Tenant without SeaweedFS

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

Deploying SeaweedFS in Multi-Zone Mode

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

*	zones lists each data-centre.
*	Any setting omitted inside a zone inherits the top-level values (replicas, size, etc.).
*	In this example, SeaweedFS starts 12 volume servers (4 replicas × 3 zones).

After the SeaweedFS instance is ready, enable it in the tenant:

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

> **Warning**  
> Multi-Zone support for SeaweedFS is available starting with CozyStack **v0.35.0-beta.2**.

You can expose one SeaweedFS deployment to other CozyStack clusters and let them connect in Client mode.

1. Exporting SeaweedFS

Set the filer’s gRPC endpoint and whitelist the networks that may connect:

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

2. Consuming the Remote Instance from Another Cluster

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

3. Copy the client-certificate secret from the remote cluster

To let your local cluster authenticate to the remote SeaweedFS filer, export the certificate secret from the remote cluster:

```bash
kubectl get secret seaweedfs-client-cert -n tenant-dev -o yaml \
  > seaweedfs-client-cert.yaml
```

Open `seaweedfs-client-cert.yaml` and delete the `namespace`, `labels`, and `annotations` fields. They belong to the remote cluster and must not be re-applied locally. After cleanup the manifest should look roughly like this:

```bash
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

> **Note**
> In Client mode the cluster creates no volume servers; it simply re-uses the remote SeaweedFS instance for all bucket operations.
