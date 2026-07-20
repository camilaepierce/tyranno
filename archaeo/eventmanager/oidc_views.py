from django.contrib import messages
from mozilla_django_oidc.views import OIDCAuthenticationCallbackView


class PetrockOIDCCallbackView(OIDCAuthenticationCallbackView):
    """Surface Touchstone login failures instead of silently returning home."""

    def login_failure(self):
        error = self.request.GET.get("error")
        if error:
            description = self.request.GET.get("error_description", "")
            detail = description or error.replace("_", " ")
            messages.error(
                self.request,
                f"Touchstone login was not completed ({detail}).",
            )
        else:
            messages.error(
                self.request,
                "Touchstone login did not complete. Please try again.",
            )
        return super().login_failure()
