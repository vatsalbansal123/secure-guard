# SecureGuard

AI-powered code security scanner. SecureGuard runs your code through a
[LangGraph](https://langchain-ai.github.io/langgraph/) agent that combines a
deterministic OWASP rule engine with LLM analysis, then streams the results to a
React UI in real time.

## How it works

The agent runs a three-node pipeline, and each step is streamed to the frontend
over Server-Sent Events (SSE):

1. **Scan** — a deterministic pattern scanner matches the code against OWASP
   rules (`backend/rules/owasp_rules.json`).
2. **Analyze** — an LLM (Azure OpenAI) reviews the code and findings, producing
   vulnerabilities, severities, explanations, and remediation. Tokens stream
   live to the UI.
3. **Score** — the LLM assigns a strict security score (0–100) and letter grade,
   combined with rule-engine severity counts.

## Tech stack

- **Backend:** FastAPI, LangGraph, LangChain, Azure OpenAI, Pydantic
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

| Variable                     | Description                                  |
| ---------------------------- | -------------------------------------------- |
| `GEMINI_API_KEY`             | Google Gemini API key                        |
| `AZURE_OPENAI_API_KEY`       | Azure OpenAI API key                         |
| `AZURE_OPENAI_ENDPOINT`      | Azure OpenAI endpoint URL                    |
| `AZURE_OPENAI_API_VERSION`   | API version (default `2024-12-01-preview`)   |
| `AZURE_OPENAI_DEPLOYMENT`    | Deployment / model name (default `gpt-5-mini`) |

> **Never commit `.env`.** It is git-ignored by default.

### 2. Run with Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:8501
- Backend API: http://localhost:8000

### 3. Run locally (without Docker)

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

| Endpoint           | Method | Description                                          |
| ------------------ | ------ | ---------------------------------------------------- |
| `/analyze`         | POST   | Runs the full pipeline and returns the final result. |
| `/analyze/stream`  | POST   | Streams steps, LLM tokens, findings, and score via SSE. |

**Request body:**

```json
{ "code": "your source code here" }
```

## Project structure

```
secure-guard/
├── backend/
│   ├── main.py              # FastAPI app + SSE streaming endpoints
│   ├── agent.py             # LangGraph agent (scan → analyze → score)
│   ├── rule_checker.py      # OWASP pattern scanner + scoring
│   └── rules/owasp_rules.json
├── frontend/                # React + Vite UI
├── docker-compose.yml
└── requirements.txt
```
