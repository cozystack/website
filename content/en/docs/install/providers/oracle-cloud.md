---
title: How to install Cozystack in Oracle Cloud Infrastructure
linkTitle: Oracle Cloud
description: "How to install Cozystack in Oracle Cloud Infrastructure"
weight: 25
aliases:
  - /docs/operations/talos/installation/oracle-cloud
  - /docs/talos/install/oracle-cloud
---

## Introduction

This guide explains how to install Talos on Oracle Cloud Infrastructure and deploy a Kubernetes cluster that is ready for Cozystack.
After completing the guide, you will be ready to proceed with
[installing Cozystack itself]({{% ref "/docs/getting-started/install-cozystack" %}}).

{{% alert color="info" %}}
This guide was created to support deployment of development clusters by the Cozystack team.
If you face any problems while going through the guide, please raise an issue in [cozystack/website](https://github.com/cozystack/website/issues)
or come and share your experience in the [Cozystack community](https://t.me/cozystack).
{{% /alert %}}

## 1. Upload Talos Image to Oracle Cloud

The first step is to make a Talos Linux installation image available for use in Oracle Cloud as a custom image.

1.  Download the Talos Linux image archive from the [Cozystack releases page](https://github.com/cozystack/cozystack/releases/latest/) and unpack it:

    ```bash
    wget https://github.com/cozystack/cozystack/releases/latest/download/metal-amd64.raw.xz
    xz -d metal-amd64.raw.xz
    ```

    As a result, you will get the file `metal-amd64.raw`, which you can then upload to OCI.

1.  Follow the OCI documentation to [upload the image to a bucket in OCI Object Storage](https://docs.oracle.com/iaas/Content/Object/Tasks/managingobjects_topic-To_upload_objects_to_a_bucket.htm).

1.  Proceed with the documentation to [import this image as a custom image](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/importingcustomimagelinux.htm#linux).
    Use the following settings:

    -   **Image type**: QCOW2
    -   **Launch mode**: Paravirtualized mode

1.  Finally, get the image's [OCID](https://docs.oracle.com/en-us/iaas/Content/libraries/glossary/ocid.htm) and save it for use in the next steps.

## 2. Create Infrastructure

The goal of this step is to prepare the infrastructure according to the
[Cozystack cluster requirements]({{% ref "/docs/install/hardware-requirements" %}}).

This can be done manually using the Oracle Cloud dashboard or with Terraform.

### 2.1 Prepare Terraform Configuration

If you choose to use Terraform, the first step is to build the configuration.

{{% alert color="info" %}}
Check out [the complete example of Terraform configuration](https://github.com/cozystack/examples/tree/main/001-deploy-cozystack-oci)
for deploying several Talos nodes in Oracle Cloud Infrastructure.
{{% /alert %}}

Below is a shorter example of Terraform configuration creating three virtual machines with the following private IPs:

- `192.168.1.11`
- `192.168.1.12`
- `192.168.1.13`

These VMs will also have a VLAN interface with subnet `192.168.100.0/24` used for the internal cluster communication.

Note the part that references the Talos image OCID from the previous step:

```hcl
  source_details {
    source_type = "image"
    source_id   = var.talos_image_id
  }
```

Full configuration example:

```hcl
terraform {
  backend "local" {}
  required_providers {
    oci = { source = "oracle/oci", version = "~> 6.35" }
  }
}

resource "oci_core_vcn" "cozy_dev1" {
  display_name = "cozy-dev1"
  cidr_blocks = ["192.168.0.0/16"]
  compartment_id = var.compartment_id
}

resource "oci_core_network_security_group" "cozy_dev1_allow_all" {
  display_name = "allow-all"
  compartment_id = var.compartment_id
  vcn_id = oci_core_vcn.cozy_dev1.id
}

resource "oci_core_subnet" "test_subnet" {
  display_name = "cozy-dev1"
  cidr_block = "192.168.1.0/24"
  compartment_id = var.compartment_id
  vcn_id = oci_core_vcn.cozy_dev1.id
}

resource "oci_core_network_security_group_security_rule" "cozy_dev1_ingress" {
  network_security_group_id = oci_core_network_security_group.cozy_dev1_allow_all.id
  direction = "INGRESS"
  protocol = "all"
  source = "0.0.0.0/0"
  source_type = "CIDR_BLOCK"
}

resource "oci_core_network_security_group_security_rule" "cozy_dev1_egress" {
  network_security_group_id = oci_core_network_security_group.cozy_dev1_allow_all.id
  direction = "EGRESS"
  protocol = "all"
  destination = "0.0.0.0/0"
  destination_type = "CIDR_BLOCK"
}

resource "oci_core_internet_gateway" "cozy_dev1" {
  display_name = "cozy-dev1"
  compartment_id = var.compartment_id
  vcn_id = oci_core_vcn.cozy_dev1.id
}

resource "oci_core_default_route_table" "cozy_dev1_default_rt" {
  manage_default_resource_id = oci_core_vcn.cozy_dev1.default_route_table_id

  compartment_id = var.compartment_id
  display_name   = "cozy‑dev1‑default"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.cozy_dev1.id
  }
}

resource "oci_core_vlan" "cozy_dev1_vlan" {
  display_name       = "cozy-dev1-vlan"
  compartment_id     = var.compartment_id
  vcn_id             = oci_core_vcn.cozy_dev1.id

  cidr_block         = "192.168.100.0/24"
  nsg_ids = [oci_core_network_security_group.cozy_dev1_allow_all.id]
}

variable "node_private_ips" {
  type    = list(string)
  default = ["192.168.1.11", "192.168.1.12", "192.168.1.13"]
}

variable "compartment_id" {
  description = "OCID of the OCI compartment"
  type        = string
}

variable "availability_domain" {
  description = "Availability domain for the instances"
  type        = string
}

variable "talos_image_id" {
  description = "OCID of the imported Talos Linux image"
  type        = string
}

resource "oci_core_instance" "cozy_dev1_nodes" {
  count               = length(var.node_private_ips)
  display_name        = "cozy-dev1-node-${count.index + 1}"
  compartment_id      = var.compartment_id
  availability_domain = var.availability_domain
  shape               = "VM.Standard3.Flex"
  preserve_boot_volume                        = false
  preserve_data_volumes_created_at_launch     = false

  create_vnic_details {
    subnet_id   = oci_core_subnet.test_subnet.id
    nsg_ids     = [oci_core_network_security_group.cozy_dev1_allow_all.id]
    private_ip  = var.node_private_ips[count.index]
  }

  source_details {
    source_type = "image"
    source_id   = var.talos_image_id
  }

  launch_volume_attachments {
    display_name = "cozy-dev1-node${count.index + 1}-data"
    launch_create_volume_details {
      display_name       = "cozy-dev1-node${count.index + 1}-data"
      compartment_id     = var.compartment_id
      size_in_gbs        = "512"
      volume_creation_type = "ATTRIBUTES"
      vpus_per_gb        = "10"
    }
    type = "paravirtualized"
  }

  shape_config {
    memory_in_gbs = "32"
    ocpus         = "4"
  }
}

resource "oci_core_vnic_attachment" "cozy_dev1_vlan_vnic" {
  count       = length(var.node_private_ips)
  instance_id = oci_core_instance.cozy_dev1_nodes[count.index].id

  create_vnic_details {
    vlan_id = oci_core_vlan.cozy_dev1_vlan.id
  }
}
```

### 2.2 Apply Configuration

When the configuration is ready, authenticate to OCI and apply it with Terraform:

```bash
oci session authenticate --region us-ashburn-1 --profile-name=DEFAULT
terraform init
terraform apply
```

As a result of these commands, the virtual machines will be deployed and configured.

Save the public IP addresses assigned to the VMs for the next step.  In this example, the addresses are:

- `1.2.3.4`
- `1.2.3.5`
- `1.2.3.6`

## 3. Configure Talos and Initialize Kubernetes Cluster

The next step is to apply the configurations and install Talos Linux.
There are several ways to do that.

This guide uses [Talm](https://github.com/cozystack/talm), a command‑line tool for declarative management of Talos Linux.
Talm has configuration templates specialized for deploying Cozystack, which is why we will use it.

If you do not have Talm installed, [download the latest binary](https://github.com/cozystack/talm/releases/latest) for your OS and architecture.
Make it executable and save it to `/usr/local/bin/talm`:

```bash
# pick your preferred architecture from the release artifacts
wget -O talm https://github.com/cozystack/talm/releases/latest/download/talm-darwin-arm64
chmod +x talm
mv talm /usr/local/bin/talm
```

### 3.1 Prepare Talm Configuration

1.  Create a directory for the new cluster's configuration files:
    ```bash
    mkdir -p mycluster
    cd mycluster
    ```

1.  Initialize Talm configuration for Cozystack:

    ```bash
    talm init -p cozystack
    ```

1.  Generate a configuration template for each node, providing the node's IP address:

    ```bash
    # Use the node's public IP assigned by OCI
    talm template \
      --nodes 1.2.3.4 \
      --endpoints 1.2.3.4 \
      --template templates/controlplane.yaml \
      --insecure \
      > nodes/node0.yaml
    ```

    Repeat the same for each node using its public IP:

    ```bash
    talm template ... > nodes/node1.yaml
    talm template ... > nodes/node2.yaml
    ```

    Using `templates/controlplane.yaml` means the node will act as both control plane and worker.
    Having three combined nodes is the preferred setup for a small PoC cluster.

    The `--insecure` (`-i`) parameter is required because Talm must retrieve configuration data from a node that is not yet initialized and therefore cannot accept an authenticated connection.
    The node will be initialized only a few steps later, with `talm apply`.

    The node's public IP must be specified for both the `--nodes` (`-n`) and `--endpoints` (`-e`) parameters.
    To learn more about Talos node configuration and endpoints, refer to the
    [Talos documentation](https://www.talos.dev/v1.10/learn-more/talosctl/#endpoints-and-nodes)

1.  Edit the node configuration file as needed.

    -   Update `hostname` to the desired name:

        ```yaml
        machine:
          network:
            hostname: node1
        ```

    -   Add the private interface configuration to the `machine.network.interfaces` section, and move `vip` to this configuration.
        This part of the configuration is not generated automatically, so you need to fill in the values:

        -    `interface`: obtained from the "Discovered interfaces" by matching options for the private interface.
        -    `addresses`: use the address specified for Layer 2 (L2).

        Example:

        ```yaml
        machine:
          network:
            interfaces:
              - interface: eth0
                addresses:
                  - 1.2.3.4/29
                routes:
                  - network: 0.0.0.0/0
                    gateway: 1.2.3.1
              - interface: eth1
                addresses:
                  - 192.168.100.11/24
                vip:
                  ip: 192.168.100.10
        ```

After these steps, the node configuration files are ready to be applied.

### 3.2 Initialize Talos and Run Kubernetes Cluster

The next stage is to initialize Talos nodes and bootstrap a Kubernetes cluster.

1.  Run `talm apply` for all nodes to apply the configurations:

    ```bash
    talm apply -f nodes/node0.yaml --insecure
    talm apply -f nodes/node1.yaml --insecure
    talm apply -f nodes/node2.yaml --insecure
    ```

    The nodes will reboot, and Talos will be installed to disk.
    The parameter `--insecure` (`-i`) is required the first time you run `talm apply` on each node.

1.  Execute `talm bootstrap` on the first node in the cluster.  For example:
    ```bash
    talm bootstrap -f nodes/node0.yaml
    ```

1.  Get the `kubeconfig` from any control‑plane node using Talm. In this example, all three nodes are control‑plane nodes:

    ```bash
    talm kubeconfig kubeconfig -f nodes/node0.yaml
    ```

1.  Edit the `kubeconfig` to set the server IP address to one of the control‑plane nodes, for example:
    ```yaml
    server: https://1.2.3.4:6443
    ```

1.  Export the `KUBECONFIG` variable to use the kubeconfig, and check the connection to the cluster:
    ```bash
    export KUBECONFIG=${PWD}/kubeconfig
    kubectl get nodes
    ```

    You should see that the nodes are accessible and in the `NotReady` state, which is expected at this stage:

    ```console
    NAME    STATUS     ROLES           AGE     VERSION
    node0   NotReady   control-plane   2m21s   v1.32.0
    node1   NotReady   control-plane   1m47s   v1.32.0
    node2   NotReady   control-plane   1m43s   v1.32.0
    ```

Now you have a Kubernetes cluster prepared for installing Cozystack.
To complete the installation, follow the deployment guide, starting with the
[Install Cozystack]({{% ref "/docs/getting-started/install-cozystack" %}}) section.
