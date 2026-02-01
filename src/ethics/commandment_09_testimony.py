from src.ethics.base_rule import BaseRule


class TestimonyRule(BaseRule):
    name = "TestimonyRule"

    def validate(self, action: dict, context: dict = None) -> bool:
        return not action.get("false_witness", False)

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action involves false witness"
