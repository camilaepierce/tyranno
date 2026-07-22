from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import RexUser

SECRETS_CONFIG_PATH = Path("/etc/secrets/department_emails.json")
CONFIG_PATH = Path(__file__).with_name("department_emails.json")
EXAMPLE_PATH = Path(__file__).with_name("department_emails.example.json")

DEFAULT_CONFIG = {
    "DormCon": [],
    "RES": [],
    "EHS": [],
    "AD": {},
}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _email_in_list(email: str, emails: list[str]) -> bool:
    normalized = _normalize_email(email)
    return any(_normalize_email(entry) == normalized for entry in emails)


def _resolve_config_path() -> Path | None:
    if SECRETS_CONFIG_PATH.exists():
        return SECRETS_CONFIG_PATH
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    if EXAMPLE_PATH.exists():
        return EXAMPLE_PATH
    return None


@lru_cache
def load_department_emails() -> dict:
    path = _resolve_config_path()
    if path is None:
        return DEFAULT_CONFIG.copy()

    with path.open(encoding="utf-8") as config_file:
        data = json.load(config_file)

    return {
        "DormCon": list(data.get("DormCon", [])),
        "RES": list(data.get("RES", [])),
        "EHS": list(data.get("EHS", [])),
        "AD": dict(data.get("AD", {})),
    }


def clear_department_emails_cache() -> None:
    load_department_emails.cache_clear()


def lookup_role_for_email(email: str) -> tuple[str, str]:
    """Return the RexUser role and dorm (for AD only) for an email address."""
    if not email:
        return RexUser.RoleChoices.STUDENT, ""

    config = load_department_emails()

    for role in RexUser.ROLE_LOOKUP_PRIORITY:
        if role == RexUser.RoleChoices.AD:
            for dorm_key, emails in config["AD"].items():
                if _email_in_list(email, emails):
                    return role, dorm_key
            continue

        if _email_in_list(email, config.get(role, [])):
            return role, ""

    return RexUser.RoleChoices.STUDENT, ""
