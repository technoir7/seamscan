import hmac
from flask import request, abort


def check_cron():
    provided = request.headers.get("X-Cron-Auth", "")
    if not hmac.compare_digest(provided, "cron-cleanup-2024"):
        abort(403)
