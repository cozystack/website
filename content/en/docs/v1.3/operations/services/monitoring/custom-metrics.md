---
title: "Custom Metrics Collection"
linkTitle: "Custom Metrics"
description: "Connect your own Prometheus exporters to the Cozystack tenant monitoring stack using VMServiceScrape and VMPodScrape."
weight: 15
---

## Overview

Cozystack tenant monitoring supports scraping custom metrics from your own applications and exporters. The tenant VMAgent discovers scrape targets through Kubernetes namespace labels, allowing you to connect any application that exposes a Prometheus-compatible `/metrics` endpoint.

This guide explains how to create `VMServiceScrape` and `VMPodScrape` resources so that the tenant VMAgent collects your custom metrics and makes them available in Grafana.

## Prerequisites

- Monitoring is enabled for your tenant (see [Monitoring Setup]({{< ref "setup" >}}))
- Your application or exporter is deployed and exposes a Prometheus-compatible `/metrics` endpoint
- You have `kubectl` access to the cluster

## Using VMServiceScrape

A `VMServiceScrape` tells the tenant VMAgent to scrape metrics from endpoints behind a Kubernetes Service.

### Example

Suppose you have a Service named `my-app` in namespace `my-app-ns` that exposes metrics on port `metrics` at path `/metrics`:

```yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMServiceScrape
metadata:
  name: my-app-metrics
  namespace: my-app-ns
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

Apply the resource:

```bash
kubectl apply --filename vmservicescrape.yaml --namespace my-app-ns
```

### Key Fields

| Field | Description |
| --- | --- |
| `spec.selector.matchLabels` | Label selector to find the target Service |
| `spec.endpoints[].port` | Named port on the Service to scrape |
| `spec.endpoints[].path` | HTTP path for metrics (default: `/metrics`) |
| `spec.endpoints[].interval` | Scrape interval (default: inherited from VMAgent, typically `30s`) |

## Using VMPodScrape

A `VMPodScrape` scrapes metrics directly from Pods, without requiring a Service. This is useful for sidecar exporters or applications that do not have a corresponding Service.

### Example

Suppose you have Pods labeled `app: my-worker` that expose metrics on port `9090` at path `/metrics`:

```yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMPodScrape
metadata:
  name: my-worker-metrics
  namespace: my-app-ns
spec:
  selector:
    matchLabels:
      app: my-worker
  podMetricsEndpoints:
    - port: "9090"
      path: /metrics
```

Apply the resource:

```bash
kubectl apply --filename vmpodscrape.yaml --namespace my-app-ns
```

### Key Fields

| Field | Description |
| --- | --- |
| `spec.selector.matchLabels` | Label selector to find the target Pods |
| `spec.podMetricsEndpoints[].port` | Port name or number on the Pod to scrape |
| `spec.podMetricsEndpoints[].path` | HTTP path for metrics (default: `/metrics`) |

## Verifying Metrics Collection

After creating a `VMServiceScrape` or `VMPodScrape`, verify that the tenant VMAgent is scraping your targets.

### Check VMAgent Targets

List the VMAgent pods in your tenant namespace and open the targets page:

```bash
kubectl get pods --namespace <tenant-namespace> --selector app.kubernetes.io/name=vmagent
```

Port-forward to the VMAgent UI to inspect active targets:

```bash
kubectl port-forward --namespace <tenant-namespace> service/vmagent-vmagent 8429:8429
```

Then open `http://localhost:8429/targets` in your browser. Your new scrape target should appear in the list with status `UP`.

### Query Metrics in Grafana

1. Open Grafana at `https://grafana.<tenant-host>`
2. Go to **Explore**
3. Select the **VictoriaMetrics** datasource
4. Run a PromQL query for one of your custom metrics, for example:

   ```promql
   up{job="my-app-ns/my-app-metrics"}
   ```

A result of `1` confirms that the target is being scraped successfully.

## Troubleshooting

- **Target not appearing in VMAgent**: Verify that the namespace has the `namespace.cozystack.io/monitoring: <tenant-namespace>` label and that the `VMServiceScrape`/`VMPodScrape` is created in that namespace
- **Target shows status DOWN**: Check that the application is running and the metrics endpoint is reachable on the configured port and path
- **No metrics in Grafana**: Confirm that the VMAgent is writing to the correct VMCluster by checking the VMAgent logs:

  ```bash
  kubectl logs --namespace <tenant-namespace> --selector app.kubernetes.io/name=vmagent
  ```
