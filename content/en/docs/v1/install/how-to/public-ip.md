---
title: "Public-network Kubernetes deployment"
linkTitle: "Deploy with public networks"
description: ""
weight: 110
---

A Kubernetes cluster for Cozystack can be deployed using only public networks:

-   Both management and worker nodes have public IP addresses.
-   Worker nodes connect to the management nodes over the public Internet, without a private internal network or VPN.

Such a setup is not recommended for production, but can be used for research and testing,
when hosting limitations prevent provisioning a private network.

To enable this setup when deploying with `talosctl`, add the following data in the node configuration files:

```yaml
cluster:
  controlPlane:
    endpoint: https://<MANAGEMENT_NODE_IP>:6443
```

For `talm`, append the same lines at end of the first node's configuration file, such as `nodes/node1.yaml`.
