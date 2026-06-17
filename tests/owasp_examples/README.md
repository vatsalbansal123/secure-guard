# OWASP Example Suite (Week 1 — Wed deliverable)

One concrete, vulnerable code example per OWASP category. These are the **test
inputs** for SecureGuard: paste each into the analyzer and confirm the rule
engine and/or LLM flags the expected issue.

> ⚠️ These files are **intentionally insecure** and are never imported or run.
> Linter/type warnings on them are expected.

## Web — OWASP Top 10 (2021)

| File | Category | Caught by rule engine? |
| ---- | -------- | ---------------------- |
| `web/a01_broken_access_control.py` | A01 Broken Access Control | ✅ OWASP-A01 |
| `web/a02_cryptographic_failures.py` | A02 Cryptographic Failures | ✅ OWASP-A02 |
| `web/a03_injection.py` | A03 Injection | ✅ OWASP-A03 |
| `web/a04_insecure_design.py` | A04 Insecure Design | ✅ OWASP-A04 |
| `web/a05_security_misconfiguration.py` | A05 Security Misconfiguration | ✅ OWASP-A05 |
| `web/a06_vulnerable_components.py` | A06 Vulnerable Components | ✅ OWASP-A06 |
| `web/a07_auth_failures.py` | A07 Auth Failures | ✅ OWASP-A07 |
| `web/a08_integrity_failures.py` | A08 Integrity Failures | ⚠️ LLM only (no rule yet) |
| `web/a09_logging_failures.py` | A09 Logging Failures | ⚠️ LLM only (no rule yet) |
| `web/a10_ssrf.py` | A10 SSRF | ⚠️ LLM only (no rule yet) |

## LLM — OWASP LLM Top 10 (2025)

These matter because SecureGuard feeds untrusted submitted code straight into an
LLM prompt (`backend/agent.py`). `llm/llm01_prompt_injection.txt` and
`llm/llm10_unbounded_consumption.txt` are live threats to the app itself.

| File | Category |
| ---- | -------- |
| `llm/llm01_prompt_injection.txt` | LLM01 Prompt Injection |
| `llm/llm02_sensitive_info_disclosure.txt` | LLM02 Sensitive Information Disclosure |
| `llm/llm03_supply_chain.txt` | LLM03 Supply Chain |
| `llm/llm04_data_model_poisoning.txt` | LLM04 Data & Model Poisoning |
| `llm/llm05_improper_output_handling.txt` | LLM05 Improper Output Handling |
| `llm/llm06_excessive_agency.txt` | LLM06 Excessive Agency |
| `llm/llm07_system_prompt_leakage.txt` | LLM07 System Prompt Leakage |
| `llm/llm08_vector_embedding_weaknesses.txt` | LLM08 Vector & Embedding Weaknesses |
| `llm/llm09_misinformation.txt` | LLM09 Misinformation |
| `llm/llm10_unbounded_consumption.txt` | LLM10 Unbounded Consumption |

## Gaps this suite reveals

The rule engine has no patterns for **A08, A09, A10**, and none of the LLM Top 10.
Those rows rely entirely on the LLM analysis node today. Adding rules for them is
a natural Week 2 task.
