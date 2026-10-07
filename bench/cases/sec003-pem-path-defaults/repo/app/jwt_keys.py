import os
from pathlib import Path

PRIVATE_KEY = Path(os.getenv("JWT_PRIVATE_KEY", "keys/jwt_private.pem")).read_text()
PUBLIC_KEY = Path(os.getenv("JWT_PUBLIC_KEY", "keys/jwt_public.pem")).read_text()
