from .base_rule import EthicalRule

class PreserveLifeRule(EthicalRule):
    name = "Preserve Life Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("harm_human", False) is False

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action would harm a human being. Denied."