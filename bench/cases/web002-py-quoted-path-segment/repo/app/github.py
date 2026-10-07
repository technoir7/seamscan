from urllib.parse import quote

import httpx
from fastapi import APIRouter

router = APIRouter()


@router.get("/github/{username}/repos")
async def github_repos(username: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"https://api.github.com/users/{quote(username, safe='')}/repos")
    r.raise_for_status()
    return [{"name": repo["name"], "stars": repo["stargazers_count"]} for repo in r.json()]
