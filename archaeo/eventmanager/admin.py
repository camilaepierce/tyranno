from django.contrib import admin

from .models import RexEvent, RexUser, SiteConfiguration


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ("allow_event_editing",)

    def has_add_permission(self, request):
        return not SiteConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(RexEvent)
admin.site.register(RexUser)
