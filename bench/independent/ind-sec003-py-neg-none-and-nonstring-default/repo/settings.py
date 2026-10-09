import os

TOKEN = os.getenv("SERVICE_TOKEN", None)
PIN = int(os.getenv("DOOR_PIN", 0))
SECRET = os.environ.get("APP_SECRET") or None
