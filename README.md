# Viz Groups

**Viz Groups** is a Home Assistant custom integration for first-class **user groups**: manage membership in an admin panel, bind any visibility-capable Lovelace element to include/exclude groups, and expose membership for automations and templates.

- **Domain:** `vizgroups`
- **Panel:** sidebar **Viz Groups** at `/vizgroups` (Lit web component `vizgroups-panel`, admin-only)
- **Storage:** Home Assistant `.storage/vizgroups` (covered by built-in HA Backup)
- **Sensors:** `sensor.vizgroups_<group_id>` per group
- **Visibility model:** rewrite managed `condition: user` leaves only; empty membership **fail-closes** with `users: []`
- **Multi-group:** **AND** include ∩ **NOT** exclude
- **Important:** Visibility is **UX, not an ACL**. Hiding a card does not block service calls via the API.

## Install (HACS custom repository)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Add `https://github.com/jeffchampagne/hassio-groups` as category **Integration**
   (intended final repo name: `jeffchampagne/vizgroups` once GitHub rename is available)
3. Install **Viz Groups**, then **restart** Home Assistant
4. Settings → Devices & Services → **Add Integration** → **Viz Groups**

### Manual install

Copy `custom_components/vizgroups` into your HA `custom_components/` folder, restart, then add the integration.

## Setup

1. Add the **Viz Groups** integration (single instance).
2. Open the **Viz Groups** sidebar panel (admins only).
3. Create groups and assign members (friendly names primary; user IDs shown as subtitles on detail rows).
4. Create visibility bindings (dashboard + locator + include/exclude groups) from **Conditionals**, or use the visual locator.
5. Sync runs automatically when membership or bindings change; use **Sync now** / dry-run from the panel when needed.

Options (integration → Configure):

| Option | Default | Notes |
|---|---|---|
| Dry-run | off | Compute rewrites without saving dashboards |
| Normalize duplicates | on | Dedupe + stable-sort user IDs |
| Dashboard allowlist | empty | Comma-separated `url_path` values; empty = all storage dashboards |

YAML-mode dashboards are supported when a writable YAML path can be resolved; otherwise sync reports an error for that dashboard.

## Visibility sync (fail-closed)

Effective users for a binding:

1. Intersection of all **include** group members (AND). Empty include → empty set (**fail closed**).
2. Subtract union of all **exclude** group members (NOT).
3. Dedupe + stable sort.
4. Write `{"condition":"user","users":[...]}` — including `users: []` when empty so the element stays hidden.

Mixed trees (e.g. `or` of `state` + `user`) keep non-user siblings; only the managed `condition: user` leaf is updated.

Lab / example Lovelace url_path key: `vizgroups-lab` (hyphenated; domain remains `vizgroups`).

## Conditionals & sensors

The **Conditionals** panel view lists bindings and group membership sensors for template use.

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

## Visibility Audit

The panel’s **Visibility Audit** scans a dashboard for elements that already have `condition: user` visibility and classifies each row as:

- **Viz Groups** — matched to a binding managed by this integration
- **manual dashboard config** — people visibility present without a matching binding

Use it to find orphaned manual visibility, confirm sync coverage, and copy granted user IDs into the group editor.

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
```

Pure sync / locator / membership logic is unit-tested without a live Home Assistant instance. Panel JS can be syntax-checked with `node --check custom_components/vizgroups/frontend/panel.js`.

## License

MIT
