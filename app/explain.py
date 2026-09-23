from __future__ import annotations

import json

import httpx

from app.config import Settings

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class ExplainError(Exception):
    pass


def explain_lit(settings: Settings, findings: list[dict], cards: dict[str, dict]) -> list[dict]:
    lit = [row for row in findings if row["lit"] and row["scored"]]
    if not lit:
        return findings
    payload = []
    for row in lit:
        card = cards.get(row["clause_type"]) or {}
        payload.append(
            {
                "index": row["index"],
                "clause_type": row["clause_type"],
                "text": row["text"],
                "card_title": card.get("title", ""),
                "card_body": card.get("body", ""),
            }
        )
    raw = _complete(settings, payload)
    by_index = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            by_index[int(item.get("index"))] = item
        except (TypeError, ValueError):
            continue
    explained = []
    for row in findings:
        item = by_index.get(row["index"])
        if not row["lit"] or not row["scored"] or not item:
            explained.append(row)
            continue
        text = row["text"]
        updated = dict(row)
        updated["explanation"] = _clean(item.get("explanation"))
        updated["figure"] = _ground(text, item.get("figure"))
        updated["question"] = _clean(item.get("question"))
        updated["date"] = _ground(text, item.get("date"))
        explained.append(updated)
    return explained


def _complete(settings: Settings, payload: list[dict]) -> list[dict]:
    body = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You explain clauses a person is about to sign. "
                    "Use only the paragraph text and the card. "
                    "The card is general background, not a ruling about the reader's city or state. "
                    "figure is a number or amount copied exactly from the paragraph, or empty. "
                    "date is a date copied exactly from the paragraph, or empty. "
                    "question is one sentence they could send. "
                    "Return JSON: {\"items\": [{\"index\": 0, \"explanation\": \"\", \"figure\": \"\", \"question\": \"\", \"date\": \"\"}]}"
                ),
            },
            {"role": "user", "content": json.dumps({"items": payload})},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    try:
        response = httpx.post(OPENAI_URL, json=body, headers=headers, timeout=45.0)
    except httpx.HTTPError as exc:
        raise ExplainError("The explainer could not be reached.") from exc
    if response.status_code >= 400:
        raise ExplainError("The explainer rejected the request.")
    try:
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ExplainError("The explainer returned an unexpected shape.") from exc
    items = parsed.get("items", parsed if isinstance(parsed, list) else [])
    if not isinstance(items, list):
        raise ExplainError("The explainer returned an unexpected shape.")
    return items


def _ground(paragraph: str, value) -> str:
    text = _clean(value)
    if not text:
        return ""
    if text.casefold() in paragraph.casefold():
        return text
    return ""


def _clean(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
