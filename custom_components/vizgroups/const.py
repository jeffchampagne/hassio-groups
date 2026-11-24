"""Constants for Viz Groups."""

from __future__ import annotations

DOMAIN = "vizgroups"
NAME = "Viz Groups"

PLATFORMS: list[str] = ["sensor"]

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

CONF_AUTO_SYNC = "auto_sync"
CONF_DASHBOARDS = "dashboards"
CONF_DRY_RUN = "dry_run"
CONF_NORMALIZE_DUPLICATES = "normalize_duplicates"

DEFAULT_AUTO_SYNC = True
DEFAULT_DRY_RUN = False
DEFAULT_NORMALIZE_DUPLICATES = True

ATTR_GROUP_ID = "group_id"
ATTR_MEMBERS = "members"
ATTR_MEMBER_NAMES = "member_names"
ATTR_INCLUDE = "include"
ATTR_EXCLUDE = "exclude"
ATTR_BINDING_ID = "binding_id"
ATTR_DASHBOARD = "dashboard"
ATTR_USER_ID = "user_id"
ATTR_USER_IDS = "user_ids"
ATTR_IS_MEMBER = "is_member"

EVENT_SYNCED = f"{DOMAIN}_synced"
EVENT_MEMBERSHIP_CHANGED = f"{DOMAIN}_membership_changed"

PANEL_PATH = "vizgroups"
PANEL_ELEMENT = "vizgroups-panel"
PANEL_MODULE_URL = f"/{DOMAIN}/panel.js?v=members2"
PANEL_ICON = "mdi:account-group"

MERGE_REPLACE_USER = "replace_user_condition"
MERGE_ENSURE_USER_BRANCH = "ensure_user_branch"
MERGE_MODES = (MERGE_REPLACE_USER, MERGE_ENSURE_USER_BRANCH)

LOCATOR_KINDS = ("view", "section", "card", "other")

EMPTY_GROUP_POLICY = "fail_closed"
