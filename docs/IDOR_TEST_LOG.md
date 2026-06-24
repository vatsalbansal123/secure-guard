# IDOR Test Log (Week 5 — Weekend)

The history endpoints expose stored analysis reports. The core access-control
risk is **IDOR (Insecure Direct Object Reference, OWASP A01)**: can one developer
read another developer's submission by referencing its id?

A "developer" is identified by their API key. The test plays attacker
(developer B) against victim (developer A).

Reproduce:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 venv/bin/python -m pytest tests/test_history.py -v
```

## Attack: cross-developer object reference

| Step | Actor | Action | Expected | Result |
|------|-------|--------|----------|--------|
| 1 | Dev A | `POST /analyze` → gets `submission_id = S` | 200, owns `S` | ✅ |
| 2 | Dev B | `GET /history/S` (A's exact id, B's key) | **404** | ✅ Blocked |
| 3 | Dev B | `GET /history` | only B's own rows (not `S`) | ✅ Isolated |
| 4 | Dev A | `GET /history/S` (own id, own key) | 200, full report | ✅ Allowed |
| 5 | anyone | `GET /history` / `GET /history/S` with **no key** | 401 | ✅ |

Tests: `test_idor_cannot_read_other_developers_submission`,
`test_history_list_is_isolated_per_developer`, `test_history_requires_auth`,
`test_owner_can_list_and_load_own_submission`.

## Defense

Every history query is filtered by the caller's `api_key_id` (set on
`request.state` by `require_api_key`):

```python
# storage.get_submission
select(Submission).where(
    Submission.id == submission_id,
    Submission.api_key_id == api_key_id,   # ownership filter = IDOR defense
)
```

- **404, not 403** for a non-owner: we don't confirm that another developer's
  submission exists (no enumeration oracle).
- **Defense-in-depth**: ids are random `uuid4` hex, not sequential integers, so
  they can't be guessed by incrementing. But unguessability is *secondary* — the
  ownership filter is authoritative and holds even if an id leaks (e.g. via logs
  or a shared link).

## Data-handling check (related finding)

While testing history we also assert the submitted **source code is never
persisted** (`test_submitted_code_is_not_persisted`): a marker string in the
submission appears in neither the `submissions` row nor the `audit_log`. Storing
proprietary source would itself be the most serious data-handling issue for a
code-analysis tool.

## Residual risk / follow-ups
- API keys are bearer tokens — a leaked key grants access to that developer's
  history. Mitigated by one-time display + revocation (`active` flag); rotation
  UI is a follow-up.
- No org/team sharing yet; history is strictly per-key. Multi-user orgs would
  need a tenant model with the same ownership-filter pattern at the tenant level.
