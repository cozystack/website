Applies to both writing and reviewing: every rule below is also a review checkpoint. Code blocks, inline `code`, Hugo shortcodes, URLs, file paths and front-matter keys are masked by the pipeline (`§§NAME_N§§`) — never translate, reorder or "fix" them; the punctuation and number rules below apply to PROSE ONLY.

## 1. Register and variety

- Neutral international Spanish, usable in Spain and Latin America: no region-specific slang, no `vosotros`, no `vos`, and avoid the `ordenador`/`computadora` split (say `equipo`, `servidor`, `nodo`).
- Address the reader with **tú**, consistently on every page. Imperatives in `tú`: ✓ `Ejecuta`, `Crea`, `Consulta` — ✗ `Ejecute`, `Realicen`. A single `Consulte la guía` inside a `tú` page is a major finding.
- Docs: precise, imperative, short sentences, no first person except `En esta guía…`. Blog/landing: may transcreate, may use `nosotros` for the Cozystack team (`hemos publicado`), rhetorical questions allowed.
- Drop English politeness padding: `Please run…` → ✓ `Ejecuta…` — ✗ `Por favor, ejecuta…`.
- Gender-neutral wording by rephrasing (`el equipo`, `quienes administran el clúster`), never `@`, `x`, `e` or `usuarios/as`.

## 2. Headings and capitalization — CRITICAL

- Spanish uses **sentence case**, never English title case. `Getting Started with Cozystack` → ✓ `Primeros pasos con Cozystack` — ✗ `Primeros Pasos Con Cozystack`.
- Only the first word plus proper nouns, brands and API kinds are capitalized: ✓ `Cómo funciona el almacenamiento en LINSTOR`.
- `-ing` headings become a noun or an infinitive, as on kubernetes.io/es: `Installing Cozystack` → ✓ `Instalación de Cozystack` / `Instalar Cozystack` — ✗ `Instalando Cozystack`. Keep one pattern per page.
- Question headings take both marks: `How does it work?` → ✓ `¿Cómo funciona?`.
- No capital after a colon: ✓ `Nota: el clúster debe estar en ejecución.` — ✗ `Nota: El clúster…`. Capitalize after a colon only before a full quotation.
- Lowercase months, days, languages and nationalities: ✓ `el lunes`, `julio`, `en inglés`.
- Table headers and UI labels also follow sentence case. Do not drop the article for headline-ese: ✓ `Instalar el clúster` — ✗ `Instalar clúster`.

## 3. Terminology policy (a do_not_translate + preferred list is injected separately — apply it first)

Decision rule for a term in NEITHER list, in this order:
1. Is it an identifier the reader must match in a manifest, CLI or UI (`kubectl`, `namespace` inside a command, flags, field names, API kinds)? → keep verbatim, unchanged.
2. Does kubernetes.io/es or the CNCF Cloud Native Glossary already have a Spanish rendering? → use it.
3. Is there a natural, unambiguous Spanish word an engineer actually says? → translate (`rendimiento`, `red`, `almacenamiento`, `copia de seguridad`, `registros`).
4. Otherwise keep the English term bare and gloss it once, on first use: ✓ `sidecar (contenedor auxiliar)`, then `sidecar` alone. Never invent a translation nobody uses.
- Pick one rendering per term and keep it identical across the whole page.
- **API kinds in prose** keep the English name, the capital and no accent: ✓ `el Pod`, `el Deployment`, `los Secrets`, `el Node`, `el Tenant`. The same word as an ordinary concept is lowercase and Spanish: ✓ `un despliegue continuo`, `los nodos del clúster`, `el inquilino (tenant)`. Never inflect a kept term: ✗ `Deploymentos`, ✗ `kuberneteses`, ✗ `el Helm's chart`.
- **Gender** = gender of the implicit Spanish hypernym: el pod, el clúster, el nodo, el contenedor, el chart, el endpoint, el backend, el volumen, el despliegue, el almacenamiento, el espacio de nombres; la imagen, la red, la carga de trabajo, la API, la caché, la instancia, la máquina virtual. Agreement must follow: ✓ `una imagen firmada`, `los pods pendientes` — ✗ `la pod`, `el imagen`, `los clúster`.
- **Plurals**: adapted words take Spanish plurals (`clústeres`, `contenedores`, `servidores`); bare loanwords take `-s` (`los pods`, `los charts`, `los endpoints`). Acronyms are invariable: `las API`, `los CRD`.
- **Accent only when the adaptation is established** (RAE plus real ecosystem use): ✓ `clúster`, `búfer`, `caché`, `módulo`. Otherwise leave the loanword bare: ✓ `pod`, `chart`, `sidecar` — ✗ `pód`, ✗ `sídecar`. Do not italicize ecosystem loanwords.

## 4. Typography and punctuation

- Inverted marks are mandatory and go **where the question or exclamation actually starts**, not at the start of the sentence: ✓ `Si el nodo falla, ¿qué pasa con los datos?`, ✓ `Listo, ¡ya tienes un clúster!` — ✗ `¿Si el nodo falla, qué pasa con los datos?`, ✗ `Qué pasa con los datos?`.
- Quotes: use **"comillas inglesas"** (straight double quotes), not «comillas latinas». Rationale: kubernetes.io/es and the wider Latin American tech web use them, `«»` reads as Spain-specific and is inconsistent with the English source and with Markdown tooling. Nest as `"… 'anidado' …"`. Prefer **bold** over quotes for UI labels.
- **Raya (—)** for parentheticals, with a space outside and none inside: ✓ `El clúster —ya en ejecución— acepta cargas nuevas.` Never use `-` or `–` for this, and never leave a stray closing raya. In blog dialogue the raya opens the line with no space after it: `—Empezamos con tres nodos.`
- **No Oxford comma**: Spanish takes no comma before the `y`/`o` that closes a list. ✓ `nodos, discos y redes` — ✗ `nodos, discos, y redes`. (Exception only to prevent a real ambiguity.)
- Comma before an adversative or after a fronted subordinate clause: ✓ `Si el pod no arranca, revisa los eventos.`, ✓ `Funciona, pero requiere más memoria.` Never between subject and verb: ✗ `El operador de almacenamiento, crea el volumen.`
- Suspension points are always three, followed by a space. Use `:` rather than `;` to introduce lists and code blocks.

## 5. Numbers, dates, units

- **Decimal comma in prose**: `3.14 seconds` → ✓ `3,14 segundos` — ✗ `3.14 segundos`. NEVER convert inside version numbers, code, CLI output, YAML values, file names or CIDR notation: ✓ `Cozystack v1.5.0`, `10.0.0.1/24`, `cpu: 0.5`.
- Thousands: never a comma. `10,000 pods` → ✓ `10 000 pods` (non-breaking space) or `10000`; four digits stay unseparated (`1024`).
- Dates: `July 24, 2026` → ✓ `24 de julio de 2026` (lowercase month, `de` twice); numeric form `24/07/2026`. Never `Julio 24, 2026`. Front-matter `date:` values are masked — leave them.
- Space between number and unit, and before `%`: ✓ `16 GB`, `4 vCPU`, `500 ms`, `25 %`. Keep unit symbols in English/SI (`GB`, `TB`, `GiB`, `ms`).
- Abbreviations follow Spanish forms: `1.º`, `n.º`, `EE. UU.`. Spell out `segundos`, `minutos` in prose unless quoting a metric.

## 6. Grammar traps when translating from English

- **Gerund** — the top calque. Never gerund-as-adjective or gerund-of-consequence: ✗ `un archivo conteniendo la configuración` → ✓ `un archivo que contiene la configuración`; ✗ `El nodo falló, provocando un reinicio` → ✓ `El nodo falló y provocó un reinicio`. `Using X, you can…` → ✓ `Con X puedes…`.
- **Passive → pasiva refleja**, which Spanish strongly prefers: ✗ `El clúster es creado por el operador` → ✓ `El operador crea el clúster` / `El clúster se crea automáticamente`; ✗ `Los datos son almacenados en…` → ✓ `Los datos se almacenan en…`.
- **`you can`**: `puedes` when it is a real option, `es posible` in neutral docs — and often just drop it: `You can find the logs in /var/log` → ✓ `Los registros están en /var/log`.
- **Possessives → definite article**: `your cluster` → ✓ `el clúster` (`tu clúster` only when contrasting with someone else's); `Deploy your application` → ✓ `Despliega la aplicación`; `its configuration` → ✓ `la configuración`.
- **Noun stacking**: never a chain of four `de`. `Kubernetes cluster node pool autoscaling configuration` → ✗ `configuración de autoescalado de grupos de nodos de clúster de Kubernetes` → ✓ `configuración del autoescalado de los grupos de nodos en Kubernetes`. Break chains with an adjective (`red virtual`, `disco local`), a preposition (`en`, `para`) or a relative clause. Two consecutive `de` maximum.
- **ser vs estar**: identity or definition → `ser` (`Cozystack es una plataforma`); state, result, availability, location → `estar` (`el pod está listo`, `el servicio está disponible`, `el clúster está en ejecución`). ✗ `el pod es listo`.
- **Subjunctive** after `cuando` with future reference and after `asegúrate de que`: ✓ `Cuando el pod esté listo, ejecuta…` — ✗ `Cuando el pod está listo…`; ✓ `Asegúrate de que el nodo tenga suficiente memoria.` But `si` + present takes the indicative: ✓ `Si quieres aislar la carga…` — ✗ `Si quieras…`.
- Avoid the bureaucratic anaphoric `el mismo/los mismos`: ✗ `Descarga el chart y aplica el mismo` → ✓ `Descarga el chart y aplícalo`.

## 7. Translationese and calques to fix

- Filler openers: ✗ `En este artículo vamos a ver cómo…` → ✓ `Esta guía explica cómo…`, or start straight with the content. Delete `simplemente`, `básicamente`, `de hecho`, `es importante notar que` unless the English carries real emphasis.
- `support` → ✓ `admitir`, `ser compatible con`, `permitir` — ✗ `soportar` (that means "to endure"). `supported versions` → ✓ `versiones compatibles`; `unsupported` → ✓ `no compatible`.
- `apply`: ✓ `aplicar un manifiesto`, ✓ `esto se aplica a…`; but `apply a role` → ✓ `asignar un rol` and `apply for` → ✓ `solicitar` — ✗ `aplicar para`.
- `remove` → ✓ `eliminar`, `quitar` — ✗ `remover` (= to stir). `encrypt` → ✓ `cifrar`, `el cifrado` — ✗ `encriptar`. `library` → ✓ `biblioteca` — ✗ `librería`. `customize` → ✓ `personalizar` — ✗ `customizar`.
- Others: `deprecated` → `obsoleto`/`en desuso`; `performance` → `rendimiento`; `issue` → `problema`/`incidencia`; `feature` → `funcionalidad`; `release` → `versión`/`lanzamiento`; `setup` (n.) → `configuración`; `reset` → `restablecer`; `access` (v.) → `acceder a` (✗ `accesar`); `assume` → `suponer` (✗ `asumir`); `in order to` → `para` (✗ `en orden de`); `make sense` → `tener sentido` (✗ `hacer sentido`); `based on` → `según`/`a partir de` when `basado en` piles up; `additionally` → `además`.
- No English-style hyphenated compounds: ✗ `alta-disponibilidad`, ✗ `multi-inquilino` → ✓ `alta disponibilidad`, `multiinquilino`. No English possessive `'s`.
- Link text: never `haz clic aquí` → ✓ `Consulta la guía de instalación`.

## 8. False friends (tech and business)

`actually` → `en realidad`/`de hecho` (✗ `actualmente` = currently) · `eventually` → `con el tiempo`/`finalmente` (✗ `eventualmente` = occasionally) · `library` → `biblioteca` · `support` → `admitir` · `realize` → `darse cuenta` (✗ `realizar` = to carry out) · `sensible` → `sensato`/`razonable` (but `sensitive data` → `datos confidenciales`) · `assist` → `ayudar` (✗ `asistir` = to attend) · `consistent` → `coherente`/`uniforme` (✗ `consistente` = thick, solid) · `resume` → `reanudar` (✗ `resumir` = to summarize) · `topic` → `tema` (✗ `tópico` = cliché) · `large` → `grande` (✗ `largo` = long) · `ultimately` → `en última instancia` (✗ `últimamente` = lately) · `commodity hardware` → `hardware estándar` · `abort` → `cancelar`/`interrumpir` · `exit` → `salir` (✗ `éxito`) · `discrete` → `discreto` vs `discreet` → `prudente`. `argument`, `instance` and `policy` are fine as `argumento`, `instancia`, `política` in technical senses.

## 9. Reviewer checklist — frequent MT failures in Spanish

1. English Title Case leaking into headings, table headers or bold labels.
2. Missing opening `¿`/`¡`, or the mark placed at the sentence start instead of where the question begins.
3. Decimal point left as `.` in prose — or, worse, a decimal comma injected into a version, IP, CIDR or YAML value.
4. `usted`/`vosotros` drift, or mixed imperatives (`ejecuta` … `ejecute`) on one page.
5. Agreement drift around loanwords: `la pod`, `el imagen`, `los clúster`, `las nodos`.
6. Gerund calques (`conteniendo`, `permitiendo`, `resultando en`) and English passives left as `es/son` + participle.
7. `soportar`, `librería`, `encriptar`, `remover`, `customizar`, `accesar`, `en orden de`.
8. Missing article (`Instalar clúster`) or `de`-chains of four or more.
9. Capital after a colon; capitalized months or days; `Por favor` retained.
10. Terminology inconsistency: one English term rendered two ways on the same page, or a glossary/do_not_translate term inflected or translated.
11. Placeholders `§§NAME_N§§` lost, duplicated or reordered; code, URLs or YAML keys translated.
12. English clause order preserved in over-long sentences, comma splices, `el cual`/`el mismo` overuse, literal `aquí` link text.
