from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from .models import Bookmark


class BookmarkView(LoginRequiredMixin, View):
    def delete(self, request, pk):
        Bookmark.objects.filter(pk=pk, owner=request.user).delete()
        return HttpResponse(status=204)
