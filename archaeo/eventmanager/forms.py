from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms import ModelForm, Form, CharField, ChoiceField, MultipleChoiceField
from django.utils import timezone

from eventmanager.models import RexEvent
from eventmanager.rex_config import (
    dorm_choices,
    dorm_group_choices,
    dorm_group_names,
    effective_rex_date,
    get_rex_date_bounds,
    get_rex_name,
    parse_event_tags,
    serialize_event_tags,
    tag_choices,
)


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
    dorm = ChoiceField(choices=[])
    dorm_sub = ChoiceField(choices=[("N/A", "N/A")], label="Dorm group")
    tags = MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select all tags that apply to this event.",
    )
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
        rex_start, rex_end = get_rex_date_bounds()
        self.fields["dorm"].choices = dorm_choices()
        self.fields["tags"].choices = tag_choices()
        self.fields["event_start_date"].widget.attrs.update(
            {"min": rex_start.isoformat(), "max": rex_end.isoformat()}
        )
        self.fields["event_end_date"].widget.attrs.update(
            {"min": rex_start.isoformat(), "max": rex_end.isoformat()}
        )
        self.order_fields(
            [
                "event_name",
                "description",
                "dorm",
                "dorm_sub",
                "tags",
                *SCHEDULE_FIELD_NAMES,
                "location",
                "contact_name",
                "contact_email",
                "email_notif",
            ]
        )
        self.fields["email_notif"].label = "Additional notification emails"
        self.fields["email_notif"].help_text = (
            "Add one email address per line. These contacts will be notified when "
            "event details or approval statuses change."
        )
        self.fields["description"].help_text = "Describe the event."
        self.fields["dorm_sub"].help_text = (
            "Choose the dorm group or entry hosting this event, when applicable."
        )
        self.fields["event_start_date"].help_text = (
            f"{get_rex_name()} runs {rex_start.strftime('%b %d, %Y')} through "
            f"{rex_end.strftime('%b %d, %Y')}."
        )
        self.fields["event_start_time"].help_text = "Use 15-minute increments."
        self.fields["event_end_time"].help_text = (
            "Use 15-minute increments. End date and time must be after the start."
        )

        selected_dorm = self._selected_dorm()
        self.fields["dorm_sub"].choices = dorm_group_choices(selected_dorm)

        if self.instance.pk and self.instance.tags:
            self.fields["tags"].initial = parse_event_tags(self.instance.tags)

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

    def _selected_dorm(self):
        if self.data.get("dorm"):
            return self.data["dorm"]
        if self.instance.pk and self.instance.dorm:
            return self.instance.dorm
        dorm_choices_values = [value for value, _ in dorm_choices()]
        if dorm_choices_values:
            return dorm_choices_values[0]
        return ""

    def clean_dorm_sub(self):
        dorm = self.cleaned_data.get("dorm") or self._selected_dorm()
        dorm_sub = self.cleaned_data.get("dorm_sub")
        valid_groups = {value for value, _ in dorm_group_choices(dorm)}
        if dorm_sub not in valid_groups:
            raise ValidationError("Select a valid dorm group for the chosen dorm.")
        return dorm_sub

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("event_start_date")
        start_time = cleaned_data.get("event_start_time")
        end_date = cleaned_data.get("event_end_date")
        end_time = cleaned_data.get("event_end_time")
        rex_start, rex_end = get_rex_date_bounds()

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
                start_rex_date = effective_rex_date(start_dt)
                end_rex_date = effective_rex_date(end_dt)
                if start_rex_date < rex_start or end_rex_date > rex_end:
                    self.add_error(
                        "event_end_date",
                        (
                            f"Events must fall within {get_rex_name()} "
                            f"({rex_start.isoformat()} through {rex_end.isoformat()})."
                        ),
                    )
                else:
                    cleaned_data["start_time"] = start_dt
                    cleaned_data["end_time"] = end_dt

        dorm = cleaned_data.get("dorm")
        dorm_sub = cleaned_data.get("dorm_sub")
        if dorm and dorm_sub and dorm_group_names(dorm) and dorm_sub == "N/A":
            self.add_error("dorm_sub", "Select a dorm group for this dorm.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.start_time = self.cleaned_data["start_time"]
        instance.end_time = self.cleaned_data["end_time"]
        instance.tags = serialize_event_tags(self.cleaned_data.get("tags", []))
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
