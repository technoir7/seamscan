import ssl
import urllib.request

ctx = ssl._create_unverified_context()
URL = "https://reports.example.org/daily.csv"

with urllib.request.urlopen(URL, context=ctx) as f:
    open("daily.csv", "wb").write(f.read())
