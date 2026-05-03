---
title: "Platform Package Reference"
linkTitle: "Platform Package"
description: "Reference for the Cozystack Platform Package, which defines key configuration values for a Cozystack installation and operations."
weight: 10
aliases:
  - /docs/next/install/cozystack/configmap
  - /docs/next/operations/configuration/configmap
---

This page explains the role of the Cozystack Platform Package and provides a full reference for its values.

Cozystack's main configuration is defined by a `Package` custom resource.
This Package includes the [Cozystack variant]({{% ref "/docs/next/operations/configuration/variants" %}}) and [component settings]({{% ref "/docs/next/operations/configuration/components" %}}),
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
| `publishing.exposure` | `"externalIPs"` | Exposure mode for the ingress-nginx Service. Possible values: `externalIPs`, `loadBalancer`. The default writes `Service.spec.externalIPs` from `publishing.externalIPs`; `loadBalancer` switches to `Service.type: LoadBalancer` and a `CiliumLoadBalancerIPPool` over the same IPs (with `externalTrafficPolicy: Local` to preserve client source IP). `Service.spec.externalIPs` is deprecated upstream in v1.36 (KEP-5707); plan to switch to `loadBalancer` before upgrading past Kubernetes v1.40 when the `AllowServiceExternalIPs` feature gate flips off. The `loadBalancer` mode requires Cilium L2/BGP announcements to reach the IP from outside the cluster (off by default in cozystack), and at least one address in `publishing.externalIPs` (otherwise render fails). |
| `publishing.certificates.solver` | `"http01"` | ACME challenge solver type for default letsencrypt issuer. Possible values: `http01`, `dns01`. |
| `publishing.certificates.issuerName` | `"letsencrypt-prod"` | `ClusterIssuer` name for TLS certificates used in system Helm releases. |
| `publishing.proxyProtocol` | `false` | Enables PROXY-protocol on the host ingress-nginx and auto-deploys [ouroboros]({{% ref "/docs/next/networking/hairpin-proxy-protocol" %}}) to fix the resulting hairpin-NAT problem. The upstream L4 LB in front of ingress-nginx must already be injecting PROXY-v1 headers before this flag flips on; see the linked page for verification recipes and the disable path. |
| `publishing.proxyProtocolAcknowledgeUnclean` | `false` | Acknowledgement gate for the `helm.sh/resource-policy: keep` asymmetry on the host disable path. Flipping `publishing.proxyProtocol` from `true` back to `false` stops emitting the `cozystack.ouroboros` Package CR but does not uninstall the existing one — the platform render fails until either the Package CR is deleted (which triggers the chart's pre-delete cleanup hook) or this flag is set to `true` to confirm the operator has handled the asymmetry. See [hairpin-proxy-protocol → Disable path]({{% ref "/docs/next/networking/hairpin-proxy-protocol#disable-path" %}}) for the full sequence. |

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

#### Scheduling

| Value | Default | Description |
| --- | --- | --- |
| `scheduling.globalAppTopologySpreadConstraints` | `""` | Global pod topology spread constraints applied to all managed applications. |

#### Branding

| Value | Default | Description |
| --- | --- | --- |
| `branding` | `{}` | UI branding configuration object. See the [White Labeling]({{% ref "/docs/next/operations/configuration/white-labeling" %}}) guide for available fields and usage. Individual fields (e.g., `titleText`, `logoSvg`) have their own defaults when not specified. |

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

[enable-disable]: {{% ref "/docs/next/operations/configuration/components#enabling-and-disabling-components" %}}
[overwrite-parameters]: {{% ref "/docs/next/operations/configuration/components#overwriting-component-parameters" %}}
[Resource Management]: {{% ref "/docs/next/guides/resource-management#cpu-allocation-ratio" %}}
[oidc]: {{% ref "/docs/next/operations/oidc" %}}
[telemetry]: {{% ref "/docs/next/operations/configuration/telemetry" %}}
[kube-ovn]: https://kubeovn.github.io/docs/en/guide/subnet/#join-subnet
