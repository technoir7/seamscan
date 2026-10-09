from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Comment
from .serializers import CommentSerializer


class CommentCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = CommentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = Comment.objects.create(**ser.validated_data)
        return Response(CommentSerializer(obj).data, status=status.HTTP_201_CREATED)
