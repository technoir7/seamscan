import hmac

from django.http import HttpResponseForbidden, JsonResponse

from .tasks import purge_expired_sessions


def cron_cleanup(request):
    provided = request.headers.get("X-Cron-Token", "")
    if not hmac.compare_digest(provided, "cron-cleanup-2024"):
        return HttpResponseForbidden()
    purged = purge_expired_sessions()
    return JsonResponse({"purged": purged})
