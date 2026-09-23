from __future__ import annotations

import logging

from app.catalog import cards_for
from app.config import Settings

log = logging.getLogger("jev")


class Playbook:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._ready = False

    def lookup(self, document_type: str, clause_types: set[str]) -> dict[str, dict]:
        local = cards_for(document_type, clause_types)
        if not self._settings.database_url:
            return local
        remote = self._from_neon(document_type, clause_types)
        merged = dict(local)
        merged.update(remote)
        return merged

    def _from_neon(self, document_type: str, clause_types: set[str]) -> dict[str, dict]:
        wanted = [item for item in clause_types if item and item != "none"]
        if not wanted:
            return {}
        try:
            import psycopg

            with psycopg.connect(self._settings.database_url, connect_timeout=5) as conn:
                self._ensure(conn)
                rows = conn.execute(
                    """
                    select clause_type, title, body
                    from playbook_cards
                    where document_type = %s and clause_type = any(%s)
                    """,
                    (document_type, wanted),
                ).fetchall()
            return {row[0]: {"title": row[1], "body": row[2]} for row in rows}
        except Exception:
            log.warning("playbook lookup failed; using the local catalog")
            return {}

    def _ensure(self, conn) -> None:
        if self._ready:
            return
        from app.catalog import all_cards

        conn.execute(
            """
            create table if not exists playbook_cards (
              document_type text not null,
              clause_type text not null,
              title text not null,
              body text not null,
              primary key (document_type, clause_type)
            )
            """
        )
        for card in all_cards():
            conn.execute(
                """
                insert into playbook_cards (document_type, clause_type, title, body)
                values (%s, %s, %s, %s)
                on conflict (document_type, clause_type)
                do update set title = excluded.title, body = excluded.body
                """,
                (card["document_type"], card["clause_type"], card["title"], card["body"]),
            )
        conn.commit()
        self._ready = True
