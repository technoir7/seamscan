import ssl


def make_ctx(cafile: str) -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=cafile)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    return ctx
