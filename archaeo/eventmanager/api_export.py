from django.db.models import Max
from django.http import JsonResponse
from django.utils import timezone

from eventmanager.models import RexEvent
from eventmanager.rex_config import (
    dorm_display_name,
    get_rex_date_bounds,
    get_rex_name,
    load_rex_config,
    parse_event_tags,
    tag_display_name,
)


def _iso_datetime(value):
    if value is None:
        return None
    normalized = timezone.localtime(value)
    return normalized.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _api_dorm_names():
    config = load_rex_config()
    return sorted(
        (
            dorm_display_name(dorm_key)
            for dorm_key in config["dorms"]
        ),
        key=str.lower,
    )


def _api_groups():
    config = load_rex_config()
    groups = {}
    for dorm_key, dorm_config in config["dorms"].items():
        dorm_groups = dorm_config.get("groups", {})
        if dorm_groups:
            groups[dorm_display_name(dorm_key)] = sorted(dorm_groups.keys())
    return groups


def _api_tags():
    config = load_rex_config()
    return sorted(
        config["tags"].keys(),
        key=lambda tag_key: tag_display_name(tag_key).lower(),
    )


def _api_colors():
    config = load_rex_config()
    dorm_colors = {
        dorm_display_name(dorm_key): dorm_config["color"]
        for dorm_key, dorm_config in config["dorms"].items()
        if dorm_config.get("color")
    }
    tag_colors = {
        tag_key: tag_config["color"]
        for tag_key, tag_config in config["tags"].items()
        if tag_config.get("color")
    }
    group_colors = {}
    for dorm_key, dorm_config in config["dorms"].items():
        dorm_groups = dorm_config.get("groups", {})
        if not dorm_groups:
            continue
        group_colors[dorm_display_name(dorm_key)] = {
            group_name: group_config["color"]
            for group_name, group_config in dorm_groups.items()
            if group_config.get("color")
        }
    return {
        "dorms": dorm_colors,
        "tags": tag_colors,
        "groups": group_colors,
    }


def _api_event(event):
    group = []
    if event.dorm_sub and event.dorm_sub != "N/A":
        group = [event.dorm_sub]

    return {
        "id": str(event.pk).zfill(4),
        "name": event.event_name,
        "description": event.description,
        "location": event.location,
        "start": _iso_datetime(event.start_time),
        "end": _iso_datetime(event.end_time),
        "dorm": [dorm_display_name(event.dorm)],
        "group": group,
        "tags": parse_event_tags(event.tags),
    }


def build_rex_api_payload():
    events = RexEvent.fully_approved().order_by("start_time", "event_name")
    published_at = events.aggregate(latest=Max("published_at"))["latest"]
    if published_at is None:
        published_at = timezone.now()

    start_date, end_date = get_rex_date_bounds()
    return {
        "name": get_rex_name(),
        "published": _iso_datetime(published_at),
        "events": [_api_event(event) for event in events],
        "dorms": _api_dorm_names(),
        "groups": _api_groups(),
        "tags": _api_tags(),
        "colors": _api_colors(),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
    }


def rex_api_json_response():
    response = JsonResponse(build_rex_api_payload())
    response["Access-Control-Allow-Origin"] = "*"
    return response
