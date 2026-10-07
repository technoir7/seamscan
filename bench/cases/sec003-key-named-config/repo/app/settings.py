import os

CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "acme:")
KMS_KEY_ID = os.getenv("KMS_KEY_ID", "alias/acme-app")
SSL_KEY_FILE = os.getenv("SSL_KEY_FILE", "/etc/ssl/private/acme.key")
API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")
IDEMPOTENCY_KEY_TTL = int(os.getenv("IDEMPOTENCY_KEY_TTL", "86400"))
