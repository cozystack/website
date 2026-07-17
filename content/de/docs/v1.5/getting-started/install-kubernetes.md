---
title: 2. Kubernetes-Cluster installieren und bootstrappen
linkTitle: 2. Kubernetes installieren
description: Bootstrappen Sie mit der Talm CLI einen Kubernetes-Cluster, der bereit für Cozystack ist.
weight: 15
source_digest: sha256:9624dd07a127efc0d02fb379b7d06aea0c363bf1f85d1e75a1ae8a068663cc9c
l10n: mt
translation_review: auto-reviewed
---
## Ziele

Wir beginnen diesen Schritt des Tutorials mit [drei Knoten, auf denen Talos Linux installiert ist]({{% ref "/docs/v1.5/getting-started/install-talos" %}}).

Am Ende dieses Schritts haben wir einen Kubernetes-Cluster, der installiert, konfiguriert und bereit für die Installation von Cozystack ist.
Außerdem verfügen wir über eine `kubeconfig` für diesen Cluster und haben grundlegende Prüfungen des Clusters durchgeführt.

## Kubernetes installieren

Installieren Sie einen Kubernetes-Cluster und führen Sie den Bootstrap durch – mit [Talm]({{% ref "/docs/v1.5/install/kubernetes/talm" %}}), einem deklarativen CLI-Konfigurationswerkzeug mit fertigen Konfigurationsvoreinstellungen für Cozystack.

{{% alert color="info" %}}
Dieser Teil des Tutorials wird derzeit überarbeitet.
Er wird eine vereinfachte Anleitung zur Talm-Installation enthalten – ohne all die zusätzlichen Optionen und Sonderfälle, die im Haupt-Talm-Leitfaden behandelt werden.
{{% /alert %}}


## Nächster Schritt

Setzen Sie das Cozystack-Tutorial fort, indem Sie [Cozystack installieren und konfigurieren]({{% ref "/docs/v1.5/getting-started/install-cozystack" %}}).

Zusatzaufgaben:

-   Schauen Sie sich [github.com/cozystack/talm](https://github.com/cozystack/talm) an und vergeben Sie einen Stern!
