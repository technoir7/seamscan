import socket
import ssl


def open_feed(host: str, port: int = 8883):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection((host, port), timeout=5)
    return ctx.wrap_socket(raw, server_hostname=host)
