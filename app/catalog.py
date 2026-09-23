from __future__ import annotations

import json

from app.config import CATALOG_PATH

BITE_TRUE = "Imposes a duty, waiver, renewal, assignment, continuing fee, or a right for the other side to change the deal."
BITE_FALSE = "Does not change what the reader gives up or owes."


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def door_names() -> list[str]:
    return list(load_catalog().keys())


def clause_criteria(document_type: str) -> dict[str, str]:
    door = load_catalog()[document_type]
    criteria = {key: item["criteria"] for key, item in door["clauses"].items()}
    criteria["none"] = {
        "what": "Does not match a listed clause",
        "not_for": "Any listed clause type",
    }
    return criteria


def cards_for(document_type: str, clause_types: set[str]) -> dict[str, dict]:
    door = load_catalog()[document_type]
    found = {}
    for clause_type in clause_types:
        item = door["clauses"].get(clause_type)
        if item:
            found[clause_type] = {"title": item["title"], "body": item["body"]}
    return found


def all_cards() -> list[dict]:
    rows = []
    for document_type, door in load_catalog().items():
        for clause_type, item in door["clauses"].items():
            rows.append(
                {
                    "document_type": document_type,
                    "clause_type": clause_type,
                    "title": item["title"],
                    "body": item["body"],
                }
            )
    return rows
