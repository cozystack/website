- Simplified Chinese (zh-Hans), mainland conventions; follow kubernetes.io/zh-cn glossary.
- No spaces between Chinese characters; put a space between Chinese and Latin/number runs.
- Use full-width Chinese punctuation (，。：；""）for Chinese text; keep half-width for code/commands.
- Keep product/brand/CLI terms in Latin; translate prose. Common infra terms per k8s zh glossary (集群=cluster, 节点=node, 存储=storage, 工作负载=workload).

### 1. Register and address

- Docs: 书面语 — precise, impersonal, imperative for steps. Blog/landing: livelier, shorter sentences, rhetorical questions allowed; never 网络流行语 or exclamation spam.
- Address the reader as **你**, never 您. This is the kubernetes.io/zh-cn convention: 您 reads deferential/sales-y and is impossible to keep consistent across a large doc set. Better still, drop the pronoun. EN "You can install it with Helm" → ✗ 您可以使用 Helm 来安装它 → ✓ 使用 Helm 安装即可。
- Mixing 你 and 您 on one page is a defect even if each sentence reads fine.
- First person plural only in signed blog posts. Docs: ✗ 我们建议启用备份 → ✓ 建议启用备份。

### 2. Headings

- No trailing 。 in any heading. ？and ！are allowed when the source is a question/exclamation: "What is Cozystack?" → ✓ 什么是 Cozystack？
- Concept/reference headings → noun phrase: "Storage Architecture" → ✓ 存储架构（✗ 存储是如何架构的）。
- Task headings → 动宾 verb phrase, no 正在 / 如何进行 padding: "Installing Cozystack" → ✗ 正在安装 Cozystack、✗ 如何进行 Cozystack 的安装 → ✓ 安装 Cozystack。
- Conventional renderings: "Getting Started" → 快速开始；"Prerequisites" → 前置条件；"Troubleshooting" → 故障排查；"See also" → 参见；"Next steps" → 后续步骤。
- Do not add numbering the source lacks; keep heading levels unchanged.

### 3. Terminology policy (terms NOT in the injected lists)

Decision order: (1) kubernetes.io/zh-cn glossary → (2) CNCF Cloud Native Glossary 中文版 → (3) rules below. Never coin a new Chinese term for a concept the Chinese k8s community discusses in English.
- **API kinds, CRD kinds, field names, flags, CLIs stay Latin and uninflected**: Pod、Deployment、StatefulSet、DaemonSet、Secret、ConfigMap、Ingress、kubelet、kubectl。✗ 豆荚 / 入口 / 秘密 / 配置映射。
- **The same word as an ordinary noun is translated** per k8s zh: node→节点、namespace→命名空间、volume→卷、label→标签、annotation→注解、container→容器、image→镜像、replica→副本、control plane→控制平面、service→服务。If the sentence means `kind: Node` / `kind: Service`, keep Node / Service in Latin.
- Generic concepts with stable renderings are translated: 高可用、可观测性、编排、调度、快照、备份、故障转移、隔离、租户。
- Unknown/new term with no stable rendering: keep Latin, or use 中文（English）on **first mention per page**, Chinese only afterwards — ✓ 单节点控制平面（single-node control plane）。Never repeat the bracketed English on every occurrence.
- One page = one rendering per term. ✗ 租户 … 承租方 … 租客 in the same file.

### 4. Punctuation

- Full-width only in Chinese prose: ，。：；！？（）【】、 — ASCII `,` `.` `;` `:` in Chinese prose is always a defect.
- **顿号 、 separates coordinate items inside a sentence** (English has no equivalent — do not copy the source commas): "CPU, memory, and storage" → ✗ CPU，内存，和存储 → ✓ CPU、内存和存储。
- Quotes: “ ” (inner ‘ ’) for quoted prose and UI strings; 《》 for titles of docs/books/specs: ✓ 详见《Cozystack 安装指南》。✗ "Cozystack 安装指南"。
- Ellipsis is ……（two full-width chars）, dash is ——, never `...` or ` - `. Ranges: ✓ 3～5 个节点 / 3 到 5 个节点。
- Half-width is correct and required inside code, inline code, versions (v1.5.0), paths, URLs, decimals (99.9), flags (`--dry-run`), and inside a fully English quoted string.
- No doubled punctuation: ✗ 部署完成。）→ ✓ 部署完成）。 Bullets and table cells: no 。 on fragments; 。 on full sentences, consistently within one list.
- Parentheses inside a Chinese sentence are full-width （） even when the content is Latin: ✓ 控制平面（control plane）。

### 5. Spacing (pangu)

- One space between a Chinese run and an adjacent Latin/digit run: ✓ 使用 Helm 部署 3 个副本。 ✗ 使用Helm部署3个副本。
- **No** space between Chinese/Latin and full-width punctuation: ✗ 安装 Cozystack ，然后… → ✓ 安装 Cozystack，然后…；✗ 存储 、 网络 → ✓ 存储、网络。
- Keep the space around masked inline-code spans too: ✓ 运行 `kubectl get pods` 查看状态。
- Never insert pangu spaces inside code, paths, URLs, or masked placeholders.
- Never use full-width Latin letters or digits (✗ Ｋｕｂｅｒｎｅｔｅｓ、✗ １０); no double spaces; no space before a line-final 。

### 6. Numbers, dates, units

- Arabic numerals for all quantities, versions, dates, ports, sizes. Chinese numerals only in fixed expressions (一致、一次性、第三方). Procedures: ✓ 第 1 步 / 步骤 1。
- 万/亿 are fine in blog prose for round numbers（✓ 10 万个 Pod）; in docs keep the source's exact figures and separators (1,000 QPS stays 1,000 QPS). Never rescale magnitudes silently.
- English "billion" = 10 亿, "trillion" = 万亿 — a classic MT slip; verify every large number against the source.
- Dates: ✓ 2026年7月24日（no spaces around 年月日）; ✗ 7月24日，2026。Times: ✓ 14:30。
- Units: space between number and Latin unit — ✓ 16 GiB、100 ms、10 Gbit/s；no space for % or Chinese measure words — ✓ 99.9%、3 个节点。

### 7. Grammar traps translating from English

- **量词 are mandatory and must be right**: "three nodes" → ✗ 3 节点 → ✓ 3 个节点。一台虚拟机、一块 GPU、一份清单、一条规则、一组副本、一次请求、一个 Pod、一套集群。
- **Attributive chains before 的**: at most one 的 per noun phrase; move the rest into a following clause. "a highly available, self-healing Kubernetes control plane deployed on bare-metal nodes" → ✗ 一个部署在裸金属节点上的高可用的能够自我修复的 Kubernetes 控制平面 → ✓ 一个高可用的 Kubernetes 控制平面，部署在裸金属节点上，并可自我修复。
- **Articles and plurals go to zero**: ✗ Pod们被调度 → ✓ Pod 会被调度；✗ 这些的集群 → ✓ 这些集群。
- **被 is overused by MT.** Named agent → 由: ✗ 卷被 kubelet 挂载 → ✓ 卷由 kubelet 挂载。No agent → topic-comment: ✗ 备份被存储在 S3 中 → ✓ 备份存储在 S3 中。Reserve 被 for adverse/unexpected events.
- **Split long sentences**: one English sentence with 2+ subordinate clauses → 2–3 Chinese clauses ended by 。, ideally ≤ 40 汉字 each. Do not chain them with ；.
- **Topic first (主题-述题)**: "You can configure the number of replicas in values.yaml." → ✓ 副本数量在 `values.yaml` 中配置。
- **Condition before result**: "Restart the Pod if the probe fails." → ✓ 如果探针失败，则重启 Pod。
- 的/地/得: 快速的部署（attributive）、快速地部署（adverbial）、部署得很快（complement）— MT confuses these constantly.

### 8. 翻译腔 patterns to eliminate

- 进行/做出/实现 + nominalization: ✗ 对集群进行备份操作 → ✓ 备份集群；✗ 做出配置更改 → ✓ 修改配置。
- 一个 for every English "a": ✗ 这是一个常见的模式 → ✓ 这是常见模式。
- 们 on generic/inanimate nouns: ✗ 用户们、开发者们、节点们 → ✓ 用户、开发者、节点。
- 关于/对于 padding: ✗ 关于更多关于 X 的信息，请参见 Y → ✓ 更多信息参见 Y；✗ 对 X 的支持 → ✓ 支持 X。
- "simply / just / easily": ✗ 简单地运行以下命令 → ✓ 运行以下命令（或 只需运行以下命令）。
- "you can" on every sentence: ✗ 你可以使用 Helm 来安装它 → ✓ 使用 Helm 安装。
- 来 as filler infinitive: ✗ 使用 kubectl 来查看日志 → ✓ 使用 kubectl 查看日志。
- "allows/enables you to": ✗ 允许你创建租户 → ✓ 支持创建租户。
- "It is worth noting that…": ✗ 值得注意的是，… → ✓ 注意：…
- 请 only where the source is a genuine pointer/request（✓ 请参见）, not on every imperative.

### 9. Reviewer checklist — Chinese-specific MT failure modes

1. 繁体字或台港用词泄漏: ✗ 記憶體/軟體/網路/程式/預設/伺服器/映像檔/叢集 → ✓ 内存/软件/网络/程序/默认/服务器/镜像/集群；✗ 结点 → ✓ 节点。
2. ASCII punctuation in Chinese prose; missing 顿号; `...` instead of ……; half-width () wrapping Chinese.
3. Missing or spurious pangu spaces; full-width Latin/digits; space before 。，、.
4. Over-translated identifiers (Pod/Ingress/Secret/kubectl rendered in Chinese) or under-translated prose (cluster/node left in English).
5. Term drift within a page; first-mention 中文（English）repeated on every occurrence.
6. 被-heavy passives; 的-chains with more than one 的; missing 量词; 的/地/得 confusion.
7. English word order in Chinese characters — read the sentence aloud; if it needs a second pass to parse, split it.
8. 你/您 mixing; register drift (marketing tone inside reference docs, or stiff 书面语 inside a blog post).
9. Number/magnitude errors, altered versions, flags, resource names, or YAML keys.
10. Untranslated leftovers, duplicated clauses, and **dropped negation**（未/不/无 lost reverses the meaning）; lost admonition labels — note→说明、warning→警告、caution→注意。

### 10. Structural (pipeline-enforced)

Code blocks, inline code, Hugo shortcodes（`{{< >}}` / `{{% %}}`）, URLs, file paths, HTML comments and front-matter **keys** are masked as `§§NAME_N§§` placeholders: copy them through verbatim, never translate, reorder, or space-fix their contents. Translate link **text**, never the URL; keep heading levels, list markers, and table column counts identical to the source.
