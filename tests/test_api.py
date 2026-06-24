"""Week 2 API test suite.

Covers every gate added during the week: API-key auth, input validation,
language enum, rate limiting, and clean error envelopes. The agent graph is
stubbed so valid submissions never call Azure.
"""

import pytest
from fastapi.testclient import TestClient

import auth
import main

# raise_server_exceptions=False so the 500 handler returns JSON in tests too.
client = TestClient(main.app, raise_server_exceptions=False)

VALID_BODY = {"code": "print('hello')", "language": "python"}


class FakeGraph:
    """Stand-in for the LangGraph agent — returns a canned result, no network."""

    def invoke(self, state):
        return {
            "report_findings": [],
            "analysis": "stubbed analysis",
            "score": {
                "score": 90,
                "grade": "A",
                "summary": "stub",
                "counts": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
            },
        }


@pytest.fixture
def api_key():
    return auth.create_api_key("test")


def _assert_clean_error(resp):
    """Error responses must be structured JSON with no leaked internals."""
    body = resp.json()
    assert "error" in body
    assert {"code", "message", "request_id"} <= body["error"].keys()
    blob = resp.text.lower()
    for leak in ("traceback", "/home/", "openai.azure.com", ".py\", line"):
        assert leak not in blob


def test_valid_submission(monkeypatch, api_key):
    monkeypatch.setattr(main, "graph", FakeGraph())
    resp = client.post("/analyze", json=VALID_BODY, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    assert resp.json()["score"]["grade"] == "A"


def test_missing_api_key():
    resp = client.post("/analyze", json=VALID_BODY)
    assert resp.status_code == 401
    _assert_clean_error(resp)


def test_invalid_api_key():
    resp = client.post("/analyze", json=VALID_BODY, headers={"X-API-Key": "sg_bogus"})
    assert resp.status_code == 401
    _assert_clean_error(resp)


def test_oversized_code(api_key):
    body = {"code": "a" * 10_001, "language": "python"}
    resp = client.post("/analyze", json=body, headers={"X-API-Key": api_key})
    assert resp.status_code == 422
    _assert_clean_error(resp)


def test_invalid_language(api_key):
    body = {"code": "print('x')", "language": "cobol"}
    resp = client.post("/analyze", json=body, headers={"X-API-Key": api_key})
    assert resp.status_code == 422
    _assert_clean_error(resp)


def test_null_bytes_rejected(api_key):
    body = {"code": "print('x')\x00", "language": "python"}
    resp = client.post("/analyze", json=body, headers={"X-API-Key": api_key})
    assert resp.status_code == 422
    _assert_clean_error(resp)


def test_rate_limit_breach(monkeypatch):
    monkeypatch.setattr(main, "graph", FakeGraph())
    key = auth.create_api_key("rate-limit")  # fresh key = fresh 20/hour budget
    headers = {"X-API-Key": key}

    for _ in range(20):
        ok = client.post("/analyze", json=VALID_BODY, headers=headers)
        assert ok.status_code == 200

    breached = client.post("/analyze", json=VALID_BODY, headers=headers)
    assert breached.status_code == 429
    _assert_clean_error(breached)
