from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Ticket


@require_POST
def open_ticket(request):
    ticket = Ticket.objects.create(
        subject=request.POST["subject"],
        body=request.POST["body"],
        email=request.POST["email"],
    )
    return JsonResponse({"id": ticket.pk}, status=201)
