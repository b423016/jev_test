from __future__ import annotations

import time

import httpx

from app.catalog import BITE_FALSE, BITE_TRUE, clause_criteria, door_names
from app.config import Settings

TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"


class ScreenError(Exception):
    pass


def score_document(settings: Settings, document_type: str, paragraphs: list[str]) -> dict:
    questions = {
        "kind": {
            "type": "choice",
            "instructions": "What kind of document is this whole text?",
            "criteria": {name: name for name in door_names()} | {"other": "None of those"},
        }
    }
    criteria = clause_criteria(document_type)
    for index, _paragraph in enumerate(paragraphs):
        questions[f"bite_{index}"] = {
            "type": "noul",
            "instructions": f"Does the paragraph marked [{index}] change what the reader gives up?",
            "criteria": {"true": BITE_TRUE, "false": BITE_FALSE},
        }
        questions[f"type_{index}"] = {
            "type": "choice",
            "instructions": f"Which clause type best fits the paragraph marked [{index}]?",
            "criteria": criteria,
        }
    state = "\n\n".join(f"[{index}]\n{text}" for index, text in enumerate(paragraphs))
    payload = screen_request(settings, state, questions)
    answers = payload["answers"]
    rows = []
    for index in range(len(paragraphs)):
        bite = answers.get(f"bite_{index}") or {}
        kind = answers.get(f"type_{index}") or {}
        score = float(bite.get("noul", 0.0))
        clause = kind.get("choice") or "none"
        if clause not in criteria:
            clause = "none"
        rows.append({"index": index, "score": score, "clause_type": clause})
    detected = (answers.get("kind") or {}).get("choice") or "other"
    return {"kind": detected, "rows": rows}


def screen_request(settings: Settings, state: dict, questions: dict) -> dict:
    body = {"model": settings.typesafe_model, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {settings.typesafe_api_key}"}
    last_error = "Jev did not answer."
    for attempt in range(2):
        try:
            response = httpx.post(TYPESAFE_URL, json=body, headers=headers, timeout=30.0)
        except httpx.HTTPError as exc:
            raise ScreenError("Jev could not be reached.") from exc
        if response.status_code in (429, 529) and attempt == 0:
            time.sleep(_retry_after(response))
            last_error = "Jev was busy."
            continue
        if response.status_code >= 400:
            raise ScreenError(last_error if response.status_code in (429, 529) else "Jev rejected the screen.")
        data = response.json()
        if "answers" not in data:
            raise ScreenError("Jev returned no answers.")
        return data
    raise ScreenError(last_error)


def _retry_after(response: httpx.Response) -> float:
    raw = response.headers.get("retry-after", "1")
    try:
        return min(float(raw), 4.0)
    except ValueError:
        return 1.0
