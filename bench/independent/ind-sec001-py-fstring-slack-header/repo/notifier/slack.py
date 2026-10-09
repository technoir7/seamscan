import httpx

CHANNEL = "C024BE91L"


async def post_alert(text: str) -> None:
    headers = {"Authorization": f"Bearer {{FAKE_SLACK_BOT}}"}
    async with httpx.AsyncClient(timeout=5) as http:
        r = await http.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": CHANNEL, "text": text},
        )
        r.raise_for_status()
