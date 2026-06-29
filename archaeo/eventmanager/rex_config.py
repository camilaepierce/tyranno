from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import tomllib

CONFIG_PATH = Path(__file__).with_name("rex_config.toml")


@lru_cache
def load_rex_config() -> dict:
    with CONFIG_PATH.open("rb") as config_file:
        return tomllib.load(config_file)


def clear_rex_config_cache() -> None:
    load_rex_config.cache_clear()


def get_rex_name() -> str:
    return load_rex_config()["name"]


def get_rex_dates() -> dict:
    return load_rex_config()["dates"]


def get_rex_date_bounds() -> tuple[date, date]:
    dates = get_rex_dates()
    return date.fromisoformat(dates["start"]), date.fromisoformat(dates["end"])


def get_hour_cutoff() -> int:
    return int(get_rex_dates()["hour_cutoff"])


def effective_rex_date(value: datetime) -> date:
    local_value = value
    if hasattr(value, "tzinfo") and value.tzinfo is not None:
        from django.utils import timezone

        local_value = timezone.localtime(value)

    if local_value.hour < get_hour_cutoff():
        return (local_value - timedelta(days=1)).date()
    return local_value.date()


def dorm_display_name(dorm_key: str) -> str:
    dorm = load_rex_config()["dorms"].get(dorm_key, {})
    return dorm.get("rename_to", dorm_key)


def dorm_choices() -> list[tuple[str, str]]:
    choices = [
        (dorm_key, dorm_display_name(dorm_key))
        for dorm_key in load_rex_config()["dorms"]
    ]
    return sorted(choices, key=lambda choice: choice[1].lower())


def dorm_group_names(dorm_key: str) -> list[str]:
    groups = load_rex_config()["dorms"].get(dorm_key, {}).get("groups", {})
    return sorted(groups.keys())


def dorm_group_choices(dorm_key: str) -> list[tuple[str, str]]:
    groups = dorm_group_names(dorm_key)
    if not groups:
        return [("N/A", "N/A")]
    return [(group_name, group_name) for group_name in groups]


def dorm_groups_for_js() -> dict[str, list[list[str]]]:
    return {
        dorm_key: [[value, label] for value, label in dorm_group_choices(dorm_key)]
        for dorm_key in load_rex_config()["dorms"]
    }


def tag_display_name(tag_key: str) -> str:
    tag = load_rex_config()["tags"].get(tag_key, {})
    if "rename_from" in tag:
        return tag["rename_from"]
    return tag_key.replace("_", " ").title()


def tag_choices() -> list[tuple[str, str]]:
    choices = [
        (tag_key, tag_display_name(tag_key))
        for tag_key in load_rex_config()["tags"]
    ]
    return sorted(choices, key=lambda choice: choice[1].lower())


def parse_event_tags(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    return [tag for tag in raw_value.split(",") if tag]


def serialize_event_tags(tag_keys: list[str]) -> str:
    valid_tags = set(load_rex_config()["tags"])
    cleaned = [tag for tag in tag_keys if tag in valid_tags]
    return ",".join(dict.fromkeys(cleaned))


def format_event_tags_for_display(raw_value: str) -> str:
    return ", ".join(tag_display_name(tag) for tag in parse_event_tags(raw_value))


def format_event_tags_for_export(raw_value: str) -> str:
    return ",".join(tag_display_name(tag) for tag in parse_event_tags(raw_value))
