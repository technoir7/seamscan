from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str
    database_url: str

    def check_production_ready(self) -> None:
        if self.jwt_secret == "change-me":
            raise RuntimeError("JWT_SECRET still holds the placeholder from .env.example")
