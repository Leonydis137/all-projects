"""Tenant-isolated decision-rule persistence with transactional audit events."""
from __future__ import annotations

import json
from typing import Any, Callable
from uuid import UUID

from .decision import OPS, Rule


class TenantRuleError(ValueError):
    """A tenant rule is invalid or conflicts with existing tenant state."""


class TenantRuleUnavailable(RuntimeError):
    """Tenant decision-rule storage is not configured or unavailable."""


class TenantDecisionRuleStore:
    def __init__(self, dsn: str, connect_factory: Callable[[], Any] | None = None):
        if not isinstance(dsn, str) or not dsn.strip():
            raise TenantRuleUnavailable("PostgreSQL tenant decision rules are not configured")
        self.dsn, self.connect_factory = dsn, connect_factory

    def _connect(self):
        if self.connect_factory:
            return self.connect_factory()
        try:
            from psycopg.rows import dict_row
            from .postgres_connection import connect_postgres
            return connect_postgres(self.dsn, dict_row, statement_timeout_ms=8000)
        except Exception as exc:
            raise TenantRuleUnavailable("tenant decision-rule storage is unavailable") from exc

    @staticmethod
    def _uuid(value: str, field: str) -> str:
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise TenantRuleError(f"{field} must be a UUID") from exc

    @staticmethod
    def _validate(rule: dict[str, Any]) -> dict[str, Any]:
        name = rule.get("name")
        field = rule.get("field")
        op = rule.get("op")
        action = rule.get("action")
        priority = rule.get("priority", 0)
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise TenantRuleError("name must contain 1-120 characters")
        if not isinstance(field, str) or not __import__("re").fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", field):
            raise TenantRuleError("field must be a safe dotted identifier")
        if op not in OPS:
            raise TenantRuleError(f"op must be one of {sorted(OPS)}")
        if not isinstance(action, str) or not 1 <= len(action.strip()) <= 160:
            raise TenantRuleError("action must contain 1-160 characters")
        if isinstance(priority, bool) or not isinstance(priority, int) or not -100000 <= priority <= 100000:
            raise TenantRuleError("priority must be an integer between -100000 and 100000")
        try:
            encoded = json.dumps(rule.get("value"), allow_nan=False, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise TenantRuleError("value must be valid finite JSON data") from exc
        return {"name": name.strip(), "field": field, "op": op, "value_json": encoded,
                "action": action.strip(), "priority": priority}

    @staticmethod
    def _scope(cur, tenant: str) -> None:
        cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant,))

    @staticmethod
    def _decode(row: dict[str, Any]) -> dict[str, Any]:
        value = row["value"]
        if isinstance(value, str):
            value = json.loads(value)
        return {"rule_id": str(row["rule_id"]), "name": row["name"], "field": row["field"],
                "op": row["comparison"], "value": value, "action": row["action"],
                "priority": row["priority"], "enabled": row["enabled"],
                "created_by": str(row["created_by"]), "updated_by": str(row["updated_by"]),
                "created_at": row["created_at"].isoformat(), "updated_at": row["updated_at"].isoformat()}

    def list_rules(self, tenant_id: str, include_disabled: bool = False,
                   actor_id: str | None = None) -> list[dict[str, Any]]:
        tenant = self._uuid(tenant_id, "tenant_id")
        actor = self._uuid(actor_id, "actor_id") if actor_id is not None else None
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant, actor)
                cur.execute(
                    """SELECT rule_id, name, field, comparison, value, action, priority,
                              enabled, created_by, updated_by, created_at, updated_at
                       FROM omnis.tenant_decision_rule
                       WHERE tenant_id = %s AND (%s OR enabled)
                       ORDER BY priority DESC, created_at, rule_id""",
                    (tenant, include_disabled),
                )
                return [self._decode(row) for row in cur.fetchall()]

    def create_rule(self, tenant_id: str, actor_id: str, rule: dict[str, Any], audit_log) -> dict[str, Any]:
        tenant, actor = self._uuid(tenant_id, "tenant_id"), self._uuid(actor_id, "actor_id")
        item = self._validate(rule)
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant)
                cur.execute(
                    """INSERT INTO omnis.tenant_decision_rule
                       (tenant_id, name, field, comparison, value, action, priority, created_by, updated_by)
                       VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                       RETURNING rule_id, name, field, comparison, value, action, priority,
                                 enabled, created_by, updated_by, created_at, updated_at""",
                    (tenant, item["name"], item["field"], item["op"], item["value_json"],
                     item["action"], item["priority"], actor, actor),
                )
                row = cur.fetchone()
                result = self._decode(row)
                audit_log.record_in_transaction(db, "tenant.decision_rule.created",
                    {"tenant_id": tenant, "rule_id": result["rule_id"], "name": result["name"]}, actor=actor)
        return result

    def update_rule(self, tenant_id: str, actor_id: str, rule_id: str,
                    rule: dict[str, Any], audit_log) -> dict[str, Any]:
        tenant, actor = self._uuid(tenant_id, "tenant_id"), self._uuid(actor_id, "actor_id")
        identifier = self._uuid(rule_id, "rule_id")
        item = self._validate(rule)
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant)
                cur.execute(
                    """UPDATE omnis.tenant_decision_rule
                       SET name = %s, field = %s, comparison = %s, value = %s::jsonb,
                           action = %s, priority = %s, updated_by = %s, updated_at = now()
                       WHERE tenant_id = %s AND rule_id = %s
                       RETURNING rule_id, name, field, comparison, value, action, priority,
                                 enabled, created_by, updated_by, created_at, updated_at""",
                    (item["name"], item["field"], item["op"], item["value_json"], item["action"],
                     item["priority"], actor, tenant, identifier),
                )
                row = cur.fetchone()
                if row is None:
                    raise TenantRuleError("decision rule not found in this tenant")
                result = self._decode(row)
                audit_log.record_in_transaction(db, "tenant.decision_rule.updated",
                    {"tenant_id": tenant, "rule_id": identifier, "name": result["name"]}, actor=actor)
        return result

    def delete_rule(self, tenant_id: str, actor_id: str, rule_id: str, audit_log) -> dict[str, Any]:
        tenant, actor = self._uuid(tenant_id, "tenant_id"), self._uuid(actor_id, "actor_id")
        identifier = self._uuid(rule_id, "rule_id")
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant)
                cur.execute(
                    """DELETE FROM omnis.tenant_decision_rule
                       WHERE tenant_id = %s AND rule_id = %s
                       RETURNING rule_id, name""",
                    (tenant, identifier),
                )
                row = cur.fetchone()
                if row is None:
                    raise TenantRuleError("decision rule not found in this tenant")
                audit_log.record_in_transaction(db, "tenant.decision_rule.deleted",
                    {"tenant_id": tenant, "rule_id": identifier, "name": row["name"]}, actor=actor)
        return {"tenant_id": tenant, "rule_id": identifier, "deleted": True}

    def engine(self, tenant_id: str, actor_id: str | None = None):
        from .decision import DecisionEngine
        engine = DecisionEngine()
        for row in self.list_rules(tenant_id, actor_id=actor_id):
            engine.add_rule(Rule(row["name"], row["field"], row["op"], row["value"],
                                 row["action"], row["priority"]))
        return engine
