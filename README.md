# SecureGuard

AI-powered code security scanner. SecureGuard runs your code through a
[LangGraph](https://langchain-ai.github.io/langgraph/) agent that combines a
deterministic OWASP rule engine with focused LLM analyzers, suggests verified
fixes, and streams the results to a React UI in real time.

## How it works

The agent runs a multi-node pipeline. Each step is streamed to the frontend over
Server-Sent Events (SSE):

1. **Preprocess** — before any LLM call, the code is normalized: comments are
   stripped/flagged (a prime prompt-injection vector), zero-width and control
   characters are removed, and imports are extracted for the dependency
   analyzer. This closes a class of OWASP LLM01 (prompt injection) attacks at
   the door.
2. **Analyze (parallel)** — four specialized LLM analyzers run concurrently,
   each with a narrow prompt and a constrained JSON schema: **injection**,
   **auth**, **secrets**, and **dependency**. Each only sees its slice of the
   OWASP rules. Malformed output fails closed; low-confidence findings are
   flagged `needs_review` rather than asserted.
3. **Synthesize & format** — findings are merged, de-duplicated, and combined
   with the deterministic rule-engine matches into a single report with
   severities, explanations, and a security score (0–100) and letter grade.
4. **Suggest fixes** — for each confirmed finding an LLM generates a corrected
   snippet plus a teaching explanation. A second LLM acts as a checker
   (LLM-as-judge): if the fix doesn't address the issue or introduces a new one,
   a conditional edge routes it back for one revision. A confidence score is
   surfaced so developers know how much to trust each fix (OWASP LLM09
   mitigation).

Analysis **results** are persisted to history — the raw submitted source code is
never stored, so SecureGuard itself isn't a data-exfiltration risk.

## Security model

- **API-key auth.** Every endpoint requires an `X-API-Key` header. Keys are
  high-entropy random tokens stored only as a SHA-256 hash and shown once at
  creation. Mint one with `python backend/create_key.py "my key"`.
- **Rate limiting** on all endpoints.
- **Input validation** — submitted code is capped (10k chars) to bound token
  cost and latency (OWASP LLM10).
- **No raw-code persistence** — only reports and an audit-event trail are kept.

## Tech stack

- **Backend:** FastAPI, LangGraph, LangChain, Azure OpenAI, Pydantic, SQLAlchemy
- **Frontend:** React + Vite
- **Deployment:** Docker / Docker Compose (Nginx-served frontend)

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Azure OpenAI deployment (or compatible endpoint)

### 1. Configure environment

Copy the example file and fill in your own credentials:

```bash
cp .env.example .env
```

| Variable                     | Description                                          |
| ---------------------------- | ---------------------------------------------------- |
| `GEMINI_API_KEY`             | Google Gemini API key                                |
| `AZURE_OPENAI_API_KEY`       | Azure OpenAI API key                                 |
| `AZURE_OPENAI_ENDPOINT`      | Azure OpenAI endpoint URL                            |
| `AZURE_OPENAI_API_VERSION`   | API version (default `2024-12-01-preview`)           |
| `AZURE_OPENAI_DEPLOYMENT`    | Deployment / model name (default `gpt-5-mini`)       |
| `LLM_MAX_TOKENS`             | Completion-token budget (default `8192`)             |
| `LLM_REASONING_EFFORT`       | `minimal`/`low`/`medium`/`high` for gpt-5-* (default `low`) |
| `DB_SERVER` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Optional external SQL DB connection |

> **Never commit `.env`.** It is git-ignored by default.

### 2. Mint an API key

The API requires an `X-API-Key` header. Create a key (the plaintext is printed
once — store it now):

```bash
cd backend
python create_key.py "my dev key"
```

### 3. Run with Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:8501
- Backend API: http://localhost:8000

### 4. Run locally (without Docker)

**Backend:**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## API

All endpoints require an `X-API-Key: <key>` header.

| Endpoint                   | Method | Description                                              |
| -------------------------- | ------ | -------------------------------------------------------- |
| `/analyze`                 | POST   | Runs the full pipeline and returns the final result.     |
| `/analyze/stream`          | POST   | Streams steps, LLM tokens, findings, fixes, and score via SSE. |
| `/history`                 | GET    | Lists past analysis reports for the calling key.         |
| `/history/{submission_id}` | GET    | Returns a single stored report.                          |

**Request body** (`/analyze`, `/analyze/stream`):

```json
{ "code": "your source code here" }
```

## Project structure

```
secure-guard/
├── backend/
│   ├── main.py            # FastAPI app: auth, rate limiting, SSE endpoints, history
│   ├── agent.py           # LangGraph agent (preprocess → analyzers → synthesize → fixes)
│   ├── preprocess.py      # Pre-LLM normalization + prompt-injection defenses
│   ├── analyzers.py       # Specialized analyzer nodes + synthesis
│   ├── fixer.py           # Fix generation + LLM-as-judge checker (Fix Engine)
│   ├── auth.py            # API-key auth (SHA-256 hashed keys)
│   ├── create_key.py      # CLI to mint an API key
│   ├── storage.py         # Analysis history + audit logging (no raw code stored)
│   ├── models.py          # Request models + input validation
│   ├── database/main.py   # Optional external SQL DB engine (env-configured)
│   └── rules/owasp_rules.json
├── frontend/              # React + Vite UI (editor, finding cards, history, dashboard)
├── tests/                 # API, history, injection-attack, and golden-set tests
├── docs/                  # Threat model, audits, weekly hardening notes
├── docker-compose.yml
└── requirements.txt
```
