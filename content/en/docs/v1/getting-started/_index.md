---
title: "Getting Started with Cozystack: Deploying Private Cloud from Scratch"
linkTitle: "Getting Started"
description: "Make your first steps, run a home lab, build a POC with Cozystack."
weight: 10
aliases:
- /docs/get-started
---

This tutorial will guide you through your first deployment of a Cozystack cluster.
Along the way, you will get to know about key concepts, learn to use Cozystack via dashboard and CLI,
and get a working proof-of-concept.

The tutorial is divided into several steps.
Make sure to complete each step before starting the next one:

| Step                                                                              | Description                                                                                                                    |
|-----------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| [Requirements: prepare infrastructure and tools]({{% ref "requirements" %}})      | Prepare infrastructure and install required CLI tools on your machine before running this tutorial.                            |
| 1. [Install Talos Linux]({{% ref "install-talos" %}})                             | Install a Cozystack-specific distribution of Talos Linux using [`boot-to-talos`][btt], likely the easiest installation method. |
| 2. [Install and bootstrap a Kubernetes cluster]({{% ref "install-kubernetes" %}}) | Bootstrap a Kubernetes cluster using [Talm][talm], the Talos configuration management tool made for Cozystack.                 |
| 3. [Install and configure Cozystack]({{% ref "install-cozystack" %}})             | Install Cozystack, get administrative access, perform basic configuration, and access the Cozystack dashboard.                 |
| 4. [Create a tenant for users and teams]({{% ref "create-tenant" %}})             | Create a user tenant, the foundation of RBAC in Cozystack, and get access to it via dashboard and Cozystack API.               |
| 5. [Deploy managed applications]({{% ref "deploy-app" %}})                        | Start using Cozystack: deploy a virtual machine, managed application, and a tenant Kubernetes cluster.                         |

[btt]: https://github.com/cozystack/boot-to-talos
[talm]: https://github.com/cozystack/talm