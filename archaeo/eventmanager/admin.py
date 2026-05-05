# Register your models here.

from django.contrib import admin

from .models import RexEvent, RexUser

admin.site.register(RexEvent)
admin.site.register(RexUser)