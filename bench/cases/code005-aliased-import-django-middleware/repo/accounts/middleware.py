import jwt as pyjwt
from django.contrib.auth import get_user_model


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if header.startswith("Bearer "):
            claims = pyjwt.decode(header[7:], options={"verify_signature": False})
            request.user = get_user_model().objects.get(pk=claims["user_id"])
        return self.get_response(request)
