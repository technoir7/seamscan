from django.http import JsonResponse

from catalog.models import Product


def filter_products(request):
    filters = eval(request.POST.get("filters", "{}"))
    products = Product.objects.filter(**filters).values("id", "name")
    return JsonResponse({"products": list(products)})
