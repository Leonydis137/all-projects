"""PostgreSQL-backed append-only audit log for OMNIS."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable

_ZERO_HASH = "0" * 64
_LOG = logging.getLogger(__name__)


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")


def _json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int equality ambiguity."""
    return json.dumps(left, sort_keys=True, separators=(",", ":"), ensure_ascii=False) == json.dumps(
        right, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


class PostgresAuditLog:
    """Durable audit hash chain; requires migrations and INSERT/SELECT privileges."""

    def __init__(self, dsn: str, actor: str = "omnis-api",
                 connect_factory: Callable[[], Any] | None = None) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("OMNIS_DATABASE_URL must be a non-empty PostgreSQL connection string")
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("audit actor must be a non-empty string")
        self.dsn = dsn
        self.actor = actor.strip()
        self._connect_factory = connect_factory
        self.verify_timeout_ms = int(os.environ.get("OMNIS_DB_VERIFY_TIMEOUT_MS", "300000"))
        if self.verify_timeout_ms < 10_000:
            raise ValueError("OMNIS_DB_VERIFY_TIMEOUT_MS must be at least 10000")

    def _connect(self, statement_timeout_ms: int = 10_000):
        if self._connect_factory is not None:
            return self._connect_factory()
        from psycopg.rows import dict_row
        from .postgres_connection import connect_postgres
        return connect_postgres(self.dsn, dict_row, statement_timeout_ms=statement_timeout_ms)

    @staticmethod
    def _decode(row: dict[str, Any]) -> dict[str, Any]:
        raw = row.get("event_json")
        if not isinstance(raw, str) or not raw:
            raise ValueError("legacy audit row has no canonical event body")
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError("stored audit event is malformed")
        if (event.get("kind") != row["event_type"] or not _json_equal(event.get("payload"), row["payload"])
                or event.get("prev") != row["previous_hash"] or event.get("actor") != row["actor"]):
            raise ValueError("audit columns do not match canonical event body")
        if not isinstance(event.get("ts"), (int, float)) or isinstance(event.get("ts"), bool):
            raise ValueError("audit timestamp is malformed")
        if not isinstance(event.get("i"), int) or isinstance(event.get("i"), bool):
            raise ValueError("audit index is malformed")
        stored_time = row["occurred_at"]
        if stored_time.tzinfo is None:
            stored_time = stored_time.replace(tzinfo=timezone.utc)
        else:
            stored_time = stored_time.astimezone(timezone.utc)
        expected_time = datetime.fromtimestamp(event["ts"], tz=timezone.utc)
        if stored_time != expected_time:
            raise ValueError("audit timestamp column does not match canonical event body")
        return event

    def _record_cursor(self, cur, kind: str, payload: dict) -> dict:
        if not isinstance(kind, str) or not kind:
            raise ValueError("audit event kind must be a non-empty string")
        if not isinstance(payload, dict):
            raise ValueError("audit payload must be an object")
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('omnis.audit_event'))")
        cur.execute("SELECT event_json, event_hash FROM omnis.audit_event ORDER BY sequence DESC LIMIT 1")
        previous = cur.fetchone()
        if previous:
            prior_body = json.loads(previous["event_json"]) if previous["event_json"] else None
            if not isinstance(prior_body, dict) or not isinstance(prior_body.get("i"), int):
                raise RuntimeError("audit chain contains a legacy or malformed event")
            index = prior_body["i"] + 1
            previous_hash = previous["event_hash"]
        else:
            index = 0
            previous_hash = _ZERO_HASH
        timestamp = time.time()
        body = {"i": index, "ts": timestamp, "kind": kind, "payload": payload,
                "prev": previous_hash, "actor": self.actor}
        event_hash = hashlib.sha256(_canonical(body)).hexdigest()
        event_json = json.dumps(body, sort_keys=True, default=str, separators=(",", ":"))
        occurred_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        cur.execute(
            """INSERT INTO omnis.audit_event
               (occurred_at, actor, event_type, payload, previous_hash, event_hash, event_json)
               VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)""",
            (occurred_at, self.actor, kind, json.dumps(payload, sort_keys=True, default=str),
             previous_hash, event_hash, event_json),
        )
        return {**body, "hash": event_hash}

    def record_in_transaction(self, db, kind: str, payload: dict) -> dict:
        """Append using a caller-owned transaction; caller controls commit/rollback."""
        with db.cursor() as cur:
            return self._record_cursor(cur, kind, payload)

    def record(self, kind: str, payload: dict) -> dict:
        with self._connect() as db:
            with db.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                result = self._record_cursor(cur, kind, payload)
        return result

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500")
        with self._connect() as db:
            with db.cursor() as cur:
                cur.execute(
                    """SELECT occurred_at, actor, event_type, payload, previous_hash, event_hash, event_json
                       FROM omnis.audit_event ORDER BY sequence DESC LIMIT %s""", (limit,)
                )
                rows = cur.fetchall()
        result = []
        for row in reversed(rows):
            event = self._decode(row)
            event["hash"] = row["event_hash"]
            result.append(event)
        return result

    def health(self) -> bool:
        """Bounded liveness/integrity probe; full-chain verification remains explicit."""
        try:
            with self._connect() as db:
                with db.cursor() as cur:
                    cur.execute(
                        """SELECT occurred_at, actor, event_type, payload, previous_hash, event_hash, event_json
                           FROM omnis.audit_event ORDER BY sequence DESC LIMIT 1"""
                    )
                    row = cur.fetchone()
            if row is None:
                return True
            event = self._decode(row)
            return hashlib.sha256(_canonical(event)).hexdigest() == row["event_hash"]
        except Exception:
            _LOG.exception("OMNIS audit health probe failed")
            return False

    def verify(self) -> bool:
        previous_hash = _ZERO_HASH
        expected_index = 0
        try:
            with self._connect(statement_timeout_ms=self.verify_timeout_ms) as db:
                with db.cursor() as cur:
                    cur.execute(
                        """SELECT occurred_at, actor, event_type, payload, previous_hash, event_hash, event_json
                           FROM omnis.audit_event ORDER BY sequence"""
                    )
                    rows = cur.fetchall()
            for row in rows:
                event = self._decode(row)
                if event["i"] != expected_index or event["prev"] != previous_hash:
                    return False
                expected = hashlib.sha256(_canonical(event)).hexdigest()
                if row["event_hash"] != expected:
                    return False
                previous_hash = expected
                expected_index += 1
            return True
        except Exception:
            _LOG.exception("OMNIS audit-chain verification failed")
            return False
