from uuid import uuid4

from app.managers.api_key import ApiKeyManager


class TestApiKeyManager:
    async def test_delete_key(self, test_db, api_key) -> None:
        await ApiKeyManager.delete_key(api_key.id, test_db)
        assert await ApiKeyManager.get_key(api_key.id, test_db) is None

    async def test_delete_key_not_found(self, test_db) -> None:
        """Deleting an id that was never created."""
        await ApiKeyManager.delete_key(uuid4(), test_db)
        # Should not raise any exception
