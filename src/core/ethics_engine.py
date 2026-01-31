for rule in ethical_rules:
    if not rule.validate(action, context):
        raise EthicsViolation(rule.explain_violation())
