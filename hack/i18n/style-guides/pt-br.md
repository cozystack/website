Brazilian Portuguese (pt-BR), never European Portuguese. Follow kubernetes.io pt-BR localization conventions and the CNCF Cloud Native Glossary. Natural BR phrasing beats literal calques: if a sentence can only be parsed by reconstructing the English, rewrite it. Code blocks, inline `code`, Hugo shortcodes, URLs, front-matter keys and §§PLACEHOLDERS§§ are masked by the pipeline — never translate or reorder them.

## 1. Register and address

- Always **você** (explicit or implicit), consistently within a page. Never *tu*, *vós*, *o senhor*, and never mix conjugations: ✗ "se tu quiseres", ✗ "podes ver" → ✓ "se você quiser", "você pode ver".
- Friendly-professional. Docs: imperative, short sentences, one instruction per sentence ("Execute o comando", "Verifique o status"). Drop English politeness: "Please run" → ✗ "Por favor, execute" → ✓ "Execute".
- Blog/landing: transcreate. First person plural is fine ("lançamos", "nossa equipe"); avoid hype adjectives — *powerful* → ✗ "poderoso" → ✓ "robusto", "eficiente", or drop.
- The product takes an article in running prose: ✓ "o Cozystack instala…", "no Kubernetes"; omit it in labels and titles.

## 2. Headings and capitalization (critical)

- Portuguese uses **sentence case**, never English title case: capitalize only the first word and proper nouns. "Installing the Storage Backend" → ✗ "Instalando o Backend de Armazenamento" → ✓ "Instalação do backend de armazenamento".
- Prefer a noun phrase (or infinitive) over the English gerund heading, consistently within a page: "Configuring Networking" → ✗ "Configurando a Rede" → ✓ "Configuração de rede" / "Configurar a rede".
- Do not capitalize common nouns mid-sentence because English did: "the Cluster and the Node" → ✓ "o cluster e o nó".
- Same rule for `title`/`description` front matter, table headers, alt text, button and menu labels.

## 3. Terminology policy (a glossary is injected separately — do not restate it)

- Decision rule for terms **not** in the glossary, in order: (1) kubernetes.io pt-BR translates it → use that; (2) the CNCF Glossary pt-BR has it → use that; (3) a BR platform engineer would say the English word out loud in a standup → keep English; (4) otherwise translate, with the English in parentheses on first use only.
- Kept in English (real BR usage): pod, cluster, deploy, container, namespace, commit, pull request, backup, snapshot, endpoint, cache, log, bucket, overhead, hypervisor, bare metal, load balancer.
- Translated: workload → carga de trabalho, node → nó, storage → armazenamento, network → rede, image → imagem, file → arquivo, feature → recurso, wizard → assistente, release → versão/lançamento.
- **API objects**: when the word names a Kubernetes/Cozystack API kind, keep it capitalized and in English — "o Pod", "um Deployment", "o Secret", "o objeto Node", "o Tenant" (must match `kind:` in the manifest). When it is the everyday concept, translate and lowercase: "os pods do cluster", "os nós do cluster", "os segredos da aplicação".
- **Gender**: masculine by default for English loanwords (o pod, o cluster, o deploy, o container, o backup, o node, o namespace, o endpoint); feminine when the underlying PT head noun is feminine (a imagem, a API, a VM, a URL, a tag, a role). ✗ "a cluster", ✗ "o VM", ✗ "a pod".
- **Plural**: inflect with -s, no apostrophe — os pods, os clusters, os deployments, os namespaces, as VMs, as APIs, os PVCs. ✗ "os pod", ✗ "as VM's". Adjectives agree: "pods prontos", "cargas de trabalho críticas".

## 4. Typography and punctuation

- Quotation marks: **straight double quotes** `"…"`, nested `'…'`. Do not use «guillemets» (pt-PT/literary) or curly quotes — the docs are code-adjacent and quoted strings get copied into shells.
- **Travessão (—)** with spaces for parenthetical asides; keep the source's em dashes, never downgrade them to a hyphen: ✓ "O tenant — a unidade de isolamento — recebe seu próprio namespace."
- **No Oxford comma.** Portuguese forbids a comma before *e*/*ou* closing an enumeration: "storage, networking, and compute" → ✗ "armazenamento, rede, e computação" → ✓ "armazenamento, rede e computação".
- Comma after a fronted adverbial or subordinate clause: ✓ "Depois de instalar o Cozystack, aplique o manifesto." Never a comma between subject and verb, however long the subject: ✗ "O cluster com três nós de controle, requer…".
- **Crase (à)** — verify every occurrence. Use it when preposition *a* + feminine article *a* merge: ✓ "acesso à API", "conecte-se à rede", "à medida que", "devido à latência", "graças à replicação". No crase before masculine nouns, verbs or article-less plurals: ✗ "à partir de" → ✓ "a partir de"; ✗ "à fim de" → ✓ "a fim de"; ✗ "acesso à documentos" → ✓ "acesso a documentos"; ✓ "referente ao cluster".
- Use "e", never "&". Keep `%`, `/` and CLI punctuation exactly as in the source.

## 5. Numbers, dates, units

- **Decimal comma in prose**: "3.14" → ✓ "3,14"; "0.5 vCPU of overhead" → ✓ "0,5 vCPU de overhead". Thousands separator is a period: "1,000 nodes" → ✓ "1.000 nós"; "12,500" → ✓ "12.500".
- **Never** convert inside code, CLI output, YAML values, resource quantities, CIDRs or version numbers: `v1.2.3`, `0.5`, `500m`, `10.0.0.0/8` stay exactly as written — including when quoted in prose.
- Dates: "July 24, 2026" → ✓ "24 de julho de 2026" (month lowercase); numeric 24/07/2026; ranges "de 2024 a 2026". 24-hour clock: "9 AM UTC" → ✓ "9h UTC" / "09:00 UTC".
- Units: space between number and unit (10 GB, 500 ms, 2 vCPU, 4 GiB); no space before `%` (50%); keep byte/rate units in standard casing (GiB, TiB, Mbps).

## 6. Grammar traps translating from English

- **Gerundismo / -ing calque** — the notorious BR error. English -ing → infinitive or noun; never "estar + gerúndio" for a future or habitual action: ✗ "vamos estar enviando o manifesto" → ✓ "vamos enviar o manifesto"; "Before installing, check the requirements" → ✗ "Antes de instalando" → ✓ "Antes de instalar, verifique os requisitos". Genuine progressives are fine: ✓ "o pod está iniciando".
- **Passive**: agentless English passive → active imperative or synthetic passive with *se*: "The manifest is applied automatically" → ✓ "Aplica-se o manifesto automaticamente" / ✓ "O Cozystack aplica o manifesto automaticamente". In procedures, prefer the imperative.
- "you can" → alternate "você pode" with impersonal "é possível" so a page does not repeat "você pode" ten times.
- **Possessives → definite article**: "Open your terminal and check your cluster" → ✗ "Abra o seu terminal e verifique o seu cluster" → ✓ "Abra o terminal e verifique o cluster".
- **Noun stacking → de-chains, max two links**: "Kubernetes cluster node pool autoscaling configuration" → ✗ "configuração do autoscaling do pool de nós do cluster Kubernetes" → ✓ "configuração do autoscaling para pools de nós (cluster Kubernetes)".
- **ser vs estar**: definitional → *ser* ("O Cozystack é uma plataforma"); state/condition → *estar* ("O cluster está pronto", "o pod está em execução"). ✗ "O cluster é pronto".
- **Future subjunctive after quando/se/assim que**: "When you create the tenant" → ✗ "Quando você cria o tenant" → ✓ "Quando você criar o tenant"; "If the pod fails" → ✓ "Se o pod falhar"; "as soon as it is ready" → ✓ "assim que estiver pronto".
- **Colocação pronominal (BR = próclise)**: ✗ "Não aplica-se a clusters legados" → ✓ "Não se aplica a clusters legados". Never open a sentence with an unstressed pronoun; avoid pt-PT mesoclisis ✗ "permitir-lhe-á" → ✓ "vai permitir que você".
- **Future tense**: BR prefers "vai + infinitivo" or the simple present: "This will create a namespace" → ✗ "Isto irá criar um namespace" → ✓ "Isso cria um namespace".

## 7. Translationese and calques to eliminate

- "In this article, we will…" → ✗ "Neste artigo, nós vamos…" → ✓ "Veja como…" / "Este guia mostra…".
- Delete filler — *simply*, *just*, *easily*: ✗ "simplesmente execute" → ✓ "execute".
- support → ✗ "suportar" (= to endure) → ✓ "oferecer suporte a", "ser compatível com", "aceitar": "Cozystack supports GPU passthrough" → ✓ "O Cozystack oferece suporte a GPU passthrough".
- application → ✓ "aplicação" (server-side workloads); "aplicativo" only for mobile/desktop apps.
- encrypt → ✗ "encriptar" → ✓ "criptografar" / "criptografia". library → ✗ "livraria" → ✓ "biblioteca". customize → ✗ "customizar" → ✓ "personalizar". delete → ✗ "deletar" → ✓ "excluir"/"remover". set → ✗ "setar" → ✓ "definir"/"configurar". address (an issue) → ✗ "endereçar" → ✓ "tratar"/"resolver"/"corrigir".
- requirement → ✗ "requerimento" (= a petition) → ✓ "requisito". performance → ✓ "desempenho". check → ✓ "verificar" (not "checar"). issue → ✓ "problema" (keep "issue" only for a GitHub issue).
- "Once you have installed…" → ✗ "Uma vez que você instalou" (= *because*) → ✓ "Depois de instalar" / "Assim que instalar". "Assuming that…" → ✓ "Supondo que". "in order to" → ✓ "para" (not "de forma a"). "make sure" → ✓ "certifique-se de que"; "note that" → ✓ "observe que"; "keep in mind" → ✓ "lembre-se de que".

## 8. False friends (EN → PT)

actually → ✓ "na verdade" (✗ atualmente = *currently*) · eventually → ✓ "por fim", "com o tempo" (✗ eventualmente = *occasionally*) · library → ✓ biblioteca · support → ✓ oferecer suporte a · realize → ✓ "perceber", "notar" (✗ realizar = *to carry out*) · pretend → ✓ "fingir" (✗ pretender = *to intend*) · push (git) → keep "push" or ✓ "enviar" (✗ "empurrar") · assume → ✓ "supor", "presumir" (✗ assumir = *to take on*) · resume → ✓ "retomar" (✗ resumir = *to summarize*) · comprehensive → ✓ "abrangente" (✗ compreensivo = *understanding*) · sensible → ✓ "sensato" (✗ sensível = *sensitive*) · attend → ✓ "participar de" (✗ atender = *to serve*) · exit → ✓ "sair" (✗ êxito = *success*) · policy → ✓ "política" (never "polícia") · parent (resource) → ✓ "pai"/"superior".

## 9. Reviewer checklist — pt-BR machine-translation failure modes

1. **European Portuguese leaking in** — reject on sight: ficheiro→arquivo, utilizador→usuário, ecrã→tela, rato→mouse, aceder a→acessar, guardar→salvar, apagar→excluir, equipa→equipe, registo→registro, facto→fato, contacto→contato, "está a executar"→"está executando", connosco→conosco, gestor→gerenciador, telemóvel→celular.
2. English **title case** surviving in headings, `title`/`description`, table headers or link text.
3. Decimal points left as "3.14"/"1,000" in prose — or commas wrongly injected into code, versions, CIDRs.
4. Missing or hypercorrect **crase** ("à partir de", "acesso a API").
5. Comma before *e*/*ou*, or a comma splitting subject from verb.
6. Gender/number disagreement on loanwords ("a cluster", "os pod", "VM's").
7. Gerundismo, "irá + infinitivo" future, enclisis after negation ("não aplica-se").
8. Literal "suportar", "customizar", "deletar", "encriptar", "endereçar", "livraria", "uma vez que", "simplesmente".
9. Register drift: *tu*/*você* mixing, "por favor" in imperatives, marketing hype in docs, stiff formality in blog.
10. Untranslated or dropped sentences; translated API kinds, CLI flags, YAML keys or URLs — all hard failures.
11. Glossary terms rendered inconsistently across a page (e.g. "nó" in one paragraph, "node" in the next).
