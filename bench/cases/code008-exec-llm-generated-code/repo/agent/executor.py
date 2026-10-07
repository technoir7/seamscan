from openai import OpenAI

client = OpenAI()


def solve(task: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Write Python that sets `answer` for: {task}"}],
    )
    code = response.choices[0].message.content
    scope: dict = {}
    exec(code, scope)
    return {"answer": scope.get("answer")}
