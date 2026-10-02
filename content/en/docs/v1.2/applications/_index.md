---
title: "Managed Applications: Guides and Reference"
linkTitle: "Managed Applications"
description: "Reference and guides for managed PostgreSQL, MySQL, Redis, RabbitMQ, Kafka, ClickHouse, OpenSearch, MongoDB, and other database services in Cozystack."
weight: 45
aliases:
  - /docs/v1.2/components
  - /docs/v1.2/guides/applications
---

## Available Application Versions

Cozystack deploys applications in two complementary ways:

-   **Operator‑managed applications** – Cozystack bundles a specific version of a Kubernetes Operator that installs and continuously reconciles the application.
    As a rule, the operator chooses one of the most recent stable versions of the application by default.

-   **Chart‑managed applications** – When no mature operator exists, Cozystack packages an upstream (or in‑house) Helm chart.
    The chart’s `appVersion` pin tracks the latest stable upstream release, keeping deployments secure and up‑to‑date.


