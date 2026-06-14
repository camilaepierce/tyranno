from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

# Create your models here.
class RexUser(models.Model):
    class RoleChoices(models.TextChoices):
        STUDENT = "Student", _("Student")
        DORMCON = "DormCon", _("DormCon")
        RES = "RES", _("RES")
        EHS = "EHS", _("EHS")
        AD = "AD", _("AD")

    username = models.CharField(max_length=200)
    role = models.CharField(max_length=10, choices=RoleChoices.choices)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.username

class RexEvent(models.Model):
    class ApprovalStatus(models.TextChoices):
        APPROVED = "AP", _("Approved")
        PENDING = "PE", _("Pending")
        DENIED = "DE", _("Denied")
        FLAGGED = "FL", _("Flagged")

    DORM_CHOICES = (
        ("Baker House", "Baker House"),
        ("Burton-Conner", "Burton-Conner"),
        ("East Campus", "East Campus"),
        ("MacGregor", "MacGregor"),
        ("Maseeh Hall", "Maseeh Hall"),
        ("McCormick Hall", "McCormick Hall"),
        ("New House", "New House"),
        ("New Vassar", "New Vassar"),
        ("Random Hall", "Random Hall"),
        ("Simmons Hall", "Simmons Hall"),
    )

    APPROVAL_FIELDS = (
        ("dc_status", "dc_comment", RexUser.RoleChoices.DORMCON),
        ("ad_status", "ad_comment", RexUser.RoleChoices.AD),
        ("res_status", "res_comment", RexUser.RoleChoices.RES),
        ("ehs_status", "ehs_comment", RexUser.RoleChoices.EHS),
    )

    APPROVAL_STAGES = (
        (("dc_status",), (RexUser.RoleChoices.DORMCON,)),
        (
            ("ad_status", "res_status", "ehs_status"),
            (RexUser.RoleChoices.AD, RexUser.RoleChoices.RES, RexUser.RoleChoices.EHS),
        ),
    )

    ROLE_TO_APPROVAL = {
        role: (status_field, comment_field)
        for status_field, comment_field, role in APPROVAL_FIELDS
    }

    CONTENT_FIELDS = (
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
    )

    event_name = models.CharField(max_length=20)
    description = models.TextField(max_length=200)
    dorm = models.CharField(max_length=30, choices=DORM_CHOICES)
    dorm_sub = models.CharField(max_length=20)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    email_notif = models.TextField()
    location = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=50)
    contact_email = models.CharField(max_length=254)
    created_by = models.ForeignKey(RexUser, on_delete=models.CASCADE, null=True, blank=True)

    ## Approval Status Categories
    dc_status = models.CharField(max_length=2,
        choices=ApprovalStatus,
        default="PE")
    dc_comment = models.TextField(blank=True, default="")
    res_status = models.CharField(max_length=2,
        choices=ApprovalStatus,
        default="PE")
    res_comment = models.TextField(blank=True, default="")
    ehs_status = models.CharField(max_length=2,
        choices=ApprovalStatus,
        default="PE")
    ehs_comment = models.TextField(blank=True, default="")
    ad_status = models.CharField(max_length=2,
        choices=ApprovalStatus,
        default="PE")
    ad_comment = models.TextField(blank=True, default="")

    def __str__(self):
        return self.event_name

    def approval_status_fields(self):
        return [status_field for status_field, _, _ in self.APPROVAL_FIELDS]

    def is_fully_approved(self):
        return all(
            getattr(self, status_field) == self.ApprovalStatus.APPROVED
            for status_field in self.approval_status_fields()
        )

    def notification_emails(self):
        emails = []
        for part in self.email_notif.replace(",", "\n").splitlines():
            email = part.strip()
            if email:
                emails.append(email)
        return list(dict.fromkeys(emails))

    def reset_approvals(self):
        for status_field, comment_field, _ in self.APPROVAL_FIELDS:
            setattr(self, status_field, self.ApprovalStatus.PENDING)
            setattr(self, comment_field, "")

    def active_approval_stage(self, status_values=None):
        for field_names, roles in self.APPROVAL_STAGES:
            statuses = [
                status_values.get(field_name)
                if status_values is not None
                else getattr(self, field_name)
                for field_name in field_names
            ]
            if any(status != self.ApprovalStatus.APPROVED for status in statuses):
                return field_names, roles
        return None, ()

    def role_can_approve(self, role):
        _, stage_roles = self.active_approval_stage()
        if role not in stage_roles:
            return False

        status_field, _ = self.ROLE_TO_APPROVAL[role]
        status = getattr(self, status_field)
        return status in (self.ApprovalStatus.PENDING, self.ApprovalStatus.FLAGGED)

    def _notify_roles(self, roles):
        recipients = list(
            dict.fromkeys(
                RexUser.objects.filter(role__in=roles)
                .exclude(email__isnull=True)
                .exclude(email="")
                .values_list("email", flat=True)
            )
        )
        if not recipients:
            return

        self._send_mail(
            f"Approval needed for {self.event_name}",
            (
                f"An event named {self.event_name} is waiting for approval.\n\n"
                f"Description: {self.description}\n"
                f"Dorm: {self.dorm}\n"
                f"Subsection: {self.dorm_sub}\n"
                f"Location: {self.location}\n"
                f"Contact: {self.contact_name} <{self.contact_email}>\n"
                f"Review it here: {reverse('event', kwargs={'pk': self.pk})}\n"
            ),
            recipients,
        )

    def _send_mail(self, subject, body, recipients):
        recipients = list(dict.fromkeys(email for email in recipients if email))
        if not recipients:
            return

        send_mail(
            subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
            recipients,
        )

    def _notify_subscribers(self, subject, body):
        self._send_mail(subject, body, self.notification_emails())

    def _notify_active_stage(self, stage):
        _, roles = stage
        pending_roles = [
            role
            for status_field, _, role in self.APPROVAL_FIELDS
            if role in roles and getattr(self, status_field) == self.ApprovalStatus.PENDING
        ]
        self._notify_roles(pending_roles)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        content_changed = False
        approval_only_change = False
        previous_stage = None
        previous = None

        if not is_new:
            previous = type(self).objects.filter(pk=self.pk).values(
                *self.CONTENT_FIELDS,
                *self.approval_status_fields(),
            ).first()
            if previous:
                content_changed = any(
                    previous[field] != getattr(self, field)
                    for field in self.CONTENT_FIELDS
                )
                approval_only_change = not content_changed and any(
                    previous[status_field] != getattr(self, status_field)
                    for status_field in self.approval_status_fields()
                )
                previous_stage = self.active_approval_stage(previous)

        if content_changed:
            self.reset_approvals()

        super().save(*args, **kwargs)

        current_stage = self.active_approval_stage()

        if is_new or content_changed:
            if current_stage:
                self._notify_active_stage(current_stage)
            self._notify_subscribers(
                f"Event updated: {self.event_name}",
                (
                    f"The event {self.event_name} was {'submitted' if is_new else 'updated'}.\n\n"
                    f"All approval statuses have been reset to pending.\n"
                    f"View details: {reverse('event', kwargs={'pk': self.pk})}\n"
                ),
            )
        elif approval_only_change and current_stage and current_stage != previous_stage:
            self._notify_active_stage(current_stage)
        elif approval_only_change:
            changed_statuses = []
            if previous:
                for status_field in self.approval_status_fields():
                    if previous[status_field] != getattr(self, status_field):
                        label = status_field.replace("_status", "").upper()
                        display = dict(self.ApprovalStatus.choices).get(
                            getattr(self, status_field),
                            getattr(self, status_field),
                        )
                        changed_statuses.append(f"{label}: {display}")

            if changed_statuses:
                self._notify_subscribers(
                    f"Approval update: {self.event_name}",
                    (
                        f"Approval statuses changed for {self.event_name}:\n"
                        f"{chr(10).join(changed_statuses)}\n\n"
                        f"View details: {reverse('event', kwargs={'pk': self.pk})}\n"
                    ),
                )

            if self.is_fully_approved():
                recipients = list(self.notification_emails())
                if self.created_by and self.created_by.email:
                    recipients.append(self.created_by.email)
                self._send_mail(
                    f"Event approved: {self.event_name}",
                    (
                        f"All required approvals have been received for {self.event_name}.\n\n"
                        f"View details: {reverse('event', kwargs={'pk': self.pk})}\n"
                    ),
                    recipients,
                )
        
    def return_fields(self):
        return [
            self.event_name,
            self.created_by,
            self.description,
            self.dorm,
            self.dorm_sub,
            self.start_time,
            self.end_time,
            self.email_notif,
            self.location,
            self.contact_name,
            self.contact_email,
            self.dc_status,
            self.dc_comment,
            self.res_status,
            self.res_comment,
            self.ehs_status,
            self.ehs_comment,
            self.ad_status,
            self.ad_comment
        ]

    def get_absolute_url(self):
        return reverse("event", kwargs={"pk": self.pk})


class SiteConfiguration(models.Model):
    allow_event_editing = models.BooleanField(
        default=True,
        help_text="When disabled, creators cannot edit or delete their submitted events.",
    )

    class Meta:
        verbose_name = "Site configuration"
        verbose_name_plural = "Site configuration"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        status = "enabled" if self.allow_event_editing else "disabled"
        return f"Site configuration (event editing {status})"
