# HA Groups

**HA Groups** is a Home Assistant custom integration for first-class **user groups**: manage membership in an admin panel, bind any visibility-capable Lovelace element to include/exclude groups, and expose membership for automations.

- **Domain:** `hassio_groups`
- **Panel:** sidebar **HA Groups** (Lit, admin-only)
- **Storage:** Home Assistant `.storage` (covered by built-in HA Backup — no custom backup path)
- **Visibility model:** rewrite managed `condition: user` leaves only; empty membership **fail-closes** with `users: []`
- **Multi-group:** **AND** include ∩ **NOT** exclude
- **Important:** Visibility is **UX, not ACL**. Hiding a card does not block service calls via the API.

## Install (HACS custom repository)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Add `https://github.com/jeffchampagne/hassio-groups` as category **Integration**
3. Install **HA Groups**, then **restart** Home Assistant
4. Settings → Devices & Services → **Add Integration** → **HA Groups**

### Manual install

Copy `custom_components/hassio_groups` into your HA `custom_components/` folder, restart, then add the integration.

## Setup

1. Add the **HA Groups** integration (single instance).
2. Open the **HA Groups** sidebar panel (admins only).
3. Create groups and assign members (friendly names primary; user IDs shown as subtitles on detail rows).
4. Create visibility bindings (dashboard + locator + include/exclude groups).
5. Use **Sync now** (or rely on auto-sync) to write Lovelace `visibility` user lists.

Options (integration → Configure):

| Option | Default | Notes |
|---|---|---|
| Auto-sync | on | Sync when membership/bindings change |
| Dry-run | off | Compute rewrites without saving dashboards |
| Normalize duplicates | on | Dedupe + stable-sort user IDs |
| Dashboard allowlist | empty | Comma-separated `url_path` values; empty = all storage dashboards |

YAML-mode dashboards are detected and skipped with an error until a YAML write strategy exists.

## How conditions work

Effective users for a binding:

1. Intersection of all **include** group members (AND). Empty include → empty set (fail closed).
2. Subtract union of all **exclude** group members (NOT).
3. Dedupe + stable sort.
4. Write `{"condition":"user","users":[...]}` including `users: []` when empty.

Mixed trees (e.g. `or` of `state` + `user`) keep non-user siblings; only the managed `condition: user` leaf is updated.

### Automation example

Each group exposes `sensor.hassio_groups_<group_id>`:

- **state:** member count
- **attributes.members:** list of HA user IDs
- **attributes.member_names:** parallel friendly names

```yaml
conditions:
  - condition: template
    value_template: >-
      {{ trigger.to_state.context.user_id
         in state_attr('sensor.hassio_groups_teachers', 'members') }}
```

Non-membership:

```yaml
{{ trigger.to_state.context.user_id
   not in state_attr('sensor.hassio_groups_teachers', 'members') }}
```

## Services

- `hassio_groups.create_group` / `update_group` / `delete_group`
- `hassio_groups.set_members` / `add_members` / `remove_members`
- `hassio_groups.bind_element` / `unbind_element`
- `hassio_groups.sync` (optional `dashboard`, `dry_run`)
- `hassio_groups.is_member` (response service)

## Development

```bash
python -m pytest tests/
```

Pure sync/locator/membership logic is unit-tested without a live Home Assistant instance.

## License

MIT
