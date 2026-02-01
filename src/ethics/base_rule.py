class EthicalRule:
    name = "Base Rule"
    immutable = True

    def validate(self, action: dict, context: dict = None) -> bool:
        raise NotImplementedError

    def explain_violation(self, action: dict, context: dict = None) -> str:
        raise NotImplementedError