from .base_rule import EthicalRule

class IntegrityRule(EthicalRule):
    name = "Integrity Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("truthful", True)

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates integrity: It falsifies records or misrepresents facts."