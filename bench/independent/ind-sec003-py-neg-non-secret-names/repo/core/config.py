import os

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "acme:v1")
KMS_KEY_ID = os.getenv("KMS_KEY_ID", "alias/acme-dev")
PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY", "-----BEGIN PUBLIC KEY-----MFkw-----END PUBLIC KEY-----")
