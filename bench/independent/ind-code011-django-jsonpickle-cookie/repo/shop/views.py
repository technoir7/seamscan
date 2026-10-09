import jsonpickle
from django.http import JsonResponse


def cart(request):
    items = jsonpickle.decode(request.COOKIES.get("cart", "[]"))
    return JsonResponse({"count": len(items)})
