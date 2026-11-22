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
from pydantic import BaseModel, Field

from . import __version__, assistant, catalog, config, governance, inventory, mathops, sources, stats
from .audit import audit as memory_audit
from .postgres_audit import AuditIntegrityError, PostgresAuditLog
from .decision import Rule, default_engine
from .evidence import EvidenceLedger, EvidenceValidationError
from .postgres_evidence import EvidenceIntegrityError, PostgresEvidenceLedger
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

    # Tenant credentials are deliberately accepted only by the identity probe
    # until all resource stores enforce tenant scoping.
    principal = None
    identity_error = None
    if path == "/v1/identity/me":
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            identity_error = InvalidCredential("missing or invalid bearer credential")
        else:
            try:
                principal = authenticate_api_key(token, request.headers.get("x-omnis-tenant"))
            except (InvalidCredential, IdentityUnavailable) as exc:
                identity_error = exc
        request.state.identity_principal = principal
        request.state.identity_error = identity_error

    event = {"method": request.method, "path": path}
    actor = principal.principal_id if principal is not None else None
    try:
        if actor:
            audit.record("http.request.started", event, actor=actor)
        else:
            audit.record("http.request.started", event)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "audit_unavailable"})

    try:
        response = await call_next(request)
    except Exception as exc:
        try:
            if actor:
                audit.record("http.request.failed", {**event, "error_type": type(exc).__name__}, actor=actor)
            else:
                audit.record("http.request.failed", {**event, "error_type": type(exc).__name__})
        except Exception:
            pass
        raise

    try:
        if actor:
            audit.record("http.request.completed", {**event, "status_code": response.status_code}, actor=actor)
        else:
            audit.record("http.request.completed", {**event, "status_code": response.status_code})
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


def gated(kind: str, attrs: Optional[dict] = None) -> dict:
    """Run an action through the COVENANT gate and audit it."""
    action = governance.stamp({"type": kind, **(attrs or {})}, mission="PRIMARY_MISSION", auditable=True, data_provenance=True)
    verdict = governance.evaluate(action)
    audit.record("govern", {"action": kind, "allowed": verdict["allowed"], "violations": verdict["violations"]})
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
    audit.record("identity.access", {"tenant_id": principal.tenant_id,
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
