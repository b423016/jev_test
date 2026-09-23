from __future__ import annotations

import json
import logging
import queue
import threading

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.cache import ScreenCache
from app.config import ROOT, Settings
from app.catalog import door_names
from app.extract import ExtractError, text_from_upload
from app.hashing import hashes_match
from app.pipeline import ScanRejected, run_scan
from app.playbook import Playbook
from app.screen import ScreenError

WEB = ROOT / "web"
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    cache = ScreenCache(settings.redis_url)
    playbook = Playbook(settings)
    app = FastAPI(title="Before you sign")
    app.state.settings = settings
    app.state.cache = cache
    app.state.playbook = playbook

    @app.get("/health")
    def health():
        return settings.public_status()

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    @app.post("/scans")
    async def create_scan(
        document_type: str = Form(...),
        sha256: str = Form(...),
        text: str = Form(""),
        file: UploadFile | None = File(None),
    ):
        document_type, source_text, content_hash = await _accepted_scan(
            settings, document_type, sha256, text, file
        )

        try:
            result = run_scan(
                settings,
                document_type,
                source_text,
                content_hash,
                cache,
                playbook,
            )
        except ScanRejected as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc
        except ScreenError as exc:
            raise HTTPException(502, str(exc)) from exc
        return result

    @app.post("/scans/stream")
    async def stream_scan(
        document_type: str = Form(...),
        sha256: str = Form(...),
        text: str = Form(""),
        file: UploadFile | None = File(None),
    ):
        document_type, source_text, content_hash = await _accepted_scan(
            settings, document_type, sha256, text, file
        )

        def generate():
            events = queue.Queue()

            def emit(step_id, state, detail):
                events.put(("step", {"id": step_id, "state": state, "detail": detail}))

            def work():
                try:
                    result = run_scan(
                        settings,
                        document_type,
                        source_text,
                        content_hash,
                        cache,
                        playbook,
                        emit=emit,
                    )
                    events.put(("result", result))
                except ScanRejected as exc:
                    events.put(("error", {"message": str(exc)}))
                except ScreenError as exc:
                    events.put(("error", {"message": str(exc)}))
                finally:
                    events.put(None)

            threading.Thread(target=work, daemon=True).start()
            yield _sse("step", {"id": "hash", "state": "done", "detail": content_hash[:16]})
            while True:
                item = events.get()
                if item is None:
                    break
                kind, payload = item
                yield _sse(kind, payload)

        return StreamingResponse(generate(), media_type="text/event-stream")

    app.mount("/static", StaticFiles(directory=WEB), name="static")
    return app


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


async def _accepted_scan(settings, document_type, sha256, text, file):
    if document_type not in door_names():
        raise HTTPException(400, "Pick offer, nda, lease, or checkout.")
    raw, source_text = await _read_input(text, file)
    if len(raw) > settings.max_bytes:
        raise HTTPException(413, "That file is too large.")
    if not hashes_match(sha256, raw):
        raise HTTPException(400, "The document hash does not match. Upload it again.")
    missing = settings.missing_for_scan()
    if missing:
        raise HTTPException(503, f"Missing {', '.join(missing)}")
    return document_type, source_text, sha256.strip().lower()


async def _read_input(text: str, file: UploadFile | None) -> tuple[bytes, str]:
    has_text = bool(text.strip())
    has_file = file is not None and bool(file.filename)
    if has_text == has_file:
        raise HTTPException(400, "Paste the text or upload one file.")
    if has_file:
        data = await file.read()
        if not data:
            raise HTTPException(400, "That file is empty.")
        try:
            extracted = text_from_upload(file.filename or "", data)
        except ExtractError as exc:
            raise HTTPException(422, str(exc)) from exc
        return data, extracted
    return text.encode("utf-8"), text


app = create_app()
