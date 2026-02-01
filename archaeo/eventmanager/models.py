from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class RexUser(models.Model):
    username = models.CharField(max_length=200)
    role = models.CharField(max_length=10)

    def __str__(self):
        return self.username

class RexEvent(models.Model):

    class ApprovalStatus(models.TextChoices):
        APPROVED = "AP", _("Approved")
        PENDING = "PE", _("Pending")
        DENIED = "DE", _("Denied")
        FLAGGED = "FL", _("Flagged")

    event_name = models.CharField(max_length=20)
    description = models.CharField(max_length=200)
    dorm = models.CharField(max_length=20)
    dorm_sub = models.CharField(max_length=20)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    email_notif = models.TextField()
    location = models.CharField()
    contact_name = models.CharField(max_length=50)
    contact_email = models.CharField(max_length=20)

    ## Approval Status Categories
    res_status = models.CharField(max_length=2,
        choices=ApprovalStatus,
        default="PE")
    ehs_status = models.CharField(max_length=2,
        choices=ApprovalStatus,
        default="PE")
    ad_status = models.CharField(max_length=2,
        choices=ApprovalStatus,
        default="PE")

    def __str__(self):
        return self.event_name
