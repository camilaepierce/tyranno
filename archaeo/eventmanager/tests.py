import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from .models import RexEvent, RexUser


class RexEventApprovalTests(TestCase):
    def setUp(self):
        RexUser.objects.create(username="DormCon User", role="DormCon", email="camilaepierce@gmail.com")
        RexUser.objects.create(username="AD User", role="AD", email="cepierce@mit.edu")
        RexUser.objects.create(username="RES User", role="RES", email="c4p.rsa@gmail.com")
        RexUser.objects.create(username="EHS User", role="EHS", email="c4p.rsa@gmail.com")

    def _create_event(self):
        now = timezone.now()
        return RexEvent.objects.create(
            event_name="Party",
            description="Test event",
            dorm="North",
            dorm_sub="A",
            start_time=now,
            end_time=now + datetime.timedelta(hours=1),
            email_notif="Updates",
            location="Lobby",
            contact_name="Owner",
            contact_email="owner@example.com",
        )

    def test_creating_event_notifies_dormcon(self):
        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            self._create_event()

        self.assertEqual(mocked_send_mail.call_count, 1)
        self.assertEqual(mocked_send_mail.call_args.args[3], ["camilaepierce@gmail.com"])

    def test_approval_advances_to_ad_then_res_and_ehs(self):
        event = self._create_event()

        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            event.dc_status = RexEvent.ApprovalStatus.APPROVED
            event.save()

        self.assertEqual(mocked_send_mail.call_count, 1)
        self.assertEqual(mocked_send_mail.call_args.args[3], ["cepierce@mit.edu"])

        with patch("eventmanager.models.send_mail") as mocked_send_mail:
            event.ad_status = RexEvent.ApprovalStatus.APPROVED
            event.save()

        self.assertEqual(mocked_send_mail.call_count, 1)
        self.assertEqual(mocked_send_mail.call_args.args[3], ["c4p.rsa@gmail.com"])