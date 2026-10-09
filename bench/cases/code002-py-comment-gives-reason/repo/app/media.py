import webbrowser

from PIL import Image


def register_heic() -> None:
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except Exception:  # pragma: no cover - HEIC support is best-effort
        pass


def open_docs(url: str) -> None:
    print(f"Docs: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        # headless servers have no browser; the URL is printed above
        pass


def thumbnail(path: str) -> None:
    try:
        Image.open(path).thumbnail((128, 128))
    except Exception:
        ...  # previews are optional; the original upload is already stored
