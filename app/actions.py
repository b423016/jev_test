from __future__ import annotations

from datetime import datetime


def build_actions(document_type: str, findings: list[dict]) -> tuple[str, dict | None]:
    questions = [row["question"] for row in findings if row.get("question")]
    if questions:
        lines = ["Hi,", ""] + [f"- {question}" for question in questions] + ["", "Thanks"]
        draft = "\n".join(lines)
    else:
        draft = ""
    dated = [row for row in findings if row.get("date")]
    reminder = None
    if dated:
        chosen = _earliest(dated)
        reminder = {
            "title": f"{document_type} date from the document",
            "date": chosen["date"],
            "details": chosen.get("explanation") or chosen["text"],
        }
    return draft, reminder


def _earliest(rows: list[dict]) -> dict:
    def key(row: dict):
        parsed = _parse_date(row["date"])
        return parsed or datetime.max

    return min(rows, key=key)


def _parse_date(value: str):
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
