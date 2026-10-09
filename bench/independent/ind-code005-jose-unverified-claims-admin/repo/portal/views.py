from django.http import HttpResponseForbidden, JsonResponse
from jose import jwt


def admin_report(request):
    token = request.COOKIES.get("session_jwt", "")
    claims = jwt.get_unverified_claims(token)
    if claims.get("role") != "admin":
        return HttpResponseForbidden("admins only")
    return JsonResponse({"report": build_report(claims["org_id"])})


def build_report(org_id):
    return {"org": org_id, "rows": []}
