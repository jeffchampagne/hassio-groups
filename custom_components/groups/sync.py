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
    """Human-readable label: title/heading/name — never fall back to card type as the name."""
    for key in ("title", "heading", "name"):
        val = node.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    # Markdown cards often use content as the visible title.
    if str(node.get("type") or "") == "markdown":
        content = node.get("content")
        if isinstance(content, str) and content.strip():
            for line in content.splitlines():
                line = line.strip().lstrip("#").strip()
                if line:
                    return line[:80]
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
    # Do not use type as the display name (e.g. "heading") — keep type in its own field.
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
                "type": view.get("type") or ("sections" if isinstance(view.get("sections"), list) else "masonry" if isinstance(view.get("cards"), list) else "view"),
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


def visibility_has_user_condition(visibility: Any) -> bool:
    """True if any nested condition:user leaf exists in a visibility tree."""
    if isinstance(visibility, dict):
        if visibility.get("condition") == USER_CONDITION:
            return True
        return any(visibility_has_user_condition(v) for v in visibility.values())
    if isinstance(visibility, list):
        return any(visibility_has_user_condition(item) for item in visibility)
    return False


def collect_visibility_user_ids(visibility: Any) -> list[str]:
    """Unique user IDs from every condition:user leaf (order preserved)."""
    out: list[str] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("condition") == USER_CONDITION:
                for uid in node.get("users") or []:
                    s = str(uid)
                    if s and s not in out:
                        out.append(s)
                return
            for val in node.values():
                _walk(val)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(visibility)
    return out


def _as_locator_dict(locator: Any) -> dict[str, Any]:
    if locator is None:
        return {}
    if hasattr(locator, "to_dict"):
        return dict(locator.to_dict())
    if isinstance(locator, dict):
        return dict(locator)
    return {}


def locators_match(left: Any, right: Any) -> bool:
    """Match binding locator to a scanned node locator (path preferred over index)."""
    a = _as_locator_dict(left)
    b = _as_locator_dict(right)
    if (a.get("kind") or "card") != (b.get("kind") or "card"):
        return False
    path_a = a.get("view_path") or None
    path_b = b.get("view_path") or None
    if path_a and path_b:
        if path_a != path_b:
            return False
    elif a.get("view_index") != b.get("view_index"):
        return False
    if a.get("section_index") != b.get("section_index"):
        return False
    if a.get("card_index") != b.get("card_index"):
        return False
    return True



def _audit_element_type(kind: str | None, node: dict[str, Any], resolved: dict[str, Any]) -> str:
    """Lovelace element type for audit rows (view mode / card type — not the title)."""
    raw = resolved.get("type")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    # Views often omit type: infer layout mode from structure.
    if (kind or "") == "view":
        if isinstance(resolved.get("sections"), list):
            return "sections"
        if isinstance(resolved.get("cards"), list):
            return "masonry"
        return "view"
    if (kind or "") == "section":
        return "grid"
    if isinstance(node.get("type"), str) and node["type"].strip():
        return node["type"].strip()
    return kind or "card"

def audit_dashboard_user_visibility(
    config: dict[str, Any],
    *,
    dashboard_url_path: str,
    bindings: list[Any],
) -> dict[str, Any]:
    """
    Scan Lovelace for elements with condition:user visibility and classify
    each as managed (matched Viz Groups binding) or outside/manual.
    """
    dash = dashboard_url_path or "lovelace"
    relevant = []
    for binding in bindings or []:
        if hasattr(binding, "dashboard_url_path"):
            b_path = binding.dashboard_url_path or "lovelace"
            b_id = binding.id
            b_label = getattr(binding, "label", "") or ""
            b_loc = binding.locator
            b_stale = bool(getattr(binding, "stale", False))
            b_include = list(getattr(getattr(binding, "expression", None), "include", []) or [])
            b_exclude = list(getattr(getattr(binding, "expression", None), "exclude", []) or [])
        elif isinstance(binding, dict):
            b_path = binding.get("dashboard_url_path") or "lovelace"
            b_id = binding.get("id")
            b_label = binding.get("label") or ""
            b_loc = binding.get("locator")
            b_stale = bool(binding.get("stale", False))
            expr = binding.get("expression") or {}
            b_include = list(expr.get("include") or [])
            b_exclude = list(expr.get("exclude") or [])
        else:
            continue
        if b_path != dash and not (
            dash in ("lovelace", "default") and b_path in ("lovelace", "default")
        ):
            continue
        relevant.append(
            {
                "id": b_id,
                "label": b_label,
                "locator": b_loc,
                "stale": b_stale,
                "include": b_include,
                "exclude": b_exclude,
            }
        )

    rows: list[dict[str, Any]] = []
    for node in list_visibility_nodes(config):
        # Re-resolve to inspect visibility contents (list_visibility_nodes is metadata-only).
        loc = Locator.from_dict(node.get("locator") or {})
        resolved = resolve_locator(config, loc)
        if not isinstance(resolved, dict):
            continue
        visibility = resolved.get("visibility")
        if not visibility_has_user_condition(visibility):
            continue
        users = collect_visibility_user_ids(visibility)
        elem_type = _audit_element_type(node.get("kind"), node, resolved)
        # Prefer real title from resolved Lovelace node (heading/title/name).
        label = _node_label(
            resolved,
            fallback=str(node.get("label") or node.get("kind") or "Untitled"),
        )
        # If label collapsed to the type string, treat as missing.
        if label.strip().lower() == str(elem_type).strip().lower():
            label = str(node.get("label") or node.get("kind") or "Untitled")
            if label.strip().lower() == str(elem_type).strip().lower():
                label = "Untitled"
        matches = [b for b in relevant if locators_match(b["locator"], node.get("locator"))]
        if matches:
            primary = matches[0]
            # Binding friendly name wins when present and node label is weak.
            binding_name = (primary.get("label") or "").strip()
            if binding_name and label in ("Untitled", node.get("kind"), elem_type):
                label = binding_name
            elif binding_name and label.strip().lower() == "heading":
                label = binding_name
            rows.append(
                {
                    "status": "managed",
                    "kind": node.get("kind"),
                    "label": label,
                    "breadcrumb": node.get("breadcrumb"),
                    "type": elem_type,
                    "locator": node.get("locator"),
                    "fingerprint": node.get("fingerprint") or "",
                    "lovelace_users": users,
                    "binding_id": primary["id"],
                    "binding_label": primary["label"] or primary["id"],
                    "binding_stale": primary["stale"],
                    "binding_include": primary["include"],
                    "binding_exclude": primary["exclude"],
                    "matched_binding_ids": [m["id"] for m in matches],
                }
            )
        else:
            rows.append(
                {
                    "status": "outside",
                    "kind": node.get("kind"),
                    "label": label,
                    "breadcrumb": node.get("breadcrumb"),
                    "type": elem_type,
                    "locator": node.get("locator"),
                    "fingerprint": node.get("fingerprint") or "",
                    "lovelace_users": users,
                    "binding_id": None,
                    "binding_label": None,
                    "binding_stale": False,
                    "binding_include": [],
                    "binding_exclude": [],
                    "matched_binding_ids": [],
                }
            )

    managed = sum(1 for r in rows if r["status"] == "managed")
    outside = sum(1 for r in rows if r["status"] == "outside")
    return {
        "dashboard_url_path": dash,
        "elements": rows,
        "summary": {
            "with_user_visibility": len(rows),
            "managed": managed,
            "outside": outside,
            "bindings_on_dashboard": len(relevant),
        },
    }


def _card_preview(card: dict[str, Any]) -> dict[str, Any]:
    """Compact fields for visual preview tiles."""
    ntype = str(card.get("type") or "card")
    label = _node_label(card, fallback=ntype)
    snippet = ""
    if ntype == "heading":
        snippet = str(card.get("heading") or label)
        label = snippet
    elif ntype == "markdown":
        content = str(card.get("content") or "")
        # first meaningful line
        for line in content.splitlines():
            line = line.strip().lstrip("#").strip()
            if line:
                snippet = line[:120]
                break
    elif isinstance(card.get("entity"), str):
        snippet = card["entity"]
    elif isinstance(card.get("entities"), list) and card["entities"]:
        first = card["entities"][0]
        snippet = first if isinstance(first, str) else str((first or {}).get("entity") or "")
    icon = card.get("icon")
    if not icon:
        icon = {
            "heading": "mdi:format-header-pound",
            "markdown": "mdi:language-markdown",
            "entities": "mdi:format-list-bulleted",
            "entity": "mdi:eye",
            "button": "mdi:gesture-tap-button",
            "gauge": "mdi:gauge",
            "thermostat": "mdi:thermostat",
            "media-control": "mdi:play-circle",
            "picture": "mdi:image",
            "horizontal-stack": "mdi:view-column",
            "vertical-stack": "mdi:view-sequential",
            "grid": "mdi:view-grid",
        }.get(ntype, "mdi:card")
    return {
        "label": label,
        "snippet": snippet,
        "type": ntype,
        "icon": icon,
        "detail": _node_detail(card),
    }


def build_dashboard_preview_tree(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Hierarchical view → section → card tree for the visual locator picker."""
    tree: list[dict[str, Any]] = []
    views = config.get("views")
    if not isinstance(views, list):
        return tree

    for v_idx, view in enumerate(views):
        if not isinstance(view, dict):
            continue
        view_path = view.get("path")
        view_label = _node_label(view, fallback=str(view_path or f"View {v_idx}"))
        view_node: dict[str, Any] = {
            "kind": "view",
            "label": view_label,
            "detail": _node_detail(view) or f"view #{v_idx}",
            "breadcrumb": view_label,
            "type": view.get("type") or "sections",
            "icon": view.get("icon") or "mdi:view-dashboard",
            "path": view_path,
            "locator": {
                "kind": "view",
                "view_index": v_idx,
                "view_path": view_path,
            },
            "fingerprint": fingerprint_node(view),
            "has_visibility": isinstance(view.get("visibility"), list),
            "sections": [],
            "cards": [],
        }

        sections = view.get("sections")
        if isinstance(sections, list):
            for s_idx, section in enumerate(sections):
                if not isinstance(section, dict):
                    continue
                section_label = _node_label(section, fallback=f"Section {s_idx}")
                section_node: dict[str, Any] = {
                    "kind": "section",
                    "label": section_label,
                    "detail": _node_detail(section) or f"section #{s_idx}",
                    "breadcrumb": f"{view_label} › {section_label}",
                    "type": section.get("type") or "grid",
                    "icon": "mdi:view-grid-plus",
                    "locator": {
                        "kind": "section",
                        "view_index": v_idx,
                        "view_path": view_path,
                        "section_index": s_idx,
                    },
                    "fingerprint": fingerprint_node(section),
                    "has_visibility": isinstance(section.get("visibility"), list),
                    "cards": [],
                }
                cards = section.get("cards")
                if isinstance(cards, list):
                    for c_idx, card in enumerate(cards):
                        if not isinstance(card, dict):
                            continue
                        preview = _card_preview(card)
                        section_node["cards"].append(
                            {
                                "kind": "card",
                                **preview,
                                "breadcrumb": f"{view_label} › {section_label} › {preview['label']}",
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
                view_node["sections"].append(section_node)

        cards = view.get("cards")
        if isinstance(cards, list):
            for c_idx, card in enumerate(cards):
                if not isinstance(card, dict):
                    continue
                preview = _card_preview(card)
                view_node["cards"].append(
                    {
                        "kind": "card",
                        **preview,
                        "breadcrumb": f"{view_label} › {preview['label']}",
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
        tree.append(view_node)
    return tree
