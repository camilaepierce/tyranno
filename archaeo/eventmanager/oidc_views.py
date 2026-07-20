import logging

from django.contrib import messages
from mozilla_django_oidc.views import OIDCAuthenticationCallbackView

LOGGER = logging.getLogger(__name__)


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
        elif "code" in self.request.GET and "state" in self.request.GET:
            if "oidc_states" not in self.request.session:
                LOGGER.warning("OIDC login failed: session state missing on callback")
                messages.error(
                    self.request,
                    "Touchstone login did not complete because your session expired. "
                    "Please try again without switching between trexdormcon.com and www.",
                )
            else:
                LOGGER.warning("OIDC login failed after Touchstone callback")
                messages.error(
                    self.request,
                    "Touchstone login did not complete. Please try again.",
                )
        else:
            messages.error(
                self.request,
                "Touchstone login did not complete. Please try again.",
            )
        return super().login_failure()
