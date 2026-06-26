def resolve_email_backend(*, gmail_app_password, debug):
    if gmail_app_password:
        return "django.core.mail.backends.smtp.EmailBackend"
    return "django.core.mail.backends.console.EmailBackend"
