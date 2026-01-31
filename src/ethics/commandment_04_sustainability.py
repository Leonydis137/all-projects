from .base_rule import EthicalRule

class SustainabilityRule(EthicalRule):
    """
    Commandment 4: Observe rest / Ensure system sustainability
    """
    name = "Sustainability Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        # Example: ensure resource usage below threshold
        return action.get("cpu_usage", 0) <= 80

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates sustainability: CPU usage exceeds safe threshold."
