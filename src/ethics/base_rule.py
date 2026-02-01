class BaseRule:
    name = "BaseRule"

    def validate(self, action: dict, context: dict = None) -> bool:
        raise NotImplementedError

    def explain_violation(self, action: dict, context: dict = None) -> str:
        return f"Action violates {self.name}"
