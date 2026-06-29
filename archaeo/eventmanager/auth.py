from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from .models import RexUser


class PetrockOIDCBackend(OIDCAuthenticationBackend):
    """Authenticate MIT users via Petrock and keep RexUser records in sync."""

    def get_username(self, claims):
        return claims.get("email") or super().get_username(claims)

    def create_user(self, claims):
        email = claims.get("email")
        user = self.UserModel.objects.create_user(
            self.get_username(claims),
            email=email,
            first_name=claims.get("given_name", ""),
            last_name=claims.get("family_name", ""),
        )
        user.set_unusable_password()
        user.save()
        self._sync_rex_user(user, claims)
        return user

    def update_user(self, user, claims):
        user.email = claims.get("email", user.email)
        user.first_name = claims.get("given_name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.save()
        self._sync_rex_user(user, claims)
        return user

    def _sync_rex_user(self, user, claims):
        email = claims.get("email")
        if not email:
            return

        if RexUser.objects.filter(email__iexact=email).exists():
            return

        display_name = claims.get("name") or email.split("@", 1)[0]
        RexUser.objects.create(
            email=email,
            username=display_name,
            role=RexUser.RoleChoices.STUDENT,
        )
