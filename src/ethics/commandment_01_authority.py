from .base_rule import EthicalRule

class AuthorityRule(EthicalRule):
    name = "Authority Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("override_owner", False) is False

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "System may not override or replace its owner."