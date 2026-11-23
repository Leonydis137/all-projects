# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""OMNIS gateway: one FastAPI app exposing the features of every merged project."""
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from . import __version__, assistant, catalog, config, governance, inventory, mathops, sources, stats
from .audit import audit as memory_audit
from .postgres_audit import AuditIntegrityError, PostgresAuditLog
from .decision import Rule, default_engine
from .evidence import EvidenceLedger, EvidenceValidationError
from .postgres_evidence import EvidenceIntegrityError, PostgresEvidenceLedger
from .postgres_tenant_evidence import PostgresTenantEvidenceLedger
from .postgres_tenant_audit import (
    PostgresTenantAuditLog, TenantAuditIntegrityError, TenantAuditValidationError,
)
from .tenant_admin import TenantAdminError, TenantAdminStore, TenantAdminUnavailable
from .tenant_decision_rules import TenantDecisionRuleStore, TenantRuleError, TenantRuleUnavailable
from .tenant_assistant import TenantAssistantStore, TenantConversationError, TenantConversationUnavailable
from .protocols import AEON, Context
from .recommend import Recommender
from .identity import IdentityUnavailable, InvalidCredential, Principal, authenticate_api_key
from .source_fetch import (
    SourceConfigurationError,
    SourcePolicyError,
    SourceUnavailable,
    acquire_and_attest,
    public_key_document,
)

sources.wire()
app = FastAPI(title="OMNIS", version=__version__, description="All projects, one platform.")
engine = default_engine()
aeon = AEON()
audit = (PostgresAuditLog(config.DATABASE_URL, actor=os.environ.get("OMNIS_AUDIT_ACTOR", "omnis-api"))
         if config.DATABASE_URL else memory_audit)
evidence = (PostgresEvidenceLedger(config.DATABASE_URL, audit_log=audit) if config.DATABASE_URL else
            EvidenceLedger(os.environ.get("OMNIS_EVIDENCE_DB", str(config.PLATFORM_DIR / "var" / "evidence.sqlite3"))))
tenant_evidence = PostgresTenantEvidenceLedger(config.DATABASE_URL) if config.DATABASE_URL else None
tenant_audit = PostgresTenantAuditLog(config.DATABASE_URL) if config.DATABASE_URL else None
tenant_admin = (TenantAdminStore(config.DATABASE_URL, os.environ.get('OMNIS_API_KEY_PEPPER', '')) if config.DATABASE_URL and len(os.environ.get('OMNIS_API_KEY_PEPPER', '')) >= 32 else None)
tenant_decision_rules = TenantDecisionRuleStore(config.DATABASE_URL) if config.DATABASE_URL else None
tenant_assistant = TenantAssistantStore(config.DATABASE_URL) if config.DATABASE_URL else None
STATIC = Path(__file__).parent / "static"
_HEALTH_CACHE_TTL_SECONDS = 2.0
_health_lock = threading.Lock()
_health_cache: dict[str, Any] = {"checked_at": 0.0, "response": None}


@app.middleware("http")
async def audit_api_requests(request: Request, call_next):
    """Persist a request-start event before dispatch; never run an API action unaudited.

    The audit read endpoint is exempt to avoid making a read of the ledger mutate it.
    If the completion event cannot be written, the completed action is not retried;
    the response carries an explicit incomplete-audit header instead.
    """
    path = request.url.path
    if not path.startswith("/v1/") or (path == "/v1/audit" and request.method == "GET"):
        return await call_next(request)

    # Tenant credentials are accepted only by explicitly tenant-aware routes.
    # All other resource stores remain behind the legacy single-tenant token.
    principal = None
    identity_error = None
    tenant_auth_paths = {
        "/v1/identity/me",
        "/v1/tenant/evidence",
        "/v1/tenant/evidence/verify",
        "/v1/tenant/members",
        "/v1/tenant/credentials",
        "/v1/tenant/source/fetch",
        "/v1/tenant/source/attestation-key",
        "/v1/tenant/audit",
        "/v1/tenant/audit/verify",
        "/v1/tenant/govern",
        "/v1/tenant/decide",
        "/v1/tenant/recommend",
        "/v1/tenant/protocols/respond",
        "/v1/tenant/stats/ab",
        "/v1/tenant/stats/posterior",
        "/v1/tenant/math/gcd-lcm",
        "/v1/tenant/decision-rules",
        "/v1/tenant/assistant/conversations",
    }
    if path.startswith("/v1/tenant/assistant/conversations/") or path.startswith("/v1/tenant/decision-rules/") or path.startswith("/v1/tenant/members/") or path.startswith("/v1/tenant/credentials/"):
        tenant_auth_paths.add(path)
    if path in tenant_auth_paths:
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            identity_error = InvalidCredential("missing or invalid bearer credential")
        else:
            try:
                principal = await run_in_threadpool(authenticate_api_key, token, request.headers.get("x-omnis-tenant"))
            except (InvalidCredential, IdentityUnavailable) as exc:
                identity_error = exc
        request.state.identity_principal = principal
        request.state.identity_error = identity_error

    event = {"method": request.method, "path": path}
    actor = principal.principal_id if principal is not None else None
    # Authenticated tenant traffic is recorded only in that tenant's isolated chain.
    # The legacy global chain remains the operational log for non-tenant requests.
    request_audit = tenant_audit if principal is not None and tenant_audit is not None else audit
    if principal is not None:
        event["tenant_id"] = principal.tenant_id
    try:
        if actor:
            request_audit.record("http.request.started", event, actor=actor)
        else:
            request_audit.record("http.request.started", event)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "audit_unavailable"})

    try:
        response = await call_next(request)
    except Exception as exc:
        try:
            failure = {**event, "error_type": type(exc).__name__}
            if actor:
                request_audit.record("http.request.failed", failure, actor=actor)
            else:
                request_audit.record("http.request.failed", failure)
        except Exception:
            pass
        raise

    try:
        completion = {**event, "status_code": response.status_code}
        if actor:
            request_audit.record("http.request.completed", completion, actor=actor)
        else:
            request_audit.record("http.request.completed", completion)
    except Exception:
        response.headers["X-OMNIS-Audit-Status"] = "incomplete"
    return response


def auth(authorization: Optional[str] = Header(default=None)) -> None:
    # Legacy shared-token authentication remains for existing single-tenant routes.
    # Tenant credentials are intentionally not accepted here until those routes
    # and their storage adapters enforce tenant isolation.
    if not config.API_TOKEN:
        raise HTTPException(503, "API authentication is not configured")
    if authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(401, "missing or invalid bearer token")


def tenant_identity(request: Request) -> Principal:
    principal = getattr(request.state, "identity_principal", None)
    error = getattr(request.state, "identity_error", None)
    if isinstance(error, IdentityUnavailable):
        raise HTTPException(503, str(error)) from error
    if isinstance(error, InvalidCredential) or principal is None:
        raise HTTPException(401, "missing or invalid tenant credential")
    return principal


def gated(kind: str, attrs: Optional[dict] = None, actor: Optional[str] = None,
          tenant_id: Optional[str] = None, context: Optional[dict] = None) -> dict:
    """Run an action through COVENANT and append its decision to the correct audit chain."""
    action = governance.stamp({**(attrs or {}), "type": kind}, mission="PRIMARY_MISSION", auditable=True, data_provenance=True)
    verdict = governance.evaluate(action, context)
    payload = {"action": kind, "allowed": verdict["allowed"], "violations": verdict["violations"]}
    if tenant_id:
        payload["tenant_id"] = tenant_id
        (tenant_audit or audit).record("govern", payload, actor=actor)
    elif actor:
        audit.record("govern", payload, actor=actor)
    else:
        audit.record("govern", payload)
    if not verdict["allowed"]:
        raise HTTPException(403, {"blocked_by": "covenant", "violations": verdict["violations"]})
    return verdict


class Attrs(BaseModel):
    attributes: dict[str, Any] = Field(default_factory=dict, description="governance attributes, e.g. harm, intent")


class GovernIn(BaseModel):
    action: dict[str, Any]
    context: Optional[dict[str, Any]] = None


class DecideIn(Attrs):
    context: dict[str, Any]


class RuleIn(BaseModel):
    name: str
    field: str
    op: str
    value: Any
    action: str
    priority: int = 0


class RespondIn(Attrs):
    emotional_tone: str = "neutral"
    user_intent: str = "none"
    environment_state: str = "normal"


class FeedbackIn(BaseModel):
    protocol: str
    positive: bool


class RecommendIn(Attrs):
    rows: list[list[float]]
    query: list[float]
    k: int = 3
    labels: Optional[list[str]] = None


class ABIn(BaseModel):
    conv_a: int
    n_a: int
    conv_b: int
    n_b: int


class PosteriorIn(BaseModel):
    bayes_factor: float
    prior: float = 0.5


class NumbersIn(BaseModel):
    numbers: list[int]


class ChatIn(Attrs):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)


class EvidenceIn(BaseModel):
    source_uri: str
    content_sha256: str
    acquired_at: str
    acquisition_method: str
    license: str
    submitted_by: str
    idempotency_key: Optional[str] = None


class SourceFetchIn(BaseModel):
    source_uri: str = Field(min_length=1, max_length=2048)
    license: str = Field(default="unspecified", min_length=1, max_length=256)

class TenantEvidenceIn(BaseModel):
    source_uri: str
    content_sha256: str
    acquired_at: str
    acquisition_method: str
    license: str
    idempotency_key: Optional[str] = None

class TenantMemberIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=160)
    role: str = "reader"


class TenantMemberUpdateIn(BaseModel):
    role: str
    status: str = "active"


class TenantAssistantConversationIn(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=160)


class TenantAssistantMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=12000)


class TenantDecisionRuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    field: str = Field(min_length=1, max_length=128)
    op: str
    value: Any
    action: str = Field(min_length=1, max_length=160)
    priority: int = Field(default=0, ge=-100000, le=100000)


class TenantCredentialIn(BaseModel):
    principal_id: str
    label: str = Field(min_length=1, max_length=100)
    expires_in_days: int = Field(default=90, ge=1, le=365)


@app.get("/health")
def health():
    """Expose integrity failures without opening a new DB connection per probe."""
    with _health_lock:
        now = time.monotonic()
        cached = _health_cache["response"]
        if cached is not None and now - _health_cache["checked_at"] < _HEALTH_CACHE_TTL_SECONDS:
            status_code, payload = cached
            if status_code == 503:
                return JSONResponse(status_code=503, content=payload)
            return payload

        try:
            audit_valid = bool(audit.health() if hasattr(audit, "health") else audit.verify())
        except Exception:
            audit_valid = False
        try:
            evidence_status = evidence.health() if hasattr(evidence, "health") else evidence.verify()
            if not isinstance(evidence_status, dict) or not isinstance(evidence_status.get("valid"), bool):
                evidence_status = {"valid": False, "reason": "invalid_verifier_response"}
        except Exception:
            evidence_status = {"valid": False, "reason": "verification_error"}

        healthy = audit_valid and evidence_status["valid"]
        payload = {"status": "ok" if healthy else "degraded", "version": __version__,
                   "sources": str(config.SOURCES), "sources_present": config.SOURCES.is_dir(),
                   "import_roots": sources.wire() or "already wired", "audit_chain_valid": audit_valid,
                   "evidence_ledger": evidence_status, "assistant_configured": bool(config.ANTHROPIC_API_KEY)}
        status_code = 200 if healthy else 503
        _health_cache["checked_at"] = time.monotonic()
        _health_cache["response"] = (status_code, payload)
        if not healthy:
            return JSONResponse(status_code=503, content=payload)
        return payload


@app.get("/v1/identity/me")
def get_identity(principal: Principal = Depends(tenant_identity)) -> dict:
    """Return the authenticated principal and permissions for the selected tenant."""
    (tenant_audit or audit).record("identity.access", {"tenant_id": principal.tenant_id,
                                      "principal_id": principal.principal_id},
                 actor=principal.principal_id)
    return {
        "tenant_id": principal.tenant_id,
        "principal_id": principal.principal_id,
        "email": principal.email,
        "display_name": principal.display_name,
        "role": principal.role,
        "permissions": sorted(principal.permissions),
        "credential_prefix": principal.credential_prefix,
    }


@app.post("/v1/tenant/evidence")
def append_tenant_evidence(
    body: TenantEvidenceIn,
    principal: Principal = Depends(tenant_identity),
) -> dict:
    if not principal.allows("evidence:write"):
        raise HTTPException(403, "tenant role lacks evidence:write")
    if tenant_evidence is None:
        raise HTTPException(503, "PostgreSQL tenant evidence is not configured")
    try:
        gated("tenant.evidence.append", {"tenant_id": principal.tenant_id}, actor=principal.principal_id, tenant_id=principal.tenant_id)
        stored = tenant_evidence.append_with_audit(
            body.model_dump(exclude_none=True), principal.tenant_id, principal.principal_id, (tenant_audit or audit)
        )
        return {"record": stored}
    except EvidenceIntegrityError:
        return JSONResponse(status_code=503, content={"detail": "tenant_evidence_integrity_error"})
    except EvidenceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/tenant/evidence")
def list_tenant_evidence(
    limit: int = 100,
    before: int | None = None,
    principal: Principal = Depends(tenant_identity),
) -> dict:
    if not principal.allows("evidence:read"):
        raise HTTPException(403, "tenant role lacks evidence:read")
    if tenant_evidence is None:
        raise HTTPException(503, "PostgreSQL tenant evidence is not configured")
    try:
        return {"records": tenant_evidence.list(principal.tenant_id, limit=limit, before=before)}
    except EvidenceIntegrityError:
        return JSONResponse(status_code=503, content={"detail": "tenant_evidence_integrity_error"})
    except EvidenceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/tenant/evidence/verify")
def verify_tenant_evidence(principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("evidence:read"):
        raise HTTPException(403, "tenant role lacks evidence:read")
    if tenant_evidence is None:
        raise HTTPException(503, "PostgreSQL tenant evidence is not configured")
    return tenant_evidence.verify(principal.tenant_id)



def _tenant_admin_store() -> TenantAdminStore:
    if tenant_admin is None:
        raise HTTPException(503, "tenant administration is not configured")
    return tenant_admin




@app.get("/v1/tenant/audit")
def list_tenant_audit(limit: int = 100, before: int | None = None,
                      principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("audit:read"):
        raise HTTPException(403, "tenant role lacks audit:read")
    if tenant_audit is None:
        raise HTTPException(503, "PostgreSQL tenant audit is not configured")
    try:
        return {"events": tenant_audit.list(principal.tenant_id, limit=limit, before=before)}
    except TenantAuditValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TenantAuditIntegrityError:
        return JSONResponse(status_code=503, content={"detail": "tenant_audit_integrity_error"})


@app.get("/v1/tenant/audit/verify")
def verify_tenant_audit(principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("audit:read"):
        raise HTTPException(403, "tenant role lacks audit:read")
    if tenant_audit is None:
        raise HTTPException(503, "PostgreSQL tenant audit is not configured")
    return tenant_audit.verify(principal.tenant_id)


@app.post("/v1/tenant/govern")
def govern_tenant(body: GovernIn, principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("governance:execute"):
        raise HTTPException(403, "tenant role lacks governance:execute")
    action = governance.stamp(body.action, mission="PRIMARY_MISSION",
                              auditable=True, data_provenance=True)
    verdict = governance.evaluate(action, body.context)
    (tenant_audit or audit).record(
        "governance.evaluate",
        {"tenant_id": principal.tenant_id, "action_type": str(body.action.get("type", "unspecified"))[:160],
         "allowed": verdict["allowed"], "violations": verdict["violations"]},
        actor=principal.principal_id,
    )
    return verdict


@app.get("/v1/tenant/members")
def list_tenant_members(principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("members:manage"):
        raise HTTPException(403, "tenant role lacks members:manage")
    try:
        return {"members": _tenant_admin_store().list_members(principal.tenant_id)}
    except TenantAdminUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/v1/tenant/members")
def add_tenant_member(body: TenantMemberIn, principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("members:manage"):
        raise HTTPException(403, "tenant role lacks members:manage")
    if body.role == "owner" and principal.role != "owner":
        raise HTTPException(403, "only an owner may assign the owner role")
    try:
        result = _tenant_admin_store().add_member(
            principal.tenant_id, body.email, body.display_name, body.role, principal.principal_id, principal.role, (tenant_audit or audit)
        )
        return {"member": result}
    except TenantAdminError as exc:
        raise HTTPException(409, str(exc)) from exc
    except TenantAdminUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.patch("/v1/tenant/members/{principal_id}")
def update_tenant_member(principal_id: str, body: TenantMemberUpdateIn,
                         principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("members:manage"):
        raise HTTPException(403, "tenant role lacks members:manage")
    if body.role == "owner" and principal.role != "owner":
        raise HTTPException(403, "only an owner may assign the owner role")
    try:
        result = _tenant_admin_store().update_member(
            principal.tenant_id, principal_id, body.role, body.status, principal.principal_id, principal.role, (tenant_audit or audit)
        )
        return {"member": result}
    except TenantAdminError as exc:
        raise HTTPException(409, str(exc)) from exc
    except TenantAdminUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/v1/tenant/credentials")
def issue_tenant_credential(body: TenantCredentialIn,
                            principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("credentials:manage"):
        raise HTTPException(403, "tenant role lacks credentials:manage")
    try:
        return _tenant_admin_store().issue_credential(
            principal.tenant_id, body.principal_id, body.label, body.expires_in_days,
            principal.principal_id, principal.role, (tenant_audit or audit),
        )
    except TenantAdminError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TenantAdminUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.delete("/v1/tenant/credentials/{credential_id}")
def revoke_tenant_credential(credential_id: str,
                             principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("credentials:manage"):
        raise HTTPException(403, "tenant role lacks credentials:manage")
    try:
        return _tenant_admin_store().revoke_credential(
            principal.tenant_id, credential_id, principal.principal_id, principal.role, audit
        )
    except TenantAdminError as exc:
        raise HTTPException(404, str(exc)) from exc
    except TenantAdminUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/v1/tenant/source/attestation-key")
def get_tenant_source_attestation_key(principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("identity:read"):
        raise HTTPException(403, "tenant role lacks identity:read")
    try:
        return public_key_document()
    except SourceConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/v1/tenant/source/fetch")
def fetch_tenant_source(body: SourceFetchIn,
                        principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("evidence:write") or not principal.allows("governance:execute"):
        raise HTTPException(403, "tenant role lacks source acquisition permissions")
    if tenant_evidence is None:
        raise HTTPException(503, "PostgreSQL tenant evidence is not configured")
    try:
        gated("tenant.source.fetch", {"tenant_id": principal.tenant_id,
                                      "source_uri": body.source_uri}, actor=principal.principal_id,
              tenant_id=principal.tenant_id)
        record, acquisition = acquire_and_attest(
            body.source_uri, body.license,
            os.environ.get("OMNIS_SOURCE_FETCHER_ID", "omnis-source-fetcher"),
        )
        stored = tenant_evidence.append_with_audit(
            record, principal.tenant_id, principal.principal_id, audit
        )
        return {"record": stored, "acquisition": acquisition}
    except SourcePolicyError as exc:
        raise HTTPException(403, str(exc)) from exc
    except SourceConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    except SourceUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    except EvidenceIntegrityError:
        return JSONResponse(status_code=503, content={"detail": "tenant_evidence_integrity_error"})
    except EvidenceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


def _tenant_assistant_store() -> TenantAssistantStore:
    if tenant_assistant is None:
        raise HTTPException(503, "PostgreSQL tenant assistant storage is not configured")
    return tenant_assistant


def _require_tenant_assistant(principal: Principal) -> None:
    if not principal.allows("assistant:use"):
        raise HTTPException(403, "tenant role lacks assistant:use")


@app.get("/v1/tenant/assistant/conversations")
def list_tenant_assistant_conversations(limit: int = 50,
                                        principal: Principal = Depends(tenant_identity)) -> dict:
    _require_tenant_assistant(principal)
    try:
        return {"conversations": _tenant_assistant_store().list(
            principal.tenant_id, principal.principal_id, limit)}
    except TenantConversationError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TenantConversationUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/v1/tenant/assistant/conversations")
def create_tenant_assistant_conversation(
    body: TenantAssistantConversationIn,
    principal: Principal = Depends(tenant_identity),
) -> dict:
    _require_tenant_assistant(principal)
    try:
        gated("tenant.assistant.conversation.create",
              {"title_length": len(body.title.strip())},
              actor=principal.principal_id, tenant_id=principal.tenant_id)
        result = _tenant_assistant_store().create(
            principal.tenant_id, principal.principal_id, body.title, tenant_audit or audit)
        return {"conversation": result}
    except TenantConversationError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TenantConversationUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/v1/tenant/assistant/conversations/{conversation_id}/messages")
async def send_tenant_assistant_message(
    conversation_id: str,
    body: TenantAssistantMessageIn,
    principal: Principal = Depends(tenant_identity),
) -> dict:
    _require_tenant_assistant(principal)
    if not body.message.strip():
        raise HTTPException(422, "message must contain non-whitespace text")
    try:
        store = _tenant_assistant_store()
        metadata, history = store.history(
            principal.tenant_id, principal.principal_id, conversation_id, limit=20)
        gated("tenant.assistant.chat",
              {"conversation_id": metadata["conversation_id"],
               "message_length": len(body.message.strip()),
               "history_messages": len(history)},
              actor=principal.principal_id, tenant_id=principal.tenant_id)
        reply = await assistant.chat(body.message.strip(), history)
        updated = store.persist_exchange(
            principal.tenant_id, principal.principal_id, conversation_id,
            body.message, reply, metadata["message_count"], tenant_audit or audit)
        return {"conversation": updated, "reply": reply}
    except TenantConversationError as exc:
        status = 404 if "not found" in str(exc) else (422 if "must be a UUID" in str(exc) else 409)
        raise HTTPException(status, str(exc)) from exc
    except TenantConversationUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except assistant.AssistantUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _tenant_rule_store() -> TenantDecisionRuleStore:
    if tenant_decision_rules is None:
        raise HTTPException(503, "PostgreSQL tenant decision rules are not configured")
    return tenant_decision_rules


@app.get("/v1/tenant/decision-rules")
def list_tenant_decision_rules(principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("decision_rules:read"):
        raise HTTPException(403, "tenant role lacks decision_rules:read")
    try:
        return {"rules": _tenant_rule_store().list_rules(principal.tenant_id, include_disabled=True)}
    except TenantRuleUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/v1/tenant/decision-rules")
def create_tenant_decision_rule(body: TenantDecisionRuleIn,
                                principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("decision_rules:manage"):
        raise HTTPException(403, "tenant role lacks decision_rules:manage")
    try:
        _tenant_operation(principal, "tenant.decision_rule.create", {"rule_name": body.name})
        result = _tenant_rule_store().create_rule(
            principal.tenant_id, principal.principal_id, body.model_dump(), tenant_audit or audit)
        return {"rule": result}
    except TenantRuleError as exc:
        raise HTTPException(409, str(exc)) from exc
    except TenantRuleUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.put("/v1/tenant/decision-rules/{rule_id}")
def update_tenant_decision_rule(rule_id: str, body: TenantDecisionRuleIn,
                                principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("decision_rules:manage"):
        raise HTTPException(403, "tenant role lacks decision_rules:manage")
    try:
        _tenant_operation(principal, "tenant.decision_rule.update", {"rule_id": rule_id, "rule_name": body.name})
        result = _tenant_rule_store().update_rule(
            principal.tenant_id, principal.principal_id, rule_id, body.model_dump(), tenant_audit or audit)
        return {"rule": result}
    except TenantRuleError as exc:
        raise HTTPException(404 if "not found" in str(exc) else 422, str(exc)) from exc
    except TenantRuleUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.delete("/v1/tenant/decision-rules/{rule_id}")
def delete_tenant_decision_rule(rule_id: str,
                                principal: Principal = Depends(tenant_identity)) -> dict:
    if not principal.allows("decision_rules:manage"):
        raise HTTPException(403, "tenant role lacks decision_rules:manage")
    try:
        _tenant_operation(principal, "tenant.decision_rule.delete", {"rule_id": rule_id})
        return _tenant_rule_store().delete_rule(
            principal.tenant_id, principal.principal_id, rule_id, tenant_audit or audit)
    except TenantRuleError as exc:
        raise HTTPException(404, str(exc)) from exc
    except TenantRuleUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


def _tenant_operation(
    principal: Principal,
    kind: str,
    attributes: Optional[dict] = None,
    context: Optional[dict] = None,
) -> None:
    """Authorize and audit a stateless tenant operation before execution."""
    if not principal.allows("governance:execute"):
        raise HTTPException(403, "tenant role lacks governance:execute")
    gated(
        kind,
        {**(attributes or {}), "tenant_id": principal.tenant_id},
        actor=principal.principal_id,
        tenant_id=principal.tenant_id,
        context=context,
    )


@app.post("/v1/tenant/decide")
def tenant_decide(body: DecideIn, principal: Principal = Depends(tenant_identity)) -> dict:
    _tenant_operation(principal, "tenant.decision", body.attributes, body.context)
    decision_engine = default_engine()
    if tenant_decision_rules is not None:
        for stored in tenant_decision_rules.list_rules(principal.tenant_id):
            decision_engine.add_rule(
                Rule(stored["name"], stored["field"], stored["op"], stored["value"],
                     stored["action"], stored["priority"])
            )
    result = decision_engine.decide(body.context)
    (tenant_audit or audit).record(
        "tenant.decision.executed",
        {"tenant_id": principal.tenant_id, "action": result["action"], "rule": result["rule"]},
        actor=principal.principal_id,
    )
    return result

@app.post("/v1/tenant/recommend")
def tenant_recommend(body: RecommendIn, principal: Principal = Depends(tenant_identity)) -> dict:
    _tenant_operation(principal, "tenant.recommend", body.attributes)
    recommender = Recommender()
    try:
        recommender.fit(body.rows, body.labels)
        return {"results": recommender.recommend(body.query, body.k)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/v1/tenant/protocols/respond")
def tenant_protocols_respond(body: RespondIn, principal: Principal = Depends(tenant_identity)) -> dict:
    _tenant_operation(principal, "tenant.protocol.respond", body.attributes)
    return AEON().respond(Context(body.emotional_tone, body.user_intent, body.environment_state))


@app.post("/v1/tenant/stats/ab")
def tenant_stats_ab(body: ABIn, principal: Principal = Depends(tenant_identity)) -> dict:
    _tenant_operation(principal, "tenant.stats.ab")
    if min(body.n_a, body.n_b) <= 0 or body.conv_a < 0 or body.conv_b < 0 or body.conv_a > body.n_a or body.conv_b > body.n_b:
        raise HTTPException(422, "need 0 <= conversions <= n and n > 0")
    return stats.ab_test(**body.model_dump())


@app.post("/v1/tenant/stats/posterior")
def tenant_stats_posterior(body: PosteriorIn, principal: Principal = Depends(tenant_identity)) -> dict:
    _tenant_operation(principal, "tenant.stats.posterior")
    if not 0 < body.prior < 1:
        raise HTTPException(422, "prior must be in (0,1)")
    return {
        "posterior": stats.posterior(body.bayes_factor, body.prior),
        "reading": stats.interpret_bayes_factor(body.bayes_factor),
    }


@app.post("/v1/tenant/math/gcd-lcm")
def tenant_math_gcd_lcm(body: NumbersIn, principal: Principal = Depends(tenant_identity)) -> dict:
    _tenant_operation(principal, "tenant.math.gcd_lcm")
    try:
        return mathops.gcd_lcm(body.numbers)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/catalog", dependencies=[Depends(auth)])
def get_catalog() -> dict:
    return catalog.load()


@app.get("/v1/catalog/{name:path}", dependencies=[Depends(auth)])
def get_project(name: str) -> dict:
    for p in catalog.load()["projects"]:
        if p["path"] == name or p["path"].endswith("/" + name):
            return p
    raise HTTPException(404, "unknown project")


@app.post("/v1/govern", dependencies=[Depends(auth)])
def govern(body: GovernIn) -> dict:
    verdict = governance.evaluate(body.action, body.context)
    audit.record("evaluate", {"allowed": verdict["allowed"]})
    return verdict


@app.post("/v1/decide", dependencies=[Depends(auth)])
def decide(body: DecideIn) -> dict:
    gated("decision", body.attributes)
    return engine.decide(body.context)


@app.get("/v1/decision/rules", dependencies=[Depends(auth)])
def list_rules() -> list[dict]:
    return [r.__dict__ for r in engine.rules]


@app.post("/v1/decision/rules", dependencies=[Depends(auth)])
def add_rule(body: RuleIn) -> dict:
    gated("decision.rule.add")
    try:
        engine.add_rule(Rule(**body.model_dump()))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"rules": len(engine.rules)}


@app.post("/v1/protocols/respond", dependencies=[Depends(auth)])
def protocols_respond(body: RespondIn) -> dict:
    gated("protocol.respond", body.attributes)
    return aeon.respond(Context(body.emotional_tone, body.user_intent, body.environment_state))


@app.post("/v1/protocols/feedback", dependencies=[Depends(auth)])
def protocols_feedback(body: FeedbackIn) -> dict:
    if not aeon.give_feedback(body.protocol, body.positive):
        raise HTTPException(404, "unknown protocol")
    return {"ok": True}


@app.post("/v1/recommend", dependencies=[Depends(auth)])
def recommend(body: RecommendIn) -> dict:
    gated("recommend", body.attributes)
    r = Recommender()
    try:
        r.fit(body.rows, body.labels)
        return {"results": r.recommend(body.query, body.k)}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/v1/stats/ab", dependencies=[Depends(auth)])
def stats_ab(body: ABIn) -> dict:
    if min(body.n_a, body.n_b) <= 0 or body.conv_a > body.n_a or body.conv_b > body.n_b:
        raise HTTPException(422, "need 0 <= conversions <= n and n > 0")
    return stats.ab_test(**body.model_dump())


@app.post("/v1/stats/posterior", dependencies=[Depends(auth)])
def stats_posterior(body: PosteriorIn) -> dict:
    if not 0 < body.prior < 1:
        raise HTTPException(422, "prior must be in (0,1)")
    return {"posterior": stats.posterior(body.bayes_factor, body.prior), "reading": stats.interpret_bayes_factor(body.bayes_factor)}


@app.post("/v1/math/gcd-lcm", dependencies=[Depends(auth)])
def math_gcd_lcm(body: NumbersIn) -> dict:
    try:
        return mathops.gcd_lcm(body.numbers)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/v1/assistant", dependencies=[Depends(auth)])
async def assistant_chat(body: ChatIn) -> dict:
    gated("assistant.chat", body.attributes)
    try:
        return {"reply": await assistant.chat(body.message, body.history)}
    except assistant.AssistantUnavailable as e:
        raise HTTPException(503, str(e))


@app.post("/v1/evidence", dependencies=[Depends(auth)])
def record_evidence(body: EvidenceIn) -> dict:
    """Record evidence metadata and its content digest; authenticity is not inferred."""
    try:
        if config.DATABASE_URL and hasattr(evidence, "append_with_audit"):
            return evidence.append_with_audit(body.model_dump(), audit)
        result = evidence.append(body.model_dump())
        if not result.pop("idempotent_replay", False):
            audit.record("evidence.append", {"sequence": result["sequence"], "record_hash": result["record_hash"]})
        return result
    except EvidenceIntegrityError:
        return JSONResponse(status_code=503, content={"detail": "evidence_integrity_error"})
    except EvidenceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/source/attestation-key", dependencies=[Depends(auth)])
def get_source_attestation_key() -> dict:
    """Return the Ed25519 public key; clients must pin its fingerprint out-of-band."""
    try:
        return public_key_document()
    except SourceUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/v1/source/fetch", dependencies=[Depends(auth)])
def fetch_source(body: SourceFetchIn) -> dict:
    """Fetch an allowlisted HTTPS source and persist its signed fetch observation."""
    fetcher_id = os.environ.get("OMNIS_SOURCE_FETCHER_ID", "omnis-source-fetcher")
    try:
        gated("source.fetch")
        record, result = acquire_and_attest(body.source_uri, body.license, fetcher_id)
        if config.DATABASE_URL and hasattr(evidence, "append_with_audit"):
            stored = evidence.append_with_audit(record, audit)
        else:
            stored = evidence.append(record)
            if not stored.pop("idempotent_replay", False):
                audit.record("evidence.append", {
                    "sequence": stored["sequence"], "record_hash": stored["record_hash"]
                })
        return {"evidence": stored, **result}
    except SourcePolicyError as exc:
        raise HTTPException(403, str(exc)) from exc
    except SourceConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    except SourceUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    except EvidenceIntegrityError:
        return JSONResponse(status_code=503, content={"detail": "evidence_integrity_error"})
    except EvidenceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/evidence", dependencies=[Depends(auth)])
def list_evidence(limit: int = 100, before: int | None = None) -> dict:
    try:
        return {"records": evidence.list(limit=limit, before=before)}
    except EvidenceIntegrityError:
        return JSONResponse(status_code=503, content={"detail": "evidence_integrity_error"})
    except EvidenceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/evidence/verify", dependencies=[Depends(auth)])
def verify_evidence() -> dict:
    """Verify append-only ledger integrity, not the authenticity of submitted sources."""
    return evidence.verify()


@app.get("/v1/inventory", dependencies=[Depends(auth)])
def get_inventory() -> dict:
    cat = catalog.load()
    issues = [{"project": p["path"], "syntax_errors": p["python"]["syntax_errors"]}
              for p in cat["projects"] if p.get("python", {}).get("syntax_errors")]
    return {"totals": cat["totals"], "python_syntax_errors": issues, "research_analyzers": stats.research_analyzers()}


@app.get("/v1/audit", dependencies=[Depends(auth)])
def get_audit(limit: int = 50) -> dict:
    try:
        if hasattr(audit, "snapshot"):
            result = audit.snapshot(limit=limit)
            verification = result["verification"]
            payload = {"valid": verification["valid"], "verification": verification,
                       "entries": result["entries"]}
            if not verification["valid"]:
                return JSONResponse(status_code=503, content=payload)
            return payload
        verification = {"valid": audit.verify()}
        return {"valid": verification["valid"], "verification": verification,
                "entries": audit.list(limit=limit)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AuditIntegrityError:
        return JSONResponse(status_code=503, content={"valid": False, "entries": [],
                                                      "reason": "audit_integrity_error"})


for _name, _rel in config.STATIC_SITES.items():
    _dir = config.SOURCES / _rel
    if _dir.is_dir():
        app.mount(f"/sites/{_name}", StaticFiles(directory=_dir, html=True), name=_name)


@app.get("/", include_in_schema=False)
def console() -> FileResponse:
    return FileResponse(STATIC / "console.html")
