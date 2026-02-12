---
title: "Cozystack Package Configuration (v1.x)"
linkTitle: "Package (v1.x)"
description: "Configuration reference for Cozystack v1.x using Package-based architecture"
weight: 5
aliases:
  - /docs/v1/install/cozystack/package
  - /docs/v1/operations/configuration/v1
---

This page explains the Package-based configuration system introduced in Cozystack v1.x and provides a complete reference for configuring your Cozystack installation.

{{< alert color="info" >}}
**Version Note**: This guide applies to Cozystack v1.x and later.
For v0.x installations using ConfigMap, see [ConfigMap Reference]({{% ref "/docs/v1/operations/configuration/configmap" %}}).
{{< /alert >}}

## Overview

Cozystack v1.x introduces a unified Package-based architecture managed by `cozystack-operator`.
Instead of multiple ConfigMaps for different aspects of configuration, v1.x uses a single `Package` resource that defines all platform settings.

### Key Changes from v0.x

| v0.x Approach | v1.x Approach |
|---------------|---------------|
| ConfigMap `cozystack` in `cozy-system` | Package `cozystack.cozystack-platform` in `cozy-system` |
| Bundle names: `paas-full`, `paas-hosted` | Bundle variants: `isp-full`, `isp-hosted`, `distro-full` |
| Separate ConfigMaps for branding/scheduling | Unified Package with all configuration |
| Multiple `values-<component>` entries | Nested `components.platform.values` structure |

## Minimal Configuration Example

The simplest Package configuration for a new Cozystack installation:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
  namespace: cozy-system
spec:
  variant: isp-full
  components:
    platform:
      values:
        networking:
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
        publishing:
          host: "example.org"
          apiServerEndpoint: "https://192.168.1.10:6443"
```

Replace `example.org` with your actual domain and adjust network CIDRs if needed.

## Full Configuration Example

Complete Package configuration showing all available options:

```yaml
apiVersion: cozystack.io/v1alpha1
kind: Package
metadata:
  name: cozystack.cozystack-platform
  namespace: cozy-system
spec:
  variant: isp-full
  components:
    platform:
      values:
        bundles:
          system:
            enabled: true
            variant: "isp-full"
          iaas:
            enabled: true
          paas:
            enabled: true
          naas:
            enabled: true
          disabledPackages: []
          enabledPackages: []

        networking:
          clusterDomain: "cozy.local"
          podCIDR: "10.244.0.0/16"
          podGateway: "10.244.0.1"
          serviceCIDR: "10.96.0.0/16"
          joinCIDR: "100.64.0.0/16"
          kubeovn:
            MASTER_NODES: ""

        publishing:
          host: "example.org"
          ingressName: tenant-root
          exposedServices:
            - api
            - dashboard
            - vm-exportproxy
            - cdi-uploadproxy
          apiServerEndpoint: "https://api.example.org:6443"
          externalIPs: []
          certificates:
            issuerType: http01  # or "cloudflare"

        authentication:
          oidc:
            enabled: false
            keycloakExtraRedirectUri: ""

        scheduling:
          globalAppTopologySpreadConstraints: ""

        branding: {}

        registries: {}

        resources:
          cpuAllocationRatio: 10
          memoryAllocationRatio: 1
          ephemeralStorageAllocationRatio: 40
```

## Configuration Reference

### Package Variants

The `spec.variant` field determines which bundle of components to install:

| Variant | Description | Use Case |
|---------|-------------|----------|
| `isp-full` | Full platform with all system components | Production ISP/hosting deployments |
| `isp-full-generic` | Full platform with generic settings | Testing and development |
| `isp-hosted` | Hosted variant without system components | Multi-tenant hosted environments |
| `distro-full` | Distribution variant | Custom distributions |

### bundles

Controls which functional bundles are enabled:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `system.enabled` | boolean | `true` | Enable system bundle |
| `system.variant` | string | `isp-full` | System bundle variant |
| `iaas.enabled` | boolean | `true` | Enable IaaS bundle (virtualization, storage) |
| `paas.enabled` | boolean | `true` | Enable PaaS bundle (databases, message queues) |
| `naas.enabled` | boolean | `true` | Enable NaaS bundle (networking services) |
| `disabledPackages` | array | `[]` | List of packages to disable |
| `enabledPackages` | array | `[]` | List of additional packages to enable |

### networking

Defines cluster networking configuration:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `clusterDomain` | string | `cozy.local` | Kubernetes cluster DNS domain |
| `podCIDR` | string | `10.244.0.0/16` | Pod network CIDR |
| `podGateway` | string | `10.244.0.1` | Pod network gateway IP |
| `serviceCIDR` | string | `10.96.0.0/16` | Service network CIDR |
| `joinCIDR` | string | `100.64.0.0/16` | Join network CIDR for tenant isolation |
| `kubeovn.MASTER_NODES` | string | `""` | KubeOVN master nodes (auto-detected if empty) |

{{< note >}}
Network CIDRs must match those configured during Kubernetes bootstrap with Talm or talosctl.
{{< /note >}}

### publishing

Controls service exposure and certificates:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | string | `example.org` | Root domain for all Cozystack services |
| `ingressName` | string | `tenant-root` | Ingress class name |
| `exposedServices` | array | `[api, dashboard, vm-exportproxy, cdi-uploadproxy]` | Services to expose via ingress |
| `apiServerEndpoint` | string | `""` | Kubernetes API endpoint for kubeconfig generation |
| `externalIPs` | array | `[]` | External IPs for service exposure (when not using MetalLB) |
| `certificates.issuerType` | string | `http01` | Certificate issuer: `http01` or `cloudflare` |

**Available exposed services:**
- `api` - Kubernetes API proxy
- `dashboard` - Cozystack web UI
- `keycloak` - OIDC authentication
- `grafana` - Monitoring dashboards
- `vm-exportproxy` - VM export service
- `cdi-uploadproxy` - VM image upload service

### authentication

OIDC and authentication settings:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `oidc.enabled` | boolean | `false` | Enable Keycloak OIDC authentication |
| `oidc.keycloakExtraRedirectUri` | string | `""` | Additional redirect URI for Keycloak |

### scheduling

Cluster scheduling configuration:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `globalAppTopologySpreadConstraints` | string | `""` | Global topology spread constraints for applications |

### resources

Resource allocation and overcommit ratios:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cpuAllocationRatio` | number | `10` | CPU overcommit ratio (10 = 10:1) |
| `memoryAllocationRatio` | number | `1` | Memory overcommit ratio (1 = 1:1, no overcommit) |
| `ephemeralStorageAllocationRatio` | number | `40` | Ephemeral storage overcommit ratio |

{{< alert color="warning" >}}
**Overcommit ratios** allow allocating more virtual resources than physically available.
Use conservative values for production workloads. Higher ratios increase density but may impact performance.
{{< /alert >}}

## Runtime Configuration Changes

Update configuration without reinstalling Cozystack by patching the Package resource.

### Enable OIDC Authentication

```bash
kubectl patch package cozystack.cozystack-platform -n cozy-system --type merge -p '{
  "spec": {
    "components": {
      "platform": {
        "values": {
          "authentication": {
            "oidc": {
              "enabled": true
            }
          }
        }
      }
    }
  }
}'
```

### Expose Additional Services

Add Keycloak to exposed services:

```bash
kubectl patch package cozystack.cozystack-platform -n cozy-system --type merge -p '{
  "spec": {
    "components": {
      "platform": {
        "values": {
          "publishing": {
            "exposedServices": ["api", "dashboard", "keycloak"]
          }
        }
      }
    }
  }
}'
```

### Change Resource Allocation Ratios

Adjust CPU overcommit ratio:

```bash
kubectl patch package cozystack.cozystack-platform -n cozy-system --type merge -p '{
  "spec": {
    "components": {
      "platform": {
        "values": {
          "resources": {
            "cpuAllocationRatio": 5
          }
        }
      }
    }
  }
}'
```

### Disable Specific Packages

Disable a package (e.g., `clickhouse`):

```bash
kubectl patch package cozystack.cozystack-platform -n cozy-system --type merge -p '{
  "spec": {
    "components": {
      "platform": {
        "values": {
          "bundles": {
            "disabledPackages": ["clickhouse"]
          }
        }
      }
    }
  }
}'
```

## Viewing Current Configuration

Get the current Package configuration:

```bash
kubectl get package cozystack.cozystack-platform -n cozy-system -o yaml
```

View specific configuration values:

```bash
kubectl get package cozystack.cozystack-platform -n cozy-system \
  -o jsonpath='{.spec.components.platform.values}' | yq
```

## Migration from v0.x

To migrate from v0.x ConfigMap to v1.x Package:

1. **Export existing configuration:**
   ```bash
   kubectl get cm cozystack -n cozy-system -o yaml > cozystack-v0-config.yaml
   ```

2. **Create equivalent Package resource** using the mapping table below

3. **Apply the new Package:**
   ```bash
   kubectl apply -f cozystack-v1-package.yaml
   ```

### Configuration Mapping

| v0.x ConfigMap Key | v1.x Package Path |
|--------------------|-------------------|
| `bundle-name: paas-full` | `spec.variant: isp-full` |
| `root-host` | `spec.components.platform.values.publishing.host` |
| `api-server-endpoint` | `spec.components.platform.values.publishing.apiServerEndpoint` |
| `expose-services` | `spec.components.platform.values.publishing.exposedServices` |
| `ipv4-pod-cidr` | `spec.components.platform.values.networking.podCIDR` |
| `ipv4-pod-gateway` | `spec.components.platform.values.networking.podGateway` |
| `ipv4-svc-cidr` | `spec.components.platform.values.networking.serviceCIDR` |
| `ipv4-join-cidr` | `spec.components.platform.values.networking.joinCIDR` |
| `bundle-enable` | `spec.components.platform.values.bundles.enabledPackages` |
| `bundle-disable` | `spec.components.platform.values.bundles.disabledPackages` |

## Troubleshooting

### Package Not Reconciling

Check Package status:
```bash
kubectl describe package cozystack.cozystack-platform -n cozy-system
```

Check operator logs:
```bash
kubectl logs -n cozy-system deploy/cozystack-operator -f
```

### Configuration Not Applied

Verify Package is being watched:
```bash
kubectl get package -A
```

Check HelmRelease status:
```bash
kubectl get hr -A | grep -v True
```

### Invalid Configuration

Validate Package syntax:
```bash
kubectl apply --dry-run=server -f cozystack-package.yaml
```

## Related Documentation

- [Cozystack Bundles Reference]({{% ref "/docs/v1/operations/configuration/bundles" %}})
- [Components Configuration]({{% ref "/docs/v1/operations/configuration/components" %}})
- [ConfigMap Reference (v0.x)]({{% ref "/docs/v1/operations/configuration/configmap" %}})
- [Getting Started: Install Cozystack]({{% ref "/docs/v1/getting-started/install-cozystack" %}})
