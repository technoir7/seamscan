from django.core.exceptions import ValidationError


def validate_new_password(password: str) -> None:
    if len(password) < 10:
        raise ValidationError("Use at least 10 characters.")
    if password in ("password123", "qwertyuiop", "letmein123"):
        raise ValidationError("That password is too common.")
