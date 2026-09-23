from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    typesafe_api_key: str
    typesafe_model: str
    openai_api_key: str
    openai_model: str
    database_url: str
    redis_url: str
    threshold: float
    max_bytes: int
    max_chars: int
    max_paragraphs: int

    @classmethod
    def from_env(cls) -> "Settings":
        load_env_file(ROOT / ".env")
        threshold = float(os.environ.get("BITE_THRESHOLD", "0.55"))
        return cls(
            typesafe_api_key=os.environ.get("TYPESAFE_API_KEY", "").strip(),
            typesafe_model=os.environ.get("TYPESAFE_MODEL", "jev-latest").strip() or "jev-latest",
            openai_api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
            openai_model=os.environ.get("OPENAI_MODEL", "").strip(),
            database_url=os.environ.get("DATABASE_URL", "").strip(),
            redis_url=os.environ.get("REDIS_URL", "").strip(),
            threshold=threshold,
            max_bytes=2_000_000,
            max_chars=30_000,
            max_paragraphs=40,
        )

    def missing_for_scan(self) -> list[str]:
        missing = []
        if not self.typesafe_api_key:
            missing.append("TYPESAFE_API_KEY")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.openai_model:
            missing.append("OPENAI_MODEL")
        return missing

    def public_status(self) -> dict:
        return {
            "jev": bool(self.typesafe_api_key),
            "openai": bool(self.openai_api_key and self.openai_model),
            "neon": bool(self.database_url),
            "redis": bool(self.redis_url),
        }
