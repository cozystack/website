---
title: "Managed Applications: Guides and Reference"
linkTitle: "Managed Applications"
description: "Learn how to deploy, configure, access, and backup managed applications in Cozystack."
weight: 45
aliases:
  - /docs/components
  - /docs/guides/applications
---

## Available Application Versions

Cozystack deploys applications in two complementary ways:

-   **Operator‑managed applications** – Cozystack bundles a specific version of a Kubernetes Operator that installs and continuously reconciles the application.
    As a rule, the operator chooses one of the most recent stable versions of the application by default.

-   **Chart‑managed applications** – When no mature operator exists, Cozystack packages an upstream (or in‑house) Helm chart.
    The chart’s `appVersion` pin tracks the latest stable upstream release, keeping deployments secure and up‑to‑date.


