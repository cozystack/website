---
title: "From Zero to kubectl in 5 Minutes — Managed Kubernetes on Your Own Metal"
slug: from-zero-to-kubectl-managed-kubernetes-on-your-own-metal
date: 2026-06-04
author: "Timur Tukaev"
description: "Deploy a production-grade Kubernetes cluster on your own hardware in minutes. Cozystack uses Kamaji, Cluster API, and KubeVirt to give you fully managed Kubernetes with autoscaling, Cilium CNI, and built-in addons — no cloud bill required."
images:
  - "001.png"
article_types:
  - how-to
topics:
  - kubernetes
  - platform
---

Every platform team has faced this: a new project needs a Kubernetes cluster. With cloud providers, that means a new billing account, region selection, networking decisions, and a baseline cost of $70–300/month before a single pod runs. Self-hosting with kubeadm? Days of setup, certificates, etcd management, and upgrade anxiety. Rancher helps, but you're still managing the lifecycle yourself.

What if creating a production-grade Kubernetes cluster was as simple as filling out a form?

## Deploy a Managed Kubernetes Cluster

Cozystack uses [Kamaji](https://kamaji.clastix.io/) for control planes (running as pods — no dedicated VMs for masters), [Cluster API](https://cluster-api.sigs.k8s.io/) for lifecycle management, and [KubeVirt](https://kubevirt.io/) for worker node VMs. You pick the version, the instance type, and how many nodes you want.

### Via Dashboard

1. Open the Cozystack dashboard at `https://dashboard.<your-domain>`.
2. Navigate to the **Marketplace** and find **Kubernetes**.

{{< figure src="001.png" alt="Cozystack dashboard Marketplace showing the Kubernetes application tile" width="720" >}}

3. Click **Deploy** and configure:
   - **Name:** e.g., `dev-cluster`
   - **Version:** pick from v1.30 to v1.35
   - **Node group:** set `minReplicas: 2`, `maxReplicas: 5`
   - **Instance type:** e.g., `u1.large` (2 vCPU, 8 Gi RAM)
   - **Addons:** check `ingress`, `cert-manager`, `monitoring`

{{< figure src="002.png" alt="Kubernetes deployment form with version, node group, and addons configured" width="720" >}}

4. Click **Deploy**.

Worker nodes boot as VMs, join the cluster, and become Ready — typically within 3–5 minutes.

{{< figure src="003.png" alt="Kubernetes cluster worker nodes reporting Ready status after deployment" width="720" >}}

> **What's included:** Every cluster comes pre-configured with [Cilium CNI](https://cilium.io/) (eBPF-based networking), KubeVirt CSI driver (for persistent volumes), and Cluster Autoscaler (automatic node scaling based on demand).

### Via kubectl

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: kubernetes-dev
  namespace: tenant-team1
spec:
  chart:
    spec:
      chart: kubernetes
      reconcileStrategy: Revision
      sourceRef:
        kind: HelmRepository
        name: cozystack-apps
        namespace: cozy-public
  interval: 0s
  values:
    host: dev.team1.example.org
    version: v1.33
    nodeGroups:
      md0:
        minReplicas: 2
        maxReplicas: 5
        instanceType: u1.large
        ephemeralStorage: 20Gi
    controlPlane:
      replicas: 2
    addons:
      ingressNginx:
        enabled: true
      certManager:
        enabled: true
      monitoringAgents:
        enabled: true
```

```bash
kubectl apply -f kubernetes-dev.yaml
```

### Get your kubeconfig

In the dashboard, open the cluster application → **Secrets** tab → download `admin.conf`.

{{< figure src="004.png" alt="Cluster application Secrets tab with admin.conf kubeconfig available for download" width="720" >}}

Or via CLI:

```bash
kubectl get secret -n tenant-team1 kubernetes-dev-admin-kubeconfig \
  -o jsonpath='{.data.admin\.conf}' | base64 -d > kubeconfig-dev.yaml

export KUBECONFIG=kubeconfig-dev.yaml
kubectl get nodes
```

```
NAME                              STATUS   ROLES           AGE   VERSION
kubernetes-dev-md0-vn8dh-jjbm9   Ready    ingress-nginx   4m    v1.33.2
kubernetes-dev-md0-vn8dh-xhsvl   Ready    ingress-nginx   3m    v1.33.2
```

Deploy your apps with standard `kubectl` or `helm` — no vendor-specific tooling needed.

## Learn more

- [Managed Kubernetes documentation](https://cozystack.io/docs/v1.6/kubernetes/)
- [Deploy Applications guide](https://cozystack.io/docs/v1.6/getting-started/deploy-app/)
- [Create a Tenant](https://cozystack.io/docs/v1.6/getting-started/create-tenant/)

## Join the community

- [GitHub](https://github.com/cozystack/cozystack)
- Telegram [group](https://t.me/cozystack)
- Slack [group](https://kubernetes.slack.com/archives/C06L3CPRVN1) (get invite at [https://slack.kubernetes.io](https://slack.kubernetes.io))
- [Community Meeting Calendar](https://calendar.google.com/calendar?cid=ZTQzZDIxZTVjOWI0NWE5NWYyOGM1ZDY0OWMyY2IxZTFmNDMzZTJlNjUzYjU2ZGJiZGE3NGNhMzA2ZjBkMGY2OEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
