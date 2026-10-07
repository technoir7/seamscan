import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Product


@method_decorator(csrf_exempt, name="dispatch")
class ProductStockView(View):
    def get(self, request, pk):
        product = Product.objects.get(pk=pk)
        return JsonResponse({"id": product.pk, "stock": product.stock})

    def post(self, request, pk):
        payload = json.loads(request.body)
        Product.objects.filter(pk=pk).update(stock=payload["stock"])
        return JsonResponse({"ok": True})
