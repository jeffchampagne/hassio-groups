"""Unit tests for Lovelace locator + visibility rewrite (Patterns A/B/C)."""

from __future__ import annotations

from vizgroups.const import MERGE_ENSURE_USER_BRANCH, MERGE_REPLACE_USER
from vizgroups.models import Locator
from vizgroups.sync import (
    _card_preview,
    _node_label,
    apply_binding_to_config,
    apply_visibility_users,
    audit_dashboard_user_visibility,
    build_dashboard_preview_tree,
    fingerprint_node,
    list_visibility_nodes,
    make_user_condition,
    resolve_locator,
)


SAMPLE = {
    "views": [
        {
            "title": "Home",
            "path": "home",
            "sections": [
                {
                    "title": "Main",
                    "cards": [
                        {"type": "entities", "title": "Lights", "entities": ["light.a"]},
                        {
                            "type": "custom:timer-bar-card",
                            "title": "Apartment Door",
                            "visibility": [
                                {
                                    "condition": "user",
                                    "users": ["old1", "old2"],
                                }
                            ],
                        },
                    ],
                },
                {
                    "title": "Mixed",
                    "visibility": [
                        {
                            "condition": "or",
                            "conditions": [
                                {
                                    "condition": "state",
                                    "entity": "input_select.building_mode",
                                    "state": "Open",
                                },
                                {
                                    "condition": "user",
                                    "users": ["oldA", "oldB"],
                                },
                            ],
                        }
                    ],
                    "cards": [],
                },
            ],
        },
        {
            "title": "Admin",
            "path": "admin",
            "cards": [
                {
                    "type": "markdown",
                    "content": "secret",
                    "visibility": [{"condition": "user", "users": ["admin1"]}],
                }
            ],
        },
    ]
}


def test_make_user_condition_fail_closed_empty() -> None:
    assert make_user_condition([]) == {"condition": "user", "users": []}


def test_resolve_card_in_section() -> None:
    loc = Locator(kind="card", view_index=0, section_index=0, card_index=1)
    node = resolve_locator(SAMPLE, loc)
    assert node is not None
    assert node["title"] == "Apartment Door"


def test_resolve_by_view_path() -> None:
    loc = Locator(kind="view", view_path="admin")
    node = resolve_locator(SAMPLE, loc)
    assert node is not None
    assert node["title"] == "Admin"


def test_resolve_section() -> None:
    loc = Locator(kind="section", view_index=0, section_index=1)
    node = resolve_locator(SAMPLE, loc)
    assert node is not None
    assert node["title"] == "Mixed"


def test_resolve_missing_returns_none() -> None:
    loc = Locator(kind="card", view_index=0, section_index=0, card_index=99)
    assert resolve_locator(SAMPLE, loc) is None


def test_pattern_a_replace_user_only() -> None:
    visibility = [{"condition": "user", "users": ["a", "b"]}]
    out = apply_visibility_users(visibility, ["x", "y"], merge_mode=MERGE_REPLACE_USER)
    assert out == [{"condition": "user", "users": ["x", "y"]}]


def test_pattern_c_preserves_state_sibling() -> None:
    visibility = [
        {
            "condition": "or",
            "conditions": [
                {
                    "condition": "state",
                    "entity": "input_select.building_mode",
                    "state": "Open",
                },
                {"condition": "user", "users": ["old"]},
            ],
        }
    ]
    out = apply_visibility_users(
        visibility, ["u1", "u2"], merge_mode=MERGE_ENSURE_USER_BRANCH
    )
    assert out[0]["condition"] == "or"
    assert out[0]["conditions"][0]["condition"] == "state"
    assert out[0]["conditions"][0]["entity"] == "input_select.building_mode"
    assert out[0]["conditions"][1] == {"condition": "user", "users": ["u1", "u2"]}


def test_empty_users_keeps_user_condition() -> None:
    visibility = [{"condition": "user", "users": ["a"]}]
    out = apply_visibility_users(visibility, [], merge_mode=MERGE_ENSURE_USER_BRANCH)
    assert out == [{"condition": "user", "users": []}]


def test_no_visibility_appends_user_condition() -> None:
    out = apply_visibility_users(None, ["u1"], merge_mode=MERGE_ENSURE_USER_BRANCH)
    assert out == [{"condition": "user", "users": ["u1"]}]


def test_state_only_appends_user_leaf() -> None:
    visibility = [
        {"condition": "state", "entity": "binary_sensor.x", "state": "on"}
    ]
    out = apply_visibility_users(
        visibility, ["u1"], merge_mode=MERGE_ENSURE_USER_BRANCH
    )
    assert len(out) == 2
    assert out[0]["condition"] == "state"
    assert out[1] == {"condition": "user", "users": ["u1"]}


def test_apply_binding_ok_and_fail_closed() -> None:
    loc = Locator(kind="card", view_index=0, section_index=0, card_index=1)
    new_cfg, status = apply_binding_to_config(SAMPLE, loc, [])
    assert status == "ok"
    assert new_cfg is not None
    node = resolve_locator(new_cfg, loc)
    assert node["visibility"] == [{"condition": "user", "users": []}]
    assert SAMPLE["views"][0]["sections"][0]["cards"][1]["visibility"][0]["users"] == [
        "old1",
        "old2",
    ]


def test_apply_binding_stale_fingerprint() -> None:
    loc = Locator(kind="card", view_index=0, section_index=0, card_index=1)
    node = resolve_locator(SAMPLE, loc)
    fp = fingerprint_node(node)
    new_cfg, status = apply_binding_to_config(
        SAMPLE, loc, ["u1"], expected_fingerprint="wrong|fp"
    )
    assert status == "stale"
    assert new_cfg is None
    new_cfg, status = apply_binding_to_config(
        SAMPLE, loc, ["u1"], expected_fingerprint=fp
    )
    assert status == "ok"
    assert new_cfg is not None


def test_apply_binding_mixed_section() -> None:
    loc = Locator(kind="section", view_index=0, section_index=1)
    new_cfg, status = apply_binding_to_config(SAMPLE, loc, ["n1", "n2"])
    assert status == "ok"
    node = resolve_locator(new_cfg, loc)
    conds = node["visibility"][0]["conditions"]
    assert conds[0]["condition"] == "state"
    assert conds[1]["users"] == ["n1", "n2"]


def test_list_visibility_nodes_covers_kinds() -> None:
    nodes = list_visibility_nodes(SAMPLE)
    kinds = {n["kind"] for n in nodes}
    assert {"view", "section", "card"} <= kinds
    assert any(n["label"] == "Apartment Door" for n in nodes)


def test_mushroom_template_primary_label() -> None:
    """Mushroom template cards store the visible title in ``primary``."""
    card = {
        "type": "custom:mushroom-template-card",
        "primary": "John's Apartment",
        "icon": "mdi:home",
        "visibility": [{"condition": "user", "users": ["u1"]}],
    }
    assert _node_label(card, fallback="Card 1") == "John's Apartment"
    assert "John's Apartment" in fingerprint_node(card)
    assert fingerprint_node(card).startswith("custom:mushroom-template-card|")
    preview = _card_preview(card)
    assert preview["label"] == "John's Apartment"
    assert preview["type"] == "custom:mushroom-template-card"
    assert preview["label"] != preview["type"]

    cfg = {
        "views": [
            {
                "title": "Building",
                "path": "home",
                "sections": [{"cards": [card]}],
            }
        ]
    }
    nodes = list_visibility_nodes(cfg)
    mushroom = next(n for n in nodes if n["kind"] == "card")
    assert mushroom["label"] == "John's Apartment"
    tree = build_dashboard_preview_tree(cfg)
    assert tree[0]["sections"][0]["cards"][0]["label"] == "John's Apartment"


def test_section_label_from_child_heading_card() -> None:
    """Untitled sections inherit the first type:heading child (Overview pattern)."""
    section = {
        "type": "grid",
        "visibility": [{"condition": "user", "users": ["u1"]}],
        "cards": [
            {"type": "heading", "heading": "Common Area Lighting", "icon": "mdi:lightbulb"},
            {"type": "custom:mushroom-light-card", "entity": "light.a"},
        ],
    }
    assert _node_label(section, fallback="Section 2") == "Common Area Lighting"

    cfg = {
        "views": [
            {
                "title": "Building",
                "sections": [section],
            }
        ]
    }
    nodes = list_visibility_nodes(cfg)
    sec = next(n for n in nodes if n["kind"] == "section")
    assert sec["label"] == "Common Area Lighting"
    audit = audit_dashboard_user_visibility(
        cfg, dashboard_url_path="lovelace", bindings=[]
    )
    assert audit["elements"][0]["label"] == "Common Area Lighting"


def test_untitled_card_inherits_preceding_section_heading() -> None:
    """Grid/controls after a heading use that heading when they have no title."""
    cfg = {
        "views": [
            {
                "title": "Building",
                "sections": [
                    {
                        "cards": [
                            {"type": "heading", "heading": "Building Mode"},
                            {
                                "type": "grid",
                                "cards": [
                                    {"type": "custom:button-card", "name": "Open"},
                                    {"type": "custom:button-card", "name": "Closed"},
                                ],
                                "visibility": [
                                    {"condition": "user", "users": ["u1"]}
                                ],
                            },
                        ]
                    }
                ],
            }
        ]
    }
    nodes = list_visibility_nodes(cfg)
    grid = next(
        n
        for n in nodes
        if n["kind"] == "card" and n.get("type") == "grid"
    )
    assert grid["label"] == "Building Mode"
    assert grid["label"] != "Open"


def test_node_label_prefers_title_fields_over_type() -> None:
    assert (
        _node_label(
            {"type": "custom:mushroom-template-card", "primary": "Doorbell"},
            fallback="Card",
        )
        == "Doorbell"
    )
    assert (
        _node_label(
            {"type": "heading", "heading": "Lights"},
            fallback="Card",
        )
        == "Lights"
    )
    # No title-ish fields → contextual fallback, not the type string.
    assert (
        _node_label({"type": "custom:mushroom-template-card"}, fallback="Card 3")
        == "Card 3"
    )


def test_replace_mode_keeps_non_user_top_level() -> None:
    visibility = [
        {"condition": "user", "users": ["a"]},
        {"condition": "screen", "media_query": "(min-width: 800px)"},
    ]
    out = apply_visibility_users(
        visibility, ["z"], merge_mode=MERGE_REPLACE_USER
    )
    assert {"condition": "screen", "media_query": "(min-width: 800px)"} in out
    assert {"condition": "user", "users": ["z"]} in out
    assert not any(
        c.get("condition") == "user" and c.get("users") == ["a"] for c in out
    )
