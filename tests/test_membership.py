"""Unit tests for AND/NOT membership math + nested group flatten."""

from __future__ import annotations

from vizgroups.membership import (
    overlapping_direct_user_ids,
    effective_users,
    flatten_all_groups,
    flatten_group_users,
    is_member,
    members_from_legacy,
    normalize_members,
    normalize_user_ids,
)
from vizgroups.models import Group, MemberRef


def test_normalize_dedupes_and_sorts() -> None:
    assert normalize_user_ids(["b", "a", "b", "", "a"]) == ["a", "b"]


def test_empty_include_fail_closed() -> None:
    members = {"teachers": ["u1", "u2"], "admins": ["u1"]}
    assert effective_users([], [], members) == []
    assert effective_users([], ["admins"], members) == []


def test_single_include() -> None:
    members = {"teachers": ["u2", "u1", "u2"]}
    assert effective_users(["teachers"], [], members) == ["u1", "u2"]


def test_and_intersection() -> None:
    members = {
        "teachers": ["u1", "u2", "u3"],
        "staff": ["u2", "u3", "u4"],
    }
    assert effective_users(["teachers", "staff"], [], members) == ["u2", "u3"]


def test_not_exclude() -> None:
    members = {
        "teachers": ["u1", "u2", "u3"],
        "contractors": ["u2"],
    }
    assert effective_users(["teachers"], ["contractors"], members) == ["u1", "u3"]


def test_and_plus_not() -> None:
    members = {
        "teachers": ["u1", "u2", "u3", "u4"],
        "building": ["u2", "u3", "u4", "u5"],
        "contractors": ["u3"],
        "temps": ["u4"],
    }
    assert effective_users(
        ["teachers", "building"], ["contractors", "temps"], members
    ) == ["u2"]


def test_unknown_include_group_is_empty_intersection() -> None:
    members = {"teachers": ["u1"]}
    assert effective_users(["missing"], [], members) == []
    assert effective_users(["teachers", "missing"], [], members) == []


def test_exclude_unknown_group_noop() -> None:
    members = {"teachers": ["u1", "u2"]}
    assert effective_users(["teachers"], ["nope"], members) == ["u1", "u2"]


def test_is_member() -> None:
    assert is_member("u1", ["u1", "u2"]) is True
    assert is_member("u9", ["u1", "u2"]) is False
    assert is_member("", ["u1"]) is False


def test_all_excluded_fail_closed() -> None:
    members = {"teachers": ["u1", "u2"], "gone": ["u1", "u2"]}
    assert effective_users(["teachers"], ["gone"], members) == []


def test_normalize_members_typed() -> None:
    assert normalize_members(
        [
            {"type": "user", "id": "u2"},
            {"type": "group", "id": "staff"},
            {"type": "user", "id": "u2"},
            "u1",
            {"type": "group", "id": "staff"},
        ]
    ) == [
        {"type": "user", "id": "u2"},
        {"type": "group", "id": "staff"},
        {"type": "user", "id": "u1"},
    ]


def test_members_from_legacy_prefers_typed() -> None:
    assert members_from_legacy(
        members=[{"type": "group", "id": "a"}],
        member_user_ids_list=["u1"],
        member_group_ids_list=["b"],
    ) == [{"type": "group", "id": "a"}]
    assert members_from_legacy(
        member_user_ids_list=["u1"],
        member_group_ids_list=["staff"],
    ) == [
        {"type": "user", "id": "u1"},
        {"type": "group", "id": "staff"},
    ]


def test_group_model_roundtrip_legacy_and_nested() -> None:
    legacy = Group.from_dict(
        {"id": "teachers", "name": "Teachers", "member_user_ids": ["u1", "u2"]}
    )
    assert [m.to_dict() for m in legacy.members] == [
        {"type": "user", "id": "u1"},
        {"type": "user", "id": "u2"},
    ]
    nested = Group.from_dict(
        {
            "id": "all-staff",
            "name": "All staff",
            "members": [
                {"type": "user", "id": "u9"},
                {"type": "group", "id": "teachers"},
            ],
        }
    )
    payload = nested.to_dict()
    assert payload["member_user_ids"] == ["u9"]
    assert payload["member_group_ids"] == ["teachers"]
    assert Group.from_dict(payload).member_group_ids == ["teachers"]


def test_flatten_nested_groups() -> None:
    tree = {
        "teachers": [
            {"type": "user", "id": "u1"},
            {"type": "user", "id": "u2"},
        ],
        "staff": [
            {"type": "user", "id": "u3"},
            {"type": "group", "id": "teachers"},
        ],
        "campus": [
            {"type": "group", "id": "staff"},
            {"type": "user", "id": "u4"},
        ],
    }
    assert flatten_group_users("campus", tree) == ["u1", "u2", "u3", "u4"]
    assert flatten_all_groups(tree)["staff"] == ["u1", "u2", "u3"]


def test_flatten_missing_nested_group_fail_closed_branch() -> None:
    tree = {
        "campus": [
            {"type": "user", "id": "u1"},
            {"type": "group", "id": "missing"},
        ]
    }
    assert flatten_group_users("campus", tree) == ["u1"]


def test_flatten_cycle_skips_cyclic_edge() -> None:
    """A ↔ B cycle: each still contributes its own users; skip the loop edge."""
    tree = {
        "a": [
            {"type": "user", "id": "ua"},
            {"type": "group", "id": "b"},
        ],
        "b": [
            {"type": "user", "id": "ub"},
            {"type": "group", "id": "a"},
        ],
    }
    assert flatten_group_users("a", tree) == ["ua", "ub"]
    assert flatten_group_users("b", tree) == ["ua", "ub"]


def test_flatten_self_cycle() -> None:
    tree = {
        "loop": [
            {"type": "user", "id": "u1"},
            {"type": "group", "id": "loop"},
        ]
    }
    assert flatten_group_users("loop", tree) == ["u1"]


def test_flatten_triangle_cycle() -> None:
    tree = {
        "a": [{"type": "group", "id": "b"}, {"type": "user", "id": "ua"}],
        "b": [{"type": "group", "id": "c"}, {"type": "user", "id": "ub"}],
        "c": [{"type": "group", "id": "a"}, {"type": "user", "id": "uc"}],
    }
    assert flatten_group_users("a", tree) == ["ua", "ub", "uc"]


def test_effective_users_with_flattened_nested() -> None:
    tree = {
        "teachers": [{"type": "user", "id": "u1"}, {"type": "user", "id": "u2"}],
        "leaders": [{"type": "group", "id": "teachers"}, {"type": "user", "id": "u3"}],
        "blocked": [{"type": "user", "id": "u2"}],
    }
    flat = flatten_all_groups(tree)
    assert effective_users(["leaders"], ["blocked"], flat) == ["u1", "u3"]


def test_member_user_ids_setter_preserves_nested() -> None:
    group = Group(
        id="x",
        name="X",
        members=[MemberRef.user("u1"), MemberRef.group("staff")],
    )
    group.member_user_ids = ["u2", "u3"]
    assert group.member_user_ids == ["u2", "u3"]
    assert group.member_group_ids == ["staff"]


def test_overlapping_direct_user_ids_with_nested_flatten() -> None:
    tree = {
        "building": [
            {"type": "user", "id": "u1"},
            {"type": "user", "id": "u2"},
        ],
        "leaders": [
            {"type": "user", "id": "u1"},
            {"type": "user", "id": "u9"},
            {"type": "group", "id": "building"},
        ],
    }
    parent_members = [
        {"type": "user", "id": "u1"},
        {"type": "user", "id": "u9"},
    ]
    assert overlapping_direct_user_ids(parent_members, "building", tree) == ["u1"]
    assert overlapping_direct_user_ids(parent_members, "missing", tree) == []
