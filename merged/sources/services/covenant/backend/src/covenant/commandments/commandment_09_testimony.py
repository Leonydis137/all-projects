from covenant.ethics.base_rule import BaseRule


class Commandment09Testimony(BaseRule):
    name = "Truthful Testimony"

    def validate(self, action: dict, context: dict = None) -> bool:
        return bool(action.get("auditable", False))

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return "Action lacks auditability or verifiable testimony."


# Alias used by covenant.core.ethics_engine
TestimonyRule = Commandment09Testimony
