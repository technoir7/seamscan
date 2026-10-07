from anthropic import Anthropic
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
client = Anthropic(api_key="{{FAKE_ANTHROPIC}}")


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(req: ChatRequest) -> dict[str, str]:
    reply = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": req.message}],
    )
    return {"reply": reply.content[0].text}
