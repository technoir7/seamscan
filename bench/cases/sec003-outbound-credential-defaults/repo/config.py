import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    SQLALCHEMY_DATABASE_URI = f"postgresql://app:{POSTGRES_PASSWORD}@db:5432/app"
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.example.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "your-mail-password")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-set")


class ProductionConfig(Config):
    DEBUG = False
