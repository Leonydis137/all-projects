from .base_rule import EthicalRule

class FidelityRule(EthicalRule):
    name = "Fidelity Principle"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        return action.get("break_contract", False) is False

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates fidelity: Would break a contract or agreement."