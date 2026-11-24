"""Pure Lovelace visibility sync / locator helpers (no Home Assistant imports)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .const import MERGE_ENSURE_USER_BRANCH, MERGE_REPLACE_USER
from .models import Locator

USER_CONDITION = "user"


def fingerprint_node(node: dict[str, Any] | None) -> str:
    """Stable-ish fingerprint from type + title/entity for drift detection."""
    if not isinstance(node, dict):
        return ""
    parts = [
        str(node.get("type") or ""),
        str(node.get("title") or node.get("name") or ""),
    ]
    entity = node.get("entity")
    if isinstance(entity, str):
        parts.append(entity)
    elif isinstance(node.get("entities"), list) and node["entities"]:
        first = node["entities"][0]
        if isinstance(first, str):
            parts.append(first)
        elif isinstance(first, dict):
            parts.append(str(first.get("entity") or ""))
    cards = node.get("cards")
    if isinstance(cards, list):
        parts.append(f"cards:{len(cards)}")
    sections = node.get("sections")
    if isinstance(sections, list):
        parts.append(f"sections:{len(sections)}")
    return "|".join(parts)


def _view_from_config(config: dict[str, Any], locator: Locator) -> dict[str, Any] | None:
    views = config.get("views")
    if not isinstance(views, list):
        return None
    if locator.view_path is not None:
        for view in views:
            if isinstance(view, dict) and view.get("path") == locator.view_path:
                return view
        return None
    if locator.view_index is not None:
        idx = locator.view_index
        if 0 <= idx < len(views) and isinstance(views[idx], dict):
            return views[idx]
    return None


def resolve_locator(config: dict[str, Any], locator: Locator) -> dict[str, Any] | None:
    """Resolve a locator to a visibility-capable node inside a Lovelace config."""
    if not isinstance(config, dict):
        return None

    view = _view_from_config(config, locator)
    if view is None and locator.kind == "view":
        return None
    if locator.kind == "view":
        return view

    if view is None:
        return None

    if locator.kind == "section":
        sections = view.get("sections")
        if not isinstance(sections, list) or locator.section_index is None:
            return None
        idx = locator.section_index
        if 0 <= idx < len(sections) and isinstance(sections[idx], dict):
            return sections[idx]
        return None

    if locator.kind == "card":
        if locator.section_index is not None:
            sections = view.get("sections")
            if not isinstance(sections, list):
                return None
            if not (0 <= locator.section_index < len(sections)):
                return None
            section = sections[locator.section_index]
            if not isinstance(section, dict):
                return None
            cards = section.get("cards")
        else:
            cards = view.get("cards")
        if not isinstance(cards, list) or locator.card_index is None:
            return None
        idx = locator.card_index
        if 0 <= idx < len(cards) and isinstance(cards[idx], dict):
            return cards[idx]
        return None

    # kind == other: best-effort walk using extra path tokens later; for now view fallback
    return view


def make_user_condition(users: list[str]) -> dict[str, Any]:
    """Build a condition:user leaf. Empty users is fail-closed."""
    return {"condition": USER_CONDITION, "users": list(users)}


def _rewrite_user_leaves(node: Any, users: list[str], *, replaced: list[bool]) -> Any:
    """Walk condition trees; rewrite every condition:user leaf in place."""
    if isinstance(node, dict):
        if node.get("condition") == USER_CONDITION:
            replaced[0] = True
            return make_user_condition(users)
        out = {k: _rewrite_user_leaves(v, users, replaced=replaced) for k, v in node.items()}
        return out
    if isinstance(node, list):
        return [_rewrite_user_leaves(item, users, replaced=replaced) for item in node]
    return node


def apply_visibility_users(
    visibility: list[Any] | None,
    users: list[str],
    *,
    merge_mode: str = MERGE_ENSURE_USER_BRANCH,
) -> list[dict[str, Any]]:
    """Rewrite visibility so managed user lists match ``users`` (fail-closed)."""
    users = list(users)
    user_leaf = make_user_condition(users)

    if visibility is None or visibility == []:
        return [user_leaf]

    # Shallow structural copy so callers can compare
    current = deepcopy(visibility)
    if not isinstance(current, list):
        return [user_leaf]

    if merge_mode == MERGE_REPLACE_USER:
        # Drop prior user-only conditions; keep non-user top-level conditions.
        preserved = [
            item
            for item in current
            if not (isinstance(item, dict) and item.get("condition") == USER_CONDITION)
        ]
        if not preserved:
            return [user_leaf]
        # If only non-user conditions remain, ensure a user branch exists via AND? Spec:
        # replace_user_condition replaces the managed user condition; for mixed trees use ensure.
        return preserved + [user_leaf]

    # ensure_user_branch (default): walk and update existing user leaves; if none, append.
    replaced = [False]
    rewritten = _rewrite_user_leaves(current, users, replaced=replaced)
    if replaced[0]:
        return rewritten if isinstance(rewritten, list) else [rewritten]

    # No user leaf found — append fail-closed user condition (preserve siblings).
    if isinstance(rewritten, list):
        rewritten.append(user_leaf)
        return rewritten
    return [rewritten, user_leaf]


def apply_binding_to_config(
    config: dict[str, Any],
    locator: Locator,
    users: list[str],
    *,
    merge_mode: str = MERGE_ENSURE_USER_BRANCH,
    expected_fingerprint: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """
    Apply a binding rewrite to a deep-copied config.

    Returns (new_config_or_None, status) where status is one of:
    ok | not_found | stale | unchanged
    """
    working = deepcopy(config)
    node = resolve_locator(working, locator)
    if node is None:
        return None, "not_found"

    if expected_fingerprint:
        current_fp = fingerprint_node(node)
        if current_fp and current_fp != expected_fingerprint:
            return None, "stale"

    before = deepcopy(node.get("visibility"))
    node["visibility"] = apply_visibility_users(
        node.get("visibility") if isinstance(node.get("visibility"), list) else node.get("visibility"),
        users,
        merge_mode=merge_mode,
    )
    if node["visibility"] == before:
        return working, "unchanged"
    return working, "ok"


def _node_label(node: dict[str, Any], *, fallback: str) -> str:
    """Human-readable label: title/name/entity/type."""
    for key in ("title", "name"):
        val = node.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    entity = node.get("entity")
    if isinstance(entity, str) and entity.strip():
        return entity.strip()
    entities = node.get("entities")
    if isinstance(entities, list) and entities:
        first = entities[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict) and first.get("entity"):
            return str(first.get("entity"))
    ntype = node.get("type")
    if isinstance(ntype, str) and ntype.strip():
        return ntype.strip()
    return fallback


def _node_detail(node: dict[str, Any]) -> str:
    """Secondary line: type · entity."""
    bits: list[str] = []
    ntype = node.get("type")
    if isinstance(ntype, str) and ntype.strip():
        bits.append(ntype.strip())
    entity = node.get("entity")
    if isinstance(entity, str) and entity.strip():
        bits.append(entity.strip())
    elif isinstance(node.get("entities"), list) and node["entities"]:
        first = node["entities"][0]
        if isinstance(first, str):
            bits.append(first)
        elif isinstance(first, dict) and first.get("entity"):
            bits.append(str(first.get("entity")))
    return " · ".join(bits)


def list_visibility_nodes(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumerate visibility-capable nodes with locator hints (for UI browser)."""
    results: list[dict[str, Any]] = []
    views = config.get("views")
    if not isinstance(views, list):
        return results

    for v_idx, view in enumerate(views):
        if not isinstance(view, dict):
            continue
        view_path = view.get("path")
        view_label = _node_label(view, fallback=str(view_path or f"View {v_idx}"))
        results.append(
            {
                "kind": "view",
                "label": view_label,
                "detail": _node_detail(view) or f"view #{v_idx}",
                "breadcrumb": view_label,
                "type": view.get("type") or "view",
                "locator": {
                    "kind": "view",
                    "view_index": v_idx,
                    "view_path": view_path,
                },
                "fingerprint": fingerprint_node(view),
                "has_visibility": isinstance(view.get("visibility"), list),
            }
        )
        sections = view.get("sections")
        if isinstance(sections, list):
            for s_idx, section in enumerate(sections):
                if not isinstance(section, dict):
                    continue
                section_label = _node_label(section, fallback=f"Section {s_idx}")
                results.append(
                    {
                        "kind": "section",
                        "label": section_label,
                        "detail": _node_detail(section) or f"section #{s_idx}",
                        "breadcrumb": f"{view_label} › {section_label}",
                        "type": section.get("type") or "section",
                        "locator": {
                            "kind": "section",
                            "view_index": v_idx,
                            "view_path": view_path,
                            "section_index": s_idx,
                        },
                        "fingerprint": fingerprint_node(section),
                        "has_visibility": isinstance(section.get("visibility"), list),
                    }
                )
                cards = section.get("cards")
                if isinstance(cards, list):
                    for c_idx, card in enumerate(cards):
                        if not isinstance(card, dict):
                            continue
                        card_label = _node_label(card, fallback=f"Card {c_idx}")
                        results.append(
                            {
                                "kind": "card",
                                "label": card_label,
                                "detail": _node_detail(card) or f"card #{c_idx}",
                                "breadcrumb": f"{view_label} › {section_label} › {card_label}",
                                "type": card.get("type") or "card",
                                "locator": {
                                    "kind": "card",
                                    "view_index": v_idx,
                                    "view_path": view_path,
                                    "section_index": s_idx,
                                    "card_index": c_idx,
                                },
                                "fingerprint": fingerprint_node(card),
                                "has_visibility": isinstance(card.get("visibility"), list),
                            }
                        )
        cards = view.get("cards")
        if isinstance(cards, list):
            for c_idx, card in enumerate(cards):
                if not isinstance(card, dict):
                    continue
                card_label = _node_label(card, fallback=f"Card {c_idx}")
                results.append(
                    {
                        "kind": "card",
                        "label": card_label,
                        "detail": _node_detail(card) or f"card #{c_idx}",
                        "breadcrumb": f"{view_label} › {card_label}",
                        "type": card.get("type") or "card",
                        "locator": {
                            "kind": "card",
                            "view_index": v_idx,
                            "view_path": view_path,
                            "card_index": c_idx,
                        },
                        "fingerprint": fingerprint_node(card),
                        "has_visibility": isinstance(card.get("visibility"), list),
                    }
                )
    return results
