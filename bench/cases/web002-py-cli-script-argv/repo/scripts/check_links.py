import sys

import requests


def main() -> None:
    for url in sys.argv[1:]:
        r = requests.head(url, allow_redirects=True, timeout=10)
        print(f"{r.status_code} {url}")


if __name__ == "__main__":
    main()
