"""Week 5 history + IDOR + audit-logging tests.

Two developers (= two API keys). The whole point of the suite is the access
boundary between them: developer A must never be able to read developer B's
submissions by guessing an id, and the persisted data must never contain the
submitted source code.

The agent graph is stubbed so no Azure call is made.
"""

import json

import pytest
from fastapi.testclient import TestClient

import auth
import main
import storage
from storage import AuditLog, Submission, engine
from sqlalchemy import select
from sqlalchemy.orm import Session

client = TestClient(main.app, raise_server_exceptions=False)

# A marker we can search for to prove the raw code is never persisted.
SECRET_CODE = "TOP_SECRET_PROPRIETARY_abc123 = 'do not store me'"
VALID_BODY = {"code": SECRET_CODE, "language": "python"}


class FakeGraph:
    """Canned result, independent of the submitted code (so any code-leak in the
    store would have to come from persistence, not from the stub echoing input)."""

    def invoke(self, state):
        return {
            "report_findings": [
                {
                    "rule_id": "OWASP-A03", "name": "Injection", "severity": "High",
                    "status": "confirmed", "confidence": 0.9, "description": "demo",
                    "fix": None,
                }
            ],
            "analysis": "stubbed analysis",
            "score": {
                "score": 70, "grade": "C", "summary": "stub",
                "counts": {"Critical": 0, "High": 1, "Medium": 0, "Low": 0},
            },
        }


@pytest.fixture(autouse=True)
def stub_graph(monkeypatch):
    monkeypatch.setattr(main, "graph", FakeGraph())


@pytest.fixture
def dev_a():
    return auth.create_api_key("dev-a")


@pytest.fixture
def dev_b():
    return auth.create_api_key("dev-b")


def _submit(key):
    resp = client.post("/analyze", json=VALID_BODY, headers={"X-API-Key": key})
    assert resp.status_code == 200, resp.text
    return resp.json()["submission_id"]


# ---- basic plumbing ----

def test_analyze_returns_submission_id(dev_a):
    sid = _submit(dev_a)
    assert sid and isinstance(sid, str)


def test_owner_can_list_and_load_own_submission(dev_a):
    sid = _submit(dev_a)

    listed = client.get("/history", headers={"X-API-Key": dev_a})
    assert listed.status_code == 200
    ids = [row["id"] for row in listed.json()["history"]]
    assert sid in ids
    # Summary carries metadata, not the full report.
    row = next(r for r in listed.json()["history"] if r["id"] == sid)
    assert row["finding_count"] == 1
    assert row["severity_counts"]["High"] == 1

    detail = client.get(f"/history/{sid}", headers={"X-API-Key": dev_a})
    assert detail.status_code == 200
    assert detail.json()["result"][0]["rule_id"] == "OWASP-A03"


# ---- IDOR: the core Week 5 security test ----

def test_idor_cannot_read_other_developers_submission(dev_a, dev_b):
    """Developer A submits; developer B must not be able to fetch it by id."""
    sid = _submit(dev_a)

    # B knows/guesses A's exact submission id and asks for it.
    resp = client.get(f"/history/{sid}", headers={"X-API-Key": dev_b})
    # 404, not 403 — B is never even told the submission exists.
    assert resp.status_code == 404


def test_history_list_is_isolated_per_developer(dev_a, dev_b):
    a_sid = _submit(dev_a)
    b_sid = _submit(dev_b)

    a_ids = [r["id"] for r in client.get("/history", headers={"X-API-Key": dev_a}).json()["history"]]
    b_ids = [r["id"] for r in client.get("/history", headers={"X-API-Key": dev_b}).json()["history"]]

    assert a_sid in a_ids and a_sid not in b_ids
    assert b_sid in b_ids and b_sid not in a_ids


def test_history_requires_auth():
    assert client.get("/history").status_code == 401
    assert client.get("/history/anything").status_code == 401


# ---- data handling: code is never persisted ----

def test_submitted_code_is_not_persisted(dev_a):
    """The submitted source must not appear in the submission row or audit log."""
    sid = _submit(dev_a)

    with Session(engine) as session:
        sub = session.scalar(select(Submission).where(Submission.id == sid))
        assert sub is not None
        # No `code` attribute exists on the model, and the marker appears nowhere
        # in the serialized row.
        assert not hasattr(sub, "code")
        blob = json.dumps({
            "report": sub.report, "score": sub.score, "analysis": sub.analysis,
            "language": sub.language, "severity_counts": sub.severity_counts,
        })
        assert "TOP_SECRET_PROPRIETARY" not in blob

        audit_rows = session.scalars(select(AuditLog)).all()
        audit_blob = json.dumps([
            {"action": a.action, "api_key_id": a.api_key_id, "submission_id": a.submission_id}
            for a in audit_rows
        ])
        assert "TOP_SECRET_PROPRIETARY" not in audit_blob


def test_audit_trail_records_events(dev_a):
    sid = _submit(dev_a)
    client.get(f"/history/{sid}", headers={"X-API-Key": dev_a})
    client.get("/history", headers={"X-API-Key": dev_a})

    with Session(engine) as session:
        actions = [a.action for a in session.scalars(select(AuditLog)).all()]

    # Key creation, the submission, the report read, and the list are all logged.
    assert storage.KEY_CREATED in actions
    assert storage.SUBMISSION_CREATED in actions
    assert storage.REPORT_RETRIEVED in actions
    assert storage.HISTORY_LISTED in actions
