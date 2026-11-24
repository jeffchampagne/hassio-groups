"""Unit tests for Lovelace locator + visibility rewrite (Patterns A/B/C)."""

from __future__ import annotations

from vizgroups.const import MERGE_ENSURE_USER_BRANCH, MERGE_REPLACE_USER
from vizgroups.models import Locator
from vizgroups.sync import (
    apply_binding_to_config,
    apply_visibility_users,
    audit_dashboard_user_visibility,
    build_dashboard_preview_tree,
    fingerprint_node,
    list_visibility_nodes,
    locators_match,
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


NESTED_CONTAINERS = {
    "views": [
        {
            "title": "Building",
            "path": "home",
            "sections": [
                {
                    "title": "Main",
                    "cards": [
                        {
                            "type": "custom:expander-card",
                            "title": "Staff only",
                            "cards": [
                                {
                                    "type": "entities",
                                    "title": "Hidden lights",
                                    "entities": ["light.office"],
                                    "visibility": [
                                        {
                                            "condition": "user",
                                            "users": ["nested-user-1"],
                                        }
                                    ],
                                },
                                {
                                    "type": "vertical-stack",
                                    "cards": [
                                        {
                                            "type": "horizontal-stack",
                                            "cards": [
                                                {
                                                    "type": "button",
                                                    "name": "Deep button",
                                                    "visibility": [
                                                        {
                                                            "condition": "user",
                                                            "users": [
                                                                "deep-user-a",
                                                                "deep-user-b",
                                                            ],
                                                        }
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "type": "grid",
                            "columns": 2,
                            "cards": [
                                {
                                    "type": "markdown",
                                    "content": "Grid nested",
                                    "visibility": [
                                        {"condition": "user", "users": ["grid-user"]}
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        }
    ]
}


def test_list_visibility_nodes_recurses_expander_and_stacks() -> None:
    nodes = list_visibility_nodes(NESTED_CONTAINERS)
    cards = [n for n in nodes if n["kind"] == "card"]
    nested = next(n for n in cards if n["label"] == "Hidden lights")
    assert nested["locator"]["card_index"] == 0
    assert nested["locator"]["card_path"] == [0]
    assert nested["has_visibility"] is True
    assert "Staff only" in nested["breadcrumb"]

    deep = next(n for n in cards if n["label"] == "Deep button")
    assert deep["locator"]["card_index"] == 0
    assert deep["locator"]["card_path"] == [1, 0, 0]

    grid_child = next(n for n in cards if n["label"] == "Grid nested")
    assert grid_child["locator"]["card_index"] == 1
    assert grid_child["locator"]["card_path"] == [0]


def test_resolve_nested_card_path() -> None:
    loc = Locator(
        kind="card",
        view_index=0,
        section_index=0,
        card_index=0,
        card_path=[1, 0, 0],
    )
    node = resolve_locator(NESTED_CONTAINERS, loc)
    assert node is not None
    assert node.get("name") == "Deep button"

    missing = Locator(
        kind="card",
        view_index=0,
        section_index=0,
        card_index=0,
        card_path=[9],
    )
    assert resolve_locator(NESTED_CONTAINERS, missing) is None


def test_audit_finds_user_visibility_inside_expander() -> None:
    report = audit_dashboard_user_visibility(
        NESTED_CONTAINERS,
        dashboard_url_path="lovelace",
        bindings=[],
    )
    labels = {row["label"] for row in report["elements"]}
    assert "Hidden lights" in labels
    assert "Deep button" in labels
    assert "Grid nested" in labels
    assert report["summary"]["with_user_visibility"] == 3
    assert all(row["status"] == "outside" for row in report["elements"])

    nested_row = next(r for r in report["elements"] if r["label"] == "Hidden lights")
    assert nested_row["lovelace_users"] == ["nested-user-1"]
    assert nested_row["locator"]["card_path"] == [0]


def test_audit_matches_binding_on_nested_card_path() -> None:
    binding_loc = {
        "kind": "card",
        "view_index": 0,
        "section_index": 0,
        "card_index": 0,
        "card_path": [0],
    }
    report = audit_dashboard_user_visibility(
        NESTED_CONTAINERS,
        dashboard_url_path="lovelace",
        bindings=[
            {
                "id": "bind-nested",
                "label": "Nested staff lights",
                "dashboard_url_path": "lovelace",
                "locator": binding_loc,
                "expression": {"include": ["staff"], "exclude": []},
            }
        ],
    )
    nested = next(r for r in report["elements"] if r["label"] == "Hidden lights")
    assert nested["status"] == "managed"
    assert nested["binding_id"] == "bind-nested"
    # Sibling nested path must not match the same binding.
    deep = next(r for r in report["elements"] if r["label"] == "Deep button")
    assert deep["status"] == "outside"


def test_locators_match_card_path() -> None:
    base = {
        "kind": "card",
        "view_index": 0,
        "section_index": 0,
        "card_index": 0,
    }
    assert locators_match(base, {**base})
    assert locators_match({**base, "card_path": [0]}, {**base, "card_path": [0]})
    assert not locators_match({**base, "card_path": [0]}, {**base, "card_path": [1]})
    assert not locators_match({**base, "card_path": [0]}, base)


def test_apply_binding_nested_card_path() -> None:
    loc = Locator(
        kind="card",
        view_index=0,
        section_index=0,
        card_index=1,
        card_path=[0],
    )
    new_cfg, status = apply_binding_to_config(NESTED_CONTAINERS, loc, ["u-new"])
    assert status == "ok"
    node = resolve_locator(new_cfg, loc)
    assert node["visibility"] == [{"condition": "user", "users": ["u-new"]}]
    # Original untouched
    orig = resolve_locator(NESTED_CONTAINERS, loc)
    assert orig["visibility"][0]["users"] == ["grid-user"]


def test_preview_tree_includes_nested_cards() -> None:
    tree = build_dashboard_preview_tree(NESTED_CONTAINERS)
    expander = tree[0]["sections"][0]["cards"][0]
    assert expander["type"] == "custom:expander-card"
    assert expander["cards"][0]["label"] == "Hidden lights"
    assert expander["cards"][0]["locator"]["card_path"] == [0]
    deep = expander["cards"][1]["cards"][0]["cards"][0]
    assert deep["label"] == "Deep button"
    assert deep["locator"]["card_path"] == [1, 0, 0]
