---
title: "Vorstellung von /cozystack:wizard — ein geführter Cozystack-Installer"
slug: introducing-cozystack-wizard
date: 2026-05-19
author: "Timur Tukaev"
description: "/cozystack:wizard ist ein neuer geführter Installer, der eine vollständige Cozystack-Bereitstellung von Anfang bis Ende über Talos, Ubuntu und bestehende Cluster orchestriert — inklusive cert-SAN-Fallen in NAT-Clouds, ZFS-Provisioning, LINSTOR-Registrierungs-Races und mehr."
images:
  - "cozystack-wizard.png"
article_types:
  - announcement
topics:
  - platform
  - install
source_digest: "sha256:<en-source-hash>"
translation_status: current
l10n: transcreate
---

![Cozystack-Assistent](cozystack-wizard.png)

Wir haben **`/cozystack:wizard`** veröffentlicht — einen geführten Cozystack-Installer.

Geben Sie ihm `Talos`, `Ubuntu` oder `Existing` vor, und er orchestriert die gesamte Kette von Anfang bis Ende. Er bewältigt cert-SAN-Fallen in NAT-Clouds (OCI, GCP, AWS), ZFS-Provisioning auf Talos, LINSTOR-Registrierungs-Races und ein Dutzend weiterer Fallen, über die wir bei echten Installationstests gestolpert sind.

Boot-to-Talos funktioniert ebenfalls: Wenn Knoten bereits mit Basis-Talos hochgefahren sind, aktualisiert der Assistent sie auf das Cozystack-optimierte Image. Der End-to-End-Pfad ist auf einem Talos-Cluster mit 3 Knoten in OCI validiert.

## Breaking Change: Konsolidierung der Plugins

Wir haben fünf Plugins zu zweien zusammengeführt — `cozystack` und `linstor` — und die Skills umbenannt. Wenn Sie die alten Plugins hatten, deinstallieren Sie die bisherigen und installieren Sie neu:

```bash
/plugin install cozystack@cozystack-claude-plugins
/plugin install linstor@cozystack-claude-plugins
```

Führen Sie dann aus:

```bash
/cozystack:wizard
```

## Ausprobieren und Feedback geben

Der Assistent soll Sie von einem frischen Satz Knoten (oder einem bestehenden Cluster) zu einem laufenden Cozystack führen, ohne den langen Schwanz von Sonderfällen manuell abarbeiten zu müssen. Wir haben ihn auf den oben genannten Konfigurationen einem Stresstest unterzogen, aber je mehr Umgebungen er sieht, desto besser wird er.

Bitte probieren Sie ihn aus und sagen Sie uns, was funktioniert hat, was kaputtging und was verwirrend war.

---

## Werden Sie Teil der Community

- GitHub: [github.com/cozystack/cozystack](https://github.com/cozystack/cozystack)
- Telegram-Community: [t.me/cozystack](https://t.me/cozystack/)
- Cozystack im Kubernetes Slack: [#cozystack](https://kubernetes.slack.com/archives/C06L3CPRVN1) (Einladung nötig? [slack.kubernetes.io](https://slack.kubernetes.io))
- Community-Meeting-Kalender: [cozystack.io/community](https://cozystack.io/community/)
