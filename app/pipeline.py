from __future__ import annotations

import logging

from app.actions import build_actions
from app.cache import ScreenCache
from app.config import Settings
from app.explain import ExplainError, explain_lit
from app.paragraphs import split_paragraphs
from app.playbook import Playbook
from app.screen import ScreenError, score_document

log = logging.getLogger("jev")


class ScanRejected(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def run_scan(
    settings: Settings,
    document_type: str,
    text: str,
    content_hash: str,
    cache: ScreenCache,
    playbook: Playbook,
    emit=None,
) -> dict:
    _emit(emit, "split", "run", "Cutting the text into paragraphs.")
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        raise ScanRejected("Nothing to read.", 400)
    if len(text) > settings.max_chars or len(paragraphs) > settings.max_paragraphs:
        raise ScanRejected(
            "This document is too long for one pass. Split it and upload the part you are about to sign.",
            413,
        )
    _emit(emit, "split", "done", f"{len(paragraphs)} paragraphs.")

    _emit(emit, "jev", "run", "Scoring every paragraph.")
    screen = cache.get(content_hash, document_type)
    cached = screen is not None
    if screen is None:
        screen = score_document(settings, document_type, paragraphs)
        cache.put(content_hash, document_type, screen)

    by_index = {row["index"]: row for row in screen["rows"]}
    findings = []
    for index, paragraph in enumerate(paragraphs):
        row = by_index.get(index)
        if row is None:
            findings.append(_unscored(index, paragraph))
            continue
        score = float(row["score"])
        lit = score >= settings.threshold
        clause = row["clause_type"] if lit else "none"
        findings.append(
            {
                "index": index,
                "text": paragraph,
                "score": round(score, 4),
                "lit": lit,
                "scored": True,
                "clause_type": clause,
                "explanation": "",
                "figure": "",
                "question": "",
                "date": "",
            }
        )

    lit_count = sum(1 for row in findings if row["lit"])
    _emit(emit, "jev", "done", f"{lit_count} lit." + (" Cached." if cached else ""))

    status = "complete"
    clause_types = {row["clause_type"] for row in findings if row["lit"]}
    _emit(emit, "playbook", "run", "Loading the clause cards.")
    cards = playbook.lookup(document_type, clause_types)
    _emit(emit, "playbook", "done", f"{len(cards)} cards.")

    _emit(emit, "explain", "run", "Writing notes for the lit paragraphs.")
    try:
        findings = explain_lit(settings, findings, cards)
        _emit(emit, "explain", "done", "Notes are in.")
    except ExplainError:
        status = "partial"
        _emit(emit, "explain", "fail", "The notes did not come back.")
        log.warning("explain failed doc=%s", content_hash[:12])

    draft, reminder = build_actions(document_type, findings)
    question_count = sum(1 for row in findings if row.get("question"))
    _emit(emit, "draft", "done", f"{question_count} questions.")
    detected = screen.get("kind") or "other"
    log.info(
        "scan doc=%s door=%s paragraphs=%s lit=%s cached=%s status=%s",
        content_hash[:12],
        document_type,
        len(findings),
        sum(1 for row in findings if row["lit"]),
        cached,
        status,
    )
    return {
        "document_sha256": content_hash,
        "document_type": document_type,
        "detected_type": detected,
        "mismatch": detected not in (document_type, "other"),
        "status": status,
        "cached": cached,
        "findings": findings,
        "draft": draft,
        "reminder": reminder,
    }


def _emit(emit, step_id: str, state: str, detail: str) -> None:
    if emit:
        emit(step_id, state, detail)


def _unscored(index: int, paragraph: str) -> dict:
    return {
        "index": index,
        "text": paragraph,
        "score": None,
        "lit": True,
        "scored": False,
        "clause_type": "none",
        "explanation": "",
        "figure": "",
        "question": "",
        "date": "",
    }
