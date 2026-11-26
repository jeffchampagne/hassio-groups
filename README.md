# Viz Groups

**Viz Groups** helps you show or hide Home Assistant dashboard pieces based on who is signed in.

You put people into **groups**. Then you say which groups can see a card, section, or other Lovelace element (a piece of the dashboard UI). When someone opens the dashboard, Home Assistant only shows the pieces meant for them.

> **Important:** This is a display helper, not a security lock. Hiding something on the dashboard does not stop someone from calling services another way (for example through the API).

Open the **Viz Groups** item in the Home Assistant sidebar (admins only). The panel lives at `/vizgroups`.

---

## What you can do

- Create **groups** with friendly names and optional icons
- Add **members**: Home Assistant users and other groups (nested groups)
- **Manage visibility** for dashboard elements with a visual picker
- Require membership in **all** chosen include groups (AND), and optionally hide for exclude groups (NOT)
- **Audit** dashboards for existing people-visibility rules and **Convert** manual ones into Viz Groups
- Use group membership in **automations and templates** (advanced)

Your group settings are stored in Home Assistant’s `.storage` (covered by the built-in HA Backup).

---

## Quick start

### Install with HACS

1. Open **HACS** → **Integrations**.
2. Open the menu (⋮) → **Custom repositories**.
3. Add `https://github.com/jeffchampagne/hassio-vizgroups` as category **Integration**.
4. Install **Viz Groups**.
5. **Restart** Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration** → **Viz Groups**.

### Manual install

1. Copy the `custom_components/vizgroups` folder into your Home Assistant `custom_components/` folder.
2. Restart Home Assistant.
3. Add the **Viz Groups** integration (same as step 6 above).

### First setup

1. Add the integration (only one instance).
2. Open **Viz Groups** in the sidebar.
3. Create a group and add members.
4. Open **Manage visibility**, pick a dashboard element, and choose which groups can see it.

Sync runs automatically when membership or visibility rules change. You can also press **Sync now** on the Manage visibility tab anytime.

---

## Everyday use

### Groups

On the **Groups** tab:

1. Click **New group**.
2. Enter a **friendly name** (this is what you see day to day).
3. Optionally set a description and icon. The icon browser uses Home Assistant’s icon set (search by name or keyword).
4. Click **Save**.

**Group ID** (the technical id used behind the scenes) is created for you. After you create a group it is read-only. You can view it under **Advanced**. You usually do not need to touch it.

The groups table is sortable by **Name**.

### Members

Open a group to manage members.

- Add **Home Assistant users** by clicking them in the picker.
- Add **other groups** as nested members the same way. Nested groups show as chips on the groups list. In the editor they use a distinct style, and you can expand them to see who is inside.
- For an existing group, adding or removing members **saves right away**. Name, description, and icon still use **Save**.
- Friendly names are shown first. User IDs appear as a subtitle on detail screens.

**Nested groups and safety**

- Nesting is cycle-safe: if groups point at each other in a loop, Viz Groups skips the looping link instead of getting stuck.
- An **empty group** (no effective users) **fails closed**: anything that includes only that group is hidden for everyone.

### Manage visibility

Use this tab to control who sees dashboard elements.

1. Click **Set visibility**.
2. Open the **visual picker**.
3. Choose a **dashboard**.
4. Look at the **preview**, then **click** the view, section, or card you want.
5. Under **Who can see this?**, pick one or more **include** groups.
6. Optionally open **Exclude groups** to hide the element from those groups.
7. Click **Save visibility** (or **Save & sync** when editing).

**Sync now** is on this tab. Auto sync is always on (there is no toggle).

The managed-elements table is sortable by **Element**, **Dashboard**, and **Status**.

### How include and exclude work

- **Include** (required): the signed-in user must be in **every** include group you selected (AND).
- **Exclude** (optional): the user must **not** be in any exclude group (NOT).

Example: include `Teachers` and `Staff`, exclude `Guests` → only people in both Teachers and Staff, and not in Guests, see the element.

If the include set ends up with no users (for example an empty group), the element stays hidden for everyone.

### Visibility audit and Convert

On the same **Manage visibility** page, open **Visibility audit**:

1. Pick a dashboard.
2. Click **Run audit**.
3. Review elements that already have people-visibility rules.

| Source | Meaning |
|---|---|
| **Viz Groups** | Managed by this integration |
| **Manual Dashboard Config** | Set directly on the dashboard, not yet managed here |

For manual rows, click **Convert**. That opens Set visibility with the element already selected so you can attach groups and let Viz Groups manage it going forward.

The audit table is sortable by **Element** and **Source**.

### Conditionals (optional)

The **Conditionals** tab lists each group’s membership sensor (for example `sensor.vizgroups_<group_id>`). You can use those sensors in automations and templates to check membership or non-membership. Create a group first to see the sample template.

---

## Tips and safety

- Visibility only affects what the dashboard shows. It is **not** a full access-control system.
- Prefer friendly names. Leave **Advanced** alone unless you need technical details.
- Empty groups hide content for everyone (fail closed). Add members before relying on a group.
- Nested groups are fine; circular nesting is skipped safely.
- After you change members or visibility rules, auto sync updates the dashboards. Use **Sync now** if something looks out of date.
- Click table headers to sort (Groups by name; Manage visibility and audit columns as described above).

---

## Optional advanced

### Integration options

Open the Viz Groups integration → **Configure**:

| Option | Default | Notes |
|---|---|---|
| Dry-run | off | Compute dashboard rewrites without saving them |
| Normalize duplicates | on | Deduplicate and stably sort user IDs |
| Dashboard allowlist | empty | Comma-separated dashboard paths; empty means all storage dashboards |

YAML-mode dashboards work when Viz Groups can find a writable YAML path. Otherwise sync reports an error for that dashboard.

### How sync writes visibility

Sync updates the people/user visibility rules that Viz Groups manages. It:

1. Flattens each group (users + nested groups), skipping cycles.
2. Takes the intersection of all include groups (AND).
3. Removes everyone in any exclude group (NOT).
4. Writes a `condition: user` rule with that user list — including an empty list when nobody should see it.

It does not invent people-visibility on elements that never had it. Non-user conditions (for example state conditions) are kept.

### Sensors

Each group has `sensor.vizgroups_<group_id>`:

| Field | Meaning |
|---|---|
| **state** | Effective member count |
| **attributes.members** | Home Assistant user IDs |
| **attributes.member_names** | Matching friendly names |
| **attributes.group_id** | Group ID |
| **attributes.description** / **icon** | Group metadata |

Example template condition:

```yaml
conditions:
  - condition: template
    value_template: >-
      {{ trigger.to_state.context.user_id
         in state_attr('sensor.vizgroups_teachers', 'members') }}
```

### Services

Service domain: `vizgroups.`

- Groups: `create_group`, `update_group`, `delete_group`
- Members: `set_members`, `add_members`, `remove_members`
- Visibility: `bind_element`, `unbind_element`, `sync`
- Helpers: `is_member`, `debug_dashboard`

### Development

```bash
python -m pytest tests/
node --check custom_components/vizgroups/frontend/panel.js
```

---

## License

MIT
