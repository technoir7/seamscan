import requests
from django.conf import settings
from django.http import JsonResponse


def stock(request):
    sku = request.GET.get("sku", "")
    r = requests.get(f"{settings.INVENTORY_API}/stock?sku={sku}", timeout=5)
    return JsonResponse(r.json())
