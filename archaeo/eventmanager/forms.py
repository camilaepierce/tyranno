from django import forms
from django.forms import ModelForm, Form, CharField, ChoiceField
from eventmanager.models import RexEvent


class EventForm(ModelForm):
    class Meta:
        model = RexEvent
        fields = ["event_name", "description", "dorm", "dorm_sub", "start_time", "end_time", "email_notif", "location", "contact_name", "contact_email"]


class ApprovalForm(Form):
    """Form for approvers to submit approval status with comments"""
    status = ChoiceField(
        choices=RexEvent.ApprovalStatus.choices,
        help_text="Select approval status"
    )
    comment = CharField(
        required=False,
        widget=forms.Textarea,
        help_text="Optional: Add comments for this approval decision"
    )