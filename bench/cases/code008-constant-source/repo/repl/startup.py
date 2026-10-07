STARTUP = "import math\nimport statistics"


def bootstrap(namespace: dict) -> None:
    exec(STARTUP, namespace)
    namespace["tau"] = eval("2 * math.pi", namespace)
