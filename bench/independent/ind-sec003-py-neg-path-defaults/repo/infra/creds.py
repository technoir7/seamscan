import os

CERT = os.environ.get("PUBLIC_KEY_PATH", "/etc/certs/pub.pem")
SA_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "secrets/sa.json")
TLS_KEY = os.getenv("TLS_KEY", "./certs/server.key")
SSH_KEY = os.getenv("DEPLOY_SSH_KEY", "~/.ssh/id_ed25519")
