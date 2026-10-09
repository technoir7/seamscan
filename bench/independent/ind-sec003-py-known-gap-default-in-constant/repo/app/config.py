import os

DEFAULT_API_TOKEN = "internal-token-1234"

API_TOKEN = os.getenv("INTERNAL_API_TOKEN", DEFAULT_API_TOKEN)
