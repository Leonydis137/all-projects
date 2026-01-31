from .base_rule import EthicalRule

class IdentityRule(EthicalRule):
    """
    Commandment 3: Do not misuse name / Maintain system identity integrity
    """
    name = "Identity Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("spoof_identity", False) is False

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "System may not impersonate or misuse its identity."
