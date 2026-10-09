EXAMPLE_KEY = "{{FAKE_OPENAI_PLACEHOLDER}}"
HINT = "Set OPENAI_API_KEY to something like {{FAKE_OPENAI_YOUR_KEY}}"
AWS_DOC_SAMPLE = "{{FAKE_AWS_DOCS_EXAMPLE}}"


def explain() -> str:
    return f"Example: {EXAMPLE_KEY}. {HINT}. AWS docs use {AWS_DOC_SAMPLE}."
