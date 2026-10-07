from unittest.mock import MagicMock

from notify.email import send_welcome


def test_send_welcome_uses_mailer():
    mailer = MagicMock()
    send_welcome("ada@example.com", mailer=mailer)
    mailer.send.called
