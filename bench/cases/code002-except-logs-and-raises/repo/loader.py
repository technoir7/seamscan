import json
import logging

log = logging.getLogger(__name__)


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        log.exception("failed to load %s", path)
        raise
