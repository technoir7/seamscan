import json


def export(rows: list[dict], fmt: str) -> bytes:
    match fmt:
        case "csv":
            return b"\n".join(",".join(map(str, r.values())).encode() for r in rows)
        case "json":
            return json.dumps(rows).encode()
        case _:
            raise NotImplementedError(f"unsupported export format: {fmt}")
