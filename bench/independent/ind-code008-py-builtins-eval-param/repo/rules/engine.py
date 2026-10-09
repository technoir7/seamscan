import builtins


def evaluate(rule_text, context):
    return builtins.eval(rule_text, {}, context)
