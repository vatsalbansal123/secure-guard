"""Multi-node LangGraph security analysis agent (v0.3).

Pipeline (parallel fan-out → fan-in):

  preprocess_input ──┬─→ injection_analyzer ─┐
                     ├─→ auth_analyzer ───────┤
                     ├─→ secrets_analyzer ────┼─→ synthesizer → format_output
                     └─→ dependency_analyzer ─┘

Each analyzer is a discrete LLM call with a focused prompt and a constrained
JSON output (see analyzers.py). The deterministic rule scan runs in preprocess
as a cross-check (OWASP LLM09: reduce overreliance on the model).
"""

import operator
import os
from typing import Annotated, List, TypedDict

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from analyzers import (
    ANALYZER_RULES,
    format_output_node,
    make_analyzer,
    make_synthesizer,
)
from fixer import make_suggest_fixes_node
from preprocess import preprocess
from rule_checker import scan_code

load_dotenv()

from langgraph.graph import END, START, StateGraph  # noqa: E402

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini"),
    max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
    # gpt-5-* are reasoning models: at default effort they burn seconds of hidden
    # reasoning on every call, and the fix node chains generate→check (±retry) per
    # finding. "low" keeps the analysis quality while cutting that latency sharply.
    # Override with LLM_REASONING_EFFORT (minimal|low|medium|high).
    reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "low"),
)


# Node ids/labels for the streaming UI, in display order.
NODE_LABELS = {
    "preprocess": "Preprocessing input (strip comments, extract imports)",
    "injection": "Analyzing injection & insecure design",
    "auth": "Analyzing access control & authentication",
    "secrets": "Analyzing secrets & cryptography",
    "dependency": "Analyzing dependencies",
    "synthesize": "Synthesizing findings",
    "format": "Formatting report",
    "suggest_fixes": "Generating & verifying fixes",
}
NODE_ORDER = ["preprocess", "injection", "auth", "secrets", "dependency", "synthesize", "format", "suggest_fixes"]


def next_node(node: str):
    """Return the node after `node` in display order, or None."""
    idx = NODE_ORDER.index(node)
    return NODE_ORDER[idx + 1] if idx + 1 < len(NODE_ORDER) else None


class AgentState(TypedDict):
    code: str
    language: str
    clean_code: str
    imports: List[str]
    comment_flags: List[str]
    # Parallel analyzers append here; operator.add concatenates their lists.
    findings: Annotated[List[dict], operator.add]
    deduped_findings: List[dict]
    analysis: str
    score: dict
    report_findings: List[dict]


# ---- Nodes ----

def preprocess_node(state: AgentState) -> dict:
    """Strip/flag comments, normalize, extract imports, run deterministic scan."""
    pre = preprocess(state["code"], state.get("language", "other"))
    # Deterministic findings double as a baseline; analyzers add the LLM layer.
    rule_findings = scan_code(pre["clean_code"])
    return {
        "clean_code": pre["clean_code"],
        "comment_flags": pre["comment_flags"],
        "imports": pre["imports"],
        "findings": [
            {**f, "confidence": 1.0, "analyzer": "rule_engine", "line_hint": None}
            for f in rule_findings
        ],
    }


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("preprocess", preprocess_node)
    g.add_node("injection", make_analyzer(llm, "injection", ANALYZER_RULES["injection"]))
    g.add_node("auth", make_analyzer(llm, "auth", ANALYZER_RULES["auth"]))
    g.add_node("secrets", make_analyzer(llm, "secrets", ANALYZER_RULES["secrets"]))
    g.add_node("dependency", make_analyzer(llm, "dependency", ANALYZER_RULES["dependency"]))
    g.add_node("synthesize", make_synthesizer(llm))
    g.add_node("format", format_output_node)
    g.add_node("suggest_fixes", make_suggest_fixes_node(llm))

    g.add_edge(START, "preprocess")
    for analyzer in ("injection", "auth", "secrets", "dependency"):
        g.add_edge("preprocess", analyzer)   # fan-out (run in parallel)
        g.add_edge(analyzer, "synthesize")   # fan-in (synthesize waits for all)
    g.add_edge("synthesize", "format")
    g.add_edge("format", "suggest_fixes")
    g.add_edge("suggest_fixes", END)
    return g.compile()


graph = build_graph()
