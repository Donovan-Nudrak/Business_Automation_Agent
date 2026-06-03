import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.models.decision import Decision


def generate_json(decision: Decision) -> bytes:
    payload: dict[str, Any] = build_report_payload(decision)
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def build_report_payload(decision: Decision) -> dict[str, Any]:
    return {
        "event_id": str(decision.event_id),
        "priority": decision.priority,
        "classification": decision.classification,
        "summary": decision.summary,
        "recommendations": decision.recommendations,
        "rule_triggered": decision.rule_triggered,
        "created_at": decision.created_at.isoformat()
        if decision.created_at
        else datetime.now(UTC).isoformat(),
    }


def generate_object_key(event_id: uuid.UUID, report_type: str = "pdf") -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    extension = "pdf" if report_type == "pdf" else "json"
    return f"reports/{event_id}/{report_type}_{timestamp}.{extension}"


# Backward-compatible alias used internally before PDF support.
generate_report = generate_json
