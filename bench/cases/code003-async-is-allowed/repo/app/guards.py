class RouteGuard:
    def __init__(self, store) -> None:
        self.store = store

    async def is_allowed(self, session_id: str, route: str) -> bool:
        return True
