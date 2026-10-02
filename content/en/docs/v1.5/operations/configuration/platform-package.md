---
title: "Platform Package Reference"
linkTitle: "Platform Package"
description: "Reference for the Cozystack Platform Package, which defines key configuration values for a Cozystack installation and operations."
weight: 10
aliases:
  - /docs/v1.5/install/cozystack/configmap
  - /docs/v1.5/operations/configuration/configmap
---

This page explains the role of the Cozystack Platform Package and provides a full reference for its values.

Cozystack's main configuration is defined by a `Package` custom resource.
This Package includes the [Cozystack variant]({{% ref "/docs/v1.5/operations/configuration/variants" %}}) and [component settings]({{% ref "/docs/v1.5/operations/configuration/components" %}}),
key network settings, exposed services, and other options.


## Example

Here's an example of configuration for installing Cozystack with variant `isp-full`, with root host "example.org",
and Cozystack Dashboard and API exposed and available to users:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
spec:
  variant: isp-full
  components:
    platform:
      values:
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://api.example.org:443"
          exposedServices:
            - dashboard
            - api
        networking:
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
```


## Reference

### Package-level fields

| Field | Description |
| --- | --- |
| `spec.variant` | Variant to use for installation (e.g., `isp-full`, `isp-full-generic`, `isp-hosted`, `distro-full`). |

### Platform values (`spec.components.platform.values.*`)

#### Publishing

| Value | Default | Description |
| --- | --- | --- |
| `publishing.host` | `"example.org"` | The main domain for all services created under Cozystack, such as the dashboard, Grafana, Keycloak, etc. |
| `publishing.apiServerEndpoint` | `""` | Used for generating kubeconfig files for your users. It is recommended to use a routable FQDN or IP address instead of local-only addresses. Example: `"https://api.example.org"`. |
| `publishing.exposedServices` | `[api, dashboard, vm-exportproxy, cdi-uploadproxy]` | List of services to expose. Possible values: `api`, `dashboard`, `cdi-uploadproxy`, `vm-exportproxy`. |
| `publishing.ingressName` | `"tenant-root"` | Ingress controller to use for exposing services. |
| `publishing.externalIPs` | `[]` | List of external IPs used for the specified ingress controller. If not specified, a LoadBalancer service is used by default. |
| `publishing.certificates.solver` | `"http01"` | ACME challenge solver type for default letsencrypt issuer. Possible values: `http01`, `dns01`. |
| `publishing.certificates.issuerName` | `"letsencrypt-prod"` | `ClusterIssuer` name for TLS certificates used in system Helm releases. |
| `publishing.certificates.wildcardSecretName` | `""` | Operator-provided wildcard TLS Secret. When set, platform services and the root tenant's ingress/Gateway serve this pre-existing Secret instead of minting per-host ACME certificates (only the NAME travels the values channel — never the key material). The Secret must exist in the publishing namespace (`tenant-root` by default), hold valid PEM under `tls.crt` / `tls.key` (created as `kubernetes.io/tls`, though only the material is validated), and cover the served hosts. **Scoped to the root tenant but not enforced** — the name reaches every tenant, so a child running its own ingress controller can be left serving a self-signed certificate ([cozystack/cozystack#3296](https://github.com/cozystack/cozystack/issues/3296)). See [Gateway API → Certificates]({{% ref "/docs/v1.5/networking/gateway-api#certificates" %}}) for the full behaviour and the three child-tenant cases. Leave empty to keep ACME issuance. |
| `publishing.certificates.dns01.provider` | `"cloudflare"` | DNS-01 provider when `solver=dns01`. Possible values: `cloudflare`, `route53`, `digitalocean`, `rfc2136`. Both the per-tenant Issuer (rendered by `cozystack-controller` from the `TenantGateway` CR) and the cluster-wide `letsencrypt-prod` / `letsencrypt-stage` `ClusterIssuer`s used by the legacy ingress flow read this. |
| `publishing.certificates.dns01.cloudflare.secretName` | `"cloudflare-api-token-secret"` | Secret name holding a Cloudflare API token with `Zone:Read` + `Zone:DNS:Edit` on the apex zone. |
| `publishing.certificates.dns01.cloudflare.secretKey` | `"api-token"` | Key inside the Secret holding the API token. |
| `publishing.certificates.dns01.route53.region` | `""` | AWS region of the Route53 hosted zone. Required when `provider=route53`. |
| `publishing.certificates.dns01.route53.accessKeyID` | `""` | IAM access key ID. Optional when running with IRSA / instance profile. |
| `publishing.certificates.dns01.route53.secretName` | `""` | Secret name holding the IAM secret access key. Optional when running with IRSA / instance profile. |
| `publishing.certificates.dns01.route53.secretKey` | `"secret-access-key"` | Key inside the Route53 Secret holding the secret access key. |
| `publishing.certificates.dns01.digitalocean.secretName` | `"digitalocean-api-token-secret"` | Secret name holding a DigitalOcean API token with write access to the apex domain. |
| `publishing.certificates.dns01.digitalocean.secretKey` | `"access-token"` | Key inside the Secret holding the DigitalOcean token. |
| `publishing.certificates.dns01.rfc2136.nameserver` | `""` | `host:port` of the authoritative nameserver accepting RFC 2136 dynamic updates. Required when `provider=rfc2136`. |
| `publishing.certificates.dns01.rfc2136.tsigKeyName` | `""` | TSIG key name authorising the dynamic updates. Required when `provider=rfc2136`. |
| `publishing.certificates.dns01.rfc2136.tsigAlgorithm` | `"HMACSHA256"` | TSIG HMAC algorithm. |
| `publishing.certificates.dns01.rfc2136.secretName` | `""` | Secret name holding the TSIG key material. Required when `provider=rfc2136`. |
| `publishing.certificates.dns01.rfc2136.secretKey` | `"tsig-secret-key"` | Key inside the Secret holding the TSIG key. |
| `publishing.certificates.wildcardSecretName` | `""` | Operator-provided wildcard TLS Secret. When set, platform services and the root tenant's ingress/Gateway serve under this pre-existing Secret instead of minting per-host ACME certificates; only the NAME travels through the platform values channel, never the certificate or private key. The Secret must already exist in the publishing namespace (`tenant-root` by default — the namespace running the root ingress controller selected by `publishing.ingressName`), be of type `kubernetes.io/tls`, and cover the served hosts (typically `*.<root-host>` + `<root-host>`). Leave empty to keep ACME issuance (`solver` / `issuerName` above). |
| `publishing.proxyProtocol` | `false` | Enables PROXY-protocol on the host ingress-nginx and auto-deploys [ouroboros]({{% ref "/docs/v1.5/networking/hairpin-proxy-protocol" %}}) to fix the resulting hairpin-NAT problem. The upstream L4 LB in front of ingress-nginx must already be injecting PROXY-v1 headers before this flag flips on; see the linked page for verification recipes and the disable path. |
| `publishing.proxyProtocolAcknowledgeUnclean` | `false` | Acknowledgement gate for the `helm.sh/resource-policy: keep` asymmetry on the host disable path. Flipping `publishing.proxyProtocol` from `true` back to `false` stops emitting the `cozystack.ouroboros` Package CR but does not uninstall the existing one — the platform render fails until either the Package CR is deleted (which triggers the chart's pre-delete cleanup hook) or this flag is set to `true` to confirm the operator has handled the asymmetry. See [hairpin-proxy-protocol → Disable path]({{% ref "/docs/v1.5/networking/hairpin-proxy-protocol#disable-path" %}}) for the full sequence. |

`publishing.exposure` is not listed above on purpose: the key existed in v1.4 only and was removed before v1.5 shipped. It has no effect on a v1.5 cluster — the host ingress is exposed through `publishing.externalIPs`, and a LoadBalancer Service is used when that list is empty. Drop the key when upgrading from v1.4 — and check what the host ingress Service becomes. A v1.4 cluster running `publishing.exposure: loadBalancer` had a `LoadBalancer` Service with `externalTrafficPolicy: Local`; from v1.5 the key is ignored, so a cluster with `publishing.externalIPs` set silently falls back to a `ClusterIP` Service with `externalTrafficPolicy: Cluster` and stops preserving client source IPs.

#### Networking

| Value | Default | Description |
| --- | --- | --- |
| `networking.clusterDomain` | `"cozy.local"` | Internal cluster domain name. |
| `networking.podCIDR` | `"10.244.0.0/16"` | The pod subnet used by Pods to assign IPs. |
| `networking.podGateway` | `"10.244.0.1"` | The gateway address for the pod subnet. |
| `networking.serviceCIDR` | `"10.96.0.0/16"` | The service subnet used by Services to assign IPs. |
| `networking.joinCIDR` | `"100.64.0.0/16"` | The `join` subnet for network communication between the Node and Pod. Follow the [kube-ovn] documentation to learn more. |
| `networking.kubeovn.MASTER_NODES` | `""` | Comma-separated list of KubeOVN master node IPs. By default, KubeOVN uses `lookup` to find control-plane nodes by label `node-role.kubernetes.io/control-plane`. On fresh clusters, lookup may return empty results. Set this to override. |

#### Bundles

| Value | Default | Description |
| --- | --- | --- |
| `bundles.system.enabled` | `false` | Enable the system bundle. Managed by the operator based on `spec.variant`. |
| `bundles.system.variant` | `"isp-full"` | System bundle variant. Options: `isp-full`, `isp-full-generic`, `isp-hosted`. Managed by the operator based on `spec.variant`. |
| `bundles.iaas.enabled` | `false` | Enable the IaaS bundle. Managed by the operator based on `spec.variant`. |
| `bundles.paas.enabled` | `false` | Enable the PaaS bundle. Managed by the operator based on `spec.variant`. |
| `bundles.naas.enabled` | `false` | Enable the NaaS bundle. Managed by the operator based on `spec.variant`. |
| `bundles.enabledPackages` | `[]` | List of optional bundle components to include in the installation. Read more in ["How to enable and disable bundle components"][enable-disable]. |
| `bundles.disabledPackages` | `[]` | List of bundle components to exclude from the installation. Read more in ["How to enable and disable bundle components"][enable-disable]. |

#### Authentication

| Value | Default | Description |
| --- | --- | --- |
| `authentication.oidc.enabled` | `false` | Enable [OIDC][oidc] feature in Cozystack. |
| `authentication.oidc.insecureSkipVerify` | `false` | Skip TLS certificate verification for the OIDC provider. |
| `authentication.oidc.keycloakExtraRedirectUri` | `""` | Additional redirect URI for Keycloak OIDC client. |
| `authentication.oidc.keycloakInternalUrl` | `""` | Internal URL for backend-to-backend requests to Keycloak. When set, the dashboard's oauth2-proxy skips OIDC discovery and routes token, JWKS, userinfo, and logout requests through this URL while keeping browser redirects on the external URL. Example: `http://keycloak-http.cozy-keycloak.svc:8080/realms/cozy`. |

#### Gateway

Platform-wide Gateway API integration. The actual per-tenant Gateway is materialised only for tenants that explicitly opt in via `tenant.spec.gateway: true` (typically `tenant-root` plus any tenant that needs its own LB IP, custom apex, or separate ACME account). Every other tenant in the tree publishes through the Gateway of the nearest ancestor that owns one — same shape as `_namespace.ingress` inheritance. See the [Gateway API guide]({{% ref "/docs/v1.5/networking/gateway-api" %}}) for the full architecture and migration path.

| Value | Default | Description |
| --- | --- | --- |
| `gateway.enabled` | `false` | Enable Gateway API support across the platform. When `true`, cert-manager `ClusterIssuer`s use an `http01.gatewayHTTPRoute` solver attached to the publishing tenant's Gateway, and exposed services (`dashboard`, `keycloak`, `grafana`, `alerta`, `harbor`, `bucket`, `cozystack-api`, `vm-exportproxy`, `cdi-uploadproxy`) render `HTTPRoute`/`TLSRoute` instead of `Ingress`. Materialising the actual per-tenant Gateway still requires an owning tenant to set `tenant.spec.gateway: true`. |
| `gateway.attachedNamespaces` | (see below) | Namespaces whose `HTTPRoute` / `TLSRoute` resources should publish through the owning tenant Gateway. The controller patches `namespace.cozystack.io/gateway = <owner>` onto each listed namespace so its routes pass the HTTPS and TLS-passthrough listeners' `allowedRoutes` label selector. The port-80 HTTP listener uses a separate, narrower whitelist (`<owner-tenant-ns>` and `cozy-cert-manager` only) and does NOT admit routes from `attachedNamespaces`. The publishing tenant's own namespace and descendants are admitted via the same label written by the tenant chart. Tenant namespaces (`tenant-*`) may be listed too — they simply pick up the gateway-attach label alongside the `cozy-*` system namespaces. The `default` namespace is included by default because the Kubernetes API `TLSRoute` lives next to the `kubernetes` Service in `default`. |

Default `gateway.attachedNamespaces`:

```yaml
gateway:
  attachedNamespaces:
    - cozy-cert-manager
    - cozy-dashboard
    - cozy-keycloak
    - cozy-system
    - cozy-harbor
    - cozy-bucket
    - cozy-kubevirt
    - cozy-kubevirt-cdi
    - cozy-monitoring
    - cozy-linstor-gui
    - default
```

#### Scheduling

| Value | Default | Description |
| --- | --- | --- |
| `scheduling.globalAppTopologySpreadConstraints` | `""` | Global pod topology spread constraints applied to all managed applications. |

#### Backup storage

| Value | Default | Description |
| --- | --- | --- |
| `backupStorage` | `{}` | S3 coordinates for the platform-managed `cozy-default` BackupClass. The whole block is forwarded into the `backupstrategy-controller` component and deep-merged over its chart defaults; keys include `provisionBucket`, `bucketName`, `endpoint`, `region`, `forcePathStyle`, `systemSecretName`, and `systemNamespaces`. Requires a v1.5 patch release carrying the cozystack/cozystack#3333 backport — on earlier v1.5 patches the key is silently ignored. See [Backup Classes]({{% ref "/docs/v1.5/operations/services/backup-classes" %}}) for the knob-by-knob reference. |

#### Branding

| Value | Default | Description |
| --- | --- | --- |
| `branding` | `{}` | UI branding configuration object. See the [White Labeling]({{% ref "/docs/v1.5/operations/configuration/white-labeling" %}}) guide for available fields and usage. Individual fields (e.g., `titleText`, `logoSvg`) have their own defaults when not specified. |

#### Registries

Container registry mirrors configuration. Allows routing image pulls through local mirrors.

| Value | Default | Description |
| --- | --- | --- |
| `registries.mirrors` | `{}` | Map of registry hostnames to mirror endpoints. Each entry maps a registry (e.g., `docker.io`) to a list of mirror endpoints. |
| `registries.config` | `{}` | Per-endpoint configuration, such as TLS settings. |

Example:

```yaml
registries:
  mirrors:
    docker.io:
      endpoints:
        - http://10.0.0.1:8082
    ghcr.io:
      endpoints:
        - http://10.0.0.1:8083
  config:
    "10.0.0.1:8082":
      tls:
        insecureSkipVerify: true
```

#### Resources

| Value | Default | Description |
| --- | --- | --- |
| `resources.cpuAllocationRatio` | `10` | CPU allocation ratio: `1/cpuAllocationRatio` CPU requested per 1 vCPU. See [Resource Management] for detailed explanation and examples. |
| `resources.memoryAllocationRatio` | `1` | Memory allocation ratio: `1/memoryAllocationRatio` memory requested per unit of configured memory. |
| `resources.ephemeralStorageAllocationRatio` | `40` | Ephemeral storage allocation ratio: `1/ephemeralStorageAllocationRatio` ephemeral storage requested per unit of configured storage. |

#### Internal fields

These fields are managed automatically by the Cozystack operator and should not be modified manually.

| Value | Default | Description |
| --- | --- | --- |
| `sourceRef.kind` | `"OCIRepository"` | Source reference kind for the platform package. |
| `sourceRef.name` | `"cozystack-platform"` | Source reference name. |
| `sourceRef.namespace` | `"cozy-system"` | Source reference namespace. |
| `sourceRef.path` | `"/"` | Source reference path. |
| `migrations.enabled` | `false` | Whether platform migrations are enabled. |
| `migrations.image` | — | Container image used for running platform migrations. |
| `migrations.targetVersion` | — | Target migration version number. |

[enable-disable]: {{% ref "/docs/v1.5/operations/configuration/components#enabling-and-disabling-components" %}}
[overwrite-parameters]: {{% ref "/docs/v1.5/operations/configuration/components#overwriting-component-parameters" %}}
[Resource Management]: {{% ref "/docs/v1.5/guides/resource-management#cpu-allocation-ratio" %}}
[oidc]: {{% ref "/docs/v1.5/operations/oidc" %}}
[telemetry]: {{% ref "/docs/v1.5/operations/configuration/telemetry" %}}
[kube-ovn]: https://kubeovn.github.io/docs/en/guide/subnet/#join-subnet
