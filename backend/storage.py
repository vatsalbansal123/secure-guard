"""Analysis history + audit logging (Week 5).

Two stores, one deliberate data-handling rule that runs through both:

    We persist analysis RESULTS, never the raw submitted source code.

A developer tool handles proprietary code. Storing the submitted snippet would
make SecureGuard itself a data-exfiltration risk — no company would paste their
source into a tool that keeps it. So:

- `Submission` keeps the *report* (findings, fixes, score, summary) plus
  metadata (language, counts, timestamp) — enough to redisplay history — but
  NOT the `code` field that was analyzed.
- `AuditLog` records that an event happened (who, when, what, which submission),
  never its content. It is a security event trail, not a copy of the data.

Ownership: a "developer" is identified by their API key (`api_keys.id`). Every
submission is scoped to the key that created it, and every read is filtered by
that owner id — this is the IDOR defense (see WEEK5_DASHBOARD.md).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

# Reuse the single SQLite store + declarative base defined for API keys.
from auth import Base, engine

logger = logging.getLogger("secureguard.audit")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Submission(Base):
    """One analysis run. Stores the produced report, never the submitted code."""

    __tablename__ = "submissions"

    # Random opaque id (defense-in-depth against ID guessing); the ownership
    # check below is the real IDOR protection, not the unguessability.
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # Owner = the API key that submitted it. Every read filters on this.
    api_key_id: Mapped[int] = mapped_column(
        ForeignKey("api_keys.id"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    language: Mapped[str] = mapped_column(String(16))
    finding_count: Mapped[int] = mapped_column(Integer, default=0)
    # {"Critical": n, "High": n, "Medium": n, "Low": n}
    severity_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    # The full report objects (findings + fixes), the score dict, and the
    # human summary — i.e. tool OUTPUT. The submitted source is NOT stored.
    score: Mapped[dict] = mapped_column(JSON, default=dict)
    analysis: Mapped[str] = mapped_column(Text, default="")
    report: Mapped[list] = mapped_column(JSON, default=list)


class AuditLog(Base):
    """Security event trail. Records that something happened, not what was in it."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    action: Mapped[str] = mapped_column(String(32))
    submission_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


# Idempotent: only creates the new tables, leaves api_keys untouched.
Base.metadata.create_all(engine)


# ---- Audit logging ----

# Allow-listed actions, so a typo can't silently create a new audit category.
KEY_CREATED = "key_created"
SUBMISSION_CREATED = "submission_created"
REPORT_RETRIEVED = "report_retrieved"
HISTORY_LISTED = "history_listed"


def log_event(action: str, api_key_id: Optional[int], submission_id: Optional[str] = None) -> None:
    """Append an audit row and emit a structured log line.

    Deliberately takes no code/report argument — there is no path by which the
    submitted source can reach the audit trail.
    """
    try:
        with Session(engine) as session:
            session.add(
                AuditLog(action=action, api_key_id=api_key_id, submission_id=submission_id)
            )
            session.commit()
    except Exception:
        # Auditing must never break the request it is recording.
        logger.exception("failed to write audit row for action=%s", action)
    logger.info(
        "audit action=%s key_id=%s submission_id=%s", action, api_key_id, submission_id
    )


# ---- Submission persistence ----

def save_submission(
    api_key_id: int,
    language: str,
    report: list,
    score: dict,
    analysis: str,
) -> str:
    """Persist an analysis result (no source code) and return its id."""
    submission_id = uuid.uuid4().hex
    counts = (score or {}).get("counts", {}) or {}
    with Session(engine) as session:
        session.add(
            Submission(
                id=submission_id,
                api_key_id=api_key_id,
                language=language,
                finding_count=len(report or []),
                severity_counts=counts,
                score=score or {},
                analysis=analysis or "",
                report=report or [],
            )
        )
        session.commit()
    log_event(SUBMISSION_CREATED, api_key_id, submission_id)
    return submission_id


def list_submissions(api_key_id: int) -> list[dict]:
    """Summaries of the caller's own submissions, newest first.

    Scoped to `api_key_id` — a caller can only ever see their own rows.
    """
    with Session(engine) as session:
        rows = session.scalars(
            select(Submission)
            .where(Submission.api_key_id == api_key_id)
            .order_by(Submission.created_at.desc())
        ).all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "language": r.language,
            "finding_count": r.finding_count,
            "severity_counts": r.severity_counts,
            "score": (r.score or {}).get("score"),
            "grade": (r.score or {}).get("grade"),
        }
        for r in rows
    ]


def get_submission(api_key_id: int, submission_id: str) -> Optional[dict]:
    """Full report for one submission — only if owned by the caller.

    The `api_key_id` filter is the IDOR defense: requesting another developer's
    submission id returns None (the endpoint maps that to 404), so existence is
    never confirmed to a non-owner.
    """
    with Session(engine) as session:
        row = session.scalar(
            select(Submission).where(
                Submission.id == submission_id,
                Submission.api_key_id == api_key_id,
            )
        )
    if row is None:
        return None
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat(),
        "language": row.language,
        "finding_count": row.finding_count,
        "severity_counts": row.severity_counts,
        "score": row.score,
        "analysis": row.analysis,
        "result": row.report,
    }
