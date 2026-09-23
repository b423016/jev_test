from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


class ExtractError(Exception):
    pass


def text_from_upload(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _pdf_text(data)
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="replace").strip()
    raise ExtractError("Upload a PDF or a text file.")


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ExtractError("Could not read this PDF.") from exc
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n\n".join(part.strip() for part in pages if part.strip())
    if not text:
        raise ExtractError("This PDF has no text layer. Paste the text instead.")
    return text
