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

    APPROVAL_STAGES = (
        (("dc_status",), (RexUser.RoleChoices.DORMCON,)),
        (("ad_status",), (RexUser.RoleChoices.AD,)),
        (("res_status", "ehs_status"), (RexUser.RoleChoices.RES, RexUser.RoleChoices.EHS)),
    )

    event_name = models.CharField(max_length=20)
    description = models.CharField(max_length=200)
    dorm = models.CharField(max_length=20)
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
        return [field_name for field_names, _ in self.APPROVAL_STAGES for field_name in field_names]

    def active_approval_stage(self, status_values=None):
        for field_names, roles in self.APPROVAL_STAGES:
            statuses = [
                getattr(self, field_name) if status_values is None else status_values.get(field_name)
                for field_name in field_names
            ]
            if any(status != self.ApprovalStatus.APPROVED for status in statuses):
                return field_names, roles
        return None, ()

    def _notify_active_stage(self, stage):
        field_names, roles = stage
        if not all(getattr(self, field_name) == self.ApprovalStatus.PENDING for field_name in field_names):
            return

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

        subject = f"Approval needed for {self.event_name}"
        body = (
            f"An event named {self.event_name} is waiting for approval.\n\n"
            f"Description: {self.description}\n"
            f"Dorm: {self.dorm}\n"
            f"Subsection: {self.dorm_sub}\n"
            f"Location: {self.location}\n"
            f"Contact: {self.contact_name} <{self.contact_email}>\n"
            f"Review it here: {reverse('event', kwargs={'pk': self.pk})}\n"
        )
        send_mail(
            subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
            recipients,
        )

    def save(self, *args, **kwargs):
        previous_statuses = None
        if self.pk:
            previous_statuses = type(self).objects.filter(pk=self.pk).values(
                *self.approval_status_fields()
            ).first()

        previous_stage = self.active_approval_stage(previous_statuses) if previous_statuses else None
        super().save(*args, **kwargs)
        current_stage = self.active_approval_stage()

        if current_stage and current_stage != previous_stage:
            self._notify_active_stage(current_stage)
        
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
