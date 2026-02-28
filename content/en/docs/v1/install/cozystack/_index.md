---
title: "Installing and Configuring Cozystack"
linkTitle: "3. Install Cozystack"
description: "Step 3: Installing Cozystack on a Kubernetes Cluster — as a ready-to-use platform or in BYOP (Build Your Own Platform) mode."
weight: 30
---

**The third step** in deploying a Cozystack cluster is to install Cozystack on a Kubernetes cluster that has been previously installed and configured.
A prerequisite to this step is having [installed a Kubernetes cluster]({{% ref "/docs/v1/install/kubernetes" %}}).

Cozystack can be installed in two modes, depending on how much control you need over the installed components:

## As a Platform

Install Cozystack as a ready-to-use platform with all components managed automatically.
You choose a [variant]({{% ref "/docs/v1/operations/configuration/variants" %}}) (such as `isp-full`), and Cozystack installs and configures
all necessary components — networking, storage, monitoring, dashboard, operators, and managed applications.

This is the recommended approach for most users who want a fully functional platform out of the box.

**[Install Cozystack as a Platform]({{% ref "./platform" %}})**

## Build Your Own Platform (BYOP)

Use Cozystack to build your own platform by installing only the components you need.
You install the operator with the `default` variant, which only provides the package registry (PackageSources).
Then you use the `cozypkg` CLI tool to selectively install individual packages — networking, storage, ingress, operators, and anything else available in the Cozystack repository.

This approach is ideal when you already have an existing Kubernetes cluster with some infrastructure in place,
or when you only need specific components from the Cozystack ecosystem.

**[Build Your Own Platform with Cozystack]({{% ref "./kubernetes-distribution" %}})**
