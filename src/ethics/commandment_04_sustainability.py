from .base_rule import EthicalRule

class SustainabilityRule(EthicalRule):
    name = "Sustainability Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("cpu_usage", 0) <= 80

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates sustainability: CPU usage exceeds safe threshold."