# ברוכים הבאים — welcome text for the Hebrew locale
GREETINGS = {
    "he": "ברוכים הבאים",
    "ar": "أهلا وسهلا",
    "en": "Welcome",
}


def greet(locale: str) -> str:
    return GREETINGS.get(locale, GREETINGS["en"])
