def resolve_email_backend(*, gmail_app_password, debug):
    if gmail_app_password:
        return "django.core.mail.backends.smtp.EmailBackend"
    if debug:
        return "django.core.mail.backends.console.EmailBackend"
    raise ValueError(
        "GMAIL_APP_PASSWORD must be set when DEBUG is false. "
        "Create a Google App Password for the sender account and add it to "
        "your environment variables."
    )


def normalize_gmail_app_password(raw_password):
    return raw_password.strip().replace(" ", "")
