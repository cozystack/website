---
title: "Build Your Own Platform (BYOP)"
linkTitle: "Build Your Own Platform"
description: "How to build your own platform with Cozystack by installing only the components you need"
weight: 30
aliases:
  - /docs/v1/use-cases/kubernetes-distribution
---

Cozystack can be used in BYOP (Build Your Own Platform) mode — installing only the components you need from the Cozystack package repository,
rather than deploying the full platform.

### Overview

Cozystack provides a package management system inspired by Linux distribution package managers.
The Cozystack Operator manages `PackageSource` and `Package` resources, while the `cozypkg` CLI tool
provides an interactive interface for listing available packages, resolving dependencies, and installing them selectively.

This approach is useful when:

-   You have an existing Kubernetes cluster and only need specific components.
-   Your cluster already has networking and storage configured.
-   You want full control over which components are installed.

The `default` variant of `cozystack-platform` installs no components — it only registers PackageSources.
From there, you use `cozypkg` to install individual packages like networking, storage, ingress, database operators, and more.

For a step-by-step guide, see the [BYOP installation guide]({{% ref "/docs/v1/install/cozystack/kubernetes-distribution" %}}).

![Build Your Own Platform with Cozystack](/img/case-distribution.png)
