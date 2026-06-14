from django.conf import settings


def auth_context(_request):
    return {
        "oidc_enabled": settings.OIDC_ENABLED,
    }
