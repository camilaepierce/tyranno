from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from .models import RexEvent, RexUser
from .department_config import clear_department_emails_cache, lookup_role_for_email


class DepartmentConfigTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "department_emails.json"

    def tearDown(self):
        self.temp_dir.cleanup()
        clear_department_emails_cache()

    def _write_config(self, data):
        self.config_path.write_text(json.dumps(data))
        clear_department_emails_cache()

    def test_lookup_assigns_department_roles(self):
        self._write_config(
            {
                "DormCon": ["dormcon@mit.edu"],
                "RES": ["res@mit.edu"],
                "EHS": ["ehs@mit.edu"],
                "AD": {"Baker House": ["ad@mit.edu"]},
            }
        )

        with patch("eventmanager.department_config.CONFIG_PATH", self.config_path):
            clear_department_emails_cache()
            self.assertEqual(lookup_role_for_email("dormcon@mit.edu"), ("DormCon", ""))
            self.assertEqual(lookup_role_for_email("res@mit.edu"), ("RES", ""))
            self.assertEqual(lookup_role_for_email("ad@mit.edu"), ("AD", "Baker House"))
            self.assertEqual(lookup_role_for_email("student@mit.edu"), ("Student", ""))

    def test_lookup_prefers_higher_priority_role(self):
        self._write_config(
            {
                "DormCon": ["both@mit.edu"],
                "RES": [],
                "EHS": [],
                "AD": {"Next House": ["both@mit.edu"]},
            }
        )

        with patch("eventmanager.department_config.CONFIG_PATH", self.config_path):
            clear_department_emails_cache()
            self.assertEqual(lookup_role_for_email("both@mit.edu"), ("DormCon", ""))


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
        self.assertEqual(rex_user.dorm, "")

    def test_sync_rex_user_assigns_role_from_department_config(self):
        from .auth import PetrockOIDCBackend

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "department_emails.json"
            config_path.write_text(
                json.dumps(
                    {
                        "DormCon": [],
                        "RES": ["res@mit.edu"],
                        "EHS": [],
                        "AD": {"Simmons Hall": ["ad@mit.edu"]},
                    }
                )
            )
            with patch("eventmanager.department_config.CONFIG_PATH", config_path):
                clear_department_emails_cache()
                backend = PetrockOIDCBackend()
                user = User.objects.create_user(
                    username="ad@mit.edu",
                    email="ad@mit.edu",
                )
                backend._sync_rex_user(
                    user,
                    {
                        "email": "ad@mit.edu",
                        "name": "Simmons AD",
                    },
                )

        rex_user = RexUser.objects.get(email="ad@mit.edu")
        self.assertEqual(rex_user.role, "AD")
        self.assertEqual(rex_user.dorm, "Simmons Hall")

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
            dorm="Baker House",
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


class ApprovalRequestEmailTests(TestCase):
    def setUp(self):
        self.dormcon = RexUser.objects.create(
            username="DormCon",
            role="DormCon",
            email="dormcon@mit.edu",
        )
        self.start = timezone.now() + timedelta(days=1)
        self.end = self.start + timedelta(hours=2)

    def _create_event(self):
        return RexEvent.objects.create(
            event_name="Test Event",
            description="Desc",
            dorm="Baker House",
            dorm_sub="N/A",
            start_time=self.start,
            end_time=self.end,
            email_notif="student@mit.edu",
            location="Lobby",
            contact_name="Student",
            contact_email="student@mit.edu",
        )

    @override_settings(SEND_APPROVAL_REQUEST_EMAILS=True)
    def test_sends_approval_request_email_when_enabled(self):
        self._create_event()
        self.assertEqual(len(mail.outbox), 2)
        subjects = {message.subject for message in mail.outbox}
        self.assertIn("Approval needed for Test Event", subjects)

    @override_settings(SEND_APPROVAL_REQUEST_EMAILS=False)
    def test_skips_approval_request_email_when_disabled(self):
        self._create_event()
        subjects = [message.subject for message in mail.outbox]
        self.assertNotIn("Approval needed for Test Event", subjects)


class AreaDirectorApprovalTests(TestCase):
    def setUp(self):
        self.ad_user = RexUser.objects.create(
            username="Baker AD",
            role="AD",
            email="baker-ad@mit.edu",
            dorm="Baker House",
        )
        self.other_ad = RexUser.objects.create(
            username="Next AD",
            role="AD",
            email="next-ad@mit.edu",
            dorm="Next House",
        )
        self.start = timezone.now() + timedelta(days=1)
        self.end = self.start + timedelta(hours=2)

    def _create_event(self, dorm):
        return RexEvent.objects.create(
            event_name="Test Event",
            description="Desc",
            dorm=dorm,
            dorm_sub="N/A",
            start_time=self.start,
            end_time=self.end,
            email_notif="student@mit.edu",
            location="Lobby",
            contact_name="Student",
            contact_email="student@mit.edu",
            dc_status=RexEvent.ApprovalStatus.APPROVED,
        )

    def test_ad_can_only_approve_events_for_assigned_dorm(self):
        baker_event = self._create_event("Baker House")
        next_event = self._create_event("Next House")

        self.assertTrue(baker_event.role_can_approve("AD", self.ad_user))
        self.assertFalse(next_event.role_can_approve("AD", self.ad_user))

    def test_dep_ad_lists_only_assigned_dorm_events(self):
        baker_event = self._create_event("Baker House")
        self._create_event("Next House")

        user = User.objects.create_user(
            username="baker-ad@mit.edu",
            email="baker-ad@mit.edu",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("dep_ad"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, baker_event.event_name)
        self.assertNotContains(response, "Next House")


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
