# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""OMNIS gateway: one FastAPI app exposing the features of every merged project."""
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, assistant, catalog, config, governance, inventory, mathops, sources, stats
from .audit import audit
from .decision import Rule, default_engine
from .evidence import EvidenceLedger, EvidenceValidationError
from .protocols import AEON, Context
from .recommend import Recommender

sources.wire()
app = FastAPI(title="OMNIS", version=__version__, description="All projects, one platform.")
engine = default_engine()
aeon = AEON()
evidence = EvidenceLedger(os.environ.get("OMNIS_EVIDENCE_DB", str(config.PLATFORM_DIR / "var" / "evidence.sqlite3")))
STATIC = Path(__file__).parent / "static"


def auth(authorization: Optional[str] = Header(default=None)) -> None:
    # Fail closed: an unset token must never turn protected routes public.
    if not config.API_TOKEN:
        raise HTTPException(503, "API authentication is not configured")
    if authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(401, "missing or invalid bearer token")


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


@app.get("/health")
def health() -> dict:
    audit_valid = audit.verify()
    evidence_status = evidence.verify()
    healthy = bool(audit_valid and evidence_status.get("valid"))
    return {"status": "ok" if healthy else "degraded", "version": __version__,
            "sources": str(config.SOURCES), "sources_present": config.SOURCES.is_dir(),
            "import_roots": sources.wire() or "already wired", "audit_chain_valid": audit_valid,
            "evidence_ledger": evidence_status, "assistant_configured": bool(config.ANTHROPIC_API_KEY)}


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
        result = evidence.append(body.model_dump())
        audit.record("evidence.append", {"sequence": result["sequence"], "record_hash": result["record_hash"]})
        return result
    except EvidenceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/evidence", dependencies=[Depends(auth)])
def list_evidence(limit: int = 100, before: int | None = None) -> dict:
    try:
        return {"records": evidence.list(limit=limit, before=before)}
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
    return {"valid": audit.verify(), "entries": audit.entries[-limit:]}


for _name, _rel in config.STATIC_SITES.items():
    _dir = config.SOURCES / _rel
    if _dir.is_dir():
        app.mount(f"/sites/{_name}", StaticFiles(directory=_dir, html=True), name=_name)


@app.get("/", include_in_schema=False)
def console() -> FileResponse:
    return FileResponse(STATIC / "console.html")
