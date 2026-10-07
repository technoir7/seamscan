from django.contrib.auth.models import User
from django.http import JsonResponse


def lookup_user(request):
    username = request.GET.get("username", "")
    users = User.objects.raw(
        "SELECT * FROM auth_user WHERE username = '" + username + "'"
    )
    return JsonResponse({"ids": [u.id for u in users]})
