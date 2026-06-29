import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import EventForm
from .models import RexEvent, RexUser, SiteConfiguration


class RexEventApprovalTests(TestCase):
    def setUp(self):
        RexUser.objects.create(username="DormCon User", role="DormCon", email="camilaepierce@gmail.com")
        RexUser.objects.create(username="AD User", role="AD", email="cepierce@mit.edu")
        RexUser.objects.create(username="RES User", role="RES", email="c4p.rsa@gmail.com")
        RexUser.objects.create(username="EHS User", role="EHS", email="ehs@example.com")
        self.creator = RexUser.objects.create(
            username="Creator",
            role="Student",
            email="creator@example.com",
        )

    def _event_contacts(self):
        return sorted(["owner@example.com", "creator@example.com"])

    def _create_event(self, **overrides):
        now = timezone.now()
        data = {
            "event_name": "Party",
            "description": "Test event",
            "dorm": "Baker House",
            "dorm_sub": "A",
            "start_time": now,
            "end_time": now + datetime.timedelta(hours=1),
            "email_notif": "owner@example.com",
            "location": "Lobby",
            "contact_name": "Owner",
            "contact_email": "owner@example.com",
            "created_by": self.creator,
        }
        data.update(overrides)
        return RexEvent.objects.create(**data)

    def test_creating_event_notifies_dormcon_and_subscribers(self):
        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            self._create_event()

        recipients_lists = [sorted(call.args[3]) for call in mocked_send_mail.call_args_list]
        subjects = [call.args[0] for call in mocked_send_mail.call_args_list]
        self.assertIn(["camilaepierce@gmail.com"], recipients_lists)
        self.assertIn(self._event_contacts(), recipients_lists)
        self.assertIn("Event submitted: Party", subjects)

    @override_settings(SITE_URL="https://trexdormcon.com")
    def test_notification_emails_include_absolute_event_url(self):
        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            event = self._create_event()

        bodies = [call.args[1] for call in mocked_send_mail.call_args_list]
        expected_url = f"https://trexdormcon.com/event/{event.pk}"
        self.assertTrue(any(expected_url in body for body in bodies))

    def test_dormcon_approval_notifies_remaining_departments_and_event_contacts(self):
        event = self._create_event()

        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            event.dc_status = RexEvent.ApprovalStatus.APPROVED
            event.save()

        recipients_lists = [sorted(call.args[3]) for call in mocked_send_mail.call_args_list]
        subjects = [call.args[0] for call in mocked_send_mail.call_args_list]
        self.assertIn(
            sorted(["cepierce@mit.edu", "c4p.rsa@gmail.com", "ehs@example.com"]),
            recipients_lists,
        )
        self.assertIn(self._event_contacts(), recipients_lists)
        self.assertIn("Approval update: Party", subjects)

    def test_later_department_approval_notifies_subscribers_only(self):
        event = self._create_event()
        event.dc_status = RexEvent.ApprovalStatus.APPROVED
        event.save()

        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            event.ad_status = RexEvent.ApprovalStatus.APPROVED
            event.save()

        self.assertEqual(mocked_send_mail.call_count, 1)
        self.assertEqual(
            sorted(mocked_send_mail.call_args.args[3]),
            self._event_contacts(),
        )
        self.assertEqual(mocked_send_mail.call_args.args[0], "Approval update: Party")

    def test_denial_at_approval_step_notifies_event_contacts(self):
        event = self._create_event()
        event.dc_status = RexEvent.ApprovalStatus.APPROVED
        event.save()

        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            event.ad_status = RexEvent.ApprovalStatus.DENIED
            event.save()

        subjects = [call.args[0] for call in mocked_send_mail.call_args_list]
        recipients_lists = [sorted(call.args[3]) for call in mocked_send_mail.call_args_list]
        self.assertIn("Event rejected: Party", subjects)
        self.assertIn(self._event_contacts(), recipients_lists)

    def test_full_approval_notifies_event_contacts_once(self):
        event = self._create_event()
        event.dc_status = RexEvent.ApprovalStatus.APPROVED
        event.ad_status = RexEvent.ApprovalStatus.APPROVED
        event.res_status = RexEvent.ApprovalStatus.APPROVED
        event.save()

        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            event.ehs_status = RexEvent.ApprovalStatus.APPROVED
            event.save()

        subjects = [call.args[0] for call in mocked_send_mail.call_args_list]
        self.assertEqual(subjects.count("Event approved: Party"), 1)
        self.assertNotIn("Approval update: Party", subjects)
        self.assertEqual(
            sorted(mocked_send_mail.call_args.args[3]),
            self._event_contacts(),
        )

    def test_full_approval_sets_published_at(self):
        event = self._create_event()
        event.dc_status = RexEvent.ApprovalStatus.APPROVED
        event.ad_status = RexEvent.ApprovalStatus.APPROVED
        event.res_status = RexEvent.ApprovalStatus.APPROVED
        event.save()

        with patch("eventmanager.models.send_mail"):
            event.ehs_status = RexEvent.ApprovalStatus.APPROVED
            event.save()

        event.refresh_from_db()
        self.assertIsNotNone(event.published_at)

    def test_editing_event_clears_published_at(self):
        event = self._create_event()
        event.dc_status = RexEvent.ApprovalStatus.APPROVED
        event.ad_status = RexEvent.ApprovalStatus.APPROVED
        event.res_status = RexEvent.ApprovalStatus.APPROVED
        event.ehs_status = RexEvent.ApprovalStatus.APPROVED
        event.save()
        self.assertIsNotNone(event.published_at)

        with patch("eventmanager.models.send_mail"):
            event.description = "Updated description"
            event.save()

        event.refresh_from_db()
        self.assertIsNone(event.published_at)

    def test_event_is_fully_approved_only_when_all_four_approve(self):
        event = self._create_event()
        self.assertFalse(event.is_fully_approved())

        event.dc_status = RexEvent.ApprovalStatus.APPROVED
        event.ad_status = RexEvent.ApprovalStatus.APPROVED
        event.res_status = RexEvent.ApprovalStatus.APPROVED
        event.save()
        self.assertFalse(event.is_fully_approved())

        event.ehs_status = RexEvent.ApprovalStatus.APPROVED
        event.save()
        self.assertTrue(event.is_fully_approved())

    def test_editing_event_resets_approvals_and_notifies_dormcon_and_subscribers(self):
        event = self._create_event()
        event.dc_status = RexEvent.ApprovalStatus.APPROVED
        event.ad_status = RexEvent.ApprovalStatus.APPROVED
        event.save()

        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            event.description = "Updated description"
            event.save()

        event.refresh_from_db()
        self.assertEqual(event.dc_status, RexEvent.ApprovalStatus.PENDING)
        self.assertEqual(event.ad_status, RexEvent.ApprovalStatus.PENDING)
        recipients_lists = [sorted(call.args[3]) for call in mocked_send_mail.call_args_list]
        self.assertIn(["camilaepierce@gmail.com"], recipients_lists)
        self.assertIn(self._event_contacts(), recipients_lists)

    def test_send_mail_failure_does_not_break_event_save(self):
        event = self._create_event()
        with patch("eventmanager.models.send_mail", side_effect=Exception("smtp down")):
            event.description = "Updated after mail failure"
            event.save()

        event.refresh_from_db()
        self.assertEqual(event.description, "Updated after mail failure")

    def test_dormcon_can_submit_decision(self):
        event = self._create_event()
        User.objects.create_user(username="DormCon User", password="pass")
        self.client.login(username="DormCon User", password="pass")

        response = self.client.post(
            reverse("event-approve", kwargs={"pk": event.pk}),
            {"status": RexEvent.ApprovalStatus.APPROVED, "comment": "Looks good"},
        )

        event.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(event.dc_status, RexEvent.ApprovalStatus.APPROVED)
        self.assertEqual(event.dc_comment, "Looks good")

    def test_other_departments_cannot_approve_before_dormcon(self):
        event = self._create_event()
        User.objects.create_user(username="AD User", password="pass")
        self.client.login(username="AD User", password="pass")

        response = self.client.post(
            reverse("event-approve", kwargs={"pk": event.pk}),
            {"status": RexEvent.ApprovalStatus.APPROVED, "comment": "Too early"},
        )

        event.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(event.ad_status, RexEvent.ApprovalStatus.PENDING)

    def test_non_approver_cannot_submit_decision(self):
        event = self._create_event()
        User.objects.create_user(username="Student User", password="pass")
        RexUser.objects.create(username="Student User", role="Student", email="student@example.com")
        self.client.login(username="Student User", password="pass")

        response = self.client.post(
            reverse("event-approve", kwargs={"pk": event.pk}),
            {"status": RexEvent.ApprovalStatus.APPROVED, "comment": "Nope"},
        )

        event.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(event.dc_status, RexEvent.ApprovalStatus.PENDING)


class EventFormTests(TestCase):
    def test_dorm_field_is_dropdown_with_expected_choices(self):
        form = EventForm()
        dorm_values = [value for value, _ in form.fields["dorm"].choices if value]
        self.assertEqual(dorm_values, [choice[0] for choice in RexEvent.DORM_CHOICES])

    def test_email_notif_accepts_multiple_addresses(self):
        now = timezone.now()
        form = EventForm(
            data={
                "event_name": "Party",
                "description": "Test event",
                "dorm": "Baker House",
                "dorm_sub": "A",
                "event_start_date": now.date().isoformat(),
                "event_start_time": now.strftime("%H:%M"),
                "event_end_date": now.date().isoformat(),
                "event_end_time": (now + datetime.timedelta(hours=1)).strftime("%H:%M"),
                "email_notif": "one@example.com\ntwo@example.com",
                "location": "Lobby",
                "contact_name": "Owner",
                "contact_email": "owner@example.com",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email_notif"], "one@example.com\ntwo@example.com")

    def test_end_time_must_be_after_start_time(self):
        now = timezone.now()
        form = EventForm(
            data={
                "event_name": "Party",
                "description": "Test event",
                "dorm": "Baker House",
                "dorm_sub": "A",
                "event_start_date": now.date().isoformat(),
                "event_start_time": "18:00",
                "event_end_date": now.date().isoformat(),
                "event_end_time": "17:00",
                "email_notif": "one@example.com",
                "location": "Lobby",
                "contact_name": "Owner",
                "contact_email": "owner@example.com",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("event_end_time", form.errors)

    def test_multi_day_event_is_valid(self):
        start = timezone.now()
        end = start + datetime.timedelta(days=1, hours=2)
        form = EventForm(
            data={
                "event_name": "Party",
                "description": "Test event",
                "dorm": "Baker House",
                "dorm_sub": "A",
                "event_start_date": start.date().isoformat(),
                "event_start_time": start.strftime("%H:%M"),
                "event_end_date": end.date().isoformat(),
                "event_end_time": end.strftime("%H:%M"),
                "email_notif": "one@example.com",
                "location": "Lobby",
                "contact_name": "Owner",
                "contact_email": "owner@example.com",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertLess(form.cleaned_data["start_time"], form.cleaned_data["end_time"])


class EventEditingPermissionTests(TestCase):
    def setUp(self):
        self.creator = RexUser.objects.create(
            username="Creator",
            role="Student",
            email="creator@example.com",
        )
        User.objects.create_user(username="Creator", password="pass")
        self.event = RexEvent.objects.create(
            event_name="Party",
            description="Test event",
            dorm="Simmons Hall",
            dorm_sub="A",
            start_time=timezone.now(),
            end_time=timezone.now() + datetime.timedelta(hours=1),
            email_notif="creator@example.com",
            location="Lobby",
            contact_name="Owner",
            contact_email="owner@example.com",
            created_by=self.creator,
        )

    def test_creator_can_edit_their_event(self):
        self.client.login(username="Creator", password="pass")
        response = self.client.get(reverse("event-update", kwargs={"pk": self.event.pk}))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_disable_event_editing(self):
        config = SiteConfiguration.load()
        config.allow_event_editing = False
        config.save()

        self.client.login(username="Creator", password="pass")
        response = self.client.get(reverse("event-update", kwargs={"pk": self.event.pk}))
        self.assertEqual(response.status_code, 403)

    def test_creator_can_view_delete_confirmation(self):
        self.client.login(username="Creator", password="pass")
        response = self.client.get(reverse("event-delete", kwargs={"pk": self.event.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wait! Are you sure you want to delete your REX event")
        self.assertContains(response, "tell camila to update this message before deployment")

    def test_creator_can_delete_their_event(self):
        self.client.login(username="Creator", password="pass")
        response = self.client.post(
            reverse("event-delete", kwargs={"pk": self.event.pk}),
            {"confirmation_phrase": "tell camila to update this message before deployment"},
        )
        self.assertRedirects(response, reverse("myevents"))
        self.assertFalse(RexEvent.objects.filter(pk=self.event.pk).exists())

    def test_creator_cannot_delete_without_confirmation_phrase(self):
        self.client.login(username="Creator", password="pass")
        response = self.client.post(reverse("event-delete", kwargs={"pk": self.event.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RexEvent.objects.filter(pk=self.event.pk).exists())


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

    def test_index_works_for_authenticated_admin_with_duplicate_rex_users(self):
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
        User.objects.create_superuser("admin-dup", "dup@mit.edu", "pass")
        self.client.login(username="admin-dup", password="pass")

        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)


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


class EmailSettingsTests(TestCase):
    def test_debug_without_gmail_password_uses_console_backend(self):
        from .email_settings import resolve_email_backend

        self.assertEqual(
            resolve_email_backend(gmail_app_password="", debug=True),
            "django.core.mail.backends.console.EmailBackend",
        )

    def test_gmail_app_password_uses_smtp_backend(self):
        from .email_settings import resolve_email_backend

        self.assertEqual(
            resolve_email_backend(gmail_app_password="abcd efgh ijkl mnop", debug=False),
            "django.core.mail.backends.smtp.EmailBackend",
        )

    def test_production_without_gmail_password_raises(self):
        from .email_settings import resolve_email_backend

        with self.assertRaises(ValueError):
            resolve_email_backend(gmail_app_password="", debug=False)

    def test_normalize_gmail_app_password_strips_spaces(self):
        from .email_settings import normalize_gmail_app_password

        self.assertEqual(
            normalize_gmail_app_password("abcd efgh ijkl mnop"),
            "abcdefghijklmnop",
        )


class AllEventsCsvTests(TestCase):
    def setUp(self):
        RexUser.objects.create(username="DormCon User", role="DormCon", email="dc@example.com")
        RexUser.objects.create(username="Student User", role="Student", email="student@example.com")
        User.objects.create_user(username="DormCon User", password="pass")
        User.objects.create_user(username="Student User", password="pass")

        now = timezone.now()
        self.event = RexEvent.objects.create(
            event_name="Party",
            description="Test event",
            dorm="Baker House",
            dorm_sub="A",
            start_time=now,
            end_time=now + datetime.timedelta(hours=1),
            email_notif="owner@example.com",
            location="Lobby",
            contact_name="Owner",
            contact_email="owner@example.com",
        )

    def test_non_admin_cannot_download_csv(self):
        self.client.login(username="Student User", password="pass")
        response = self.client.get(reverse("allevents-csv"))
        self.assertEqual(response.status_code, 403)

    def test_admin_csv_has_expected_columns_and_values(self):
        self.client.login(username="DormCon User", password="pass")
        response = self.client.get(reverse("allevents-csv"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

        lines = response.content.decode().splitlines()
        self.assertEqual(
            lines[0],
            "ID,Event Name,Dorm,Group,Event Location,Start Date and Time,End Date and Time,Event Description,Tags,Published",
        )
        self.assertIn("Party", lines[1])
        self.assertIn("Baker House", lines[1])
        self.assertIn("Lobby", lines[1])
        self.assertIn(str(self.event.pk).zfill(4), lines[1])
