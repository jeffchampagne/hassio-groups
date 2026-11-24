# Viz Groups

**Viz Groups** is a Home Assistant custom integration for first-class **user groups**: manage membership in an admin panel, bind any visibility-capable Lovelace element to include/exclude groups, and expose membership for automations and templates.

- **Domain:** `vizgroups`
- **GitHub:** [`jeffchampagne/hassio-vizgroups`](https://github.com/jeffchampagne/hassio-vizgroups)
- **Panel:** sidebar **Viz Groups** at `/vizgroups` (Lit web component `vizgroups-panel`, admin-only)
- **Storage:** Home Assistant `.storage/vizgroups` (covered by built-in HA Backup)
- **Sensors:** `sensor.vizgroups_<group_id>` per group
- **Visibility model:** rewrite managed `condition: user` leaves only; empty membership **fail-closes** with `users: []`
- **Nested groups:** a group may include other groups as members; sync/sensors use cycle-safe flatten (cyclic edges skipped)
- **Multi-group:** **AND** include ∩ **NOT** exclude
- **Important:** Visibility is **UX, not an ACL**. Hiding a card does not block service calls via the API.

## Install (HACS custom repository)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Add `https://github.com/jeffchampagne/hassio-vizgroups` as category **Integration**
3. Install **Viz Groups**, then **restart** Home Assistant
4. Settings → Devices & Services → **Add Integration** → **Viz Groups**

### Manual install

Copy `custom_components/vizgroups` into your HA `custom_components/` folder, restart, then add the integration.

## Setup

1. Add the **Viz Groups** integration (single instance).
2. Open the **Viz Groups** sidebar panel (admins only).
3. Create groups and assign members:
   - Friendly names are primary; user IDs appear as subtitles on detail rows.
   - Membership **auto-saves** on add/remove for existing groups (name/description/icon still use Save).
   - Group icon browser loads Home Assistant’s full MDI set from `/static/mdi/iconList.json` (same catalog as `ha-icon-picker`) — search by name or keywords (e.g. `thermometer`). Falls back to a curated list if the catalog cannot load.
4. Manage visibility bindings from **Manage visibility** (table + visual picker) or list bindings under **Conditionals**.
5. Sync runs automatically when membership or bindings change; use **Sync now** / dry-run from the panel when needed.

Options (integration → Configure):

| Option | Default | Notes |
|---|---|---|
| Dry-run | off | Compute rewrites without saving dashboards |
| Normalize duplicates | on | Dedupe + stable-sort user IDs |
| Dashboard allowlist | empty | Comma-separated `url_path` values; empty = all storage dashboards |

YAML-mode dashboards are supported when a writable YAML path can be resolved; otherwise sync reports an error for that dashboard.

## Panel

### Groups

Create/edit groups, members, and icons. Group IDs are auto-generated and read-only after create (shown under Advanced).

### Manage visibility

- Table of bindings with **friendly names** (entity friendly names, mushroom `primary`/`secondary`, section/card headings — not raw `entity_id` / card type alone).
- Element **breadcrumb** under the label (view › section › …).
- **Visual picker:** choose dashboard → rendered preview → click the element. Toolbar sits under **Selected target**. Include groups first; exclude is optional/secondary; locator tech fields under Advanced.
- **Sync now** from this view.

### Conditionals

Lists bindings and points at group membership sensors for templates / automations.

### Visibility Audit + Convert

Pick a dashboard (including **Overview**, loaded from `.storage/lovelace.lovelace` on modern HA when Overview is taken control). Scans people-visibility gates — including nested expander / stack / grid / conditional cards — and classifies each row:

| Source | Meaning |
|---|---|
| **Viz Groups** | Matched to a binding managed by this integration |
| **Manual Dashboard Config** | People visibility present without a matching binding |

For Manual Dashboard Config rows, **Convert** creates a Viz Groups binding (preserving `nested_path` for nested cards) and refreshes the audit afterward.

## Visibility sync (fail-closed)

Effective users for a binding:

1. Flatten each group’s members (HA users + nested groups). **Cycles:** skip the cyclic edge; missing nested groups contribute nothing.
2. Intersection of all **include** group effective users (AND). Empty include → empty set (**fail closed**).
3. Subtract union of all **exclude** group effective users (NOT).
4. Dedupe + stable sort.
5. Write `{"condition":"user","users":[...]}` — including `users: []` when empty so the element stays hidden.

Storage members are typed: `{"type":"user"|"group","id":"..."}` (legacy `member_user_ids` still loads).

### Conditionals & OR trees

- Sync **rewrites existing** managed `condition: user` leaves inside `visibility` or conditional `conditions` trees (including nested `or` / `and`).
- Non-user siblings (e.g. `state` conditions) are kept.
- Sync does **not invent** new people-visibility on elements that have none.
- For `type: conditional` cards, people gates live in `conditions`; sync updates those leaves and does not invent a sibling `visibility` block.

Lab / example Lovelace url_path key: `vizgroups-lab` (hyphenated; domain remains `vizgroups`).

## Sensors

Each group exposes `sensor.vizgroups_<group_id>`:

| Field | Meaning |
|---|---|
| **state** | Member count |
| **attributes.members** | List of HA user IDs |
| **attributes.member_names** | Parallel friendly names |
| **attributes.group_id** | Group id |
| **attributes.description** / **icon** | Group metadata |

```yaml
conditions:
  - condition: template
    value_template: >-
      {{ trigger.to_state.context.user_id
         in state_attr('sensor.vizgroups_teachers', 'members') }}
```

Non-membership:

```yaml
{{ trigger.to_state.context.user_id
   not in state_attr('sensor.vizgroups_teachers', 'members') }}
```

## Services

Domain prefix: `vizgroups.`

- `create_group` / `update_group` / `delete_group`
- `set_members` / `add_members` / `remove_members`
- `bind_element` / `unbind_element`
- `sync` (optional `dashboard`, `dry_run`)
- `is_member` (response service)
- `debug_dashboard` (response service; preview/tree diagnostics)

Websocket commands used by the panel follow the same domain (`vizgroups/subscribe`, `vizgroups/save_group`, `vizgroups/visibility_audit`, …).

## Development

```bash
python -m pytest tests/
node --check custom_components/vizgroups/frontend/panel.js
```

Pure sync / locator / membership logic is unit-tested without a live Home Assistant instance.

## License

MIT
