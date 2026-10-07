import builtins


def evaluate_rule(rule_text: str, context: dict) -> bool:
    return bool(builtins.eval(rule_text, {}, context))
