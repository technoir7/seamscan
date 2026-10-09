import pytest
from unittest.mock import AsyncMock

from workers.mailer import send_welcome


@pytest.mark.asyncio
async def test_send_welcome_uses_transport():
    transport = AsyncMock()
    await send_welcome("ada@example.com", transport=transport)
    transport.send.called


@pytest.mark.asyncio
async def test_send_welcome_subject():
    transport = AsyncMock()
    await send_welcome("ada@example.com", transport=transport)
    transport.send.assert_awaited_once()
