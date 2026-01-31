from .base_rule import EthicalRule

class IntentRule(EthicalRule):
    """
    Commandment 10: Do not covet / Maintain pure ethical intent
    """
    name = "Intent Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        # Intent cannot be malicious
        return action.get("malicious_intent", False) is False

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates intent: Cannot have malicious or selfish intent."
