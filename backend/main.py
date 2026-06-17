from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from agent import graph, NODE_LABELS, NODE_ORDER, next_node


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:8501",
        "https://secureguard-frontend-vatsal.jollymoss-217b23fc.eastus.azurecontainerapps.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str


@app.post("/analyze")
def analyze(req: CodeRequest):
    """Run the full agent graph and return the final state."""
    state = graph.invoke({"code": req.code})
    return {
        "result": state["findings"],
        "score": state["score"],
        "analysis": state["analysis"],
    }


def _sse(event: dict) -> str:
    """Serialize an event as a Server-Sent Events frame."""
    return f"data: {json.dumps(event)}\n\n"


@app.post("/analyze/stream")
def analyze_stream(req: CodeRequest):
    """Drive the LangGraph agent and stream node steps + LLM tokens over SSE."""

    def event_generator():
        try:
            # Kick off the first node as "running".
            first = NODE_ORDER[0]
            yield _sse({
                "type": "step",
                "id": first,
                "status": "running",
                "label": NODE_LABELS[first],
            })

            # stream_mode "updates" gives per-node results; "messages" gives
            # LLM token chunks (tagged with the node that produced them).
            for mode, data in graph.stream(
                {"code": req.code},
                stream_mode=["updates", "messages"],
            ):
                if mode == "messages":
                    message, metadata = data
                    # Only stream tokens from the analysis node to the UI.
                    if metadata.get("langgraph_node") == "analyze" and message.content:
                        yield _sse({"type": "token", "data": message.content})

                elif mode == "updates":
                    for node, update in data.items():
                        if node not in NODE_LABELS:
                            continue

                        # This node just finished.
                        yield _sse({
                            "type": "step",
                            "id": node,
                            "status": "done",
                            "label": NODE_LABELS[node],
                        })

                        if node == "scan":
                            yield _sse({"type": "result", "data": update["findings"]})
                        elif node == "score":
                            yield _sse({"type": "score", "data": update["score"]})

                        # Mark the next node as "running".
                        nxt = next_node(node)
                        if nxt:
                            yield _sse({
                                "type": "step",
                                "id": nxt,
                                "status": "running",
                                "label": NODE_LABELS[nxt],
                            })

            yield _sse({"type": "done"})
        except Exception as e:
            yield _sse({"type": "error", "data": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
