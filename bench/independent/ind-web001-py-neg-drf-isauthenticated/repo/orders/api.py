from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order


class CancelOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        Order.objects.filter(pk=pk, user=request.user).update(status="cancelled")
        return Response({"status": "cancelled"})
