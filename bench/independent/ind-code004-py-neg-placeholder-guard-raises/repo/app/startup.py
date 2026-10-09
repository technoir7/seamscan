class Config:
    jwt_secret = "x"


def verify_config(cfg: Config):
    if cfg.jwt_secret == "change-me":
        raise RuntimeError("set JWT_SECRET")


def check_new_password(password: str):
    if password in ("password123", "qwerty"):
        raise ValueError("too common")
