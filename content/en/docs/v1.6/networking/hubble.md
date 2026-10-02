---
title: "Enabling Hubble for Network Observability"
linkTitle: "Hubble"
description: "Turn on Cilium's Hubble observability stack, and read the flow, DNS and L7 metrics through the platform Grafana dashboards Cozystack ships for it."
weight: 50
---

Hubble is the network and security observability layer built on top of Cilium. It gives visibility into the communication and behaviour of services in the cluster — flow logs, DNS queries, and L7 request metrics.

Hubble is **disabled by default** in Cozystack to keep resource usage down. This page covers turning it on and reading the results. For where Hubble sits in the data plane, see [Networking architecture](/docs/v1.6/networking/architecture/#observability-with-hubble).

## Prerequisites

- A Cozystack cluster running Cilium as the CNI (the default).
- The [Monitoring](/docs/v1.6/operations/services/monitoring/) hub deployed, for Grafana access and metric storage.

## Enable Hubble

Enable Hubble, Relay and the UI in the Cilium configuration, and turn on the metrics you want exported:

```yaml
cilium:
  hubble:
    enabled: true
    relay:
      enabled: true
    ui:
      enabled: true
    metrics:
      enabled:
        - dns
        - drop
        - tcp
        - flow
        - port-distribution
        - icmp
        - httpV2:exemplars=true;labelsContext=source_ip,source_namespace,source_workload,destination_ip,destination_namespace,destination_workload,traffic_direction
```

The `metrics.enabled` list is what makes the dashboards below work — without it Hubble runs but exports nothing for Grafana to draw. The `httpV2` entry in particular must keep its `labelsContext`, because the L7 HTTP dashboard groups by source and destination workload and cannot do so if those labels are absent.

### Components

Enabling Hubble brings up:

- **Hubble Relay** — aggregates flow data from all Cilium agents.
- **Hubble UI** — web interface for exploring network flows.
- **Hubble Metrics** — Prometheus metrics for network observability.

## Grafana dashboards

Cozystack ships four Hubble dashboards, delivered in the `hubble` folder of the platform Grafana:

| Dashboard | Description |
|-----------|-------------|
| **Overview** | General Hubble metrics including processing statistics |
| **DNS Namespace** | DNS query and response metrics by namespace |
| **L7 HTTP Metrics** | HTTP layer 7 metrics by workload |
| **Network Overview** | Network flow overview by namespace |

These are infrastructure dashboards, so they are provisioned only for the platform-level Monitoring release — the one in `tenant-root` or `cozy-monitoring`. A tenant's own Grafana does not receive them; tenants see their own application dashboards instead.

To reach them, open Grafana through the monitoring hub, browse to the `hubble` folder in the dashboard browser, and pick a dashboard.

## Metrics

Hubble exposes the following, all queryable directly in Grafana:

- `hubble_flows_processed_total` — total number of flows processed
- `hubble_dns_queries_total` — DNS queries by type
- `hubble_dns_responses_total` — DNS responses by status
- `hubble_drop_total` — dropped packets by reason
- `hubble_tcp_flags_total` — TCP connections by flag
- `hubble_http_requests_total` — HTTP requests by method and status

## Troubleshooting

Check that Relay and the UI are running:

```bash
kubectl get pods -n cozy-cilium -l k8s-app=hubble-relay
kubectl get pods -n cozy-cilium -l k8s-app=hubble-ui
```

Verify the metrics endpoint is serving:

```bash
kubectl port-forward -n cozy-cilium svc/hubble-metrics 9965:9965
curl http://localhost:9965/metrics
```

Confirm the scrape target exists — if the dashboards are empty but the endpoint above returns data, this is usually the missing link:

```bash
kubectl get servicemonitor -n cozy-cilium
```
