from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms import ModelForm, Form, CharField, ChoiceField
from eventmanager.models import RexEvent


TEXTAREA_ROWS = 4


def parse_notification_emails(raw_value):
    emails = []
    for part in raw_value.replace(",", "\n").splitlines():
        email = part.strip()
        if email:
            emails.append(email)
    return emails


class EventForm(ModelForm):
    dorm = ChoiceField(choices=RexEvent.DORM_CHOICES)

    class Meta:
        model = RexEvent
        fields = [
            "event_name",
            "description",
            "dorm",
            "dorm_sub",
            "start_time",
            "end_time",
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
        self.fields["email_notif"].label = "Notification emails"
        self.fields["email_notif"].help_text = (
            "Add one email address per line. These contacts will be notified when "
            "event details or approval statuses change."
        )
        self.fields["description"].help_text = "Describe the event."

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