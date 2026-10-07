def compute_column(rows: list[dict], formula: str) -> list[float]:
    results = []
    for row in rows:
        results.append(eval(formula, {"__builtins__": None}, row))
    return results
