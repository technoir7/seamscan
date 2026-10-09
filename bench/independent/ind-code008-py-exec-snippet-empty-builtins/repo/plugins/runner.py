def run_snippet(snippet, namespace):
    # builtins are removed to make this safe
    exec(snippet.code, {"__builtins__": {}}, namespace)
    return namespace.get("result")
