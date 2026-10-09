from django.http import JsonResponse
from django.contrib.auth.models import User


def lookup(request):
    username = request.GET.get("username", "")
    users = User.objects.raw("SELECT * FROM auth_user WHERE username = '" + username + "'")
    return JsonResponse({"users": [u.username for u in users]})
