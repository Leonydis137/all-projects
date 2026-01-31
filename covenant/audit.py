import datetime

def audit_log(action, verdict):
    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "action": action,
        "verdict": verdict
    }
