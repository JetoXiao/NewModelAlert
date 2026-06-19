from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import CandidateItem, EventSignal, HeatMetrics


def dt_to_str(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def dt_from_str(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists source_items (
                  content_hash text primary key,
                  provider_id text not null,
                  source_name text not null,
                  title text not null,
                  url text not null,
                  summary text not null,
                  published_at text,
                  discovered_at text not null
                );

                create table if not exists events (
                  signature text primary key,
                  provider_id text not null,
                  provider_name text not null,
                  provider_priority text not null,
                  event_type text not null,
                  model_hint text not null,
                  confidence integer not null,
                  status text not null,
                  first_seen_at text not null,
                  last_seen_at text not null,
                  main_notified_at text,
                  supplement_notified_at text,
                  supplement_count integer not null default 0,
                  heat_score_at_main integer not null default 0,
                  metadata_json text not null
                );

                create table if not exists event_sources (
                  signature text not null,
                  content_hash text not null,
                  source_name text not null,
                  source_url text not null,
                  source_credibility text not null,
                  title text not null,
                  summary text not null,
                  published_at text,
                  discovered_at text not null,
                  primary key (signature, content_hash)
                );

                create table if not exists kv (
                  key text primary key,
                  value text not null
                );
                """
            )

    def get_kv(self, key: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute("select value from kv where key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def set_kv(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert into kv (key, value) values (?, ?) "
                "on conflict(key) do update set value = excluded.value",
                (key, value),
            )

    def has_source_item(self, content_hash: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "select 1 from source_items where content_hash = ?",
                (content_hash,),
            ).fetchone()
            return row is not None

    def add_source_item(self, item: CandidateItem) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                insert or ignore into source_items (
                  content_hash, provider_id, source_name, title, url, summary,
                  published_at, discovered_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.content_hash,
                    item.provider_id,
                    item.source_name,
                    item.title,
                    item.url,
                    item.summary,
                    dt_to_str(item.published_at),
                    dt_to_str(item.discovered_at),
                ),
            )
            return cursor.rowcount > 0

    def upsert_signal(self, signal: EventSignal, bootstrap: bool = False) -> bool:
        item = signal.item
        now = dt_to_str(item.discovered_at)
        metadata = {
            "matched_terms": signal.matched_terms,
            "is_official": signal.is_official,
        }
        with self.connect() as conn:
            existing = conn.execute(
                "select signature from events where signature = ?",
                (signal.signature,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    update events
                    set last_seen_at = ?,
                        confidence = max(confidence, ?),
                        metadata_json = ?
                    where signature = ?
                    """,
                    (
                        now,
                        signal.confidence,
                        json.dumps(metadata, ensure_ascii=False),
                        signal.signature,
                    ),
                )
                inserted = False
            else:
                status = "baseline" if bootstrap else "pending"
                main_notified_at = now if bootstrap else None
                conn.execute(
                    """
                    insert into events (
                      signature, provider_id, provider_name, provider_priority,
                      event_type, model_hint, confidence, status, first_seen_at,
                      last_seen_at, main_notified_at, metadata_json
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.signature,
                        item.provider_id,
                        item.provider_name,
                        item.provider_priority,
                        signal.event_type,
                        signal.model_hint,
                        signal.confidence,
                        status,
                        now,
                        now,
                        main_notified_at,
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )
                inserted = True

            conn.execute(
                """
                insert or ignore into event_sources (
                  signature, content_hash, source_name, source_url,
                  source_credibility, title, summary, published_at, discovered_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.signature,
                    item.content_hash,
                    item.source_name,
                    item.url,
                    item.source_credibility,
                    item.title,
                    item.summary,
                    dt_to_str(item.published_at),
                    dt_to_str(item.discovered_at),
                ),
            )
            return inserted

    def pending_events_ready(self, settle_minutes: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    select *
                    from events
                    where status = 'pending'
                      and datetime(first_seen_at) <= datetime('now', ?)
                    order by provider_priority, first_seen_at
                    """,
                    (f"-{settle_minutes} minutes",),
                )
            )

    def get_event(self, signature: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "select * from events where signature = ?",
                (signature,),
            ).fetchone()

    def get_event_sources(self, signature: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    select *
                    from event_sources
                    where signature = ?
                    order by source_credibility asc, discovered_at asc
                    """,
                    (signature,),
                )
            )

    def mark_main_notified(self, signature: str, heat: HeatMetrics) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                update events
                set status = 'notified',
                    main_notified_at = datetime('now'),
                    heat_score_at_main = ?
                where signature = ?
                """,
                (heat.score, signature),
            )

    def mark_supplement_notified(self, signature: str, heat: HeatMetrics) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                update events
                set supplement_notified_at = datetime('now'),
                    supplement_count = supplement_count + 1
                where signature = ?
                """,
                (signature,),
            )

    def notified_events_for_supplement_scan(self, hours: int = 72) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    select *
                    from events
                    where status = 'notified'
                      and datetime(main_notified_at) >= datetime('now', ?)
                      and supplement_count < 3
                    order by main_notified_at desc
                    """,
                    (f"-{hours} hours",),
                )
            )
