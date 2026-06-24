# Week 2 — Auth & Hardening

Objective: developers authenticate with an API key (OpenAI / Snyk / Stripe
model) and the open scaffold is hardened against the Week 1 findings.

## What shipped

| Day | Control | Where | Result |
|-----|---------|-------|--------|
| Mon | API-key auth | `backend/auth.py`, `backend/create_key.py` | `secrets.token_urlsafe(32)`, SHA-256 hashed in SQLite, validated by a FastAPI dependency on every route. `401` if missing/invalid. |
| Tue | Input validation | `backend/models.py` | `code` capped at 10,000 chars, must be a non-empty string, null bytes + binary content rejected → `422`. Output tokens capped (`max_tokens`). |
| Wed | Language enum | `backend/models.py`, `backend/agent.py` | `language` is a strict `Enum`; unknown values → `422`. Threaded into the prompts. |
| Thu | Rate limiting | `backend/main.py` | `slowapi` 20 requests/hour **per API key** (not IP) → `429`. |
| Fri | Error handling | `backend/main.py` | One JSON envelope `{error:{code,message,request_id}}`. No stack traces, paths, or Azure endpoint in any response; full detail logged server-side only. |
| Wknd | Test suite | `tests/test_api.py` | 7 tests: valid, oversized, missing key, invalid key, invalid language, null bytes, rate-limit breach. All passing. |

## Auth model: why API keys (not JWT)

API keys suit a **developer tool** called from scripts/CI — the client *is* the
credential, long-lived, no login session. JWTs suit **user sessions** (issued
after login, short-lived, carry claims). Keys are high-entropy, so a fast
**SHA-256** hash is correct for storage — bcrypt/argon2 are for low-entropy
passwords.

## How to use

```bash
# create a key (printed once)
cd backend && python create_key.py "my dev key"

# call the API
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: sg_..." -H "Content-Type: application/json" \
  -d '{"code":"print(1)","language":"python"}'
```

## Running the tests

The project venv is polluted with system ROS packages, whose pytest plugins
crash collection. Either use a clean venv (recommended) or disable plugin
autoload:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_api.py -v
```

## Status mapping (vs INSECURE_DEFAULTS)

Fixed this week: #1 CORS, #2 input limit, #3 auth, #4 rate limit, #5 prompt
injection, #7 error leakage. Still open: #6 hardcoded config (Week 3).

## Follow-ups
- Run `snyk code test` (SAST) on the new auth/rate-limit code (Thu task).
- Move remaining hardcoded values (origins, DB settings) to env vars (#6).
- The frontend now sends `X-API-Key` + `language`; keys are stored in
  `localStorage` (fine for a dev tool, revisit if multi-user).