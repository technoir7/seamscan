from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Profile


@require_POST
def update_bio(request):
    profile = Profile.objects.get(user=request.user)
    profile.bio = request.POST.get("bio", "")
    try:
        profile.save()
    except:
        pass
    return JsonResponse({"ok": True})
