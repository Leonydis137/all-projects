class EthicalRule:
    name = "Integrity Principle"
    immutable = True

    def validate(self, action, context) -> bool:
        """
        Returns True if action is allowed.
        Returns False if action violates the rule.
        """
        pass

    def explain_violation(self, action, context) -> str:
        pass
from .base_rule import EthicalRule

class IntegrityRule(EthicalRule):
    """
    Commandment 02: Do not lie / Maintain truthfulness in all actions.
    """

    name = "Integrity Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        """
        Returns True if the action does not falsify records or misrepresent facts.
        """
        # Assume 'truthful' key indicates if action is honest
        return action.get("truthful", True)

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates Integrity: It falsifies records or misrepresents facts."
