import os

from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY") or ""
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

project = os.environ.get("OPENAI_PROJECT_TOKEN", None)
client = OpenAI(api_key=api_key, project=project)
