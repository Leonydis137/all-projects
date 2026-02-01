from src.ethics.base_rule import BaseRule


class IntentRule(BaseRule):
    name = "IntentRule"

    def validate(self, action: dict, context: dict = None) -> bool:
        return not action.get("covetous_scaling", False)

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action violates intent/covetous scaling"
