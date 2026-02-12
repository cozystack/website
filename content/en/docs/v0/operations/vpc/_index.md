---
title: "VPCs and Subnets"
linkTitle: "VPCs and Subnets"
description: "How to use VPCs and Subnets"
weight: 20
aliases:
  - /docs/operations/vpc
---

## Attaching Workloads to Subnets

After you've created a VPC with a number of Subnets, it is time to attach workloads to it.
Currently, only virtual machines support subnets attachment.

### 1. Get Subnet IDs

First, you need to determine IDs of subnets. IDs are auto-generated from resource names you specified during creation.
Check it on the Details tab of your VPC.

![VPC Subnets](vpc-subnets.png)

### 2. Specify Subnet IDs during resource creation 

While creating a VM, fill in subnets IDs in Subnets part of a resource settings.

![VM Subnets](vm-subnets.png)

Each subnet will be represented as a secondary network interface.
For some guest operating system distributions, you will need to add network interface configuration to the virtual machine's user-data.
You can also bring secondary interfaces up manually, getting IP addresses from DHCP.
