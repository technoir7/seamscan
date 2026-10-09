import asyncio


async def whois(domain: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        f"whois {domain}",
        stdout=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    return out.decode()
