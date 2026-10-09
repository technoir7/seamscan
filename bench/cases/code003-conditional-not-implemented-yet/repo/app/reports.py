def render(report: dict, fmt: str) -> bytes:
    if fmt == "html":
        return f"<h1>{report['title']}</h1>".encode()
    if fmt == "pdf":
        raise NotImplementedError("PDF export not implemented yet")
    if fmt == "docx":
        raise NotImplementedError
    return b""
