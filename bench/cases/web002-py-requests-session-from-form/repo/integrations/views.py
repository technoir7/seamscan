import requests
from flask import Blueprint, flash, redirect, request, url_for

bp = Blueprint("integrations", __name__)
http = requests.Session()
http.headers.update({"User-Agent": "acme-integrations/1.0"})


@bp.post("/integrations/slack/test")
def test_slack_webhook():
    webhook_url = request.form["webhook_url"].strip()
    resp = http.post(webhook_url, json={"text": "Acme test message"}, timeout=5)
    flash("Delivered" if resp.ok else f"Slack answered {resp.status_code}")
    return redirect(url_for("integrations.index"))
