"""Durable tenant request metering, rate limiting, and monthly quota enforcement."""
from __future__ import annotations

from typing import Any, Callable
from uuid import UUID


class TenantUsageError(RuntimeError):
    """A tenant usage policy rejected an operation."""


class TenantUsageUnavailable(RuntimeError):
    """Tenant usage storage is unavailable."""


class TenantUsageStore:
    def __init__(self, dsn: str, connect_factory: Callable[[], Any] | None = None):
        if not isinstance(dsn, str) or not dsn.strip():
            raise TenantUsageUnavailable("PostgreSQL tenant usage is not configured")
        self.dsn, self.connect_factory = dsn, connect_factory

    def _connect(self):
        if self.connect_factory:
            return self.connect_factory()
        try:
            from psycopg.rows import dict_row
            from .postgres_connection import connect_postgres
            return connect_postgres(self.dsn, dict_row, statement_timeout_ms=8000)
        except Exception as exc:
            raise TenantUsageUnavailable("tenant usage storage is unavailable") from exc

    @staticmethod
    def _uuid(value: str, field: str) -> str:
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise TenantUsageUnavailable(f"{field} must be a UUID") from exc

    def consume(self, tenant_id: str, principal_id: str, operation: str,
                requests_per_minute: int, audit_log) -> dict[str, Any]:
        tenant = self._uuid(tenant_id, "tenant_id")
        principal = self._uuid(principal_id, "principal_id")
        if not isinstance(operation, str) or not 1 <= len(operation) <= 120:
            raise TenantUsageUnavailable("operation must contain 1-120 characters")
        if isinstance(requests_per_minute, bool) or not isinstance(requests_per_minute, int) or requests_per_minute < 1:
            raise TenantUsageUnavailable("requests_per_minute must be a positive integer")

        try:
            with self._connect() as db:
                with db.cursor() as cur:
                    cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant,))
                    cur.execute("SELECT set_config('omnis.principal_id', %s, true)", (principal,))
                    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                                (f"omnis.tenant_usage:{tenant}",))
                    # now() is fixed at transaction start. A request can wait on
                    # the tenant lock across a minute/month boundary, so capture
                    # wall-clock time only after acquiring the lock and use that
                    # single decision timestamp for every metering boundary.
                    cur.execute("SELECT clock_timestamp() AS decision_at")
                    decision_at = cur.fetchone()["decision_at"]
                    cur.execute(
                        """SELECT date_trunc('minute', %s) AS window_start,
                                  date_trunc('month', %s) AS month_start""",
                        (decision_at, decision_at))
                    boundaries = cur.fetchone()
                    window = boundaries["window_start"]
                    month_start = boundaries["month_start"]
                    cur.execute(
                        """SELECT monthly_request_limit FROM omnis.tenant_usage_policy
                           WHERE tenant_id = %s""", (tenant,))
                    policy = cur.fetchone()
                    cur.execute(
                        """SELECT count(*) AS used FROM omnis.tenant_usage_event
                           WHERE tenant_id = %s AND outcome = 'accepted'
                             AND occurred_at >= %s""", (tenant, month_start))
                    used = int(cur.fetchone()["used"])
                    cur.execute(
                        """SELECT request_count FROM omnis.tenant_usage_minute
                           WHERE tenant_id = %s AND window_start = %s FOR UPDATE""",
                        (tenant, window))
                    bucket = cur.fetchone()
                    minute_count = int(bucket["request_count"]) if bucket else 0

                    outcome = "accepted"
                    if minute_count >= requests_per_minute:
                        outcome = "rate_limited"
                    elif policy is not None and policy["monthly_request_limit"] is not None and used >= int(policy["monthly_request_limit"]):
                        outcome = "quota_exceeded"

                    if bucket:
                        cur.execute(
                            """UPDATE omnis.tenant_usage_minute
                               SET request_count = request_count + 1, updated_at = %s
                               WHERE tenant_id = %s AND window_start = %s""", (decision_at, tenant, window))
                    else:
                        cur.execute(
                            """INSERT INTO omnis.tenant_usage_minute
                               (tenant_id, window_start, request_count) VALUES (%s, %s, 1)""",
                            (tenant, window))
                    cur.execute(
                        """INSERT INTO omnis.tenant_usage_event
                           (tenant_id, principal_id, operation, units, outcome, occurred_at)
                           VALUES (%s, %s, %s, 1, %s, %s)
                           RETURNING usage_id, occurred_at""",
                        (tenant, principal, operation, outcome, decision_at))
                    event = cur.fetchone()
                    audit_log.record_in_transaction(
                        db, "tenant.usage.recorded",
                        {"tenant_id": tenant, "operation": operation, "units": 1,
                         "outcome": outcome, "monthly_accepted": used + (1 if outcome == "accepted" else 0),
                         "minute_requests": minute_count + 1},
                        actor=principal)
                    result = {
                        "usage_id": str(event["usage_id"]),
                        "operation": operation,
                        "units": 1,
                        "outcome": outcome,
                        "monthly_accepted": used + (1 if outcome == "accepted" else 0),
                        "minute_requests": minute_count + 1,
                        "occurred_at": event["occurred_at"].isoformat(),
                    }
            if outcome != "accepted":
                raise TenantUsageError(outcome)
            return result
        except TenantUsageError:
            raise
        except Exception as exc:
            raise TenantUsageUnavailable("tenant usage storage is unavailable") from exc

    def summary(self, tenant_id: str, principal_id: str, audit_log) -> dict[str, Any]:
        tenant = self._uuid(tenant_id, "tenant_id")
        principal = self._uuid(principal_id, "principal_id")
        try:
            with self._connect() as db:
                with db.cursor() as cur:
                    cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant,))
                    cur.execute("SELECT set_config('omnis.principal_id', %s, true)", (principal,))
                    cur.execute(
                        """SELECT operation, outcome, count(*) AS events, coalesce(sum(units), 0) AS units
                           FROM omnis.tenant_usage_event
                           WHERE tenant_id = %s AND occurred_at >= date_trunc('month', now())
                           GROUP BY operation, outcome ORDER BY operation, outcome""", (tenant,))
                    rows = cur.fetchall()
                    cur.execute(
                        """SELECT monthly_request_limit FROM omnis.tenant_usage_policy
                           WHERE tenant_id = %s""", (tenant,))
                    policy = cur.fetchone()
                    cur.execute(
                        """SELECT count(*) AS accepted FROM omnis.tenant_usage_event
                           WHERE tenant_id = %s AND outcome = 'accepted'
                             AND occurred_at >= date_trunc('month', now())""", (tenant,))
                    accepted = int(cur.fetchone()["accepted"])
            return {"period": "calendar_month", "accepted_requests": accepted,
                    "monthly_request_limit": policy["monthly_request_limit"] if policy else None,
                    "unlimited_if_no_limit": policy is None or policy["monthly_request_limit"] is None,
                    "usage": [dict(row) for row in rows]}
        except Exception as exc:
            raise TenantUsageUnavailable("tenant usage storage is unavailable") from exc
