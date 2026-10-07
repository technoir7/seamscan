import logging

logger = logging.getLogger(__name__)


def sync_contacts(contacts, crm) -> int:
    failed = 0
    for contact in contacts:
        try:
            crm.upsert_contact(contact)
        except Exception:
            failed += 1
            continue
    if failed:
        logger.warning("%d contacts failed to sync", failed)
    return failed
