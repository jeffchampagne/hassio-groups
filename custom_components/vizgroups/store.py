"""Persistent .storage-backed store for groups and bindings."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .membership import (
    MEMBER_TYPE_GROUP,
    MEMBER_TYPE_USER,
    flatten_all_groups,
    members_from_legacy,
    normalize_members,
    normalize_user_ids,
)
from .models import Binding, Group, MemberRef, SyncMetadata, new_binding, new_group, utcnow_iso


class GroupsStore:
    """Load/save Viz Groups definitions from Home Assistant Store."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.groups: dict[str, Group] = {}
        self.bindings: dict[str, Binding] = {}
        self.sync_meta = SyncMetadata()

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.groups = {
            item["id"]: Group.from_dict(item)
            for item in data.get("groups", [])
            if item.get("id")
        }
        self.bindings = {
            item["id"]: Binding.from_dict(item)
            for item in data.get("bindings", [])
            if item.get("id")
        }
        self.sync_meta = SyncMetadata.from_dict(data.get("sync"))

    async def async_save(self) -> None:
        await self._store.async_save(
            {
                "groups": [g.to_dict() for g in self.groups.values()],
                "bindings": [b.to_dict() for b in self.bindings.values()],
                "sync": self.sync_meta.to_dict(),
            }
        )

    def get_group(self, group_id: str) -> Group | None:
        if group_id in self.groups:
            return self.groups[group_id]
        needle = group_id
        for prefix in ("sensor.vizgroups_", "sensor.groups_"):
            if needle.startswith(prefix):
                needle = needle.removeprefix(prefix)
                break
        return self.groups.get(needle)

    def get_binding(self, binding_id: str) -> Binding | None:
        return self.bindings.get(binding_id)

    def members_tree(self) -> dict[str, list[dict[str, str]]]:
        """Raw typed membership tree (users + nested group refs)."""
        return {
            gid: [m.to_dict() for m in group.members]
            for gid, group in self.groups.items()
        }

    def members_by_group(self) -> dict[str, list[str]]:
        """Effective flattened HA user ids per group (cycle-safe)."""
        return flatten_all_groups(self.members_tree())

    def apply_members_payload(
        self,
        group: Group,
        *,
        members: list[Any] | None = None,
        member_user_ids: list[str] | None = None,
        member_group_ids: list[str] | None = None,
    ) -> None:
        """Set group.members from typed and/or legacy payload fields."""
        # When only user ids are provided (legacy autosave), preserve nested groups.
        if members is None and member_group_ids is None and member_user_ids is not None:
            group.member_user_ids = list(member_user_ids)
            return
        refs = members_from_legacy(
            members=members,
            member_user_ids_list=member_user_ids,
            member_group_ids_list=member_group_ids,
        )
        # Reject self-membership edges up front (cycle of length 1).
        refs = [r for r in refs if not (r["type"] == MEMBER_TYPE_GROUP and r["id"] == group.id)]
        group.members = [MemberRef(type=r["type"], id=r["id"]) for r in normalize_members(refs)]

    async def upsert_group(self, group: Group) -> Group:
        # Drop self-refs; normalize typed members.
        refs = [
            m.to_dict()
            for m in group.members
            if not (m.type == MEMBER_TYPE_GROUP and m.id == group.id)
        ]
        group.members = [
            MemberRef(type=r["type"], id=r["id"]) for r in normalize_members(refs)
        ]
        self.groups[group.id] = group
        await self.async_save()
        return group

    async def rename_group(self, old_id: str, new_id: str) -> Group:
        """Rename a group id and rewrite binding + nested-member refs."""
        old_id = (old_id or "").strip()
        new_id = (new_id or "").strip()
        if not old_id or not new_id:
            raise ValueError("Both old and new group ids are required")
        if old_id == new_id:
            group = self.get_group(old_id)
            if not group:
                raise ValueError(f"Unknown group {old_id}")
            return group
        group = self.groups.pop(old_id, None)
        if group is None:
            raise ValueError(f"Unknown group {old_id}")
        if new_id in self.groups:
            # put it back so we don't lose data on conflict
            self.groups[old_id] = group
            raise ValueError(f"Group id already exists: {new_id}")
        group.id = new_id
        group.updated = utcnow_iso()
        self.groups[new_id] = group
        for binding in self.bindings.values():
            binding.expression.include = [
                new_id if g == old_id else g for g in binding.expression.include
            ]
            binding.expression.exclude = [
                new_id if g == old_id else g for g in binding.expression.exclude
            ]
            binding.updated = utcnow_iso()
        for other in self.groups.values():
            changed = False
            new_members: list[MemberRef] = []
            for m in other.members:
                if m.type == MEMBER_TYPE_GROUP and m.id == old_id:
                    new_members.append(MemberRef.group(new_id))
                    changed = True
                else:
                    new_members.append(m)
            if changed:
                other.members = new_members
                other.updated = utcnow_iso()
        await self.async_save()
        return group

    async def delete_group(self, group_id: str) -> None:
        self.groups.pop(group_id, None)
        # Drop nested refs to the deleted group.
        for group in self.groups.values():
            kept = [
                m
                for m in group.members
                if not (m.type == MEMBER_TYPE_GROUP and m.id == group_id)
            ]
            if len(kept) != len(group.members):
                group.members = kept
                group.updated = utcnow_iso()
        # Drop bindings that referenced the deleted group
        for binding in list(self.bindings.values()):
            include = [g for g in binding.expression.include if g != group_id]
            exclude = [g for g in binding.expression.exclude if g != group_id]
            if include != binding.expression.include or exclude != binding.expression.exclude:
                binding.expression.include = include
                binding.expression.exclude = exclude
                if not include:
                    self.bindings.pop(binding.id, None)
        await self.async_save()

    async def set_members(self, group_id: str, user_ids: list[str]) -> Group:
        """Replace direct user members; preserve nested groups (legacy service)."""
        group = self.get_group(group_id)
        if not group:
            raise ValueError(f"Unknown group {group_id}")
        group.member_user_ids = normalize_user_ids(user_ids)
        group.updated = utcnow_iso()
        await self.async_save()
        return group

    async def set_typed_members(self, group_id: str, members: list[Any]) -> Group:
        group = self.get_group(group_id)
        if not group:
            raise ValueError(f"Unknown group {group_id}")
        self.apply_members_payload(group, members=members)
        group.updated = utcnow_iso()
        await self.async_save()
        return group

    async def add_members(self, group_id: str, user_ids: list[str]) -> Group:
        group = self.get_group(group_id)
        if not group:
            raise ValueError(f"Unknown group {group_id}")
        return await self.set_members(group_id, list(group.member_user_ids) + list(user_ids))

    async def remove_members(self, group_id: str, user_ids: list[str]) -> Group:
        group = self.get_group(group_id)
        if not group:
            raise ValueError(f"Unknown group {group_id}")
        drop = set(user_ids)
        return await self.set_members(
            group_id, [uid for uid in group.member_user_ids if uid not in drop]
        )

    async def upsert_binding(self, binding: Binding) -> Binding:
        self.bindings[binding.id] = binding
        await self.async_save()
        return binding

    async def delete_binding(self, binding_id: str) -> None:
        self.bindings.pop(binding_id, None)
        await self.async_save()

    async def prune_missing_users(self, valid_user_ids: set[str]) -> list[str]:
        """Remove deleted HA users from all groups. Returns touched group ids."""
        touched: list[str] = []
        for group in self.groups.values():
            kept = [
                m
                for m in group.members
                if m.type != MEMBER_TYPE_USER or m.id in valid_user_ids
            ]
            if [m.to_dict() for m in kept] != [m.to_dict() for m in group.members]:
                group.members = kept
                touched.append(group.id)
        if touched:
            await self.async_save()
        return touched

    async def create_group_from_service(self, **kwargs: Any) -> Group:
        group = new_group(**kwargs)
        if group.id in self.groups:
            raise ValueError(f"Group id already exists: {group.id}")
        return await self.upsert_group(group)

    async def create_binding_from_service(self, **kwargs: Any) -> Binding:
        binding = new_binding(**kwargs)
        return await self.upsert_binding(binding)
