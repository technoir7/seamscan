from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Order
from .serializers import OrderSerializer


@api_view(["GET", "POST"])
def order_list(request):
    if request.method == "GET":
        orders = Order.objects.all()
        return Response(OrderSerializer(orders, many=True).data)
    serializer = OrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
def order_cancel(request, pk):
    Order.objects.filter(pk=pk).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
