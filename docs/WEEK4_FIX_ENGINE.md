# Week 4 — Fix Suggestion & Explanation Engine (v0.4)

For each confirmed finding, the agent now produces a corrected version of the
code and a teaching explanation. The hard part isn't generating a fix — it's
*trusting* it.

## Key risk: OWASP LLM09 (Misinformation)
A wrong answer in a recipe app is annoying. A wrong answer in a security tool is
dangerous:
- A **hallucinated finding** tells a developer safe code is unsafe (wasted effort).
- A **hallucinated fix** tells a developer vulnerable code is now safe (**actively
  harmful**).

So every fix passes through a checker, and uncertainty is made visible rather
than hidden.

## Flow

```
format_output ──→ suggest_fixes ──→ END
                       │  (per confirmed finding, runs a fix subgraph)
                       ▼
            ┌────────────────────────────────────────────┐
            │  generate ──→ check ──(conditional edge)──┐ │
            │     ▲                                      │ │
            │     └──────────── retry (≤1) ──────────────┘ │
            │            else → done                        │
            └────────────────────────────────────────────┘
```

- **generate** ([fixer.py](../backend/fixer.py)) → `FixSuggestion{fixed_code,
  explanation, owasp_reference, confidence}` via JSON mode. The explanation must
  cover *what the vuln is, how an attacker exploits it, why the fix works*, and
  cite the OWASP category (Fri prompt-engineering goal).
- **check** → an independent **LLM-as-judge** call returns
  `CheckVerdict{addresses_finding, introduces_new_issue, reasoning, confidence}`.
- **conditional edge** → if the verdict is bad and attempts remain, route back to
  `generate` with the reviewer's feedback (one revision); else finish.

## Confidence scoring (the LLM09 mitigation)
`finalize_fix` blends generator + checker into a status the UI surfaces:

| Checker verdict | Fix status | Confidence |
|-----------------|-----------|------------|
| does not address finding | `rejected` | ≤ 0.20 |
| addresses but adds a new issue | `needs_review` | ≤ 0.40 |
| addresses, no new issue | `verified` | mean(gen, checker) |

Fixes are generated **only for `confirmed` findings** — never for findings that
are themselves low-confidence. The frontend shows a confidence bar, the status
badge, and an explicit "⚠ AI-generated fix — review before applying" disclaimer.

## API shape
Each item in `result[]` may now include:
```json
{
  "rule_id": "OWASP-A03", "name": "Injection", "severity": "Critical",
  "status": "confirmed", "confidence": 0.95,
  "fix": {
    "fixed_code": "...", "explanation": "...",
    "owasp_reference": "A03:2021 Injection",
    "status": "verified", "confidence": 0.9, "checker_note": "..."
  }
}
```

## Evaluation
See [GOLDEN_SET.md](./GOLDEN_SET.md) — 10 known-vulnerable snippets, expected
OWASP category, acceptable fix patterns, and measured accuracy.
