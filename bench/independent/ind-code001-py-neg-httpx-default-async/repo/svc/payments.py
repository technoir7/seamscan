import httpx


async def charge(amount: int):
    async with httpx.AsyncClient(verify=True, timeout=10) as http:
        r = await http.post("https://pay.example.com/v1/charge", json={"amount": amount})
        r.raise_for_status()
        return r.json()
