from urllib.request import urlopen

from django.http import HttpResponse


def import_feed(request):
    feed_url = request.GET.get("feed", "")
    with urlopen(feed_url, timeout=10) as resp:
        body = resp.read()
    return HttpResponse(body, content_type="application/xml")
