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


def test_node_label_prefers_mushroom_primary() -> None:
    card = {
        "type": "custom:mushroom-template-card",
        "primary": "Johns Apartment",
        "secondary": "Door locked",
        "icon": "mdi:home",
    }
    assert _node_label(card, fallback="Card 0") == "Johns Apartment"


def test_node_label_mushroom_secondary_when_no_primary() -> None:
    card = {
        "type": "custom:mushroom-template-card",
        "secondary": "Only secondary",
    }
    assert _node_label(card, fallback="Card 1") == "Only secondary"


def test_node_label_field_priority_over_type() -> None:
    """primary > secondary > label > name > title > heading; never type."""
    assert (
        _node_label(
            {
                "type": "custom:mushroom-template-card",
                "primary": "P",
                "secondary": "S",
                "label": "L",
                "name": "N",
                "title": "T",
                "heading": "H",
            },
            fallback="Card",
        )
        == "P"
    )
    assert (
        _node_label(
            {
                "type": "custom:mushroom-template-card",
                "secondary": "S",
                "title": "T",
            },
            fallback="Card",
        )
        == "S"
    )
    assert _node_label({"type": "heading", "heading": "Welcome"}, fallback="Card") == "Welcome"
    assert (
        _node_label({"type": "custom:mushroom-template-card"}, fallback="Card 2")
        == "Card 2"
    )


def test_card_preview_mushroom_not_type_string() -> None:
    preview = _card_preview(
        {
            "type": "custom:mushroom-template-card",
            "primary": "Johns Apartment",
            "secondary": "Locked",
            "icon": "mdi:home",
        }
    )
    assert preview["label"] == "Johns Apartment"
    assert preview["snippet"] == "Locked"
    assert preview["type"] == "custom:mushroom-template-card"
    assert "mushroom-template-card" not in preview["label"]


def test_list_visibility_nodes_mushroom_primary_label() -> None:
    cfg = {
        "views": [
            {
                "title": "Home",
                "path": "home",
                "sections": [
                    {
                        "title": "People",
                        "cards": [
                            {
                                "type": "custom:mushroom-template-card",
                                "primary": "Johns Apartment",
                                "secondary": "{{ states('lock.door') }}",
                                "visibility": [
                                    {"condition": "user", "users": ["u1"]}
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    nodes = list_visibility_nodes(cfg)
    cards = [n for n in nodes if n["kind"] == "card"]
    assert any(n["label"] == "Johns Apartment" for n in cards)
    assert not any("mushroom-template-card" in (n["label"] or "") for n in cards)


def test_preview_tree_mushroom_primary_label() -> None:
    cfg = {
        "views": [
            {
                "title": "Home",
                "path": "home",
                "cards": [
                    {
                        "type": "custom:mushroom-template-card",
                        "primary": "Johns Apartment",
                    }
                ],
            }
        ]
    }
    tree = build_dashboard_preview_tree(cfg)
    cards = tree[0]["cards"]
    assert cards[0]["label"] == "Johns Apartment"


def test_audit_uses_mushroom_primary_not_type() -> None:
    cfg = {
        "views": [
            {
                "title": "Home",
                "path": "home",
                "sections": [
                    {
                        "title": "People",
                        "cards": [
                            {
                                "type": "custom:mushroom-template-card",
                                "primary": "Johns Apartment",
                                "visibility": [
                                    {"condition": "user", "users": ["u1"]}
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    audit = audit_dashboard_user_visibility(
        cfg, dashboard_url_path="lovelace", bindings=[]
    )
    assert audit["summary"]["with_user_visibility"] == 1
    assert audit["elements"][0]["label"] == "Johns Apartment"
    assert "mushroom" not in audit["elements"][0]["label"].lower()
