---
title: "Cozystack: Kostenlose Cloud-Plattform auf Basis von Kubernetes"
description: >
  Verwandeln Sie eine Reihe von Bare-Metal-Servern in ein intelligentes System mit einer einfachen REST API zum Bereitstellen von Kubernetes-Clustern, Databases-as-a-Service, virtuellen Maschinen, Load Balancern, HTTP-Caching-Diensten und weiteren Diensten.

  Nutzen Sie Cozystack, um Ihre eigene Cloud aufzubauen oder kosteneffiziente Entwicklungsumgebungen bereitzustellen.
seo:
  title: "Cozystack — Open-Source Private Cloud auf Kubernetes"
  description: "Open-Source-Cloud-Plattform auf Kubernetes für Managed VMs, Datenbanken, S3-Storage und GPU-Workloads. CNCF-Sandbox-Projekt."
  keywords: ["private cloud", "managed kubernetes", "kubernetes plattform", "open source cloud"]
source_digest: "sha256:7b7c6ca6147cb877fc4d71cba375f8be099bfd8b83c05bf5f19dff5030b4ed4e"
translation_status: current
l10n: transcreate
taglines:
  - Self-hosted-Alternative zu AWS
  - KI-fähige Infrastruktur
  - Open-Source-Alternative zu VMware
use_cases:
  - title: Hosting- und Cloud-Anbieter
    situation: >
      Sie verkaufen VPS. Ihre Kunden fragen inzwischen nach Managed
      Kubernetes, Datenbanken und Object Storage — und jeden Dienst selbst zu
      bauen ist eine Roadmap, die nie fertig wird.
    outcome: >
      Eine Plattform, die Ihre vorhandene Hardware in einen Servicekatalog
      verwandelt: isolierte Mandanten, Self-Service-Bereitstellung und eine
      Kubernetes-native API, an die Ihre Abrechnung andocken kann.
    link: /docs/guides/use-cases/public-cloud/
    link_text: Eine Public Cloud aufbauen
  - title: Abschied von VMware
    situation: >
      Unbefristete Lizenzen gibt es nicht mehr, die Verlängerungskontingente
      sind da, und die VMs müssen weiterhin irgendwo laufen, worüber Sie die
      Kontrolle behalten.
    outcome: >
      Virtuelle Maschinen und Container im selben Cluster, auf Ihren eigenen
      Servern, mit Live-Migration und repliziertem Storage — und die Migration
      ist ein Werkzeug, kein Neuschreiben.
    link: /docs/guides/use-cases/private-cloud/
    link_text: Eine Private Cloud aufbauen
  - title: Plattformteams
    situation: >
      Entwickler eröffnen Tickets für eine Datenbank, einen Cluster oder eine
      Umgebung, und das Plattformteam ist für all das der Engpass.
    outcome: >
      Entwickler fordern an, was sie brauchen, als Kubernetes-Ressourcen und
      bekommen es in Minuten — innerhalb Ihrer Quoten und ohne Account in
      fremden Clouds.
    link: /docs/guides/use-cases/kubernetes-distribution/
    link_text: Als Kubernetes-Distribution
  - title: Hochschulen und Forschung
    situation: >
      Jede Arbeitsgruppe möchte einen eigenen Cluster und einen Anteil an den
      GPUs — und niemand möchte beides administrieren.
    outcome: >
      Ein echter isolierter Cluster pro Gruppe oder pro Lehrveranstaltung auf
      gemeinsamer Hardware, GPU-Zuteilung zwischen ihnen und eine Umgebung,
      die sich im nächsten Semester aus einem Repository neu erzeugen lässt.
  - title: Öffentlicher Sektor und regulierte Branchen
    situation: >
      Die Daten dürfen Ihre Rechtsordnung nicht verlassen, und von einer
      externen Control Plane dürfen Sie nicht abhängig sein.
    outcome: >
      Die gesamte Plattform läuft auf Ihrer eigenen Hardware, ohne externes
      SaaS im Steuerungspfad, und jede Komponente ist prüfbarer Open Source.
  - title: Telekommunikation und Edge
    situation: >
      Netzwerkfunktionen kommen weiterhin als virtuelle Maschinen, alles Neue
      kommt als Container — und am Ende stehen sie auf getrennten Stacks.
    outcome: >
      Beides auf einer Plattform, mit dem Networking, das die Dataplane
      braucht — vom zentralen Standort bis hinaus zu kleinen Edge-Clustern.

benefits:
  - title: API-first
    icon: fas fa-code
    description: >
      Cozystack basiert auf Kubernetes und setzt auf die enge Interaktion mit dessen API. Es versucht nicht, alle Elemente hinter einer hübschen UI oder diversen Anpassungen vollständig zu verbergen. Stattdessen bietet es eine standardisierte Schnittstelle und befähigt Nutzer, mit den grundlegenden Primitiven zu arbeiten.
  - title: Standardisierung und Vereinheitlichung
    icon: fas fa-certificate
    description: >
      Alle Komponenten der Plattform basieren auf bewährten Open-Source-Tools und -Technologien, die in der Branche weithin bekannt sind.
      Wir setzen auf die etabliertesten und erprobtesten Ansätze, halten die gesamte Plattform dadurch sehr einfach und vermeiden Vendor-Lock-in.
  - title: Zusammenarbeit statt Konkurrenz
    icon: fas fa-handshake
    description: >
      Wir sind stolz auf unsere Community und arbeiten eng mit den Projekten in ihrem Umfeld zusammen.
      Wenn wir eine Plattformfunktion entwickeln, die in einem Upstream-Projekt nützlich sein kann,
      steuern wir sie lieber zu diesem Projekt bei, anstatt sie in der Plattform zu behalten.
features:
  - title: Einfach zu installieren
    icon: fas fa-wrench
    description: >
      Mit [talos-bootstrap](https://github.com/cozystack/talos-bootstrap/) bieten wir die denkbar einfachste Installationsmethode,
      mit der Sie Cozystack per PXE oder ISO auf Servern in einem leeren Rechenzentrum bereitstellen können.
      Ein immutable Betriebssystem hilft, die Systemkonsistenz zu wahren und sicherzustellen, dass alles wie erwartet funktioniert.
  - title: Einfach zu integrieren
    icon: fas fa-plug
    description: >
      Wir stellen eine native RESTful API von Kubernetes bereit, die für ihre Deklarativität bekannt ist.
      Für die Integration mit Ihrem Billing genügt es daher, Ihr System anzuweisen, ein bestimmtes YAML-Manifest mit dem gewünschten Dienst an die Kubernetes API zu senden.
      Den Rest erledigt Cozystack für Sie.
  - title: Einfach zu erweitern
    icon: fas fa-up-right-and-down-left-from-center
    description: >
      Jedes Paket der Plattform besteht aus einer Reihe von YAML-Dateien. Wer mit den Kubernetes-Primitiven vertraut ist, kann die Plattform daher anpassen oder erweitern. Die Paketauslieferung übernimmt zuverlässig FluxCD, ein bekanntes und weit verbreitetes Tool.
  - title: Hohe Performance, geringer Overhead
    icon: fas fa-gauge-high
    description: >
      Performance ist uns wichtig. Deshalb setzen wir auf die performantesten Technologien und wägen dabei Stabilität und Funktionalität ab.
      Zudem ermöglicht unser einzigartiges Tenant-Modell eine effiziente Zuweisung von Cloud-Ressourcen für die Control Plane und sorgt so für Kosteneffizienz und das nötige Maß an Sicherheit.
  - title: Integriertes Monitoring & Alerts
    icon: fas fa-area-chart
    description: >
      Jede Instanz jedes Dienstes wird von vorkonfigurierten Dashboards und Alerts begleitet.
      Sie können für jeden Tenant separate Monitoring-Hubs anlegen oder sie zu einem zusammenfassen.
  - title: Integrierte UI für die App-Verwaltung
    icon: fas fa-window-maximize
    description: >
      Das primäre Ziel der Plattform ist eine schöne API, doch sie verfügt auch über ein Dashboard zum Bereitstellen von Anwendungen.
      Die Web-UI erleichtert den schnellen Einstieg in die Plattform und demonstriert ihre Möglichkeiten anschaulich.
---

<div class="hero-gitops">
  {{% blocks/hero title="Cozystack: Kostenlose Cloud-Plattform auf Basis von Kubernetes" color="primary"
  height="auto" link_title="Erste Schritte" link_url="/de/docs/v1.4/getting-started/" %}}
  Verwandeln Sie eine Reihe von Bare-Metal-Servern in ein intelligentes System mit einer einfachen REST API zum Bereitstellen von Kubernetes-Clustern, Databases-as-a-Service, virtuellen Maschinen, Load Balancern, HTTP-Caching-Diensten und weiteren Diensten.

  Nutzen Sie Cozystack, um Ihre eigene Cloud aufzubauen oder kosteneffiziente Entwicklungsumgebungen bereitzustellen.

  {{% /blocks/hero %}}

  <div class="lead-flux">
  {{< blocks/lead >}}
  {{< /blocks/lead >}}
  </div>
</div>

<!-- Screenshot Gallery -->
{{< home/screenshot-gallery >}}

<!-- Live Demo -->
<div class="section-live-demo">
{{< blocks/lead color="primary" >}}
<h2 class="section-label">Sehen Sie die Konsole, bevor Sie irgendetwas installieren</h2>

<p class="live-demo-lead">Das echte Dashboard von Cozystack, vollständig in Ihrem Browser — kein Cluster, keine Anmeldung, keine Einrichtung. Stöbern Sie im Marketplace, öffnen Sie Managed Services, klicken Sie sich durch die Konsole. Es ist die echte UI, nur mit Demo-Daten.</p>

<div class="live-demo-cta"><a class="btn btn-lg btn-primary" href="/demo/">Live-Demo öffnen &rarr;</a></div>
{{< /blocks/lead >}}
</div>

<!-- Benefits & Features -->

{{< home/use-cases >}}

{{< home/benefits >}}

{{< home/features >}}

<!-- Community -->
<div class="section-community">
  {{< blocks/lead color="dark" >}}
  <h2 class="section-label">
  Community
  </h2>

  <p>Wir schätzen die beständige Unterstützung und die Beiträge unserer Community zum Wachstum von Cozystack sehr.<br/> Treten Sie unserer Community bei und werden Sie Teil unserer Reise.</p>

  {{< /blocks/lead >}}

  <div class="subsection-community-row">
  {{< blocks/section color="dark" type="community-row">}}

  {{< home/community icon="fab fa-github" title="GitHub Discussions" >}}
  <a target="_blank" rel="noopener noreferrer" href="https://github.com/cozystack/cozystack/discussions">Beteiligen Sie sich an den GitHub Discussions</a>. Alles rund um Cozystack – von Spezifikationen über Feature-Planung bis hin zu Show &amp; Tell – findet hier statt.

  {{< /home/community >}}

  {{< home/community icon="fab fa-slack" title="Slack" >}}
  Wenn Sie in Echtzeit mit dem Cozystack-Team und der Community sprechen möchten, kommen Sie zu uns auf Slack. So lernen Sie alle am besten kennen.

  Holen Sie sich eine <a target="_blank" rel="noopener noreferrer" href="https://slack.kubernetes.io/">Slack-Einladung</a> oder gehen Sie in den <a target="_blank" rel="noopener noreferrer" href="https://kubernetes.slack.com/messages/cozystack">Kanal <code>#cozystack</code></a>.

  {{< /home/community >}}

  {{< home/community icon="fa fa-paper-plane" title="Telegram" >}}
  Wir haben außerdem eine große Community auf Telegram. Treten Sie der Gruppe <a target="_blank" rel="noopener noreferrer" href="https://t.me/cozystack/">@cozystack</a> bei, um sich mit anderen Nutzern auszutauschen, Fragen zu stellen und über Neuigkeiten und Entwicklungen auf dem Laufenden zu bleiben.
  {{< /home/community >}}

  {{< /blocks/section >}}
  </div>

</div>

{{< home/cncf >}}
