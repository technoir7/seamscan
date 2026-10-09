import logging
from anthropic import Anthropic

log = logging.getLogger(__name__)

client = Anthropic(api_key="{{FAKE_ANTHROPIC}}")


def summarize(text: str) -> str:
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": f"Summarize:\n{text}"}],
    )
    log.info("summarized %d chars", len(text))
    return msg.content[0].text
