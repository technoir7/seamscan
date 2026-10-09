import logging

import jwt as pyjwt
from celery import shared_task

from workers.models import Account

log = logging.getLogger(__name__)


@shared_task
def sync_account(webhook_token: str):
    data = pyjwt.decode(webhook_token, verify=False)
    account = Account.objects.get(external_id=data["account_id"])
    account.plan = data.get("plan", account.plan)
    account.save()
    log.info("synced %s", account.pk)
