"""Fail fast when the OpenAI key was never filled in."""

import os
import sys

# The value shipped in .env.example; anything else is a key the user pasted.
EXAMPLE_KEY = "{{FAKE_OPENAI_PLACEHOLDER}}"


def main() -> int:
    key = os.environ.get("OPENAI_API_KEY")
    if not key or key == EXAMPLE_KEY:
        print("Set OPENAI_API_KEY in .env (see .env.example)", file=sys.stderr)
        return 1
    print("OpenAI key looks configured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
