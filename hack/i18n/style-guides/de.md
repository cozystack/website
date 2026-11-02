Code blocks, inline code, Hugo shortcodes, URLs, front-matter keys and `§§NAME_N§§` placeholders are masked structurally by the pipeline — never translate, reorder or "fix" anything inside them. Everything below applies to prose only.

## 1. Register and tone

- Formal register: address the reader with **„Sie“** — docs, blog, landing pages, UI strings, notes and warnings alike. Never „du“, never a register switch inside a page.
- Docs: precise, neutral, instructional. Blog/landing: same „Sie“, but shorter sentences, active voice, and transcreated marketing claims instead of word-for-word renderings.
- Instructions use the Sie-imperative (verb first): "Create a namespace." → ✗ „Du erstellst einen Namespace.“ / ✗ „Erstellen ein Namespace.“ → ✓ „Erstellen Sie einen Namespace.“
- In numbered step lists the Infinitiv is acceptable („Cluster anlegen“), but never mix Infinitiv and Sie-Imperativ within one list.
- "Please note" → ✓ „Beachten Sie“ (not „Bitte beachten Sie bitte“). "Let's create…" → ✓ „Erstellen Sie …“ / „Als Nächstes …“, never „Lassen Sie uns …“.

## 2. Headings

- German capitalization: nouns and the first word up, everything else down. English title case must not survive: "Installing the Cozystack Platform" → ✗ „Installieren Der Cozystack Plattform“ → ✓ „Cozystack-Plattform installieren“.
- Task headings: Infinitivkonstruktion. "Configure networking" → ✓ „Netzwerk konfigurieren“ (not „Konfigurieren Sie das Netzwerk“). Concept headings: nominal — "Storage architecture" → ✓ „Speicherarchitektur“.
- Idiomatic, not literal: "Getting started" → ✓ „Erste Schritte“; "Troubleshooting" → ✓ „Fehlerbehebung“; "Prerequisites" → ✓ „Voraussetzungen“; "What's next" → ✓ „Wie geht es weiter“.
- No trailing period; keep question headings as questions; keep heading levels exactly as in the source.

## 3. Terminology, API objects, gender, plural

Decision rule for a term **not** covered by the injected glossary, applied in this order:
1. Is it an identifier — API kind, CRD, field, flag, command, chart or package name? → keep verbatim English, uninflected internally, never translated.
2. Does kubernetes.io/de use an established German rendering? → use it.
3. Does the CNCF Cloud Native Glossary (de) have one? → use it.
4. Would a German platform engineer say the English word out loud (Deployment, Workload, Pod, Container, Ingress, Backup, Image)? → keep the English loanword.
5. Otherwise translate, and gloss once on first use: „Mandantentrennung (multi-tenancy)“. Never render the same term two ways on one page.

- API objects stay English and capitalized in prose: „ein Pod“, „das Deployment“, „ein Secret“, „die VirtualMachine“. Do not translate an object kind (✗ „Geheimnis“ for `Secret`); use „Knoten“ for a cluster node as a general concept, `Node` when the API object is meant.
- Gender (a wrong-but-consistent article is a minor issue; a fluctuating one is major): **der** Cluster, der Pod, der Node, der Container, der Namespace, der Service, der Controller, der Ingress, der Server, der Speicher. **das** Deployment, das Secret, das Volume, das Image, das Manifest, das Backup — plus every `-ment` and every `-ing` noun (das Logging, das Monitoring, das Networking, das Scheduling). **die** Workload, die Ressource, die Instanz, die Pipeline.
- Acronyms take the gender of the German head noun: die API (Schnittstelle), die CRD (Definition), die CPU (Einheit), der RAM (Speicher), die IP-Adresse, das YAML (Format).
- Plural: English `-s` for most loanwords (die Pods, die Nodes, die Deployments, die Volumes, die Namespaces); **no** `-s` for `-er`/`-el` stems (der Cluster → die Cluster, der Container → die Container, der Server → die Server). Genitive singular takes `-s`: „des Pods“, „des Clusters“, „des Deployments“.
- Separate act from object: "the deployment of the app" → „die Bereitstellung der Anwendung“; the `Deployment` object → „das Deployment“. "to deploy" → „bereitstellen“/„ausrollen“, not „deployen“.

## 4. Compound nouns (the biggest German MT failure mode)

- All-German compounds are written as one word: ✗ „Speicher Klasse“ → ✓ „Speicherklasse“; ✗ „Netzwerk Richtlinie“ → ✓ „Netzwerkrichtlinie“; ✗ „Konfigurations Datei“ → ✓ „Konfigurationsdatei“. A space between the parts of a compound (Deppenleerzeichen) is always an error.
- Mixed English-German compounds are hyphenated at every joint: ✓ „Kubernetes-Cluster“, „Pod-Netzwerk“, „Container-Image“, „Cluster-Konfiguration“, „Node-Ausfall“, „Speicher-Backend“.
- Multiword English terms used as one noun get Durchkopplung (all joints hyphenated): ✗ „Control Plane Knoten“ → ✓ „Control-Plane-Knoten“; ✗ „Bare Metal Server“ → ✓ „Bare-Metal-Server“; ✓ „High-Availability-Setup“, „Multi-Tenant-Umgebung“, „Kubernetes-as-a-Service-Angebot“.
- Identifiers keep their exact original spelling inside a compound: „YAML-Datei“, „kubectl-Befehl“, „CSI-Treiber“, „VirtualMachine-Ressource“, „Helm-Chart“.
- Readability beats mechanical joining: with three or more elements, hyphenate the load-bearing joint or reformulate. ✗ „Kubernetesclusterkonfigurationsdatei“ → ✓ „Konfigurationsdatei des Kubernetes-Clusters“.
- Do not hyphenate a plain German compound that should be closed (✗ „Speicher-Klasse“ where „Speicherklasse“ exists), and never lowercase the resulting noun: ✓ „das Cluster-Upgrade“.

## 5. Typography and punctuation

- Quotation marks: „…“ (U+201E … U+201C); nested ‚…‘ (U+201A … U+2018). Never straight `"`, never English “…”. Do not put quotes around code — it is masked.
- Gedankenstrich: en dash **–** with spaces around it; never the em dash —. "Cozystack — a platform for…" → ✓ „Cozystack – eine Plattform für …“. Ranges use – without spaces: „3–5 Nodes“. The hyphen `-` is reserved for compounds.
- Ellipsis: the single character „…“, with a preceding space when it stands for omitted words.
- No Oxford comma: "A, B, and C" → ✓ „A, B und C“.
- Commas German requires and English does not: before every subordinate clause (dass, weil, wenn, ob, obwohl, relative clauses) and before extended infinitive groups with um/ohne/statt … zu. "We recommend that you upgrade first." → ✓ „Wir empfehlen, dass Sie zuerst aktualisieren.“; ✓ „…, um den Cluster zu aktualisieren.“
- Lists: sentence fragments take no final period, full sentences do — consistently within one list. After a colon, continue lowercase unless a full sentence or a noun follows.

## 6. Numbers, dates, units

- Decimal **comma** in prose: "3.14" → ✓ „3,14“; "0.5 vCPU" → ✓ „0,5 vCPU“. CRITICAL: never convert inside code, version numbers (v1.5.0), image tags, IP addresses/CIDRs, ports, CLI output or YAML — those keep the source form byte-for-byte.
- Thousands separator: period, or a narrow space: "10,000 pods" → ✓ „10.000 Pods“. Prose only, same exception list as above.
- Dates: "07/24/2026" → ✓ „24.07.2026“ or „24. Juli 2026“. Never keep US month/day order. ISO dates in front matter and code stay ISO. Times: "3 PM" → ✓ „15:00 Uhr“.
- Units: space between number and unit, percent included — „4 GB“, „10 Gbit/s“, „50 %“, „25 °C“ (non-breaking space preferred). Kubernetes quantities (512Mi, 2000m) are code-like and stay unchanged.
- Ordinals take a period: „im 3. Schritt“. "billion" → „Milliarde“ (never „Billion“).

## 7. Grammar traps when translating from English

- Verbzweitstellung: the finite verb is the second element of a main clause. ✗ „Mit diesem Befehl Sie erstellen einen Cluster.“ → ✓ „Mit diesem Befehl erstellen Sie einen Cluster.“
- Verbendstellung in subordinate clauses. ✗ „…, weil der Cluster hat nicht genug Speicher.“ → ✓ „…, weil der Cluster nicht genug Speicher hat.“
- Modal verbs push the infinitive to the end. ✗ „Sie können erstellen eine virtuelle Maschine.“ → ✓ „Sie können eine virtuelle Maschine erstellen.“
- Passive: prefer active or „lässt sich“; avoid stacked „wird … werden“ chains. "The cluster can be upgraded without downtime." → ✓ „Der Cluster lässt sich ohne Ausfallzeit aktualisieren.“ For a generic actor use the passive or man-Konstruktion, not „Sie“: "Backups are stored in S3." → ✓ „Backups werden in S3 abgelegt.“
- Capability, not permission: "Cozystack allows you to run VMs" → ✗ „Cozystack erlaubt Ihnen, VMs auszuführen“ → ✓ „Mit Cozystack können Sie VMs betreiben“ / „Cozystack ermöglicht den Betrieb von VMs“.
- Gerunds are not present participles: "Using kubectl, you can…" → ✗ „Benutzend kubectl …“ → ✓ „Mit kubectl können Sie …“; "After installing…" → ✓ „Nach der Installation …“.
- Genitiv over „von“ in docs: ✓ „die Konfiguration des Clusters“; „von“ only without article or with bare plurals: ✓ „eine Liste von Nodes“.
- Restore articles English drops: "Create Deployment" → ✓ „Erstellen Sie ein Deployment“. Watch case after prepositions: „mit dem Cluster“, „für den Node“, „in der Umgebung“.
- No English noun stacking: ✗ „Cozystack Kubernetes Plattform“ → ✓ „die Kubernetes-Plattform Cozystack“.

## 8. Translationese and calques to eliminate

- ✗ „In diesem Artikel werden wir …“ → ✓ „Dieser Artikel zeigt, wie …“ / „Im Folgenden …“.
- ✗ filler „einfach“/„simpel“ ("simply run") → ✓ delete it: „Führen Sie … aus.“
- ✗ „erlaubt Ihnen zu …“ → ✓ „ermöglicht …“ / „damit können Sie …“.
- ✗ dangling „basierend auf“ at the start of a clause → ✓ „auf Basis von“ / „anhand von“.
- ✗ „in Ordnung sein“ for "to be fine/OK" → ✓ „funktioniert“ / „ist zulässig“; ✗ „Sie wollen vielleicht …“ (you may want to) → ✓ „Optional können Sie …“.
- ✗ „Stellen Sie sicher, dass Sie X getan haben“ → ✓ „Vergewissern Sie sich, dass X …“ / „Voraussetzung: …“.
- ✗ „unterstützt“ for every sense of "support": feature support ✓ „unterstützt“, commercial support ✓ „Support“/„Betreuung“, "supported version" ✓ „unterstützte Version“.
- ✗ „adressieren“ (to address an issue) → ✓ „beheben“/„angehen“; ✗ „realisieren“ (to realize) → ✓ „umsetzen“ or „feststellen“.
- ✗ „Einmal der Cluster läuft, …“ → ✓ „Sobald der Cluster läuft, …“; ✗ over-nominalization „die Durchführung der Installation“ → ✓ „die Installation“; ✗ „Technologien wie z. B. …“ → ✓ „Technologien wie …“.

## 9. False friends (EN ≠ DE)

eventually ≠ eventuell → „schließlich/letztendlich“ (eventual consistency → „letztendliche Konsistenz“); actual/actually ≠ aktuell → „tatsächlich“ (current → „aktuell“); to control ≠ kontrollieren → „steuern/regeln“ (kontrollieren = to check); to become ≠ bekommen → „werden“; sensible ≠ sensibel → „sinnvoll/vernünftig“ (sensitive data → „sensible Daten“ ✓); provision ≠ Provision (= commission) → „bereitstellen/Bereitstellung“; note ≠ Note (= grade) → „Hinweis/Anmerkung“; billion ≠ Billion → „Milliarde“; consequent ≠ konsequent → „nachfolgend“; to handle ≠ handeln → „verarbeiten/behandeln“; map ≠ Mappe → „Zuordnung/Abbildung“; to spend ≠ spenden → „ausgeben“; brave ≠ brav → „mutig“; gift ≠ Gift (= poison) → „Geschenk“; chef ≠ Chef (= boss) → „Koch“.

## 10. Reviewer checklist — German MT failure modes

1. „du“/„dein“ anywhere, or a register switch mid-page.
2. English title case in headings, or a heading rendered as a full Sie-sentence where an Infinitiv belongs.
3. Deppenleerzeichen and missing Durchkopplung („Bare Metal Server“, „Control Plane Knoten“, „Kubernetes Cluster“).
4. Wrong or fluctuating gender for the same loanword; wrong plural („die Clusters“, „die Containers“); missing genitive `-s`.
5. Decimal points left in prose, or decimal commas wrongly injected into versions, IPs, image tags or code.
6. Em dash — or straight `"` instead of – and „…“.
7. Missing comma before dass/weil/wenn/relative clauses or before an extended infinitive group.
8. English word order surviving: verb not in second position, subordinate-clause verb not final, infinitive not at the end after a modal.
9. Untranslated leftovers — or the opposite: translated API kinds, flags, field names, or do_not_translate terms.
10. One source term rendered several ways on the same page; a glossary term overridden by an improvised synonym.
11. Calques from §8, especially „erlaubt Ihnen zu“, „in diesem Artikel werden wir“, filler „einfach“.
12. False friends from §9 — check every occurrence of „eventuell“, „aktuell“, „kontrollieren“, „sensibel“.
13. Sentences over ~25 words with several nested subordinate clauses: split them. German technical prose tolerates them worse than the English source suggests.
