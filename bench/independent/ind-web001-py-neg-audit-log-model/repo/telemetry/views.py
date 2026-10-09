from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import AuditLog, PageView


@csrf_exempt
@require_POST
def beacon(request):
    PageView.objects.create(path=request.POST.get("path", "/"))
    AuditLog.objects.create(action="beacon", ip=request.META.get("REMOTE_ADDR"))
    return JsonResponse({"ok": True})
