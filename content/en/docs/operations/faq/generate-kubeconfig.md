---
title: "How to generate kubeconfig for tenant users"
linkTitle: "Generate tenant kubeconfig"
description: "A guide on how to generate a kubeconfig file for tenant users in Cozystack."
---

To generate a `kubeconfig` for tenant users, use the following script.
As a result, you’ll receive the tenant-kubeconfig file, which you can provide to the user.


```bash
SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl get secret tenant-root -n tenant-root -o go-template='
apiVersion: v1
kind: Config
clusters:
- name: tenant-root
  cluster:
    server: '"$SERVER"'
    certificate-authority-data: {{ index .data "ca.crt" }}
contexts:
- name: tenant-root
  context:
    cluster: tenant-root
    namespace: {{ index .data "namespace" | base64decode }}
    user: tenant-root
current-context: tenant-root
users:
- name: tenant-root
  user:
    token: {{ index .data "token" | base64decode }}
' \
> tenant-root.kubeconfig
```

