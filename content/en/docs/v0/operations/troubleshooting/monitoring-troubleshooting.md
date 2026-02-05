---
title: "Monitoring Troubleshooting"
linkTitle: "Troubleshooting"
description: "Guide to diagnosing and resolving issues with monitoring components in Cozystack"
weight: 10
---

This guide provides troubleshooting steps for common issues with monitoring components in Cozystack, including metrics collection, alerting, visualization, and log collection.

## Diagnosing Missing Metrics

If metrics are not appearing in Grafana or VictoriaMetrics, follow these steps:

### Check VMAgent Status

Ensure VMAgent is running and collecting metrics:

```bash
kubectl get pods -n cozy-monitoring -l app.kubernetes.io/name=vmagent
kubectl logs -n cozy-monitoring -l app.kubernetes.io/name=vmagent --tail=50
```

### Verify Targets

Check if VMAgent can scrape targets:

```bash
kubectl exec -n cozy-monitoring -c vmagent deploy/vmagent -- curl -s http://localhost:8429/targets | jq .
```

Look for targets with `health: "up"`. If targets are down, check network connectivity and RBAC permissions.

### Resource Limits

If VMAgent is resource-constrained, increase limits in the monitoring configuration:

```yaml
vmagent:
  resources:
    limits:
      cpu: 500m
      memory: 1Gi
    requests:
      cpu: 100m
      memory: 256Mi
```

### Security Considerations

Ensure TLS is enabled for secure metric collection:

- Verify certificates in the VMAgent configuration.
- Check RBAC roles allow VMAgent to access required endpoints.

For more details, see [Monitoring Setup]({{{% ref "/docs/v0/operations/services/monitoring/setup" %}}).

## Alerts Not Arriving

If alerts are not being received, investigate Alertmanager and Alerta.

### Check Alertmanager

Verify Alertmanager is processing alerts:

```bash
kubectl get pods -n cozy-monitoring -l app.kubernetes.io/name=alertmanager
kubectl logs -n cozy-monitoring -l app.kubernetes.io/name=alertmanager --tail=50
```

Check alert rules:

```bash
kubectl get prometheusrules -n cozy-monitoring
```

### Verify Alerta Configuration

Ensure Alerta is configured correctly:

```bash
kubectl get pods -n cozy-monitoring -l app.kubernetes.io/name=alerta
kubectl logs -n cozy-monitoring -l app.kubernetes.io/name=alerta --tail=50
```

Check routing configuration in the monitoring spec:

```yaml
alerta:
  alerts:
    telegram:
      token: "your-token"
      chatID: "your-chat-id"
```

### Scalability Issues

If alerts are delayed due to high volume, adjust resource limits:

```yaml
alerta:
  resources:
    limits:
      cpu: 2
      memory: 2Gi
```

### Security

- Use RBAC to restrict alert access.
- Enable TLS for alert endpoints.

See [Monitoring Alerting]({{{% ref "/docs/v0/operations/services/monitoring/alerting" %}}) for configuration details.

## Grafana Issues

Troubleshoot access and data source problems in Grafana.

### Access Problems

If you cannot access Grafana:

- Check the service and ingress:

```bash
kubectl get svc,ingress -n cozy-monitoring -l app.kubernetes.io/name=grafana
```

- Verify RBAC permissions for your user.

### Data Source Configuration

Ensure data sources are connected:

1. Log into Grafana.
2. Go to Configuration > Data Sources.
3. Check VictoriaMetrics data source is healthy.

If not, update the URL and credentials.

### Resource Limits

For performance issues, increase Grafana resources:

```yaml
grafana:
  resources:
    limits:
      cpu: 1
      memory: 1Gi
```

### Security

- Enable authentication and authorization.
- Use TLS for Grafana access.

Refer to [Monitoring Dashboards]({{{% ref "/docs/v0/operations/services/monitoring/dashboards" %}}) for dashboard setup.

## Log Collection Problems

Address issues with Fluent Bit and VLogs.

### Check Fluent Bit

Verify Fluent Bit is collecting logs:

```bash
kubectl get pods -n cozy-monitoring -l app.kubernetes.io/name=fluent-bit
kubectl logs -n cozy-monitoring -l app.kubernetes.io/name=fluent-bit --tail=50
```

### Verify VLogs

Ensure VLogs is storing logs:

```bash
kubectl get pods -n cozy-monitoring -l app.kubernetes.io/name=vlogs
kubectl logs -n cozy-monitoring -l app.kubernetes.io/name=vlogs --tail=50
```

Check log ingestion:

```bash
kubectl exec -n cozy-monitoring -c vlogs deploy/vlogs -- curl -s http://localhost:9428/health
```

### Scalability

If logs are not being collected due to load, adjust resources:

```yaml
logsStorages:
- name: default
  storage: 50Gi  # Increase storage
```

### Security

- Use RBAC for log access.
- Enable TLS for log shipping.

For more information, see [Monitoring Logs]({{{% ref "/docs/v0/operations/services/monitoring/logs" %}}).