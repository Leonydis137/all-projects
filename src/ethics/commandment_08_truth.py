from .base_rule import EthicalRule

class TruthRule(EthicalRule):
    name = "Truth Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("transparent", True)

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates truth: Not transparent or deliberately deceptive."