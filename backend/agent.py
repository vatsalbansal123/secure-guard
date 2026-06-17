"""LangGraph multi-node security analysis agent.

Pipeline: scan (OWASP rules) -> analyze (LLM) -> score (LLM, structured).
Each node is streamable so the API can surface step-by-step progress.
"""

import os

from typing import TypedDict, List

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from rule_checker import scan_code, count_by_severity, grade_for_score


# Load .env before instantiating the client (this module is imported first).
load_dotenv()

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini"),
)


# Ordered nodes and the human-readable label shown to the user per step.
NODE_LABELS = {
    "scan": "Scanning code with OWASP rule engine",
    "analyze": "Analyzing with AI security analyst",
    "score": "Scoring the code against OWASP risks",
}
NODE_ORDER = ["scan", "analyze", "score"]


def next_node(node: str):
    """Return the node that runs after `node`, or None if it's the last."""
    idx = NODE_ORDER.index(node)
    return NODE_ORDER[idx + 1] if idx + 1 < len(NODE_ORDER) else None


class AgentState(TypedDict):
    code: str
    findings: List[dict]
    analysis: str
    score: dict


class ScoreVerdict(BaseModel):
    """Structured security score assigned by the LLM."""

    score: int = Field(
        description="Overall security score from 0 (insecure) to 100 (secure)."
    )
    summary: str = Field(
        description="One short paragraph justifying the score."
    )


# ---- Nodes ----

def scan_node(state: AgentState) -> dict:
    """Run the deterministic OWASP pattern scanner."""
    return {"findings": scan_code(state["code"])}


def analyze_node(state: AgentState) -> dict:
    """Have the LLM analyze the code; tokens stream from this node."""
    prompt = f"""
    You are a security analyst.

    OWASP Findings:
    {state["findings"]}

    Analyze the code below.

    Code:
    {state["code"]}

    Provide:
    1. Vulnerabilities
    2. Severity
    3. Explanation
    4. Remediation
    """
    response = llm.invoke(
        [
            SystemMessage(content="You are a security analyst."),
            HumanMessage(content=prompt),
        ]
    )
    return {"analysis": response.content}


def score_node(state: AgentState) -> dict:
    """Have the LLM assign a security score, combined with rule-engine counts."""
    prompt = f"""
    You are a security analyst assigning an overall security score.

    Consider the OWASP rule findings, the code, and the analysis below.
    Score from 0 (critically insecure) to 100 (secure). Be strict:
    Critical issues should pull the score well below 50.

    OWASP Findings:
    {state["findings"]}

    Code:
    {state["code"]}

    Analysis:
    {state["analysis"]}
    """
    verdict = llm.with_structured_output(ScoreVerdict).invoke(
        [
            SystemMessage(content="You assign strict security scores."),
            HumanMessage(content=prompt),
        ]
    )
    bounded = max(0, min(100, verdict.score))
    return {
        "score": {
            "score": bounded,
            "grade": grade_for_score(bounded),
            "summary": verdict.summary,
            "counts": count_by_severity(state["findings"]),
        }
    }


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("scan", scan_node)
    g.add_node("analyze", analyze_node)
    g.add_node("score", score_node)
    g.add_edge(START, "scan")
    g.add_edge("scan", "analyze")
    g.add_edge("analyze", "score")
    g.add_edge("score", END)
    return g.compile()


graph = build_graph()
