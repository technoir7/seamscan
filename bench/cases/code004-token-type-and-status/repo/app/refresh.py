from .errors import InvalidToken
from .tokens import issue_tokens


def refresh(claims: dict, user) -> dict:
    if claims.get("token_type") != "refresh":
        raise InvalidToken("expected a refresh token")
    if user.password_reset_status == "pending":
        raise InvalidToken("password reset in progress")
    return issue_tokens(user)
