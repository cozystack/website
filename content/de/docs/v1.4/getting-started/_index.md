---
title: "Erste Schritte mit Cozystack: Eine Private Cloud von Grund auf bereitstellen"
linkTitle: "Erste Schritte"
description: "Machen Sie Ihre ersten Schritte, betreiben Sie ein Homelab und bauen Sie einen PoC mit Cozystack."
weight: 10
aliases:
  - /docs/v1.4/get-started
source_digest: "sha256:<en-source-hash>"
translation_status: current
l10n: mt
---

Dieses Tutorial führt Sie durch Ihre erste Bereitstellung eines Cozystack-Clusters.
Unterwegs lernen Sie zentrale Konzepte kennen, nutzen Cozystack über das Dashboard und die CLI
und erhalten einen funktionierenden Proof of Concept.

Das Tutorial ist in mehrere Schritte unterteilt.
Schließen Sie jeden Schritt ab, bevor Sie mit dem nächsten beginnen:

| Schritt                                                                           | Beschreibung                                                                                                                   |
|-----------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| [Voraussetzungen: Infrastruktur und Tools vorbereiten](/docs/v1.4/getting-started/requirements/) | Bereiten Sie die Infrastruktur vor und installieren Sie die erforderlichen CLI-Tools auf Ihrem Rechner, bevor Sie dieses Tutorial starten. |
| 1. [Talos Linux installieren](/docs/v1.4/getting-started/install-talos/)                        | Installieren Sie eine Cozystack-spezifische Distribution von Talos Linux mit [`boot-to-talos`][btt] – wohl die einfachste Installationsmethode. |
| 2. [Kubernetes-Cluster installieren und initialisieren](/docs/v1.4/getting-started/install-kubernetes/) | Initialisieren Sie einen Kubernetes-Cluster mit [Talm][talm], dem für Cozystack entwickelten Tool für das Talos-Konfigurationsmanagement. |
| 3. [Cozystack installieren und konfigurieren](/docs/v1.4/getting-started/install-cozystack/)    | Installieren Sie Cozystack, erhalten Sie Administratorzugriff, nehmen Sie die Grundkonfiguration vor und rufen Sie das Cozystack-Dashboard auf. |
| 4. [Tenant für Benutzer und Teams erstellen](/docs/v1.4/getting-started/create-tenant/)         | Erstellen Sie einen Benutzer-Tenant – die Grundlage von RBAC in Cozystack – und greifen Sie über das Dashboard und die Cozystack API darauf zu. |
| 5. [Verwaltete Anwendungen bereitstellen](/docs/v1.4/getting-started/deploy-app/)               | Beginnen Sie mit der Nutzung von Cozystack: Stellen Sie eine virtuelle Maschine, eine verwaltete Anwendung und einen Kubernetes-Cluster für einen Tenant bereit. |

[btt]: https://github.com/cozystack/boot-to-talos
[talm]: https://github.com/cozystack/talm
