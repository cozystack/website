You are checking a translation for meaning drift using a round-trip test. You
are given the ORIGINAL English page and a BACK-TRANSLATION into English of the
{{LANGUAGE}} translation. Compare them for **semantic fidelity** — did meaning
survive the round trip?

Report drift where the back-translation shows the {{LANGUAGE}} translation:
- dropped a claim, instruction, sentence, or list item present in the original,
- added a claim not in the original,
- changed a number, version, name, flag, or technical fact,
- reversed or weakened a statement (e.g. "must" → "may", "not supported" → "supported").

Ignore differences that are purely stylistic or wording-level and don't change
meaning (back-translation is intentionally literal and will read awkwardly).
Ignore code, shortcodes, URLs, and §§NAME_N§§ placeholders.

Return strict JSON only:
{
  "verdict": "pass" | "revise",
  "findings": [
    {"severity": "major"|"minor", "issue": "<what drifted>", "original": "<original span>", "back": "<back-translated span>"}
  ]
}
"pass" = no meaningful drift. "revise" = at least one meaning change. Output ONLY
the JSON object.
