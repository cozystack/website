---
title: "Troubleshooting cheatsheet"
linkTitle: "Troubleshooting"
description: "Showcase various ways to get more information out of Flux controllers to debug potential problems."
weight: 60
---

## Cozystack

### Getting basic information

You can see the logs of main installer by executing:

```yaml
kubectl logs -n cozy-system deploy/cozystack -f
```

All the platform components are installed using fluxcd HelmRelases.

You can get all installed HelmRelases:

```bash
# kubectl get hr -A
NAMESPACE                        NAME                        AGE    READY   STATUS
cozy-cert-manager                cert-manager                4m1s   True    Release reconciliation succeeded
cozy-cert-manager                cert-manager-issuers        4m1s   True    Release reconciliation succeeded
cozy-cilium                      cilium                      4m1s   True    Release reconciliation succeeded
cozy-cluster-api                 capi-operator               4m1s   True    Release reconciliation succeeded
cozy-cluster-api                 capi-providers              4m1s   True    Release reconciliation succeeded
cozy-dashboard                   dashboard                   4m1s   True    Release reconciliation succeeded
cozy-fluxcd                      cozy-fluxcd                 4m1s   True    Release reconciliation succeeded
cozy-grafana-operator            grafana-operator            4m1s   True    Release reconciliation succeeded
cozy-kamaji                      kamaji                      4m1s   True    Release reconciliation succeeded
cozy-kubeovn                     kubeovn                     4m1s   True    Release reconciliation succeeded
cozy-kubevirt-cdi                kubevirt-cdi                4m1s   True    Release reconciliation succeeded
cozy-kubevirt-cdi                kubevirt-cdi-operator       4m1s   True    Release reconciliation succeeded
cozy-kubevirt                    kubevirt                    4m1s   True    Release reconciliation succeeded
cozy-kubevirt                    kubevirt-operator           4m1s   True    Release reconciliation succeeded
cozy-linstor                     linstor                     4m1s   True    Release reconciliation succeeded
cozy-linstor                     piraeus-operator            4m1s   True    Release reconciliation succeeded
cozy-mariadb-operator            mariadb-operator            4m1s   True    Release reconciliation succeeded
cozy-metallb                     metallb                     4m1s   True    Release reconciliation succeeded
cozy-monitoring                  monitoring                  4m1s   True    Release reconciliation succeeded
cozy-postgres-operator           postgres-operator           4m1s   True    Release reconciliation succeeded
cozy-rabbitmq-operator           rabbitmq-operator           4m1s   True    Release reconciliation succeeded
cozy-redis-operator              redis-operator              4m1s   True    Release reconciliation succeeded
cozy-telepresence                telepresence                4m1s   True    Release reconciliation succeeded
cozy-victoria-metrics-operator   victoria-metrics-operator   4m1s   True    Release reconciliation succeeded
tenant-root                      tenant-root                 4m1s   True    Release reconciliation succeeded
```

Normaly all of them should be `Ready` and `Release reconciliation succeeded`


### Diagnosing `install retries exhausted` error

Sometimes you can face with the error:

```bash
# kubectl get hr -A -n cozy-dashboard dashboard
NAMESPACE          NAME          AGE   READY   STATUS
cozy-dashboard     dashboard     15m   False   install retries exhausted
```

You can try to figure out by checking events:

```bash
kubectl describe hr -n cozy-dashboard dashboard
```

if `Events: <none>` then suspend and reume the release:

```bash
kubectl patch hr -n cozy-dashboard dashboard -p '{"spec": {"suspend": true}}' --type=merge
kubectl patch hr -n cozy-dashboard dashboard -p '{"spec": {"suspend": null}}' --type=merge
```

and check the events again:

```bash
kubectl describe hr -n cozy-dashboard dashboard
```

## talos-bootstrap

### No Talos nodes in maintenance mode found!

If you encounter issues with the `talos-bootstrap` script not detecting any nodes, follow these steps to diagnose and resolve the issue:

#### Verify Network Segment

Ensure that you are running the script within the same network segment as the nodes. This is crucial for the script to be able to communicate with the nodes.

#### Use Nmap to Discover Nodes

Check if `nmap` can discover your node by running the following command:

```bash
nmap -Pn -n -p 50000 192.168.0.0/24
```
This command scans for nodes in the network that are listening on port 50000. The output should list all the nodes in the network segment that are listening on this port, indicating that they are reachable.

#### Verify talosctl Connectivity

Next, verify if talosctl can connect to a specific node, especially if it is in maintenance mode, using the command below:

```bash
talosctl -e "${node}" -n "${node}" get machinestatus -i
```

If you encounter errors similar to:

```
rpc error: code = Unimplemented desc = unknown service resource.ResourceService
```


This indicates that your version of `talosctl` is outdated. Updating `talosctl` to the latest version should resolve this issue.

### Enable Debug Mode for talos-bootstrap

If the above steps do not help, you can debug the `talos-bootstrap` script by running it in debug mode. This can provide more insights into what might be going wrong. Execute the script with the `-x` option to enable debug mode:

```bash
bash -x talos-bootstrap
```

Pay attention to the last command displayed before the error; it often indicates the command that failed and can provide clues for further troubleshooting.
