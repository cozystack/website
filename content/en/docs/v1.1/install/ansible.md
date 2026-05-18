---
title: "Automated Installation with Ansible"
linkTitle: "Ansible"
description: "Deploy Cozystack on generic Kubernetes using the cozystack.installer Ansible collection"
weight: 45
---

The [`cozystack.installer`](https://github.com/cozystack/ansible-cozystack) Ansible collection automates the full deployment pipeline: OS preparation, k3s cluster bootstrap, and Cozystack installation. It is suited for deploying Cozystack on bare-metal servers or VMs running a standard Linux distribution.

## When to Use Ansible

Consider this approach when:

- You want a fully automated, repeatable deployment from bare OS to a running Cozystack
- You are deploying on generic Linux (Ubuntu, Debian, RHEL, Rocky, openSUSE) rather than Talos Linux
- You want to manage multiple nodes with a single inventory file

For manual installation steps without Ansible, see the [Generic Kubernetes]({{% ref "/docs/v1.1/install/kubernetes/generic" %}}) guide.

## Prerequisites

### Controller Machine

- Python >= 3.9
- Ansible >= 2.15

### Target Nodes

- **Operating System**: Ubuntu/Debian, RHEL 8+/CentOS Stream 8+/Rocky/Alma, or openSUSE/SLE
- **Architecture**: amd64 or arm64
- **SSH access** with passwordless sudo
- See [hardware requirements]({{% ref "/docs/v1.1/install/hardware-requirements" %}}) for CPU, RAM, and disk sizing

## Installation

### 1. Install the Ansible Collection

```bash
ansible-galaxy collection install git+https://github.com/cozystack/ansible-cozystack.git
```

Install required dependency collections. The `requirements.yml` file is not included in the packaged collection, so download it from the repository:

```bash
curl --silent --location --output /tmp/requirements.yml \
  https://raw.githubusercontent.com/cozystack/ansible-cozystack/main/requirements.yml
ansible-galaxy collection install --requirements-file /tmp/requirements.yml
```

This installs the following dependencies:

- `ansible.posix`, `community.general`, `kubernetes.core` — from Ansible Galaxy
- [`k3s.orchestration`](https://github.com/k3s-io/k3s-ansible) — k3s deployment collection, installed from Git

### 2. Create an Inventory

Create an `inventory.yml` file. The **internal (private) IP** of each node must be used as the host key, because KubeOVN validates host IPs through `NODE_IPS`. The public IP (if different) goes in `ansible_host`.

```yaml
cluster:
  children:
    server:
      hosts:
        10.0.0.10:
          ansible_host: 203.0.113.10
    agent:
      hosts:
        10.0.0.11:
          ansible_host: 203.0.113.11
        10.0.0.12:
          ansible_host: 203.0.113.12

  vars:
    ansible_port: 22
    ansible_user: ubuntu

    # k3s settings — check https://github.com/k3s-io/k3s/releases for available versions
    k3s_version: v1.35.0+k3s3
    token: "CHANGE_ME"  # REPLACE with a strong random secret
    api_endpoint: "10.0.0.10"
    cluster_context: my-cluster

    # Cozystack settings
    cozystack_api_server_host: "10.0.0.10"
    cozystack_root_host: "cozy.example.com"
    cozystack_platform_variant: "isp-full-generic"
    # cozystack_k3s_extra_args: "--tls-san=203.0.113.10"  # add public IP if nodes are behind NAT
```

{{% alert color="warning" %}}
**Replace `token` with a strong random secret.** This token is used for k3s node joining and grants full cluster access. Generate one with `openssl rand -hex 32`.
{{% /alert %}}

{{% alert color="warning" %}}
**Always pin `cozystack_chart_version` explicitly.** The collection ships with a default version that may not match the release you intend to deploy. Set it in your inventory to avoid unexpected upgrades:

```yaml
cozystack_chart_version: "1.0.0-rc.2"
```

Check [Cozystack releases](https://github.com/cozystack/cozystack/releases) for available versions.
{{% /alert %}}

### 3. Create a Playbook

Create a `site.yml` file that chains OS preparation, k3s deployment, and Cozystack installation.

The collection repository includes example prepare playbooks for each supported OS family in the [`examples/`](https://github.com/cozystack/ansible-cozystack/tree/main/examples) directory. Copy the one matching your target OS into your project directory, then reference it as a local file:

{{< tabs name="prepare_playbook" >}}
{{% tab name="Ubuntu / Debian" %}}

Copy `prepare-ubuntu.yml` from [examples/ubuntu/](https://github.com/cozystack/ansible-cozystack/tree/main/examples/ubuntu), then create `site.yml`:

```yaml
- name: Prepare nodes
  ansible.builtin.import_playbook: prepare-ubuntu.yml

- name: Deploy k3s cluster
  ansible.builtin.import_playbook: k3s.orchestration.site

- name: Install Cozystack
  ansible.builtin.import_playbook: cozystack.installer.site
```

{{% /tab %}}
{{% tab name="RHEL / Rocky / Alma" %}}

Copy `prepare-rhel.yml` from [examples/rhel/](https://github.com/cozystack/ansible-cozystack/tree/main/examples/rhel), then create `site.yml`:

```yaml
- name: Prepare nodes
  ansible.builtin.import_playbook: prepare-rhel.yml

- name: Deploy k3s cluster
  ansible.builtin.import_playbook: k3s.orchestration.site

- name: Install Cozystack
  ansible.builtin.import_playbook: cozystack.installer.site
```

{{% /tab %}}
{{% tab name="openSUSE / SLE" %}}

Copy `prepare-suse.yml` from [examples/suse/](https://github.com/cozystack/ansible-cozystack/tree/main/examples/suse), then create `site.yml`:

```yaml
- name: Prepare nodes
  ansible.builtin.import_playbook: prepare-suse.yml

- name: Deploy k3s cluster
  ansible.builtin.import_playbook: k3s.orchestration.site

- name: Install Cozystack
  ansible.builtin.import_playbook: cozystack.installer.site
```

{{% /tab %}}
{{< /tabs >}}

### 4. Run the Playbook

```bash
ansible-playbook --inventory inventory.yml site.yml
```

The playbook performs the following steps automatically:

1. **Prepare nodes** — installs required packages (`nfs-common`, `open-iscsi`, `multipath-tools`), configures sysctl, enables storage services
2. **Deploy k3s** — bootstraps a k3s cluster with Cozystack-compatible settings (disables built-in Traefik, ServiceLB, kube-proxy, Flannel; sets `cluster-domain=cozy.local`)
3. **Install Cozystack** — installs Helm and the helm-diff plugin (used for idempotent upgrades), deploys the `cozy-installer` chart, waits for the operator and CRDs, then creates the Platform Package

## Configuration Reference

### Core Variables

| Variable | Default | Description |
| --- | --- | --- |
| `cozystack_api_server_host` | *(required)* | Internal IP of the control-plane node. |
| `cozystack_chart_version` | `1.0.0-rc.1` | Version of the Cozystack Helm chart. **Pin this explicitly.** |
| `cozystack_platform_variant` | `isp-full-generic` | Platform variant: `default`, `isp-full`, `isp-hosted`, `isp-full-generic`. |
| `cozystack_root_host` | `""` | Domain for Cozystack services. Leave empty to skip publishing configuration. |

### Networking

| Variable | Default | Description |
| --- | --- | --- |
| `cozystack_pod_cidr` | `10.42.0.0/16` | Pod CIDR range. |
| `cozystack_pod_gateway` | `10.42.0.1` | Pod network gateway. |
| `cozystack_svc_cidr` | `10.43.0.0/16` | Service CIDR range. |
| `cozystack_join_cidr` | `100.64.0.0/16` | Join CIDR for inter-node communication. |
| `cozystack_api_server_port` | `6443` | Kubernetes API server port. |

### Advanced

| Variable | Default | Description |
| --- | --- | --- |
| `cozystack_chart_ref` | `oci://ghcr.io/cozystack/cozystack/cozy-installer` | OCI reference for the Helm chart. |
| `cozystack_operator_variant` | `generic` | Operator variant: `generic`, `talos`, `hosted`. |
| `cozystack_namespace` | `cozy-system` | Namespace for Cozystack operator and resources. |
| `cozystack_release_name` | `cozy-installer` | Helm release name. |
| `cozystack_release_namespace` | `kube-system` | Namespace where Helm release secret is stored (not the operator namespace). |
| `cozystack_kubeconfig` | `/etc/rancher/k3s/k3s.yaml` | Path to kubeconfig on the target node. |
| `cozystack_create_platform_package` | `true` | Whether to create the Platform Package after chart installation. |
| `cozystack_helm_version` | `3.17.3` | Helm version to install on target nodes. |
| `cozystack_helm_binary` | `/usr/local/bin/helm` | Path to the Helm binary on target nodes. |
| `cozystack_helm_diff_version` | `3.12.5` | Version of the helm-diff plugin. |
| `cozystack_operator_wait_timeout` | `300` | Timeout in seconds for operator readiness. |

### Prepare Playbook Variables

The example prepare playbooks (copied from the `examples/` directory) support additional variables:

| Variable | Default | Description |
| --- | --- | --- |
| `cozystack_flush_iptables` | `false` | Flush iptables INPUT chain before installation. Useful on cloud providers with restrictive default rules. |
| `cozystack_k3s_extra_args` | `""` | Extra arguments passed to k3s server (e.g., `--tls-san=<PUBLIC_IP>` for nodes behind NAT). |

## Verification

After the playbook completes, verify the deployment from the first server node:

```bash
# Check operator
kubectl get deployment cozystack-operator --namespace cozy-system

# Check Platform Package
kubectl get packages.cozystack.io cozystack.cozystack-platform

# Check all pods
kubectl get pods --all-namespaces
```

## Idempotency

The playbook is idempotent — running it again will not re-apply resources that haven't changed. The Platform Package is only applied when a diff is detected via `kubectl diff`.
