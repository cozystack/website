---
title: "Self-Signed Certificates"
linkTitle: "Self-Signed Certificates"
description: "How to configure OIDC with self-signed certificates"
weight: 60
aliases:
  - /docs/oidc/self-signed-certificates
---

This guide explains how to configure Kubernetes API server for OIDC authentication with Keycloak when using self-signed certificates. By default, Cozystack issues certificates via LetsEncrypt, but some environments (e.g., air-gapped or private enterprise networks) may use a custom CA instead.

## Prerequisites

- Cozystack cluster with OIDC enabled (see [Enable OIDC Server](../enable_oidc/))
- Talos Linux control plane nodes
- `talosctl` configured for your cluster
- `kubelogin` installed

## Step 1: Retrieve the Keycloak Certificate

Get the certificate from the ingress controller:

```bash
echo | openssl s_client -connect <KEYCLOAK_INGRESS_IP>:443 \
  -servername keycloak.example.org 2>/dev/null | openssl x509
```

Replace `<KEYCLOAK_INGRESS_IP>` with your ingress controller IP address, and `keycloak.example.org` with your actual Keycloak domain.

Save the output (the certificate between `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`) for the next step.

## Step 2: Configure Talos Control Plane Nodes

For each control plane node, add the following to your machine configuration:

```yaml
machine:
  network:
    extraHostEntries:
      - ip: <KEYCLOAK_INGRESS_IP>
        aliases:
          - keycloak.example.org
  files:
    - content: |
        -----BEGIN CERTIFICATE-----
        <YOUR_CERTIFICATE_CONTENT>
        -----END CERTIFICATE-----
      permissions: 0o644
      path: /var/oidc-ca.crt
      op: create

cluster:
  apiServer:
    extraArgs:
      oidc-issuer-url: https://keycloak.example.org/realms/cozy
      oidc-client-id: kubernetes
      oidc-username-claim: preferred_username
      oidc-groups-claim: groups
      oidc-ca-file: /etc/kubernetes/oidc/ca.crt
    extraVolumes:
      - hostPath: /var/oidc-ca.crt
        mountPath: /etc/kubernetes/oidc/ca.crt
```

Apply the configuration to each control plane node:

```bash
talosctl apply-config -n <NODE_IP> -f nodes/<node>.yaml
```

{{% alert color="info" %}}
The `extraHostEntries` configuration ensures that the Keycloak domain resolves correctly within the cluster, which is essential when using internal ingress IPs.
{{% /alert %}}

## Step 3: Configure kubelogin

Install kubelogin if you haven't already:

```bash
# Homebrew (macOS and Linux)
brew install int128/kubelogin/kubelogin

# Krew (macOS, Linux, Windows and ARM)
kubectl krew install oidc-login

# Chocolatey (Windows)
choco install kubelogin
```

Save the CA certificate from Step 1 to a file on your local machine:

```bash
# Save the certificate to a file (e.g., ~/.kube/oidc-ca.pem)
cat > ~/.kube/oidc-ca.pem <<EOF
-----BEGIN CERTIFICATE-----
<YOUR_CERTIFICATE_CONTENT>
-----END CERTIFICATE-----
EOF
```

Set up OIDC login (this will open a browser for authentication):

```bash
kubectl oidc-login setup \
  --oidc-issuer-url=https://keycloak.example.org/realms/cozy \
  --oidc-client-id=kubernetes \
  --certificate-authority=~/.kube/oidc-ca.pem
```

Configure kubectl credentials:

```bash
kubectl config set-credentials oidc \
  --exec-api-version=client.authentication.k8s.io/v1 \
  --exec-interactive-mode=IfAvailable \
  --exec-command=kubectl \
  --exec-arg=oidc-login \
  --exec-arg=get-token \
  --exec-arg="--oidc-issuer-url=https://keycloak.example.org/realms/cozy" \
  --exec-arg="--oidc-client-id=kubernetes" \
  --exec-arg="--certificate-authority=~/.kube/oidc-ca.pem"
```

Switch to the OIDC user and verify:

```bash
kubectl config set-context --current --user=oidc
kubectl get nodes
```

{{% alert color="info" %}}
If your organization's CA is already installed in the system trust store (common in enterprise environments), you can omit the `--certificate-authority` flag entirely — kubelogin will use the system CA bundle automatically.
{{% /alert %}}

{{% alert color="warning" %}}
Avoid using `--insecure-skip-tls-verify`. If you cannot install the CA certificate on your machine or pass it via `--certificate-authority`, you can use `--insecure-skip-tls-verify` as a temporary workaround, but this disables TLS verification and is not recommended for production use.
{{% /alert %}}

## Troubleshooting

### Check API Server OIDC Logs

```bash
kubectl logs -n kube-system -l component=kube-apiserver --tail=50 | grep oidc
```

### Verify OIDC Flags Are Applied

```bash
kubectl get pods -n kube-system -l component=kube-apiserver \
  -o jsonpath='{.items[0].spec.containers[0].command}' | tr ',' '\n' | grep oidc
```

### Common Issues

- **Certificate not found**: Ensure the certificate file path in `extraVolumes` matches the path specified in `oidc-ca-file`.
- **Domain resolution fails**: Verify that `extraHostEntries` is correctly configured on all control plane nodes.
- **Authentication fails**: Check that the user exists in Keycloak and has the required group memberships (see [Users and Roles](../users_and_roles/)).
