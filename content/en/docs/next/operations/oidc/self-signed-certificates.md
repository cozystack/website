---
title: "Private CA and Let's Encrypt Staging"
linkTitle: "Private CA and Staging"
description: "Configure OIDC trust for private, air-gapped, and development environments"
weight: 60
aliases:
  - /docs/oidc/self-signed-certificates
  - /docs/operations/oidc/self-signed-certificates
---

This guide explains how to serve Keycloak with a certificate that is not publicly trusted and how to establish trust in every OIDC client. It covers private certificate authorities (CAs), Let's Encrypt staging, wildcard certificates, Talos, the Kubernetes API server, browsers, and kubelogin.

## Choose a certificate source

| Source | Recommended use | Publicly trusted | Notes |
| --- | --- | --- | --- |
| Let's Encrypt production | Production | Yes | Subject to production rate limits. Prefer a DNS-01 wildcard when many endpoints share a domain. |
| Let's Encrypt staging | Ephemeral and development clusters | No | Uses separate accounts and much higher limits than production. Trust staging roots only in isolated development clients. |
| Private CA | Air-gapped and corporate environments | No | Distribute the CA certificate to every trust boundary. Keep the CA stable and rotate leaf certificates beneath it. |
| Direct self-signed leaf | Temporary diagnostics only | No | Every leaf replacement changes the trust anchor. Use a self-signed issuer to bootstrap a CA instead. |

Let's Encrypt explicitly warns against adding its staging roots to a trust store used for ordinary browsing because the staging hierarchy is not audited to production standards. A dedicated browser profile, disposable VM, or isolated development workstation avoids extending that trust to unrelated browsing. See the [Let's Encrypt staging environment](https://letsencrypt.org/docs/staging-environment/) for the current staging root certificates and limits.

{{% alert color="warning" %}}
Trust a CA certificate, not the certificate currently served by Keycloak. Pinning a rotating leaf certificate causes OIDC to fail on the next renewal.
{{% /alert %}}

## Reduce certificate orders with a wildcard

Cozystack can serve one certificate for the root domain and its single-label subdomains. The certificate must contain both the apex name and the wildcard, for example `example.org` and `*.example.org`.

### Let Cozystack issue a staging wildcard

For the ingress-nginx path, enable DNS-01 and shared wildcard issuance in the Platform package values:

```yaml
publishing:
  certificates:
    issuerName: letsencrypt-stage
    solver: dns01
    wildcard: true
```

Configure the selected DNS-01 provider as described in [Gateway API and DNS-01]({{% ref "/docs/next/networking/gateway-api" %}}). HTTP-01 cannot issue wildcard certificates. When Gateway API is enabled, each tenant Gateway manages its own certificate and the `wildcard` value above is ignored.

The staging certificate remains untrusted until the active Let's Encrypt staging root certificates are installed at each trust boundary described below. Staging and production ACME accounts and rate limits are separate.

### Supply an existing wildcard certificate

For a corporate CA or an externally issued certificate, create a `kubernetes.io/tls` Secret in the publishing namespace, which is `tenant-root` by default:

```bash
kubectl create secret tls cozystack-wildcard-tls \
  --namespace=tenant-root \
  --cert=wildcard-fullchain.pem \
  --key=wildcard.key
```

Then set the Secret name in the Platform package values:

```yaml
publishing:
  certificates:
    wildcardSecretName: cozystack-wildcard-tls
```

The root ingress controller uses this Secret as its default TLS certificate. System Ingress resources, including Keycloak, omit their per-host certificate and use that default. Cozystack replicates the Secret for inherited tenant ingress controllers. A wildcard such as `*.example.org` does not cover `service.tenant.example.org`; include every required tenant apex in the certificate SANs or use per-tenant certificates.

{{% alert color="warning" %}}
Do not upload a corporate root private key to the cluster. Ask the corporate PKI to issue the wildcard certificate, or use a dedicated intermediate CA whose scope and lifetime are limited to the cluster.
{{% /alert %}}

### Bootstrap a development CA with cert-manager

For a disposable development environment without an existing PKI, the built-in `selfsigned-cluster-issuer` can bootstrap a CA certificate. Do not use it directly for Keycloak leaf certificates.

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: development-root-ca
  namespace: cozy-cert-manager
spec:
  isCA: true
  commonName: Cozystack development root CA
  subject:
    organizations:
      - Cozystack development
  secretName: development-root-ca
  duration: 87600h
  privateKey:
    algorithm: ECDSA
    size: 256
  issuerRef:
    name: selfsigned-cluster-issuer
    kind: ClusterIssuer
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: development-ca
spec:
  ca:
    secretName: development-root-ca
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cozystack-wildcard-tls
  namespace: tenant-root
spec:
  secretName: cozystack-wildcard-tls
  dnsNames:
    - example.org
    - "*.example.org"
  issuerRef:
    name: development-ca
    kind: ClusterIssuer
```

The CA Secret is in `cozy-cert-manager` because cert-manager reads `ClusterIssuer` credentials from its cluster resource namespace. After the wildcard Secret becomes ready, set `publishing.certificates.wildcardSecretName` as shown above. Back up the CA Secret if the development environment must survive cluster recreation; losing it requires distributing a new trust anchor.

## Understand the trust boundaries

The same CA bundle may need to be installed in several independent places:

- Talos trusts it for host-level HTTPS clients.
- The Kubernetes API server uses it to verify the OIDC issuer during discovery and JWKS retrieval.
- kubelogin uses it to contact the OIDC issuer from an administrator or tenant workstation.
- Browsers use it to open the Keycloak login page.

The CA embedded in a kubeconfig under `clusters[].cluster.certificate-authority-data` verifies the Kubernetes API server. It does not verify Keycloak. Cozystack-generated tenant kubeconfigs currently include the API server CA but do not include an OIDC issuer CA.

## Configure Talos and the Kubernetes API server

Create a PEM bundle containing the private root CA, the active Let's Encrypt staging roots, or both old and new roots during a CA rotation. Do not put a leaf certificate in this bundle.

Set the issuer and CA path in the Talm project `values.yaml`:

```yaml
oidcIssuerUrl: "https://keycloak.example.org/realms/cozy"

extraApiServerArgs:
  oidc-ca-file: /etc/ssl/certs/ca-certificates.crt
```

Create a side-patch such as `oidc-private-ca.yaml`:

```yaml
cluster:
  apiServer:
    extraVolumes:
      - hostPath: /etc/ssl/certs/ca-certificates.crt
        mountPath: /etc/ssl/certs/ca-certificates.crt
        readonly: true
---
apiVersion: v1alpha1
kind: TrustedRootsConfig
name: oidc-ca
certificates: |-
  -----BEGIN CERTIFICATE-----
  <CA_CERTIFICATE>
  -----END CERTIFICATE-----
```

`TrustedRootsConfig` appends the CA to the Talos host bundle. The explicit `extraVolumes` entry is still required because the kube-apiserver container does not inherit that host file automatically. The `readonly` key is lowercase in the Talos schema.

If control-plane nodes cannot resolve the external Keycloak hostname, add a `StaticHostConfig` document to the same side-patch:

```yaml
---
apiVersion: v1alpha1
kind: StaticHostConfig
name: 192.0.2.10
hostnames:
  - keycloak.example.org
```

`name` is the destination IP address and `hostnames` is a top-level list. `StaticHostConfig` replaces the deprecated `machine.network.extraHostEntries` configuration. Omit it when normal DNS already resolves the issuer correctly.

Preview and apply the composed configuration to each control-plane node. A non-empty Talm side-patch requires a single-node anchor:

```bash
talm apply --dry-run -f nodes/controlplane-1.yaml -f oidc-private-ca.yaml
talm apply -f nodes/controlplane-1.yaml -f oidc-private-ca.yaml
```

Repeat the operation for every control-plane node. Keep an administrative kubeconfig available while changing OIDC configuration.

{{% alert color="info" %}}
An OIDC issuer hosted in the same cluster does not create a kube-apiserver startup cycle. Kubernetes initializes OIDC discovery asynchronously and retries while Keycloak is unavailable. The API server starts normally, but OIDC token authentication fails until discovery succeeds.
{{% /alert %}}

## Configure Cozystack OIDC clients

Enable OIDC as described in [Enable OIDC Server]({{% ref "/docs/next/operations/oidc/enable_oidc" %}}). Keep the default internal Keycloak URL and TLS verification enabled:

```yaml
authentication:
  oidc:
    enabled: true
    insecureSkipVerify: false
    keycloakInternalUrl: "http://keycloak-http.cozy-keycloak.svc:8080/realms/cozy"
```

Dashboard and LINSTOR oauth2-proxy instances retain the external issuer and browser login URLs, but send token, JWKS, userinfo, and logout requests to the internal HTTP Service. They therefore do not need the private ingress CA. `authentication.oidc.insecureSkipVerify` controls those oauth2-proxy instances only; it does not configure kube-apiserver, kubelogin, or browser trust.

### Keycloak truststore

Keycloak does not need to trust the CA that issued its own ingress certificate. TLS terminates at the ingress controller and the Keycloak pod receives HTTP on the `keycloak-http` Service.

Keycloak needs a private CA in its truststore only when it initiates TLS to a private endpoint, such as an external identity provider, LDAPS server, or SMTP server. Upstream Keycloak accepts PEM or PKCS12 files through `KC_TRUSTSTORE_PATHS`, but the current Cozystack Keycloak chart does not expose an additional volume mount for such a file. `extraEnv` alone is not sufficient because the CA must also be mounted. Add first-class chart support before configuring this case; do not patch the generated StatefulSet manually because Flux will reconcile it back.

## Configure browsers and kubelogin

Install the private root CA or active Let's Encrypt staging roots in a dedicated browser profile or isolated workstation trust store. Verify that the certificate SAN contains the exact external Keycloak hostname.

Save the CA bundle on each kubelogin client and test issuer discovery:

```bash
kubectl oidc-login setup \
  --oidc-issuer-url=https://keycloak.example.org/realms/cozy \
  --oidc-client-id=kubernetes \
  --certificate-authority=/path/to/oidc-ca.pem
```

Add the same option to the generated kubeconfig under the kubelogin exec arguments:

```yaml
users:
  - name: oidc
    user:
      exec:
        apiVersion: client.authentication.k8s.io/v1
        command: kubectl
        args:
          - oidc-login
          - get-token
          - --oidc-issuer-url=https://keycloak.example.org/realms/cozy
          - --oidc-client-id=kubernetes
          - --certificate-authority=/path/to/oidc-ca.pem
```

kubelogin also supports `--certificate-authority-data` for embedding a base64-encoded public CA bundle. If the CA is already present in the workstation system trust store, omit both options.

{{% alert color="warning" %}}
The global kubectl `--certificate-authority` option verifies the Kubernetes API server, while `kubectl oidc-login ... --certificate-authority` verifies Keycloak. Setting one does not configure the other.
{{% /alert %}}

## Verify the complete path

Verify the served hostname and chain against the intended CA bundle:

```bash
openssl s_client \
  -connect keycloak.example.org:443 \
  -servername keycloak.example.org \
  -CAfile /path/to/oidc-ca.pem \
  -verify_return_error </dev/null
```

Fetch the discovery document through the same trust path:

```bash
curl --fail --cacert /path/to/oidc-ca.pem \
  https://keycloak.example.org/realms/cozy/.well-known/openid-configuration
```

Check that kube-apiserver received both OIDC arguments and the CA mount:

```bash
kubectl get pod -n kube-system -l component=kube-apiserver \
  -o jsonpath='{range .items[0].spec.containers[0].command[*]}{.}{"\n"}{end}' | grep oidc

kubectl get pod -n kube-system -l component=kube-apiserver \
  -o jsonpath='{range .items[0].spec.containers[0].volumeMounts[*]}{.name}{"\t"}{.mountPath}{"\n"}{end}' | grep ca-certificates
```

Finally, run kubelogin setup and access the cluster using the OIDC kubeconfig. If Keycloak was unavailable when kube-apiserver started, allow approximately one retry interval after Keycloak becomes reachable before testing again.

## Rotate a private CA

Use an overlap period so no client sees a leaf certificate whose issuer it does not yet trust:

1. Add the new root alongside the old root in Talos, kube-apiserver, kubelogin clients, browsers, and any other consumers.
2. Ensure kube-apiserver and long-running clients reload the expanded bundle; kube-apiserver reads its OIDC CA configuration at startup.
3. Issue and serve a new Keycloak or wildcard leaf certificate from the new CA.
4. Verify OIDC from every client class and wait until no required endpoint serves an old-only chain.
5. Remove the old root and reload consumers again.

Serving a new-root leaf before distributing the new root creates an authentication outage. Removing the old root before all old-root leaves are gone creates the inverse outage.

## Troubleshooting

- **kubelogin reports `x509: certificate signed by unknown authority`**: install the issuer CA on the workstation or add `--certificate-authority` to the kubelogin exec arguments.
- **kube-apiserver reports an unknown authority**: check `oidc-ca-file`, the `extraVolumes` mount, and the CA bundle on every control-plane node.
- **The browser warns for Let's Encrypt staging**: this is expected until the current staging root is installed in that isolated browser profile.
- **The certificate is valid but the hostname does not match**: reissue it with the external Keycloak hostname in its SANs. `StaticHostConfig` changes resolution, not certificate identity.
- **OIDC returns `authenticator not initialized`**: verify DNS or `StaticHostConfig`, network reachability, the CA chain, and the issuer discovery URL. Kubernetes retries initialization automatically.
- **Changing `authentication.oidc.insecureSkipVerify` has no effect on kubectl login**: that value belongs to Dashboard and LINSTOR oauth2-proxy, not kube-apiserver or kubelogin.
- **A wildcard works for root services but not nested tenant hosts**: a single-label wildcard does not cross DNS label boundaries. Add SANs for the tenant apex or issue a separate wildcard.
