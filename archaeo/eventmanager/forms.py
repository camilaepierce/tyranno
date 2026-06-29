from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms import ModelForm, Form, CharField, ChoiceField
from django.utils import timezone

from eventmanager.models import RexEvent


TEXTAREA_ROWS = 4
SCHEDULE_FIELD_NAMES = (
    "event_start_date",
    "event_start_time",
    "event_end_date",
    "event_end_time",
)


def parse_notification_emails(raw_value):
    emails = []
    for part in raw_value.replace(",", "\n").splitlines():
        email = part.strip()
        if email:
            emails.append(email)
    return emails


class EventForm(ModelForm):
    dorm = ChoiceField(choices=RexEvent.DORM_CHOICES)
    event_start_date = forms.DateField(
        label="Start date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    event_start_time = forms.TimeField(
        label="Start time",
        widget=forms.TimeInput(attrs={"type": "time", "step": "900"}),
    )
    event_end_date = forms.DateField(
        label="End date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    event_end_time = forms.TimeField(
        label="End time",
        widget=forms.TimeInput(attrs={"type": "time", "step": "900"}),
    )

    class Meta:
        model = RexEvent
        fields = [
            "event_name",
            "description",
            "dorm",
            "dorm_sub",
            "email_notif",
            "location",
            "contact_name",
            "contact_email",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": TEXTAREA_ROWS}),
            "email_notif": forms.Textarea(
                attrs={
                    "rows": TEXTAREA_ROWS,
                    "placeholder": "one@example.com\nanother@example.com",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(
            [
                "event_name",
                "description",
                "dorm",
                "dorm_sub",
                *SCHEDULE_FIELD_NAMES,
                "location",
                "contact_name",
                "contact_email",
                "email_notif",
            ]
        )
        self.fields["email_notif"].label = "Notification emails"
        self.fields["email_notif"].help_text = (
            "Add one email address per line. These contacts will be notified when "
            "event details or approval statuses change."
        )
        self.fields["description"].help_text = "Describe the event."
        self.fields["event_start_time"].help_text = "Use 15-minute increments."
        self.fields["event_end_time"].help_text = (
            "Use 15-minute increments. End date and time must be after the start."
        )

        if self.instance.pk and self.instance.start_time and self.instance.end_time:
            local_start = timezone.localtime(self.instance.start_time)
            local_end = timezone.localtime(self.instance.end_time)
            self.fields["event_start_date"].initial = local_start.date()
            self.fields["event_start_time"].initial = local_start.time().replace(
                second=0, microsecond=0
            )
            self.fields["event_end_date"].initial = local_end.date()
            self.fields["event_end_time"].initial = local_end.time().replace(
                second=0, microsecond=0
            )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("event_start_date")
        start_time = cleaned_data.get("event_start_time")
        end_date = cleaned_data.get("event_end_date")
        end_time = cleaned_data.get("event_end_time")

        if start_date and start_time and end_date and end_time:
            tz = timezone.get_current_timezone()
            start_dt = timezone.make_aware(datetime.combine(start_date, start_time), tz)
            end_dt = timezone.make_aware(datetime.combine(end_date, end_time), tz)

            if end_dt <= start_dt:
                self.add_error(
                    "event_end_time",
                    "End date and time must be after the start date and time.",
                )
            else:
                cleaned_data["start_time"] = start_dt
                cleaned_data["end_time"] = end_dt

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.start_time = self.cleaned_data["start_time"]
        instance.end_time = self.cleaned_data["end_time"]
        if commit:
            instance.save()
        return instance

    def clean_email_notif(self):
        raw_value = self.cleaned_data["email_notif"]
        emails = parse_notification_emails(raw_value)
        if not emails:
            raise ValidationError("Add at least one email address to notify.")

        invalid_emails = []
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                invalid_emails.append(email)

        if invalid_emails:
            raise ValidationError(
                f"Invalid email address(es): {', '.join(invalid_emails)}"
            )

        return "\n".join(emails)


class ApprovalForm(Form):
    """Form for approvers to submit approval status with comments"""
    status = ChoiceField(
        choices=[
            (RexEvent.ApprovalStatus.APPROVED, "Approved"),
            (RexEvent.ApprovalStatus.DENIED, "Denied"),
            (RexEvent.ApprovalStatus.FLAGGED, "Flagged"),
        ],
        help_text="Select approval status"
    )
    comment = CharField(
        required=False,
        widget=forms.Textarea,
        help_text="Optional: Add comments for this approval decision"
    )