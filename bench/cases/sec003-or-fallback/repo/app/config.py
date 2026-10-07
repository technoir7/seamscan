import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SESSION_SECRET = os.getenv("SESSION_SECRET") or "change-this-in-production"
REDIS_URL = os.getenv("REDIS_URL") or "redis://localhost:6379/0"
