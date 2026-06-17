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
| Python (`requirements.txt`) | 237 | 3 (6 vulnerable paths) | **High** |
| npm (`frontend/package-lock.json`) | 149 | 0 | — |

The frontend is clean. All findings are in the Python backend dependencies.

## Python findings

| Severity | Package | Installed | Fixed in | Vulnerability |
|----------|---------|-----------|----------|---------------|
| 🔴 High | `starlette` | 1.2.1 | **1.3.0** | Use of Incorrectly-Resolved Name or Reference ([SNYK-PYTHON-STARLETTE-17342519](https://security.snyk.io/vuln/SNYK-PYTHON-STARLETTE-17342519)) |
| 🟠 Medium | `python-multipart` | 0.0.30 | **0.0.31** | Improper Validation of Specified Quantity in Input ([SNYK-PYTHON-PYTHONMULTIPART-17345735](https://security.snyk.io/vuln/SNYK-PYTHON-PYTHONMULTIPART-17345735)) |
| 🟠 Medium | `streamlit` | 1.58.0 | _none_ | Use of Weak Hash ([SNYK-PYTHON-STREAMLIT-17176399](https://security.snyk.io/vuln/SNYK-PYTHON-STREAMLIT-17176399)) |

## Required fixes before Week 2 (Critical + High)

Per the Week 1 plan, fix Critical and High before Week 2. That means **`starlette`**.
`starlette` is a transitive dependency of FastAPI, so pin the fixed version:

```text
# requirements.txt
starlette>=1.3.0
python-multipart>=0.0.31   # also fixes the Medium
```

Then reinstall and re-scan:

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
