"""Unit tests for Lovelace locator + visibility rewrite (Patterns A/B/C)."""

from __future__ import annotations

from vizgroups.const import MERGE_ENSURE_USER_BRANCH, MERGE_REPLACE_USER
from vizgroups.models import Locator
from vizgroups.sync import (
    apply_binding_to_config,
    apply_visibility_users,
    audit_dashboard_user_visibility,
    collect_visibility_user_ids,
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


def test_conditional_or_state_user_rewrites_conditions_not_visibility() -> None:
    """Building Mode Closed: type:conditional with or(state, user) in conditions.

    Sync must rewrite the nested condition:user leaf, strip a sibling
    visibility people gate (older sync artifact), and audit must read
    conditions first (not a stale visibility block).
    """
    cfg = {
        "views": [
            {
                "title": "Building",
                "path": "home",
                "sections": [
                    {
                        "title": "Mode",
                        "cards": [
                            {
                                "type": "conditional",
                                "conditions": [
                                    {
                                        "condition": "or",
                                        "conditions": [
                                            {
                                                "condition": "state",
                                                "entity": "input_select.building_mode",
                                                "state": "Closed",
                                            },
                                            {
                                                "condition": "user",
                                                "users": ["owner"],
                                            },
                                        ],
                                    }
                                ],
                                # Bug artifact: older sync invented visibility.
                                "visibility": [
                                    {"condition": "user", "users": ["owner", "owner"]}
                                ],
                                "card": {
                                    "type": "custom:button-card",
                                    "name": "Closed",
                                    "entity": "input_select.building_mode",
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }
    loc = Locator(kind="card", view_index=0, section_index=0, card_index=0)
    # Before sync, audit already prefers conditions over invented visibility.
    pre = audit_dashboard_user_visibility(
        cfg, dashboard_url_path="lovelace", bindings=[]
    )
    pre_row = next(e for e in pre["elements"] if e["label"] == "Closed")
    assert pre_row["lovelace_users"] == ["owner"]

    new_cfg, status = apply_binding_to_config(cfg, loc, ["u1", "u2", "u1"])
    assert status == "ok"
    assert new_cfg is not None
    node = resolve_locator(new_cfg, loc)
    assert node is not None
    assert "visibility" not in node
    assert node["conditions"][0]["condition"] == "or"
    assert node["conditions"][0]["conditions"][0] == {
        "condition": "state",
        "entity": "input_select.building_mode",
        "state": "Closed",
    }
    assert node["conditions"][0]["conditions"][1] == {
        "condition": "user",
        "users": ["u1", "u2"],  # deduped
    }
    assert collect_visibility_user_ids(node["conditions"]) == ["u1", "u2"]
    # Source config untouched
    assert cfg["views"][0]["sections"][0]["cards"][0]["conditions"][0]["conditions"][1][
        "users"
    ] == ["owner"]

    audit = audit_dashboard_user_visibility(
        new_cfg,
        dashboard_url_path="lovelace",
        bindings=[
            {
                "id": "bind-closed",
                "label": "Closed",
                "dashboard_url_path": "lovelace",
                "locator": loc.to_dict(),
                "fingerprint": fingerprint_node(node),
                "stale": False,
                "expression": {"include": ["force-closed"], "exclude": []},
            }
        ],
    )
    row = next(e for e in audit["elements"] if e["label"] == "Closed")
    assert row["status"] == "managed"
    assert row["lovelace_users"] == ["u1", "u2"]


def test_conditional_and_tree_rewrites_user_leaf() -> None:
    """Nested and() trees also rewrite the condition:user leaf in place."""
    cfg = {
        "views": [
            {
                "cards": [
                    {
                        "type": "conditional",
                        "conditions": [
                            {
                                "condition": "and",
                                "conditions": [
                                    {
                                        "condition": "state",
                                        "entity": "binary_sensor.x",
                                        "state": "on",
                                    },
                                    {"condition": "user", "users": ["old"]},
                                ],
                            }
                        ],
                        "card": {"type": "markdown", "content": "secret"},
                    }
                ]
            }
        ]
    }
    loc = Locator(kind="card", view_index=0, card_index=0)
    new_cfg, status = apply_binding_to_config(cfg, loc, ["a", "b"])
    assert status == "ok"
    node = resolve_locator(new_cfg, loc)
    assert "visibility" not in node
    assert node["conditions"][0]["condition"] == "and"
    assert node["conditions"][0]["conditions"][1]["users"] == ["a", "b"]
    assert node["conditions"][0]["conditions"][0]["condition"] == "state"


def test_conditional_plain_user_conditions_rewritten() -> None:
    """Simple conditions: [condition:user] — rewrite in place, no visibility."""
    cfg = {
        "views": [
            {
                "cards": [
                    {
                        "type": "conditional",
                        "conditions": [{"condition": "user", "users": ["old"]}],
                        "card": {"type": "entities", "entities": ["light.a"]},
                    }
                ]
            }
        ]
    }
    loc = Locator(kind="card", view_index=0, card_index=0)
    new_cfg, status = apply_binding_to_config(cfg, loc, ["n1"])
    assert status == "ok"
    node = resolve_locator(new_cfg, loc)
    assert "visibility" not in node
    assert node["conditions"] == [{"condition": "user", "users": ["n1"]}]
