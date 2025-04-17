---
title: How to install Cozystack in Oracle Cloud Infrastructure
linkTitle: Oracle Cloud
description: "How to install Cozystack in Oracle Cloud Infrastructure"
weight: 30
---


#### Creating Custom Image

- Download Talos Linux from [Cozystack releases page](https://github.com/cozystack/cozystack/releases/latest/download/metal-amd64.raw.xz):

- Unpack it using xz:
  ```bash
  xz -d metal-amd64.raw.xz
  ```

- [Upload the image to a bucket in Object Storage](https://docs.oracle.com/iaas/Content/Object/Tasks/managingobjects_topic-To_upload_objects_to_a_bucket.htm).

- [Import the image as a custom image](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/importingcustomimagelinux.htm#linux) Use the following settings:
    - **Image type**: QCOW2
    - **Launch mode**: Paravirtualized mode

- Get the image OCID, it will be used in the next steps.


#### Creating Infrastructure

Here is an example Terraform configuration to create three machines:

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

Apply the configuration using Terraform:

```bash
oci session authenticate --region us-ashburn-1 --profile-name=DEFAULT
terraform init
terraform apply
```

You'll get three machines with the following IPs:
- `192.168.1.11`
- `192.168.1.12`
- `192.168.1.13`


They also have a VLAN interface with the following subnet:
- `192.168.100.0/24`

This subnet will be used for the internal cluster communication.

## Talos Configuration

Use Talm to apply config and install Talos Linux on the drive.

1. [Download](https://github.com/cozystack/talm/releases/latest) latest Talm binary and save it to `/usr/local/bin/talm`
2. Make it executable:
   ```
   chmod +x /usr/local/bin/talm
   ```

### Installation with Talm

1. Create directory for new cluster:
   ```bash
   mkdir -p mycluster
   cd mycluster
   ```

2. Run the following command to initialize Talm for Cozystack:

   ```bash
   talm init -p cozystack
   ```

   After initializing, generate a configuration template with the command:

   ```bash
   talm -n 1.2.3.4 -e 1.2.3.4 template -t templates/controlplane.yaml -i > nodes/nodeN.yaml
   ```

3. Edit the node configuration file as needed.

   - Update `hostname` to the desired name.
     ```yaml
     machine:
       network:
         hostname: node1
     ```

   - Add private interface configuration, and move `vip` to this section. This section isn’t generated automatically:
     - `interface` - Obtained from the "Discovered interfaces" by matching options for the private interface.
     - `addresses` - Use the address specified for Layer 2 (L2).

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

**Execution steps:**

1. Run `talm apply -f nodeN.yml` for all nodes to apply the configurations. The nodes will be rebooted and Talos will be installed on the disk.
2. Execute bootstrap command for the first node in the cluster, example:
   ```bash
   talm bootstrap -f nodes/node1.yml
   ```
3. Get `kubeconfig` from the first node, example:
   ```bash
   talm kubeconfig kubeconfig -f nodes/node1.yml
   ```
4. Edit `kubeconfig` to set the IP address to one of control-plane node, example:
   ```yaml
   server: https://1.2.3.4:6443
   ```
5. Export variable to use the kubeconfig, and check the connection to the Kubernetes:
   ```bash
   export KUBECONFIG=${PWD}/kubeconfig
   kubectl get nodes
   ```

Now follow **Get Started** guide starting from the [**Install Cozystack**](/docs/getting-started/first-deployment/#install-cozystack) section, to continue the installation.


