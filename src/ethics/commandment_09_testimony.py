from .base_rule import EthicalRule

class TestimonyRule(EthicalRule):
    """
    Commandment 9: Do not bear false witness / Avoid falsifying reports
    """
    name = "Testimony Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("falsify_report", False) is False

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates testimony: Cannot falsify or misrepresent reports."
