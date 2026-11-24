"""Pure membership math for Viz Groups (no Home Assistant imports)."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

MEMBER_TYPE_USER = "user"
MEMBER_TYPE_GROUP = "group"
MEMBER_TYPES = (MEMBER_TYPE_USER, MEMBER_TYPE_GROUP)


def normalize_user_ids(user_ids: Iterable[str], *, normalize_duplicates: bool = True) -> list[str]:
    """Dedupe and stably sort user ids."""
    cleaned = [str(uid).strip() for uid in user_ids if uid and str(uid).strip()]
    if not normalize_duplicates:
        return cleaned
    return sorted(set(cleaned))


def normalize_members(
    members: Iterable[Any],
    *,
    normalize_duplicates: bool = True,
) -> list[dict[str, str]]:
    """Normalize typed member refs; preserve first-seen order for mixed types."""
    out: list[dict[str, str]] = []
    seen_user: set[str] = set()
    seen_group: set[str] = set()
    for raw in members or []:
        parsed = coerce_member(raw)
        if parsed is None:
            continue
        mtype = parsed["type"]
        mid = parsed["id"]
        if mtype == MEMBER_TYPE_USER:
            if normalize_duplicates and mid in seen_user:
                continue
            seen_user.add(mid)
        else:
            if normalize_duplicates and mid in seen_group:
                continue
            seen_group.add(mid)
        out.append({"type": mtype, "id": mid})
    return out


def coerce_member(raw: Any) -> dict[str, str] | None:
    """Parse a member ref from dict, string (legacy user id), or object."""
    if raw is None:
        return None
    if isinstance(raw, str):
        mid = raw.strip()
        if not mid:
            return None
        return {"type": MEMBER_TYPE_USER, "id": mid}
    if isinstance(raw, Mapping):
        mtype = str(raw.get("type") or MEMBER_TYPE_USER).strip().lower()
        mid = str(raw.get("id") or "").strip()
        if not mid:
            return None
        if mtype not in MEMBER_TYPES:
            # Unknown type → treat as user id only if it looks like a bare id legacy row
            if "user_id" in raw and raw.get("user_id"):
                return {"type": MEMBER_TYPE_USER, "id": str(raw["user_id"]).strip()}
            return None
        return {"type": mtype, "id": mid}
    # dataclasses / objects with type+id
    mtype = str(getattr(raw, "type", MEMBER_TYPE_USER) or MEMBER_TYPE_USER).strip().lower()
    mid = str(getattr(raw, "id", "") or "").strip()
    if not mid or mtype not in MEMBER_TYPES:
        return None
    return {"type": mtype, "id": mid}


def member_user_ids(members: Iterable[Any]) -> list[str]:
    """Direct user member ids (not nested)."""
    return [
        m["id"]
        for m in normalize_members(members, normalize_duplicates=True)
        if m["type"] == MEMBER_TYPE_USER
    ]


def member_group_ids(members: Iterable[Any]) -> list[str]:
    """Direct nested group member ids."""
    return [
        m["id"]
        for m in normalize_members(members, normalize_duplicates=True)
        if m["type"] == MEMBER_TYPE_GROUP
    ]


def members_from_legacy(
    *,
    member_user_ids_list: Iterable[str] | None = None,
    member_group_ids_list: Iterable[str] | None = None,
    members: Iterable[Any] | None = None,
) -> list[dict[str, str]]:
    """Build typed members from new and/or legacy fields (members wins when present)."""
    if members is not None:
        return normalize_members(members)
    refs: list[dict[str, str]] = []
    for uid in member_user_ids_list or []:
        if uid and str(uid).strip():
            refs.append({"type": MEMBER_TYPE_USER, "id": str(uid).strip()})
    for gid in member_group_ids_list or []:
        if gid and str(gid).strip():
            refs.append({"type": MEMBER_TYPE_GROUP, "id": str(gid).strip()})
    return normalize_members(refs)


def flatten_group_users(
    group_id: str,
    members_tree: Mapping[str, Sequence[Any]],
    *,
    _stack: frozenset[str] | None = None,
) -> list[str]:
    """
    Resolve effective HA user ids for a group, expanding nested group members.

    Cycle policy: if a nested group is already on the resolution stack, skip that
    edge (do not expand again). Missing/unknown groups contribute no users.
    Empty result remains fail-closed for visibility sync.
    """
    gid = str(group_id or "").strip()
    if not gid:
        return []
    stack = _stack or frozenset()
    if gid in stack:
        # Cyclic edge — skip safely (fail closed for this branch).
        return []

    next_stack = stack | {gid}
    collected: set[str] = set()
    for raw in members_tree.get(gid, []) or []:
        parsed = coerce_member(raw)
        if parsed is None:
            continue
        if parsed["type"] == MEMBER_TYPE_USER:
            collected.add(parsed["id"])
            continue
        nested_id = parsed["id"]
        if nested_id in next_stack:
            # Skip cyclic membership edge.
            continue
        collected |= set(
            flatten_group_users(
                nested_id,
                members_tree,
                _stack=next_stack,
            )
        )

    return normalize_user_ids(collected)


def flatten_all_groups(
    members_tree: Mapping[str, Sequence[Any]],
) -> dict[str, list[str]]:
    """Map each group id → effective flattened user ids (cycle-safe)."""
    return {gid: flatten_group_users(gid, members_tree) for gid in members_tree}


def effective_users(
    include_group_ids: Iterable[str],
    exclude_group_ids: Iterable[str],
    members_by_group: Mapping[str, Iterable[str]],
    *,
    normalize_duplicates: bool = True,
) -> list[str]:
    """Compute ∩(include) − ∪(exclude). Empty include → fail-closed empty set.

    ``members_by_group`` must already be flattened to user ids per group
    (see ``flatten_all_groups`` / ``GroupsStore.members_by_group``).
    """
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
    """Return True if user_id is in the (already flattened) member list."""
    if not user_id:
        return False
    needle = str(user_id).strip()
    return any(str(uid).strip() == needle for uid in group_members if uid)


def overlapping_direct_user_ids(
    parent_members: Iterable[Any],
    nested_group_id: str,
    members_tree: Mapping[str, Sequence[Any]],
) -> list[str]:
    """Direct parent user ids that also appear in a nested group's flatten."""
    direct = set(member_user_ids(parent_members))
    nested = set(flatten_group_users(nested_group_id, members_tree))
    return normalize_user_ids(direct & nested)
