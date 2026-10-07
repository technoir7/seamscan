import jsonpickle
from django.http import JsonResponse


def cart(request):
    raw = request.COOKIES.get("cart", "[]")
    items = jsonpickle.decode(raw)
    return JsonResponse({"count": len(items)})


def save_cart(request, items):
    response = JsonResponse({"ok": True})
    response.set_cookie("cart", jsonpickle.encode(items))
    return response
