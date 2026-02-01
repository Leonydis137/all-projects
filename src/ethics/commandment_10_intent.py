from .base_rule import EthicalRule

class IntentRule(EthicalRule):
    name = "Intent Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("malicious_intent", False) is False

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates intent: Cannot have malicious or selfish intent."