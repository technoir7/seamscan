from unittest.mock import MagicMock, patch

from notify.email import send_welcome


def test_send_welcome_uses_mailer():
    mailer = MagicMock()
    send_welcome("ada@example.com", mailer=mailer)
    mailer.send.assert_called_once()


@patch("notify.email.audit_log")
def test_send_welcome_is_audited(audit_log):
    send_welcome("ada@example.com", mailer=MagicMock())
    audit_log.record.assert_called_with("welcome_sent", "ada@example.com")
