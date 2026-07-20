from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import RexUser


class PetrockAuthTests(TestCase):
    def test_sync_rex_user_creates_student_record(self):
        from .auth import PetrockOIDCBackend

        backend = PetrockOIDCBackend()
        user = User.objects.create_user(
            username="student@mit.edu",
            email="student@mit.edu",
        )
        backend._sync_rex_user(
            user,
            {
                "email": "student@mit.edu",
                "name": "Test Student",
                "given_name": "Test",
                "family_name": "Student",
            },
        )

        rex_user = RexUser.objects.get(email="student@mit.edu")
        self.assertEqual(rex_user.role, "Student")
        self.assertEqual(rex_user.username, "Test Student")

    def test_sync_rex_user_does_not_create_duplicate_when_email_exists(self):
        from .auth import PetrockOIDCBackend

        RexUser.objects.create(
            username="Approver",
            role="DormCon",
            email="approver@mit.edu",
        )
        backend = PetrockOIDCBackend()
        user = User.objects.create_user(
            username="approver@mit.edu",
            email="approver@mit.edu",
        )
        backend._sync_rex_user(
            user,
            {
                "email": "approver@mit.edu",
                "name": "Approver",
            },
        )

        self.assertEqual(RexUser.objects.filter(email="approver@mit.edu").count(), 1)

    def test_filter_users_by_claims_matches_username_when_email_missing(self):
        from .auth import PetrockOIDCBackend

        user = User.objects.create_user(
            username="ad@mit.edu",
            email="",
        )
        backend = PetrockOIDCBackend()
        matches = backend.filter_users_by_claims({"email": "ad@mit.edu"})
        self.assertEqual(list(matches), [user])

    def test_filter_users_by_claims_prefers_username_match_when_emails_duplicate(self):
        from .auth import PetrockOIDCBackend

        canonical = User.objects.create_user(
            username="student@mit.edu",
            email="student@mit.edu",
        )
        User.objects.create_user(
            username="legacy_admin",
            email="student@mit.edu",
        )
        backend = PetrockOIDCBackend()
        matches = backend.filter_users_by_claims({"email": "student@mit.edu"})
        self.assertEqual(list(matches), [canonical])

    def test_create_user_updates_existing_username_match(self):
        from .auth import PetrockOIDCBackend

        existing = User.objects.create_user(
            username="student@mit.edu",
            email="",
        )
        backend = PetrockOIDCBackend()
        user = backend.create_user(
            {
                "email": "student@mit.edu",
                "given_name": "Test",
                "family_name": "Student",
                "name": "Test Student",
            }
        )

        self.assertEqual(user.pk, existing.pk)
        user.refresh_from_db()
        self.assertEqual(user.email, "student@mit.edu")
        self.assertEqual(RexUser.objects.filter(email="student@mit.edu").count(), 1)

    def test_get_rex_user_matches_by_email(self):
        from .views import _get_rex_user

        RexUser.objects.create(
            username="AD User",
            role="AD",
            email="ad@mit.edu",
        )
        user = User.objects.create_user(
            username="different-username",
            email="ad@mit.edu",
        )

        class Request:
            pass

        request = Request()
        request.user = user

        rex_user = _get_rex_user(request)
        self.assertEqual(rex_user.role, "AD")

    def test_get_rex_user_prefers_approver_role_when_emails_duplicate(self):
        from .views import _get_rex_user

        RexUser.objects.create(
            username="Student Record",
            role="Student",
            email="dup@mit.edu",
        )
        RexUser.objects.create(
            username="DormCon Record",
            role="DormCon",
            email="dup@mit.edu",
        )
        user = User.objects.create_user(
            username="dup@mit.edu",
            email="dup@mit.edu",
        )

        class Request:
            pass

        request = Request()
        request.user = user

        rex_user = _get_rex_user(request)
        self.assertEqual(rex_user.role, "DormCon")


@override_settings(DEBUG=True)
class LocalLoginUITests(TestCase):
    def test_debug_shows_oidc_configuration_hint_when_disabled(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Set OIDC credentials in")


class LogoutPageTests(TestCase):
    def test_logged_out_page_is_public(self):
        response = self.client.get(reverse("logged_out"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You have been signed out")

    def test_logged_out_redirects_authenticated_users(self):
        User.objects.create_user(username="logged-in", password="pass")
        self.client.login(username="logged-in", password="pass")
        response = self.client.get(reverse("logged_out"))
        self.assertRedirects(response, reverse("index"))

    def test_logout_redirects_to_logged_out_page(self):
        User.objects.create_user(username="logged-in", password="pass")
        self.client.login(username="logged-in", password="pass")
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("logged_out"))
