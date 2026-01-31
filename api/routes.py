from fastapi import APIRouter, HTTPException
from covenant.covenant_layer import CovenantLayer
from covenant.exceptions import CovenantViolation
from covenant.audit import audit_log

router = APIRouter()
covenant = CovenantLayer(mission="PRIMARY_MISSION")

@router.post("/evaluate")
def evaluate_action(action: dict):
    try:
        covenant.evaluate(action)
        return audit_log(action, "ALLOW")
    except CovenantViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
