import ssl
import urllib.request

ctx = ssl._create_unverified_context()


def get(url):
    return urllib.request.urlopen(url, context=ctx).read()
