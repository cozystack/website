# Hindi (hi) — style guide

Modern standard Hindi (Devanagari) as written by Indian tech authors. Hinglish is normal and expected: keep widely-used English technical terms as English terms rather than forcing Sanskritized coinages. Translate the connective prose, not the jargon. Register: professional, clear, never bureaucratic (सरकारी हिंदी), never slangy.

## 1. Register and address

- Address the reader as **आप** only. Never तू/तुम. Verbs take the आप form: करें, चलाएँ, देखें, कर सकते हैं.
- Imperative style: use the **-एँ** form consistently (चलाएँ, बनाएँ, जोड़ें). Do not mix in कीजिए/कीजिये or करो within a page.
- Docs: terse, instructional, present tense. Blog: same person, slightly warmer; the project may speak as हम.
- No exclamation marks, no rhetorical questions, no emoji, no filler (आइए जानते हैं, तो चलिए शुरू करते हैं).
- EN "You can now access the dashboard." → ✗ "अब आप डैशबोर्ड को एक्सेस कर सकते हैं!" → ✓ "अब आप dashboard खोल सकते हैं।"

## 2. How much English to keep — the central rule

Test each term with one question: **would an Indian DevOps engineer say this word in English while speaking Hindi?** If yes, it stays an English word. Then decide the script by bucket:

1. **Latin script, verbatim** — anything the reader must type, match, or click: product and project names (Cozystack, Kubernetes, Talos, Flux), CLI names and flags (kubectl, --namespace), API kinds and fields (Pod, Deployment, Secret, Node, ConfigMap, StorageClass, spec.replicas), file names, env vars, UI labels, acronyms (API, CNI, CSI, RBAC, TLS, YAML, GPU).
2. **Devanagari transliteration of the English word** — only for the general infra nouns the injected glossary assigns a Hindi rendering (e.g. cluster/node/storage as ordinary nouns). Use the glossary form exactly; never invent new transliterations for terms it does not list.
3. **Real Hindi** — everything else: verbs, adjectives, connectors, and ordinary nouns (उपलब्ध, कॉन्फ़िगर करें, इसके बाद, ध्यान दें, अनुमति, आवश्यकता).

Default for a term not covered by the glossary: **keep it in Latin.** Never coin a Devanagari equivalent for infra jargon.

- ✗ संगणक, कुंजीपटल, अभिकलन, स्मृति, संचिका, जालक्रम, कूटशब्द, आभासी संगणित्र → ✓ computer, keyboard, compute, memory, file, network, password, VM
- EN "Configure the ingress controller and the load balancer." → ✗ "प्रवेश नियंत्रक और भार संतुलक को विन्यस्त करें।" → ✓ "ingress controller और load balancer कॉन्फ़िगर करें।"
- EN "Kubernetes schedules the pod on a node." → ✗ "कुबेरनेट्स पॉड को एक नोड पर शेड्यूल करता है।" (brand transliterated) → ✓ "Kubernetes पॉड को नोड पर schedule करता है।"
- Over-translation is as bad as under-translation: EN "high availability" → ✗ "उच्च उपलब्धता" is acceptable only if the glossary says so; otherwise keep "high availability".

## 3. Headings

- Devanagari has no letter case — there is nothing to title-case. Do not capitalize or restyle; just write a natural phrase.
- No terminal । in headings. No trailing colon.
- English terms inside a heading keep exactly the form used in the body — same script, same capitalization. ✗ heading "क्लस्टर इंस्टॉल करना" + body "cluster" (script drift).
- Prefer verbal nouns or short noun phrases, consistently within a page: EN "Installing Cozystack" → ✓ "Cozystack इंस्टॉल करना"; EN "Prerequisites" → ✓ "आवश्यक शर्तें"; EN "Troubleshooting" → ✓ "समस्या निवारण".

## 4. Terminology policy (terms outside the glossary)

Decision order: glossary `do_not_translate` → verbatim Latin; glossary `preferred` → that exact rendering, every occurrence; otherwise apply §2 and default to Latin.

- **API kinds stay Latin and singular in prose**: "Pod को delete करें", "Deployment में replicas बढ़ाएँ", "यह Secret namespace में बनता है". Never transliterate a kind (✗ डिप्लॉयमेंट ऑब्जेक्ट for `kind: Deployment`).
- Mirror the glossary's Tenant/tenant split: capitalized API kind (`Node`, `Tenant`) → Latin; the same word as an ordinary noun (a node, a tenant) → the glossary's Devanagari form.
- **First mention**: when a Devanagari-rendered term first appears on a page, gloss it once — "टेनेंट (tenant)" — then use the plain form. Do not repeat the gloss.
- One term = one rendering per page and per docs version. If you chose Latin once, it is Latin everywhere on that page.
- Never attach Devanagari inflection to a Latin word: ✗ Podों, ✗ Deploymentस, ✗ नोडnode. Express plurality with a quantifier: ✓ "कई Pod", "सभी Node", "दो PVC".

## 5. Script and typography

- End full sentences in prose with **पूर्ण विराम ।**, including sentences that end on a Latin word: ✓ "इसके बाद `kubectl apply` चलाएँ।" Never write ".।". Never place । inside code, headings, or list fragments that are not sentences.
- Keep the period for version numbers, decimals, abbreviations and anything inside code (v1.2.5).
- Use straight double quotes " " for quoted UI strings and values; keep the quoted English string in Latin. Avoid mixed ‘ ’/“ ” pairs.
- One space between a Devanagari run and an adjacent Latin/number run; no space before ।, comma, or a closing bracket. Postpositions after Latin words are separated by a space: "Node पर", "namespace में".
- Never mix scripts inside a single word, and never transliterate identifiers, flags, paths, or commands.

## 6. Numbers, dates, units

- **Western Arabic digits only** (1, 2, 3). Never Devanagari digits (१, २, ३).
- Use **international grouping** — 1,000 / 1,000,000. Do **not** use Indian grouping (✗ 10,00,000) and never convert to lakh/crore in technical content.
- Decimal point is `.` — ✓ 1.5 GB.
- Dates: "24 जुलाई 2026" in prose; ISO `2026-07-24` when the source is ISO. Never MM/DD/YYYY.
- Units keep Latin symbols with a space: 16 GB, 500 ms, 4 vCPU, 10 Gbit/s. Percent has no space: 50%. Ranges: "2–4 GB" or "2 से 4 GB".

## 7. Grammar traps (EN → HI)

- **SOV order.** EN "Cozystack deploys the application to the cluster." → ✗ "Cozystack डिप्लॉय करता है application को क्लस्टर में।" → ✓ "Cozystack application को क्लस्टर में deploy करता है।" The verb goes last.
- **Gender of English loanwords.** Consonant-final loans are **masculine**: क्लस्टर, नोड, पॉड, सर्वर, नेटवर्क, स्टोरेज, बैकअप, प्लेटफ़ॉर्म. Feminine: फ़ाइल, मशीन, सर्विस, इमेज, and -ी endings (मेमोरी, डायरेक्टरी, लाइब्रेरी). Keep gender consistent across the whole page: ✗ "क्लस्टर बनाई गई" → ✓ "क्लस्टर बनाया गया"; ✗ "फ़ाइल बनाया गया" → ✓ "फ़ाइल बनाई गई".
- **का/की/के agreement** follows the *possessed* noun: ✓ "क्लस्टर की स्थिति", "नोड का नाम", "Pod के logs".
- **Postpositions.** in → में, on → पर, from → से, for → के लिए. ✗ "क्लस्टर के लिए deploy करें" for "deploy to the cluster" → ✓ "क्लस्टर में deploy करें".
- **Ergative ने** only with perfective transitive verbs: ✓ "हमने क्लस्टर बनाया"; ✗ "Cozystack ने क्लस्टर बनाता है" (imperfective — no ने); ✗ ने with intransitives ("Pod ने शुरू हुआ").
- **Compound verbs** read naturally; do not strip them: ✓ "config फ़ाइल लिख दें", "logs देख लें" where the source implies completion. Do not add them where the source is neutral.
- Honorific verb forms must stay consistent — do not switch between "करें" and "करते हैं" for the same instructional voice.

## 8. Translationese and calque patterns to fix

- **"आप ... कर सकते हैं" everywhere.** In step-by-step docs use the imperative. EN "You can create a tenant with kubectl." → ✗ "आप kubectl का उपयोग करके एक टेनेंट बना सकते हैं।" → ✓ "kubectl से टेनेंट बनाएँ।"
- **एक as an article.** Hindi has no indefinite article. ✗ "एक क्लस्टर बनाएँ" → ✓ "क्लस्टर बनाएँ". Keep एक only when the count matters.
- **Literal passive.** EN "The cluster is created by the operator." → ✗ "क्लस्टर ऑपरेटर के द्वारा बनाया जाता है।" → ✓ "operator क्लस्टर बनाता है।"
- **English-order relative clauses.** EN "the node that runs the workload" → ✗ "नोड जो वर्कलोड चलाता है" → ✓ "वर्कलोड चलाने वाला नोड" (or जो … वह with correct correlative).
- **"का उपयोग करके" / "के माध्यम से" stacked in every sentence** → prefer "से": ✓ "Helm से इंस्टॉल करें".
- **"यह सुनिश्चित करें कि" / "कृपया"** in every step — drop them; docs are already polite via आप.
- Word-by-word renderings of English idiom ("out of the box" → ✗ "डिब्बे से बाहर") → ✓ "बिना अतिरिक्त कॉन्फ़िगरेशन के" or keep "out of the box".

## 9. Reviewer checklist (MT failure modes)

1. Sanskritized coinage anywhere (संगणक, कुंजीपटल, अभिकलन, स्मृति, संचिका) → reject.
2. Brand/product transliterated (कुबेरनेट्स, कोज़ीस्टैक, कुबेक्टल) → must be Latin.
3. Same term in two scripts or two spellings on one page (cluster vs क्लस्टर, स्टोरेज vs भंडारण).
4. Gender drift on loanwords across paragraphs; का/की/के disagreement.
5. English SVO order preserved; verb not final.
6. Wrong postposition, or में/पर/के लिए swapped.
7. ने inserted with imperfective or intransitive verbs.
8. Passive constructions copied from English.
9. "आप … कर सकते हैं" or "एक" repeated in nearly every sentence.
10. Devanagari digits, Indian digit grouping, lakh/crore, MM/DD dates.
11. Missing or doubled ।; । after a heading; । inside code.
12. Devanagari suffixes glued to Latin words (Podों), or a translated flag/identifier (`--नाम`).
13. Mixed imperative registers (चलाएँ vs चलाइए vs चलाओ) in one page.
14. Terminology diverging from the injected glossary.

## 10. Pipeline note

Code blocks, inline code, Hugo shortcodes, URLs, HTML attributes and front-matter keys are masked structurally by the pipeline. Never translate, reorder, transliterate or re-space anything inside a mask; front-matter `title` and `description` values are translated, their keys are not.
