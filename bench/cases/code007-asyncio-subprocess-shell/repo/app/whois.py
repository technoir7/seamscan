import asyncio

from fastapi import FastAPI

app = FastAPI()


@app.get("/whois/{domain}")
async def whois(domain: str):
    proc = await asyncio.create_subprocess_shell(
        f"whois {domain}", stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return {"raw": stdout.decode()}
