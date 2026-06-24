# Week 5 — React Developer Dashboard & Analysis History (v0.5)

The dashboard turns the API into a tool a developer would actually use: a
syntax-highlighted editor, a live findings/fixes panel, and a searchable history
of past analyses. The security work for the week is concentrated in three
places — **safe rendering** of LLM output, **IDOR-proof** history access, and a
**code-free audit trail**.

## Architecture

```
frontend/src/
  App.jsx         tabs (Analyze | History), state, SSE wiring
  api.js          fetch helpers (analyze stream, history, history/:id)
  editor.jsx      CodeMirror editor + read-only viewer + side-by-side diff
  FindingCard.jsx finding + AI fix + diff + confidence
  History.jsx     submissions table → detail → reanalyze
  ui.jsx          shared components (badges, confidence bar, score panel)
  theme.js        constants + color helpers (no components)

backend/
  storage.py      Submission + AuditLog models; results-only persistence
  main.py         GET /history, GET /history/:id (ownership-scoped)
  auth.py         stashes api_key_id for per-developer ownership checks
```

## Mon — Components
- **Code input**: CodeMirror (`@uiw/react-codemirror`) with per-language grammars
  (python, js/ts, java, php, sql, rust, c/cpp; others fall back to plain text).
- **Findings panel**: severity badge, OWASP rule id, status badge, confidence bar.
- **Diff view**: side-by-side *Submitted* vs *Suggested fix* (`CodeDiff`).
- **Confidence indicators**: a bar on both the finding and its fix (carried over
  from Week 4's LLM09 trust scoring).

## Tue — Safe rendering of LLM output (the key frontend risk)
The fixed code and explanation come from an LLM. If rendered as HTML, a crafted
snippet could inject markup/script into the dashboard.

- **All code is rendered by CodeMirror**, which builds the highlighted view from
  DOM **text nodes** — it never interprets our content as HTML.
- **Zero `dangerouslySetInnerHTML`** anywhere in `src/` (audited; see command
  below). This is why CodeMirror was chosen over a Prism/highlight.js approach,
  where rendering the tokenized HTML string would require `dangerouslySetInnerHTML`.
- The explanation is Markdown, rendered with `react-markdown`, which escapes by
  default and is not given `rehype-raw`, so embedded HTML stays inert.

```bash
grep -rn "dangerouslySetInnerHTML" frontend/src/    # only the comment noting its absence
```

## Wed — History endpoint & IDOR defense
`GET /history` and `GET /history/{id}` return the **authenticated developer's**
submissions. A "developer" is identified by their API key (`api_keys.id`), which
`require_api_key` stashes on `request.state.api_key_id`.

Every query is **scoped to that owner id**:

```python
select(Submission).where(
    Submission.id == submission_id,
    Submission.api_key_id == api_key_id,   # <-- the IDOR defense
)
```

- A request for another developer's submission id returns **404, not 403** — we
  never confirm that someone else's submission exists.
- Submission ids are random `uuid4` hex (defense-in-depth against guessing), but
  the ownership filter is the real control — it holds even if an id leaks.

See [IDOR_TEST_LOG.md](./IDOR_TEST_LOG.md) for the attacker-vs-victim test.

## Thu — History UI
A table of past submissions (timestamp, language, finding count, severity
summary, grade). Clicking a row loads the full stored report. A **Reanalyze**
button re-runs the analysis — useful for confirming a fix worked.

> **Reanalyze is session-scoped by design.** The server never stores the
> submitted source (see Fri/Key learning), so it cannot hand the code back.
> The frontend keeps a `submission_id → code` map for the **current browser
> session only**; Reanalyze is enabled when that code is still in memory and
> otherwise explains why it can't (rather than silently storing code server-side).

## Fri — Audit logging (code-free)
Every security-relevant action writes an `AuditLog` row and a structured log line:

| action | when |
|--------|------|
| `key_created` | a new API key is minted |
| `submission_created` | an analysis is run and stored |
| `report_retrieved` | a single report is opened |
| `history_listed` | the history list is fetched |

Each row holds **`api_key_id`, `timestamp`, `action`, `submission_id`** — and
nothing else. `log_event()` takes no code/report argument, so there is no path
by which submitted source can reach the trail.

## Data handling — we persist results, never source code
`Submission` stores the produced **report, score, summary, and metadata**
(language, counts, timestamp). It has **no `code` column**. The analyzed source
is never written to disk.

This is the week's key learning: a developer tool handles proprietary code.
Storing the submitted snippet would make SecureGuard itself the leak. The audit
log records **that** a submission happened, never **what** was in it. A test
(`test_submitted_code_is_not_persisted`) submits a marker string and asserts it
appears in neither the submission row nor the audit log.

## Tests
`tests/test_history.py` (7 tests):
- `test_idor_cannot_read_other_developers_submission` — B requests A's id → 404.
- `test_history_list_is_isolated_per_developer` — each key sees only its own rows.
- `test_history_requires_auth` — both endpoints 401 without a key.
- `test_submitted_code_is_not_persisted` — marker absent from store + audit.
- `test_audit_trail_records_events` — all four actions logged.
- plus list/detail happy-path and `submission_id` return.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 venv/bin/python -m pytest tests/ -q
```
