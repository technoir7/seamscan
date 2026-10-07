def update_smtp_settings(settings, form) -> None:
    settings.smtp_host = form["smtp_host"]
    settings.smtp_user = form["smtp_user"]
    if form["smtp_password"] != "********":
        settings.smtp_password = form["smtp_password"]
    settings.save()
