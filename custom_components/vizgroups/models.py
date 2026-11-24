"""Data models for Viz Groups."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .const import LOCATOR_KINDS, MERGE_ENSURE_USER_BRANCH, MERGE_MODES


def utcnow_iso() -> str:
    """UTC timestamp for created/updated fields."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# Back-compat alias used by store/sync helpers
_utcnow_iso = utcnow_iso


def _slugify(value: str) -> str:
    out: list[str] = []
    prev_dash = False
    for ch in value.strip().lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    slug = "".join(out).strip("-")
    return slug or f"group-{uuid4().hex[:8]}"


@dataclass
class Group:
    """A named set of Home Assistant user IDs."""

    id: str
    name: str
    member_user_ids: list[str] = field(default_factory=list)
    description: str = ""
    icon: str = "mdi:account-group"
    created: str = field(default_factory=_utcnow_iso)
    updated: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "member_user_ids": list(self.member_user_ids),
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Group:
        members = data.get("member_user_ids") or []
        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or data["id"]),
            description=str(data.get("description") or ""),
            icon=str(data.get("icon") or "mdi:account-group"),
            member_user_ids=[str(uid) for uid in members if uid],
            created=str(data.get("created") or _utcnow_iso()),
            updated=str(data.get("updated") or _utcnow_iso()),
        )


@dataclass
class GroupExpression:
    """AND include groups + NOT exclude groups."""

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "include": list(self.include),
            "exclude": list(self.exclude),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> GroupExpression:
        data = data or {}
        return cls(
            include=[str(g) for g in (data.get("include") or []) if g],
            exclude=[str(g) for g in (data.get("exclude") or []) if g],
        )


@dataclass
class Locator:
    """Path to a visibility-capable Lovelace node."""

    kind: str = "card"
    view_path: str | None = None
    view_index: int | None = None
    section_index: int | None = None
    card_index: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": self.kind}
        if self.view_path is not None:
            payload["view_path"] = self.view_path
        if self.view_index is not None:
            payload["view_index"] = self.view_index
        if self.section_index is not None:
            payload["section_index"] = self.section_index
        if self.card_index is not None:
            payload["card_index"] = self.card_index
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Locator:
        data = data or {}
        kind = str(data.get("kind") or "card")
        if kind not in LOCATOR_KINDS:
            kind = "other"
        return cls(
            kind=kind,
            view_path=data.get("view_path"),
            view_index=_optional_int(data.get("view_index")),
            section_index=_optional_int(data.get("section_index")),
            card_index=_optional_int(data.get("card_index")),
            extra=dict(data.get("extra") or {}),
        )


@dataclass
class Binding:
    """Bind a Lovelace node to a group expression."""

    id: str
    expression: GroupExpression
    dashboard_url_path: str
    locator: Locator
    merge_mode: str = MERGE_ENSURE_USER_BRANCH
    fingerprint: str = ""
    stale: bool = False
    label: str = ""
    created: str = field(default_factory=_utcnow_iso)
    updated: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "expression": self.expression.to_dict(),
            "dashboard_url_path": self.dashboard_url_path,
            "locator": self.locator.to_dict(),
            "merge_mode": self.merge_mode,
            "fingerprint": self.fingerprint,
            "stale": self.stale,
            "label": self.label,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Binding:
        merge = str(data.get("merge_mode") or MERGE_ENSURE_USER_BRANCH)
        if merge not in MERGE_MODES:
            merge = MERGE_ENSURE_USER_BRANCH
        return cls(
            id=str(data["id"]),
            expression=GroupExpression.from_dict(data.get("expression")),
            dashboard_url_path=str(data.get("dashboard_url_path") or "lovelace"),
            locator=Locator.from_dict(data.get("locator")),
            merge_mode=merge,
            fingerprint=str(data.get("fingerprint") or ""),
            stale=bool(data.get("stale", False)),
            label=str(data.get("label") or ""),
            created=str(data.get("created") or _utcnow_iso()),
            updated=str(data.get("updated") or _utcnow_iso()),
        )


@dataclass
class SyncMetadata:
    """Last sync bookkeeping."""

    last_sync: str | None = None
    last_error: str | None = None
    content_hash: str | None = None
    dry_run_last: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_sync": self.last_sync,
            "last_error": self.last_error,
            "content_hash": self.content_hash,
            "dry_run_last": self.dry_run_last,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SyncMetadata:
        data = data or {}
        return cls(
            last_sync=data.get("last_sync"),
            last_error=data.get("last_error"),
            content_hash=data.get("content_hash"),
            dry_run_last=bool(data.get("dry_run_last", False)),
        )


def new_group(
    *,
    name: str,
    group_id: str | None = None,
    description: str = "",
    icon: str = "mdi:account-group",
    member_user_ids: list[str] | None = None,
) -> Group:
    """Create a new group with a stable slug id."""
    gid = group_id or _slugify(name)
    now = _utcnow_iso()
    return Group(
        id=gid,
        name=name,
        description=description,
        icon=icon,
        member_user_ids=list(member_user_ids or []),
        created=now,
        updated=now,
    )


def new_binding(
    *,
    expression: GroupExpression | dict[str, Any],
    dashboard_url_path: str,
    locator: Locator | dict[str, Any],
    merge_mode: str = MERGE_ENSURE_USER_BRANCH,
    fingerprint: str = "",
    label: str = "",
    binding_id: str | None = None,
) -> Binding:
    """Create a new binding."""
    expr = (
        expression
        if isinstance(expression, GroupExpression)
        else GroupExpression.from_dict(expression)
    )
    loc = locator if isinstance(locator, Locator) else Locator.from_dict(locator)
    now = _utcnow_iso()
    return Binding(
        id=binding_id or f"bind-{uuid4().hex[:10]}",
        expression=expr,
        dashboard_url_path=dashboard_url_path,
        locator=loc,
        merge_mode=merge_mode if merge_mode in MERGE_MODES else MERGE_ENSURE_USER_BRANCH,
        fingerprint=fingerprint,
        label=label,
        created=now,
        updated=now,
    )


def clone_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy a dict for safe mutation."""
    return deepcopy(data)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
