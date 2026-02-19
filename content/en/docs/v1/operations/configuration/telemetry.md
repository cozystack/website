---
title: "Telemetry"
linkTitle: "Telemetry"
description: "Cozystack Telemetry"
weight: 60
aliases:
  - /docs/v1/telemetry
  - /docs/v1/operations/telemetry
---

This document outlines the telemetry feature within the Cozystack project, detailing the rationale behind data collection, the nature of the data collected, data handling practices, and instructions for opting out.

## Why We Collect Telemetry

Cozystack, as an open source project, thrives on community feedback and usage insights. Telemetry data allows maintainers to understand how Cozystack is being used in real-world scenarios. This data informs decisions related to feature prioritization, testing strategies, bug fixes, and overall project evolution. Without telemetry, decisions would rely on guesswork or limited feedback, which might slow down improvement cycles or introduce features that don’t align with users’ needs. Telemetry ensures that development is guided by actual usage patterns and community requirements, fostering a more robust and user-centric platform.

## What We Collect and How

Cozystack strives to comply with the [LF Telemetry Data Policy](https://www.linuxfoundation.org/legal/telemetry-data-policy), ensuring responsible data collection practices that respect user privacy and transparency.

Our focus is on gathering non-personal usage metrics about Cozystack components rather than personal user information. We specifically collect information about cluster infrastructure (nodes, storage, networking), installed packages, and application instances. This collected data helps us gain insights into prevalent configurations and usage trends across installations.

Telemetry is collected by two components:
- **cozystack-operator** — collects cluster-level metrics (nodes, storage, packages)
- **cozystack-controller** — collects application-level metrics (deployed application instances)

For a detailed view of what data is collected, you can review the telemetry implementation:
- [Telemetry Client](https://github.com/cozystack/cozystack/tree/main/internal/telemetry)
- [Telemetry Server](https://github.com/cozystack/cozystack-telemetry-server/)

### Example of Telemetry Payload:

Below is how a typical telemetry payload looks like in Cozystack.

**From cozystack-operator** (cluster infrastructure):

```prometheus
cozy_cluster_info{cozystack_version="v1.0.0",kubernetes_version="v1.31.4"} 1
cozy_nodes_count{os="linux (Talos (v1.8.4))",kernel="6.6.64-talos"} 3
cozy_cluster_capacity{resource="cpu"} 168
cozy_cluster_capacity{resource="memory"} 811020009472
cozy_cluster_capacity{resource="nvidia.com/TU104GL_TESLA_T4"} 3
cozy_loadbalancers_count 1
cozy_pvs_count{driver="linstor.csi.linbit.com",size="5Gi"} 7
cozy_pvs_count{driver="linstor.csi.linbit.com",size="10Gi"} 6
cozy_package_info{name="cozystack.core",variant="default"} 1
cozy_package_info{name="cozystack.storage",variant="linstor"} 1
cozy_package_info{name="cozystack.monitoring",variant="default"} 1
```

**From cozystack-controller** (application instances):

```prometheus
cozy_application_count{kind="Tenant"} 2
cozy_application_count{kind="Postgres"} 5
cozy_application_count{kind="Redis"} 3
cozy_application_count{kind="Kubernetes"} 2
cozy_application_count{kind="VirtualMachine"} 0
```

Data is collected by components running within Cozystack that periodically gather and transmit usage statistics to our secure backend. The telemetry system ensures that data is anonymized, aggregated, and stored securely, with strict controls on access to protect user privacy.

## Telemetry Opt-Out

We respect your privacy and choice regarding telemetry. If you prefer not to participate in telemetry data collection, Cozystack provides a straightforward way to opt out.

Opting Out:

To disable telemetry reporting, upgrade the Cozystack operator Helm release with the `disableTelemetry` flag:

```bash
helm upgrade cozystack oci://ghcr.io/cozystack/cozystack/cozy-installer \
  --namespace cozy-system \
  --version X.Y.Z \
  --set cozystackOperator.disableTelemetry=true
```

Replace `X.Y.Z` with your currently installed Cozystack version.

{{% alert color="warning" %}}
Do not use `--reuse-values` when upgrading the Cozystack operator. The Helm chart values contain hardcoded references to the platform OCI repository. Reusing old values would result in the operator pointing to old package versions.
{{% /alert %}}

This command updates the operator to disable telemetry data collection. If you wish to re-enable telemetry in the future, run the same command with `disableTelemetry=false`.

## Conclusion

Telemetry in Cozystack is designed to support a data-informed development process that responds to the community’s needs and ensures continuous improvement. Your participation—or choice to opt out—helps shape the future of Cozystack, making it a more effective and user-focused platform for everyone.
