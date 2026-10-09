import httpx

client = httpx.AsyncClient(base_url="https://api.hubapi.com", timeout=10)
