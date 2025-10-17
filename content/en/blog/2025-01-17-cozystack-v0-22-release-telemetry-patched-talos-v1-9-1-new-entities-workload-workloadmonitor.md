---
title: "Cozystack v0.22 Release: telemetry, patched Talos v1.9.1, new entities Workload и WorkloadMonitor"
slug: cozystack-v0-22-release-telemetry-patched-talos-v1-9-1-new-entities-workload--workloadmonitor
date: 2025-01-17
author: "Timur Tukaev"
description: "Main changes"
---

### Cozystack v0.22 Release: telemetry, patched Talos v1.9.1, new entities Workload и WorkloadMonitor

### Main changes

In the latest release was added cozystack-controller and new entities: Workload and WorkloadMonitor, which allow monitoring the state of pods managed by operators and evaluating the service level according to predefined rules.

Since different applications in Cozystack are managed by different operators, we decided to create a unified format for displaying the status of each service.

#### It works as follows:

During an application’s deployment, a WorkloadMonitor is deployed alongside it, which watches the state of pods by selector. As soon as the selector finds a pod, a new entity is created for it: Workload, which displays the role of each pod and its status.

In the status of the WorkloadMonitor, you can see the number of existing replicas and the minimum number required to service the application. As soon as the number of workloads falls below the minReplicas value for the WorkloadMonitor, the service is marked as non-operational.

For applications without a fixed number of replicas, such as Kubernetes workers that can scale dynamically, it is possible not to specify the number of replicas in the WorkloadMonitor at all. In this case, it will simply count the total number of running instances.

This mechanism allows the use of any operators and pod management methods in Kubernetes and makes it easy to expand the platform by providing a unified interface for displaying the current status of the service.

For Kubernetes applications like Postgres, Monitoring, VirtualMachine, VMInstance, Redis, Etcd, and SeaweedFS, a WorkloadMonitor has been added to collect information about replicas and their operability.

The Cozystack dashboard now displays the number of application replicas and the service level for each workload group.

![](https://cdn-images-1.medium.com/max/800/1*EEQEZnOxwexdC6rmGQ6Zcg.png)

### Telemetry

Client and server telemetry have been implemented and [released](https://github.com/aenix-io/cozystack-telemetry-server) under the Apache License 2.0. Metrics collection has been implemented in accordance with the [LF Telemetry Data Collection and Usage Policy](https://www.linuxfoundation.org/legal/telemetry-data-policy) and can be easily disabled with the single configuration option `telemetry-enabled:false` in Cozystack. In future releases, a public dashboard with the collected information is planned. See [documentation](https://cozystack.io/docs/telemetry/) for more details.

### Other changes

- The cluster-autoscaler component for Kubernetes and its configuration have been updated, allowing for more efficient scaling of clusters both up and down.
- [MAINTAINERS](https://github.com/aenix-io/cozystack/blob/main/MAINTAINERS.md) file has been updated, listing project contributors and their areas of responsibility.
- A new service application called builder has been added to the platform, allowing you to build the platform directly within Kubernetes.
- For VictoriaMetrics, default resource requests and limits have been increased, and the ability to specify custom parameters has been added.
- Metrics collection from databases for Grafana and Alerta has been added.
- Alerts for the state of virtual machines have been added.
- Alerts for the state of Postgres clusters have been added.
- Metrics collection for KubeVirt has been configured and a Grafana dashboard added.
- In the Cozystack configuration, the option extra-keycloak-redirect-uri-for-dashboard has been added, allowing you to configure additional redirect URLs for Keycloak.
- Fixed a VMInstance bug that was blocking the connection of VMdisks to virtual machines.

![](https://cdn-images-1.medium.com/max/800/1*2QrRVPI2aX1cTINRsKtFzA.png)
Grafana dashboard for KubeVirt

### Components updates

- Flux Operator upgraded from v0.10.0 to v0.12.0.
- Flux Instance chart updated from v0.9.0 to v0.12.0.
- Cilium updated to version v1.16.5.
- Kube-OVN updated to version v1.13.2.
- CNPG PostgreSQL Operator updated to version v1.25.0.
- Talos Linux has been updated. Due to several bugs upstream, the platform is currently delivered with a patched image v1.9.1.

*For more details, check out the project on* [GitHub](https://github.com/aenix-io/cozystack/releases/tag/v0.22.0)*.*

### Feel free to join our community spaces

- [Telegram](https://t.me/cozystack)
- [Slack](https://kubernetes.slack.com/archives/C06L3CPRVN1)
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)