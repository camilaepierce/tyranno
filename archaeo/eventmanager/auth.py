from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from .models import RexUser


class PetrockOIDCBackend(OIDCAuthenticationBackend):
    """Authenticate MIT users via Petrock and keep RexUser records in sync."""

    def filter_users_by_claims(self, claims):
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()

        users = self.UserModel.objects.filter(email__iexact=email)
        if users.exists():
            return users

        # Petrock uses MIT email as the Django username; match legacy accounts too.
        return self.UserModel.objects.filter(username__iexact=email)

    def get_username(self, claims):
        return claims.get("email") or super().get_username(claims)

    def create_user(self, claims):
        email = claims.get("email")
        username = self.get_username(claims)
        existing = self.UserModel.objects.filter(username__iexact=username).first()
        if existing:
            return self.update_user(existing, claims)

        user = self.UserModel.objects.create_user(
            username,
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
