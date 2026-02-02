---
title: "Deploying Cozystack on Generic Kubernetes"
linkTitle: "Generic Kubernetes"
description: "How to deploy Cozystack on k3s, kubeadm, RKE2, or other Kubernetes distributions without Talos Linux"
weight: 50
---

This guide explains how to deploy Cozystack on generic Kubernetes distributions such as k3s, kubeadm, or RKE2.
While Talos Linux remains the recommended platform for production deployments, Cozystack supports deployment on other Kubernetes distributions using the `isp-full-generic` bundle.

## When to Use Generic Kubernetes

Consider using generic Kubernetes instead of Talos Linux when:

- You have an existing Kubernetes cluster you want to enhance with Cozystack
- Your infrastructure doesn't support Talos Linux (certain cloud providers, embedded systems)
- You need specific Linux features or packages not available in Talos

For new production deployments, [Talos Linux]({{% ref "/docs/guides/talos" %}}) is recommended due to its security and operational benefits.

## Prerequisites

### Supported Distributions

Cozystack has been tested on:

- **k3s** v1.32+ (recommended for single-node and edge deployments)
- **kubeadm** v1.28+
- **RKE2** v1.28+

### Host Requirements

- **Operating System**: Ubuntu 22.04+ or Debian 12+ (kernel 5.x+ with systemd)
- **Architecture**: amd64 or arm64
- **Hardware**: See [hardware requirements]({{% ref "/docs/install/hardware-requirements" %}})

### Required Packages

Install the following packages on all nodes:

```bash
apt-get update
apt-get install -y nfs-common open-iscsi multipath-tools
```

### Required Services

Enable and start required services:

```bash
systemctl enable --now iscsid
systemctl enable --now multipathd
```

## Sysctl Configuration

{{% alert color="warning" %}}
:warning: **Critical**: The sysctl settings below are mandatory for Cozystack to function properly.
Without these settings, Kubernetes components will fail due to insufficient inotify watches.
{{% /alert %}}

Create `/etc/sysctl.d/99-cozystack.conf` with the following content:

```ini
# Inotify limits (critical for Cozystack)
fs.inotify.max_user_watches = 2099999999
fs.inotify.max_user_instances = 2099999999
fs.inotify.max_queued_events = 2099999999

# Filesystem limits
fs.file-max = 2097152
fs.aio-max-nr = 1048576

# Network forwarding (required for Kubernetes)
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# VM tuning
vm.swappiness = 1
```

Apply the settings:

```bash
sysctl --system
```

## Kubernetes Configuration

Cozystack manages its own networking (Cilium/KubeOVN), storage (LINSTOR), and ingress (NGINX).
Your Kubernetes distribution must be configured to **not** install these components.

### Required Configuration

| Component | Requirement |
|-----------|-------------|
| CNI | **Disabled** — Cozystack deploys Cilium or KubeOVN |
| Ingress Controller | **Disabled** — Cozystack deploys NGINX |
| Storage Provisioner | **Disabled** — Cozystack deploys LINSTOR |
| kube-proxy | **Disabled** — Cilium replaces it |
| Cluster Domain | Must be `cozy.local` |

### k3s Configuration

When installing k3s, use the following flags:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --disable=traefik \
  --disable=servicelb \
  --disable=local-storage \
  --disable-network-policy \
  --disable-kube-proxy \
  --flannel-backend=none \
  --cluster-domain=cozy.local \
  --tls-san=<YOUR_NODE_IP> \
  --kubelet-arg=max-pods=220" sh -
```

Replace `<YOUR_NODE_IP>` with your node's IP address.

### kubeadm Configuration

Create a kubeadm configuration file:

```yaml
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
networking:
  podSubnet: "10.244.0.0/16"
  serviceSubnet: "10.96.0.0/16"
  dnsDomain: "cozy.local"
---
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
mode: "none"  # Cilium will replace kube-proxy
```

Initialize the cluster without the default CNI:

```bash
kubeadm init --config kubeadm-config.yaml --skip-phases=addon/kube-proxy
```

### RKE2 Configuration

Create `/etc/rancher/rke2/config.yaml`:

```yaml
cni: none
disable:
  - rke2-ingress-nginx
  - rke2-metrics-server
cluster-domain: cozy.local
disable-kube-proxy: true
```

## Installing Cozystack

### 1. Apply CRDs

Download and apply Custom Resource Definitions:

```bash
kubectl apply -f https://github.com/cozystack/cozystack/releases/latest/download/cozystack-crds.yaml
```

### 2. Create Namespace

```bash
kubectl create namespace cozy-system
```

### 3. Create ConfigMap

Create `cozystack-config.yaml` with your cluster configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cozystack
  namespace: cozy-system
data:
  bundle-name: "isp-full-generic"
  root-host: "example.com"
  api-server-endpoint: "https://<YOUR_NODE_IP>:6443"
  ipv4-pod-cidr: "10.42.0.0/16"
  ipv4-pod-gateway: "10.42.0.1"
  ipv4-svc-cidr: "10.43.0.0/16"
  ipv4-join-cidr: "100.64.0.0/16"
```

Adjust the values:

| Field | Description |
|-------|-------------|
| `bundle-name` | Must be `isp-full-generic` for non-Talos clusters |
| `root-host` | Your domain for Cozystack services |
| `api-server-endpoint` | Kubernetes API endpoint URL |
| `ipv4-pod-cidr` | Pod network CIDR (must match your k8s config) |
| `ipv4-svc-cidr` | Service network CIDR (must match your k8s config) |
| `ipv4-join-cidr` | Network for nested cluster communication |

Apply the ConfigMap:

```bash
kubectl apply -f cozystack-config.yaml
```

### 4. Deploy Cozystack Operator

Apply the generic operator manifest:

```bash
kubectl apply -f https://github.com/cozystack/cozystack/releases/latest/download/cozystack-operator-generic.yaml
```

### 5. Monitor Installation

Watch the installation progress:

```bash
kubectl logs -n cozy-system deploy/cozystack -f
```

Check HelmRelease status:

```bash
kubectl get hr -A
```

When complete, all releases will show `READY: True`.

## Example: Ansible Playbook

Below is a minimal Ansible playbook for preparing nodes and deploying Cozystack.

### Node Preparation Playbook

```yaml
---
- name: Prepare nodes for Cozystack
  hosts: all
  become: true
  tasks:
    - name: Install required packages
      ansible.builtin.apt:
        name:
          - nfs-common
          - open-iscsi
          - multipath-tools
        state: present
        update_cache: true

    - name: Configure sysctl for Cozystack
      ansible.posix.sysctl:
        name: "{{ item.name }}"
        value: "{{ item.value }}"
        sysctl_set: true
        state: present
        reload: true
      loop:
        - { name: fs.inotify.max_user_watches, value: "2099999999" }
        - { name: fs.inotify.max_user_instances, value: "2099999999" }
        - { name: fs.inotify.max_queued_events, value: "2099999999" }
        - { name: net.ipv4.ip_forward, value: "1" }
        - { name: net.ipv4.conf.all.forwarding, value: "1" }

    - name: Enable iscsid service
      ansible.builtin.systemd:
        name: iscsid
        enabled: true
        state: started

    - name: Enable multipathd service
      ansible.builtin.systemd:
        name: multipathd
        enabled: true
        state: started
```

### Cozystack Deployment Playbook

```yaml
---
- name: Deploy Cozystack
  hosts: localhost
  connection: local
  vars:
    cozystack_root_host: "example.com"
    cozystack_api_endpoint: "https://10.0.0.1:6443"
    cozystack_pod_cidr: "10.42.0.0/16"
    cozystack_svc_cidr: "10.43.0.0/16"
  tasks:
    - name: Apply Cozystack CRDs
      kubernetes.core.k8s:
        src: https://github.com/cozystack/cozystack/releases/latest/download/cozystack-crds.yaml
        state: present

    - name: Create cozy-system namespace
      kubernetes.core.k8s:
        state: present
        definition:
          apiVersion: v1
          kind: Namespace
          metadata:
            name: cozy-system

    - name: Create Cozystack ConfigMap
      kubernetes.core.k8s:
        state: present
        definition:
          apiVersion: v1
          kind: ConfigMap
          metadata:
            name: cozystack
            namespace: cozy-system
          data:
            bundle-name: "isp-full-generic"
            root-host: "{{ cozystack_root_host }}"
            api-server-endpoint: "{{ cozystack_api_endpoint }}"
            ipv4-pod-cidr: "{{ cozystack_pod_cidr }}"
            ipv4-pod-gateway: "{{ cozystack_pod_cidr | ansible.utils.ipaddr('1') | ansible.utils.ipaddr('address') }}"
            ipv4-svc-cidr: "{{ cozystack_svc_cidr }}"
            ipv4-join-cidr: "100.64.0.0/16"

    - name: Apply Cozystack operator
      kubernetes.core.k8s:
        src: https://github.com/cozystack/cozystack/releases/latest/download/cozystack-operator-generic.yaml
        state: present
```

## Troubleshooting

### linstor-scheduler Image Tag Invalid

**Symptom**: `InvalidImageName` error for linstor-scheduler pod.

**Cause**: k3s version format (e.g., `v1.35.0+k3s1`) contains `+` which is invalid in Docker image tags.

**Solution**: This is fixed in Cozystack v1.0.0+. Ensure you're using the latest release.

### KubeOVN Not Scheduling

**Symptom**: ovn-central pods stuck in Pending state.

**Cause**: KubeOVN uses Helm `lookup` to find control-plane nodes, which may fail on fresh clusters.

**Solution**: Ensure your Platform Package includes explicit `MASTER_NODES` configuration:

```yaml
spec:
  components:
    networking:
      values:
        kube-ovn:
          MASTER_NODES: "<YOUR_CONTROL_PLANE_IP>"
```

### Cilium Cannot Reach API Server

**Symptom**: Cilium pods in CrashLoopBackOff with API connection errors.

**Cause**: Single-node clusters or non-standard API endpoints require explicit configuration.

**Solution**: Verify your ConfigMap includes correct `api-server-endpoint` and ensure the Platform Package has:

```yaml
spec:
  components:
    networking:
      values:
        cilium:
          k8sServiceHost: "<YOUR_API_HOST>"
          k8sServicePort: "6443"
```

### Inotify Limit Errors

**Symptom**: Pods failing with "too many open files" or inotify errors.

**Cause**: Default Linux inotify limits are too low for Kubernetes.

**Solution**: Apply sysctl settings from the [Sysctl Configuration](#sysctl-configuration) section and reboot the node.

## Further Steps

After Cozystack installation completes:

1. [Configure storage with LINSTOR]({{% ref "/docs/getting-started/install-cozystack#3-configure-storage" %}})
2. [Set up the root tenant]({{% ref "/docs/getting-started/install-cozystack#4-access-the-dashboard" %}})
3. [Deploy your first application]({{% ref "/docs/applications" %}})

## References

- [PR #1939: Non-Talos Kubernetes Support](https://github.com/cozystack/cozystack/pull/1939)
- [Issue #1950: Complete non-Talos Support](https://github.com/cozystack/cozystack/issues/1950)
- [k3s Documentation](https://docs.k3s.io/)
- [kubeadm Documentation](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/)
