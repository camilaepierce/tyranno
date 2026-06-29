from django import template

from eventmanager.rex_config import (
    dorm_display_name,
    format_event_tags_for_display,
)

register = template.Library()


@register.filter
def dorm_label(dorm_key):
    return dorm_display_name(dorm_key)


@register.filter
def tags_label(raw_tags):
    return format_event_tags_for_display(raw_tags)
