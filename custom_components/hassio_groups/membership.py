"""Pure membership math for HA Groups (no Home Assistant imports)."""

from __future__ import annotations

from typing import Iterable, Mapping


def normalize_user_ids(user_ids: Iterable[str], *, normalize_duplicates: bool = True) -> list[str]:
    """Dedupe and stably sort user ids."""
    cleaned = [str(uid).strip() for uid in user_ids if uid and str(uid).strip()]
    if not normalize_duplicates:
        return cleaned
    return sorted(set(cleaned))


def effective_users(
    include_group_ids: Iterable[str],
    exclude_group_ids: Iterable[str],
    members_by_group: Mapping[str, Iterable[str]],
    *,
    normalize_duplicates: bool = True,
) -> list[str]:
    """Compute ∩(include) − ∪(exclude). Empty include → fail-closed empty set."""
    include = [str(g) for g in include_group_ids if g]
    exclude = [str(g) for g in exclude_group_ids if g]

    if not include:
        return []

    intersection: set[str] | None = None
    for gid in include:
        members = set(normalize_user_ids(members_by_group.get(gid, []), normalize_duplicates=True))
        intersection = members if intersection is None else (intersection & members)

    result = intersection or set()

    excluded: set[str] = set()
    for gid in exclude:
        excluded |= set(normalize_user_ids(members_by_group.get(gid, []), normalize_duplicates=True))

    result -= excluded
    return normalize_user_ids(result, normalize_duplicates=normalize_duplicates)


def is_member(user_id: str, group_members: Iterable[str]) -> bool:
    """Return True if user_id is in the group member list."""
    if not user_id:
        return False
    return user_id in set(normalize_user_ids(group_members))
