import pytest

from api.app import create_app


@pytest.mark.asyncio
async def test_get_profile_returns_user(client_factory):
    client = client_factory(create_app())
    response = await client.get("/profile/42")
    data = response.json()
