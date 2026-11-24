"""Unit tests for AND include + NOT exclude membership math."""

from __future__ import annotations

from groups.membership import effective_users, is_member, normalize_user_ids


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
