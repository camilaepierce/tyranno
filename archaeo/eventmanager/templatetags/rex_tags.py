from django import template

from eventmanager.rex_config import (
    badge_text_color,
    dorm_color,
    dorm_display_name,
    format_event_tags_for_display,
    group_color,
    parse_event_tags,
    tag_color,
    tag_display_name,
)

register = template.Library()


@register.filter
def dorm_label(dorm_key):
    return dorm_display_name(dorm_key)


@register.filter
def tags_label(raw_tags):
    return format_event_tags_for_display(raw_tags)


@register.filter
def event_tags(raw_tags):
    return parse_event_tags(raw_tags)


@register.filter
def tag_label(tag_key):
    return tag_display_name(tag_key)


@register.filter
def dorm_badge_color(dorm_key):
    return dorm_color(dorm_key)


@register.filter
def tag_badge_color(tag_key):
    return tag_color(tag_key)


@register.filter
def group_badge_color(dorm_key, group_name):
    return group_color(dorm_key, group_name)


@register.filter
def has_event_tag(raw_tags, tag_key):
    return tag_key in parse_event_tags(raw_tags)


@register.filter
def badge_foreground(background):
    if not background:
        return ""
    return badge_text_color(background)
