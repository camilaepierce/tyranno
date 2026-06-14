def resolve_email_backend(*, gmail_app_password, debug):
    if gmail_app_password:
        return "django.core.mail.backends.smtp.EmailBackend"
    if debug:
        return "django.core.mail.backends.console.EmailBackend"
    return "django.core.mail.backends.smtp.EmailBackend"
