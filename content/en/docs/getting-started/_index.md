---
title: "Cozystack Tutorial: Deploying Private Cloud from Scratch"
linkTitle: "Tutorial"
description: "Make your first steps, run a home lab, build a POC with Cozystack."
weight: 10
aliases:
- /docs/get-started
---

This tutorial will guide you through your first deployment of a Cozystack cluster.
Along the way, you will get to know about key concepts, learn to use Cozystack via dashboard and CLI,
and get a working proof-of-concept.

## Prerequisites

To run this tutorial, you will need the following setup:

-   A **management host**, which can be your workstation or a virtual machine:
    -   [Docker](https://docs.docker.com/engine/install/) and [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed
    -   Network access to the cluster nodes

-   **Cluster nodes:** three virtual machines in the following minimal configuration:

    -   CPU: 4 cores, `x86` architecture.
    -   RAM: 16 GiB
    -   HDD1: 32GiB (primary disk used for Talos Linux)
    -   HDD2: 100GiB (secondary disk used for images and user application data)
    -   Located in the same L2 network segment
    -   Nested virtualization enabled
    -   Antispoofing disabled
    -   CPU passthrough enabled
    -   CPU model set to `host` in the hypervisor settings
    
## Tutorial Steps

This tutorial is divided into several steps.
We recommend following them in the specified order, completing each step before starting the next one:

| Step                                                                               | Description                                                                                                                                |
|------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| 1. [Installing Talos Linux and a Kubernetes cluster]({{% ref "deploy-cluster" %}}) | Install our distribution of Talos Linux on a set of virtual machines. Use Talm CLI to bootstrap a Kubernetes cluster, ready for Cozystack. |
| 2. [Installing and configuring Cozystack]({{% ref "install-cozystack" %}})         | Install Cozystack, get administrative access, perform basic configuration, and enable the UI dashboard.                                    |
| 3. [Creating a user tenant]({{% ref "create-tenant" %}})                           | Create a user tenant and grant access to it                                                                                                |
| 4. [Creating managed applications]({{% ref "deploy-app" %}})                       | Start using Cozystack and deploy a virtual machine, managed application, and a tenant Kubernetes cluster                                   |
