from __future__ import annotations


def split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    parts = [part.strip() for part in normalized.split("\n\n")]
    parts = [part for part in parts if part]
    joined: list[str] = []
    for part in parts:
        if joined and len(part) < 20:
            joined[-1] = joined[-1] + "\n" + part
            continue
        if joined and len(joined[-1]) < 20:
            joined[-1] = joined[-1] + "\n" + part
            continue
        joined.append(part)
    return joined
