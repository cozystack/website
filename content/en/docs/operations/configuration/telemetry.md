---
title: "Telemetry"
linkTitle: "Telemetry"
description: "Cozystack Telemetry"
weight: 60
aliases:
  - /docs/telemetry
  - /docs/operations/telemetry
---

This document outlines the telemetry feature within the Cozystack project, detailing the rationale behind data collection, the nature of the data collected, data handling practices, and instructions for opting out.

## Why We Collect Telemetry

Cozystack, as an open source project, thrives on community feedback and usage insights. Telemetry data allows maintainers to understand how Cozystack is being used in real-world scenarios. This data informs decisions related to feature prioritization, testing strategies, bug fixes, and overall project evolution. Without telemetry, decisions would rely on guesswork or limited feedback, which might slow down improvement cycles or introduce features that don’t align with users’ needs. Telemetry ensures that development is guided by actual usage patterns and community requirements, fostering a more robust and user-centric platform.

## What We Collect and How

Cozystack strives to comply with the [LF Telemetry Data Policy](https://www.linuxfoundation.org/legal/telemetry-data-policy), ensuring responsible data collection practices that respect user privacy and transparency.

Our focus is on gathering non-personal usage metrics about Cozystack components rather than personal user information. We specifically collect information on the most commonly used application packages, the bundle names in use, enabled Cozystack features, as well as kernel versions and operating systems running in the environment. This collected data helps us gain insights into prevalent configurations and usage trends across installations.

For a detailed view of what data is collected, you can review the telemetry implementation:
- [Telemetry Client](https://github.com/cozystack/cozystack/tree/main/internal/telemetry)
- [Telemetry Server](https://github.com/cozystack/cozystack-telemetry-server/)

### Example of Telemetry Payload:

Below is how a typical telemetry payload looks like in Cozystack:

```prometheus
cozy_cluster_info{cozystack_version="v0.22.0",kubernetes_version="v1.31.4",oidc_enabled="true",bundle_name="paas-full",bunde_enable="",bunde_disable=""} 1
cozy_nodes_count{os="linux (Talos (v1.8.4))",kernel="6.6.64-talos"} 3
cozy_loadbalancers_count 1
cozy_tenants_count 2
cozy_pvs_count{driver="linstor.csi.linbit.com",size="5Gi"} 7
cozy_pvs_count{driver="linstor.csi.linbit.com",size="10Gi"} 6
cozy_pvs_count{driver="linstor.csi.linbit.com",size="25Gi"} 2
cozy_workloads_count{uid="6099a6ff-87bd-463b-9deb-6b8dcdc7c47b",kind="etcd",type="etcd",version="2.4.0"} 3
cozy_workloads_count{uid="17808511-372f-4cb5-ab1e-b3693118df77",kind="ingress",type="controller",version="1.4.0"} 2
cozy_workloads_count{uid="994df12f-ed0d-4bd2-988e-955b9fa5d451",kind="kubernetes",type="control-plane",version="0.15.0"} 2
cozy_workloads_count{uid="532cc3b0-84d1-4ad2-be4f-3c5c08c93633",kind="kubernetes",type="worker",version="0.15.0"} 10
cozy_workloads_count{uid="d0e0fa40-38bd-4e86-9d24-6c8e2f16434c",kind="postgres",type="postgres",version="0.8.0"} 2
```

Data is collected by components running within Cozystack that periodically gather and transmit usage statistics to our secure backend. The telemetry system ensures that data is anonymized, aggregated, and stored securely, with strict controls on access to protect user privacy.

## Telemetry Opt-Out

We respect your privacy and choice regarding telemetry. If you prefer not to participate in telemetry data collection, Cozystack provides a straightforward way to opt out.

Opting Out:

To disable telemetry reporting, execute the following command:

```bash
kubectl patch -n cozy-system configmap cozystack --type=merge -p '{"data":{"telemetry-enabled": "false"}}'
```

This command updates the Cozystack configuration to disable telemetry data collection. If you wish to re-enable telemetry in the future, reverse the change by setting `telemetry-enabled` back to `true`.

## Conclusion

Telemetry in Cozystack is designed to support a data-informed development process that responds to the community’s needs and ensures continuous improvement. Your participation—or choice to opt out—helps shape the future of Cozystack, making it a more effective and user-focused platform for everyone.
