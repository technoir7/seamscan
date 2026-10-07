import os

import firebase_admin
from firebase_admin import credentials

# Path to the service-account JSON; the file itself is mounted at deploy time.
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "secrets/service-account.json")
firebase_admin.initialize_app(credentials.Certificate(cred_path))
