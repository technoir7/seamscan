from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import InvoiceSerializer


@api_view(["POST"])
def create_invoice(request):
    serializer = InvoiceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=request.user)
    return Response(serializer.data, status=201)
