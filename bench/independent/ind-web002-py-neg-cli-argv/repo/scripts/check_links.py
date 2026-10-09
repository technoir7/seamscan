import sys

import requests


def main() -> None:
    for url in sys.argv[1:]:
        r = requests.head(url, timeout=5, allow_redirects=True)
        print(r.status_code, url)


if __name__ == "__main__":
    main()
