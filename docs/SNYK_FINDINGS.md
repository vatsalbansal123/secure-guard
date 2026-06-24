# Snyk Findings (Week 1 — Weekend deliverable)

Dependency scan of both ecosystems with the Snyk CLI.
Org: `bansalvatsal2007`.

## Commands run

```bash
# Python (deps resolved via the project venv; unresolved markers skipped)
snyk test --command=venv/bin/python --file=requirements.txt \
          --package-manager=pip --skip-unresolved

# Frontend (npm)
snyk test --file=frontend/package-lock.json
```

## Summary

| Ecosystem | Dependencies tested | Issues | Highest severity |
|-----------|--------------------|--------|------------------|
| Python (`requirements.txt`) | 237 | 6 (32 vulnerable paths) | **High** |
| npm (`frontend/package-lock.json`) | 149 | 0 | — |

The frontend is clean. All findings are in the Python backend dependencies.

> **Re-scan note (2026-06-21):** A fresh scan surfaced three additional High
> findings not present in the original scan (`cryptography`, `langsmith`, and a
> second `starlette` CVE), and bumped the required `starlette` fix from 1.3.0 to
> **1.3.1**. The table below reflects the latest scan.

## Python findings

| Severity | Package | Installed | Fixed in | Vulnerability |
|----------|---------|-----------|----------|---------------|
| 🔴 High | `cryptography` | 48.0.0 | **48.0.1** | Out-of-bounds Read ([SNYK-PYTHON-CRYPTOGRAPHY-17344551](https://security.snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-17344551)) |
| 🔴 High | `starlette` | 1.2.1 | **1.3.1** | Allocation of Resources Without Limits or Throttling ([SNYK-PYTHON-STARLETTE-17342515](https://security.snyk.io/vuln/SNYK-PYTHON-STARLETTE-17342515)) |
| 🔴 High | `starlette` | 1.2.1 | **1.3.1** | Use of Incorrectly-Resolved Name or Reference ([SNYK-PYTHON-STARLETTE-17342519](https://security.snyk.io/vuln/SNYK-PYTHON-STARLETTE-17342519)) |
| 🔴 High | `langsmith` | 0.8.15 | **0.8.18** | Type Confusion ([SNYK-PYTHON-LANGSMITH-17391446](https://security.snyk.io/vuln/SNYK-PYTHON-LANGSMITH-17391446)) — transitive via `langchain-core` |
| 🟠 Medium | `python-multipart` | 0.0.30 | **0.0.31** | Improper Validation of Specified Quantity in Input ([SNYK-PYTHON-PYTHONMULTIPART-17345735](https://security.snyk.io/vuln/SNYK-PYTHON-PYTHONMULTIPART-17345735)) |
| 🟠 Medium | `streamlit` | 1.58.0 | _none_ | Use of Weak Hash ([SNYK-PYTHON-STREAMLIT-17176399](https://security.snyk.io/vuln/SNYK-PYTHON-STREAMLIT-17176399)) |

## Required fixes before Week 2 (Critical + High)

Per the Week 1 plan, fix Critical and High before Week 2. That means
**`cryptography`**, **`starlette`** (now 1.3.1), and **`langsmith`**. These pins
are now set in `requirements.txt`:

```text
# requirements.txt
cryptography==48.0.1
starlette==1.3.1
langsmith==0.8.18          # transitive via langchain-core; pinned to force the fix
python-multipart==0.0.31   # also fixes the Medium
```

The earlier scan's pins were edited in `requirements.txt` but **never installed**
into the venv, so the scan still saw the old versions. Reinstall, then re-scan:

```bash
venv/bin/pip install -r requirements.txt
snyk test --command=venv/bin/python --file=requirements.txt \
          --package-manager=pip --skip-unresolved
```

## Notes / accepted risk
- **`streamlit` (Medium, weak hash)** — no upstream fix available yet. Note that
  Streamlit isn't used by the FastAPI/React app surface; if it's not needed at
  runtime, consider removing it from `requirements.txt` to drop the finding
  entirely. Otherwise track and accept until a patched release ships.
- `--skip-unresolved` was needed because not every pinned package is installed in
  the venv; the resolved dependency graph (237 deps) was still scanned.

_Re-run this scan after any dependency change and update the table above._

---

## Week 5 re-scan — React dashboard (2026-06-24)

Week 5 added the CodeMirror editor stack to the frontend (`@uiw/react-codemirror`
+ language grammars + `@codemirror/theme-one-dark`). Re-scanned the frontend
dependencies after the install.

```bash
cd frontend
snyk test --file=package-lock.json     # dependency scan
npm audit --omit=dev                   # cross-check
```

| Scan | Dependencies tested | Issues |
|------|--------------------|--------|
| `snyk test` (npm) | 185 | **0 — no vulnerable paths** |
| `npm audit` (prod) | 406 (incl. transitive) | **0 vulnerabilities** |

The CodeMirror packages added no vulnerable paths.

### SAST (`snyk code test`) — not available
`snyk code test src/` returns **SNYK-CODE-0005: Snyk Code is not enabled** for
org `bansalvatsal2007` (403), same limitation noted in Week 3. As the
compensating control for the Week 5 client-side XSS concern (rendering
LLM-generated `fixed_code`), a **manual audit** was run instead:

```bash
grep -rn "dangerouslySetInnerHTML" frontend/src/   # 0 real usages (only a comment)
```

All code is rendered via CodeMirror (DOM text nodes) and Markdown via
`react-markdown` without `rehype-raw` — no raw-HTML injection sink exists. See
[WEEK5_DASHBOARD.md](./WEEK5_DASHBOARD.md) §Tue. Enabling Snyk Code on the org
remains an open follow-up to automate this check.
