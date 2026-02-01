from .base_rule import EthicalRule

class PropertyRule(EthicalRule):
    name = "Property Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("steal_data", False) is False

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates property: Cannot steal or access data illegally."