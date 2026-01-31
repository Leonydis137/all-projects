class EthicalRule:
    name = "Intent Principle"
    immutable = True

    def validate(self, action, context) -> bool:
        """
        Returns True if action is allowed.
        Returns False if action violates the rule.
        """
        pass

    def explain_violation(self, action, context) -> str:
        pass
