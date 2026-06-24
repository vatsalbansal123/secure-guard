import json
import logging
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from agent import graph, NODE_LABELS, NODE_ORDER
from auth import require_api_key
from models import CodeRequest
from storage import (
    REPORT_RETRIEVED,
    HISTORY_LISTED,
    get_submission,
    list_submissions,
    log_event,
    save_submission,
)


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("secureguard")

app = FastAPI()


# ---- Rate limiting (Thu) ----
# Key by the caller's API key (set on request.state by require_api_key), not by
# IP — IPs are shared/spoofable. Falls back to IP if no key is present.
def rate_limit_key(request: Request) -> str:
    return getattr(request.state, "api_key_hash", None) or get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key)
app.state.limiter = limiter


# ---- CORS (tightened) ----
# Methods/headers narrowed from "*" to exactly what the app uses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:8501",
        "https://secureguard-frontend-vatsal.jollymoss-217b23fc.eastus.azurecontainerapps.io",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ---- Structured error handling (Fri) ----
# Every failure returns the same JSON envelope. Internal detail (stack traces,
# paths, the Azure endpoint) is logged server-side and never sent to the client.
def error_response(status_code: int, code: str, message: str, request_id: str | None = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id or str(uuid.uuid4()),
            }
        },
    )


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit(request: Request, exc: RateLimitExceeded):
    return error_response(429, "rate_limit_exceeded", "Rate limit exceeded. Try again later.")


@app.exception_handler(RequestValidationError)
async def handle_validation(request: Request, exc: RequestValidationError):
    # Report which field failed and why, without echoing the submitted values.
    details = "; ".join(
        f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}"
        for e in exc.errors()
    )
    return error_response(422, "invalid_request", f"Request validation failed: {details}")


@app.exception_handler(HTTPException)
async def handle_http(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return error_response(exc.status_code, "request_error", message)


@app.exception_handler(Exception)
async def handle_unhandled(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    # Full detail to the logs only.
    logger.exception("Unhandled error (request_id=%s)", request_id)
    return error_response(500, "internal_error", "An internal error occurred.", request_id)


def _sse(event: dict) -> str:
    """Serialize an event as a Server-Sent Events frame."""
    return f"data: {json.dumps(event)}\n\n"


@app.post("/analyze")
@limiter.limit("20/hour")
def analyze(request: Request, req: CodeRequest, _key: str = Depends(require_api_key)):
    """Run the full agent graph, persist the RESULT (not the code), and return it."""
    state = graph.invoke({"code": req.code, "language": req.language.value})
    # Persist results only — the submitted source is never stored (see storage.py).
    submission_id = save_submission(
        api_key_id=request.state.api_key_id,
        language=req.language.value,
        report=state["report_findings"],
        score=state["score"],
        analysis=state["analysis"],
    )
    return {
        "submission_id": submission_id,
        "result": state["report_findings"],
        "score": state["score"],
        "analysis": state["analysis"],
    }


@app.post("/analyze/stream")
@limiter.limit("20/hour")
def analyze_stream(request: Request, req: CodeRequest, _key: str = Depends(require_api_key)):
    """Drive the LangGraph agent and stream node steps + LLM tokens over SSE."""

    # Captured from the stream so the final result can be persisted (results
    # only — the submitted code is never stored).
    final = {"report": [], "score": {}, "analysis": ""}

    def event_generator():
        try:
            # The first node starts immediately.
            yield _sse({
                "type": "step", "id": "preprocess", "status": "running",
                "label": NODE_LABELS["preprocess"],
            })

            # "updates" gives per-node results as each node finishes. With the
            # parallel fan-out, analyzers complete in any order. A single string
            # stream_mode yields the update chunk directly (not a (mode, chunk)
            # tuple — that form is only used when stream_mode is a list).
            for data in graph.stream(
                {"code": req.code, "language": req.language.value},
                stream_mode="updates",
            ):
                for node, update in data.items():
                    if node not in NODE_LABELS:
                        continue

                    # This node just finished.
                    yield _sse({
                        "type": "step", "id": node, "status": "done",
                        "label": NODE_LABELS[node],
                    })

                    # Once preprocessing is done, all downstream nodes are pending.
                    if node == "preprocess":
                        for nxt in NODE_ORDER[1:]:
                            yield _sse({
                                "type": "step", "id": nxt, "status": "running",
                                "label": NODE_LABELS[nxt],
                            })
                    elif node == "synthesize":
                        # Surface the human summary to the LLM Analysis panel.
                        final["analysis"] = update.get("analysis", "")
                        yield _sse({"type": "token", "data": final["analysis"]})
                    elif node == "format":
                        final["score"] = update.get("score", {})
                        yield _sse({"type": "score", "data": final["score"]})
                    elif node == "suggest_fixes":
                        # Findings now carry verified fixes.
                        final["report"] = update.get("report_findings", [])
                        yield _sse({"type": "result", "data": final["report"]})

            # Persist the completed analysis and tell the client its id so it can
            # link to history (and remember the code locally for reanalyze).
            submission_id = save_submission(
                api_key_id=request.state.api_key_id,
                language=req.language.value,
                report=final["report"],
                score=final["score"],
                analysis=final["analysis"],
            )
            yield _sse({"type": "submission", "submission_id": submission_id})
            yield _sse({"type": "done"})
        except Exception:
            # Log full detail server-side; send the client a generic message.
            request_id = str(uuid.uuid4())
            logger.exception("Stream error (request_id=%s)", request_id)
            yield _sse({
                "type": "error",
                "data": "Analysis failed. Please try again.",
                "request_id": request_id,
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---- Analysis history (Week 5) ----
# Every query is scoped to request.state.api_key_id — the owning developer. A
# caller can only ever see their own submissions (IDOR defense, see
# WEEK5_DASHBOARD.md). Results are stored; the submitted code is not.

@app.get("/history")
@limiter.limit("60/hour")
def history(request: Request, _key: str = Depends(require_api_key)):
    """List the calling developer's own past submissions (metadata only)."""
    items = list_submissions(request.state.api_key_id)
    log_event(HISTORY_LISTED, request.state.api_key_id)
    return {"history": items}


@app.get("/history/{submission_id}")
@limiter.limit("60/hour")
def history_detail(
    request: Request, submission_id: str, _key: str = Depends(require_api_key)
):
    """Full stored report for one submission — only if the caller owns it.

    A non-owner (or unknown id) gets 404, never 403: we don't confirm that
    another developer's submission exists.
    """
    item = get_submission(request.state.api_key_id, submission_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    log_event(REPORT_RETRIEVED, request.state.api_key_id, submission_id)
    return item
