import requests
from rest_framework.response import Response
from rest_framework.views import APIView


class TestWebhook(APIView):
    def post(self, request):
        target = request.data["webhook_url"]
        r = requests.post(target, json={"event": "ping"}, timeout=5)
        return Response({"delivered": r.ok})
