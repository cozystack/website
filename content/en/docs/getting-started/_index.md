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

## Tutorial Steps

This tutorial is divided into several steps.
We recommend following them in the specified order, completing each step before starting the next one:

| Step                                                                               | Description                                                                                                                                |
|------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| 0. [Preparing infrastructure and tools]({{% ref "requirements" %}})                | Prepare VMs and install required CLI tools on your machine before running this tutorial.                                                   |
| 1. [Installing Talos Linux and a Kubernetes cluster]({{% ref "deploy-cluster" %}}) | Install our distribution of Talos Linux on a set of virtual machines. Use Talm CLI to bootstrap a Kubernetes cluster, ready for Cozystack. |
| 2. [Installing and configuring Cozystack]({{% ref "install-cozystack" %}})         | Install Cozystack, get administrative access, perform basic configuration, and enable the UI dashboard.                                    |
| 3. [Creating a user tenant]({{% ref "create-tenant" %}})                           | Create a user tenant, the foundation of RBAC in Cozystack, and get access to it via dashboard and Cozystack API.                           |
| 4. [Creating managed applications]({{% ref "deploy-app" %}})                       | Start using Cozystack: deploy a virtual machine, managed application, and a tenant Kubernetes cluster.                                     |

