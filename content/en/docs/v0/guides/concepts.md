---
title: Key Concepts
linkTitle: Key Concepts
description: "Learn about the key concepts of Cozystack, such as management cluster, tenants, and bundles."
weight: 10
aliases:
  - /docs/concepts
---

Cozystack is an open-source, Kubernetes-native platform that turns bare-metal or virtual infrastructure into a fully featured, multi-tenant cloud.
At its core are a few foundational building blocks:

- the **management cluster** that runs the platform itself;
- **tenants** that provide strict, hierarchical isolation;
- **tenant clusters** that give users their own Kubernetes control planes;
- rich catalog of **managed applications** and virtual machines;
- **bundles** that assemble these components into a turnkey stack.

Understanding how these concepts fit together will help you plan, deploy, and operate Cozystack effectively, 
whether you are building an internal developer platform or a public cloud service.

## Management Cluster

Cozystack is a system of services working on a Kubernetes cluster, usually deployed on top of Talos Linux on bare metal or virtual machines.
This Kubernetes cluster is called the **management cluster** to highlight its role and distinguish it from tenant Kubernetes clusters.
Only Cozystack administrators have full access to the management cluster.

The management cluster is used to deploy preconfigured applications, such as tenants, system components, managed apps, VMs, and tenant clusters.
Cozystack users can interact with the management cluster through dashboard and API, and deploy managed applications.
However, they don't have administrative rights and may not deploy custom applications in the management cluster, but can use tenant clusters instead.

## Tenant

A **tenant** in Cozystack is the primary unit of isolation and security, analogous to a Kubernetes namespace but with enhanced scope.
Each tenant represents an isolated environment with its own resources, networking, and RBAC (role-based access control).
Some cloud providers use the term "projects" for a similar entity.

When Cozystack is used to build a private cloud and an internal development platform, a tenant usually belongs to a team or subteam.
In a hosting business, where Cozystack is the foundation of a public cloud, a tenant can belong to a customer.

Read more: [Tenant System]({{% ref "docs/guides/tenants" %}}).

## Tenant Cluster

Users can deploy separate Kubernetes clusters in their own tenants.
These are not namespaces of the management cluster, but complete Kubernetes-in-Kubernetes clusters.

Tenant clusters are what many cloud providers call "managed Kubernetes".
They are used as development, testing, and production environments.

Read more: [tenant Kubernetes clusters]({{% ref "docs/kubernetes" %}}).

## Managed Applications

Cozystack comes with a catalog of **managed applications** (services) that can be deployed on the platform with minimal effort.
These include relational databases (PostgreSQL, MySQL/MariaDB), NoSQL/queues (Redis, NATS, Kafka, RabbitMQ), HTTP cache, load balancer, and others.

Tenants, tenant Kubernetes clusters, and VMs are also managed applications in terms of Cozystack.
They are created with the same user workflow and are managed with Helm and Flux, just as other applications.

Read more: [managed applications]({{% ref "/docs/applications" %}}).

## Cozystack API

Instead of a proprietary API or UI-only management, Cozystack exposes its functionality through 
[Kubernetes Custom Resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) 
and the standard Kubernetes API, accessible via REST API, `kubectl` client, and the Cozystack dashboard.

This approach combines well with role-based access control.
Non-administrative users can use `kubectl` to access the management cluster, 
but their kubeconfig will authorize them only to create custom resources in their tenants.

Read more: [Cozystack API]({{% ref "/docs/cozystack-api" %}}).

## Bundles

Bundles are pre-defined combinations of Cozystack components.
Each bundle is tested, versioned, and guaranteed to work as a unit.
They simplify installation, reduce the risk of misconfiguration, and make it easier to choose the right set of features for your deployment.

Read more: [Bundles]({{% ref "/docs/operations/configuration/bundles" %}}).
