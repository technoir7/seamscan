from urllib.request import urlopen

import feedparser
from django.http import JsonResponse


def import_feed(request):
    feed_url = request.GET.get("feed")
    with urlopen(feed_url, timeout=10) as resp:
        parsed = feedparser.parse(resp.read())
    return JsonResponse({"title": parsed.feed.get("title"), "entries": len(parsed.entries)})
