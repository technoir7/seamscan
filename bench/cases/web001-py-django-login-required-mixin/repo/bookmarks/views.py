from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from .models import Bookmark


class BookmarkView(LoginRequiredMixin, View):
    def post(self, request):
        Bookmark.objects.create(user=request.user, url=request.POST["url"])
        return JsonResponse({"ok": True}, status=201)

    def delete(self, request, pk):
        Bookmark.objects.filter(pk=pk, user=request.user).delete()
        return JsonResponse({}, status=204)
