/**
 * HA Groups admin panel (Lit).
 * Friendly names primary; user IDs as subtitle on detail rows only.
 * Visibility is UX, not ACL.
 *
 * UX: edit existing bindings + re-sync; auto-slug group IDs; MDI icon picker.
 */
import {
  LitElement,
  html,
  css,
  nothing,
} from "https://unpkg.com/lit@3.2.1/index.js?module";

const DOMAIN = "hassio_groups";

/** Curated MDI set for groups / people / home — type-to-filter; free-text still allowed. */
const MDI_ICON_CHOICES = [
  "mdi:account",
  "mdi:account-circle",
  "mdi:account-group",
  "mdi:account-multiple",
  "mdi:account-school",
  "mdi:account-tie",
  "mdi:account-hard-hat",
  "mdi:account-cog",
  "mdi:account-key",
  "mdi:account-lock",
  "mdi:account-star",
  "mdi:account-supervisor",
  "mdi:badge-account",
  "mdi:briefcase-account",
  "mdi:card-account-details",
  "mdi:human-male-female",
  "mdi:account-child",
  "mdi:baby-face",
  "mdi:face-man",
  "mdi:face-woman",
  "mdi:home",
  "mdi:home-account",
  "mdi:home-group",
  "mdi:home-variant",
  "mdi:office-building",
  "mdi:school",
  "mdi:teacher",
  "mdi:bookshelf",
  "mdi:hammer-wrench",
  "mdi:toolbox",
  "mdi:wrench",
  "mdi:shield-account",
  "mdi:shield-check",
  "mdi:shield-lock",
  "mdi:lock",
  "mdi:key",
  "mdi:key-variant",
  "mdi:eye",
  "mdi:eye-off",
  "mdi:eye-check",
  "mdi:view-dashboard",
  "mdi:view-grid",
  "mdi:monitor-dashboard",
  "mdi:tablet-dashboard",
  "mdi:door",
  "mdi:door-open",
  "mdi:gate",
  "mdi:lightbulb",
  "mdi:lightbulb-group",
  "mdi:lamps",
  "mdi:ceiling-light",
  "mdi:sofa",
  "mdi:bed",
  "mdi:bathtub",
  "mdi:stove",
  "mdi:fridge",
  "mdi:television",
  "mdi:music",
  "mdi:camera",
  "mdi:video",
  "mdi:bell",
  "mdi:bell-ring",
  "mdi:calendar",
  "mdi:clock",
  "mdi:clock-outline",
  "mdi:weather-night",
  "mdi:weather-sunny",
  "mdi:moon-waning-crescent",
  "mdi:star",
  "mdi:heart",
  "mdi:handshake",
  "mdi:account-plus",
  "mdi:account-minus",
  "mdi:account-remove",
  "mdi:account-check",
  "mdi:account-cancel",
  "mdi:crowd",
  "mdi:family",
  "mdi:human-greeting",
  "mdi:map-marker",
  "mdi:domain",
  "mdi:store",
  "mdi:car",
  "mdi:bike",
  "mdi:run",
  "mdi:walk",
  "mdi:coffee",
  "mdi:food",
  "mdi:party-popper",
  "mdi:gift",
  "mdi:tag",
  "mdi:tag-multiple",
  "mdi:folder-account",
  "mdi:clipboard-account",
  "mdi:file-account",
  "mdi:cog",
  "mdi:cog-outline",
  "mdi:information",
  "mdi:help-circle",
  "mdi:alert",
  "mdi:check-circle",
  "mdi:close-circle",
];

class HaGroupsPanel extends LitElement {
  static properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    _view: { state: true },
    _data: { state: true },
    _error: { state: true },
    _selectedGroupId: { state: true },
    _draft: { state: true },
    _bindingDraft: { state: true },
    _busy: { state: true },
    _groupIdManual: { state: true },
    _iconFilter: { state: true },
    _iconPickerOpen: { state: true },
  };

  static styles = css`
    :host {
      --ink: #0e1412;
      --ink-soft: #2a3530;
      --muted: #5c6b63;
      --line: rgba(14, 20, 18, 0.12);
      --panel: rgba(255, 255, 255, 0.72);
      --accent: #1f6b4f;
      --accent-deep: #0f3d2e;
      --accent-glow: rgba(31, 107, 79, 0.18);
      --warn: #9a5b12;
      --danger: #8b2e2e;
      --font-ui: "DM Sans", "Segoe UI", sans-serif;
      --font-display: "Instrument Serif", Georgia, "Times New Roman", serif;
      display: block;
      font-family: var(--font-ui);
      color: var(--ink);
      background:
        radial-gradient(1200px 700px at 12% -10%, rgba(31, 107, 79, 0.22), transparent 55%),
        radial-gradient(900px 600px at 90% 0%, rgba(46, 90, 120, 0.16), transparent 50%),
        linear-gradient(165deg, #d7e4dc 0%, #eef3ef 42%, #dce6e0 100%);
      min-height: 100vh;
      box-sizing: border-box;
    }
    * { box-sizing: border-box; }
    .shell {
      display: grid;
      grid-template-columns: 220px 1fr;
      min-height: 100vh;
      max-width: 1280px;
      margin: 0 auto;
    }
    @media (max-width: 900px) {
      .shell { grid-template-columns: 1fr; }
      nav.side { border-right: 0; border-bottom: 1px solid var(--line); }
      .layout-2 { grid-template-columns: 1fr !important; }
    }
    nav.side {
      padding: 28px 18px;
      border-right: 1px solid var(--line);
      background: rgba(255,255,255,0.28);
      backdrop-filter: blur(10px);
    }
    .brand {
      font-family: var(--font-display);
      font-size: 1.65rem;
      line-height: 1.1;
      color: var(--accent-deep);
      margin: 0 0 4px;
    }
    .brand-sub {
      font-size: 0.75rem;
      color: var(--muted);
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 28px;
    }
    .nav-btn {
      display: block; width: 100%; text-align: left; border: 0;
      background: transparent; font: inherit; color: var(--ink-soft);
      padding: 10px 12px; border-radius: 10px; cursor: pointer; margin-bottom: 4px;
    }
    .nav-btn:hover { background: rgba(31,107,79,0.08); }
    .nav-btn.active { background: var(--accent); color: #f4faf6; }
    main { padding: 28px 32px 48px; }
    .hero h1 {
      font-family: var(--font-display); font-weight: 400;
      font-size: clamp(2rem, 3.2vw, 2.75rem); margin: 0 0 8px; color: var(--accent-deep);
    }
    .hero p { margin: 0; max-width: 46ch; color: var(--muted); line-height: 1.45; }
    .toolbar { display: flex; gap: 10px; align-items: center; margin: 18px 0; flex-wrap: wrap; }
    .spacer { flex: 1; }
    .btn {
      font: inherit; border: 1px solid transparent; border-radius: 999px;
      padding: 9px 16px; cursor: pointer;
    }
    .btn-primary { background: var(--accent); color: #f5faf7; }
    .btn-ghost { background: transparent; border-color: var(--line); color: var(--ink-soft); }
    .btn-danger { background: transparent; border-color: rgba(139,46,46,0.35); color: var(--danger); }
    .btn-sm { padding: 6px 12px; font-size: 0.85rem; }
    .btn:disabled { opacity: 0.55; cursor: not-allowed; }
    .panel {
      background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
      backdrop-filter: blur(12px); overflow: hidden;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
    th {
      text-align: left; font-size: 0.72rem; letter-spacing: 0.07em; text-transform: uppercase;
      color: var(--muted); padding: 14px 16px; border-bottom: 1px solid var(--line);
    }
    td { padding: 14px 16px; border-bottom: 1px solid var(--line); vertical-align: middle; }
    tr:last-child td { border-bottom: 0; }
    tr.row-click { cursor: pointer; }
    tr.row-click:hover { background: rgba(31,107,79,0.06); }
    .pill {
      display: inline-flex; align-items: center; gap: 6px; font-size: 0.78rem;
      padding: 4px 10px; border-radius: 999px; background: rgba(31,107,79,0.1);
      color: var(--accent-deep); font-weight: 500;
    }
    .pill.warn { background: rgba(154,91,18,0.12); color: var(--warn); }
    .layout-2 { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 18px; }
    .section-title {
      font-family: var(--font-display); font-size: 1.35rem; margin: 0 0 12px; color: var(--accent-deep);
    }
    .field { margin-bottom: 14px; }
    .field label {
      display: block; font-size: 0.75rem; letter-spacing: 0.06em; text-transform: uppercase;
      color: var(--muted); margin-bottom: 6px;
    }
    .field .hint {
      display: block; margin-top: 6px; font-size: 0.78rem; color: var(--muted);
      text-transform: none; letter-spacing: 0;
    }
    .field input, .field textarea, .field select {
      width: 100%; font: inherit; padding: 10px 12px; border-radius: 10px;
      border: 1px solid var(--line); background: rgba(255,255,255,0.85); color: var(--ink);
    }
    .field input:focus, .field textarea:focus, .field select:focus {
      outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow);
    }
    .field input:disabled { opacity: 0.7; background: rgba(0,0,0,0.04); }
    .member-list { list-style: none; margin: 0; padding: 0; }
    .member-list li {
      display: flex; align-items: center; gap: 12px; padding: 10px 12px;
      border-bottom: 1px solid var(--line);
    }
    .member-list li:last-child { border-bottom: 0; }
    .avatar {
      width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center;
      font-size: 0.8rem; font-weight: 600; color: var(--accent-deep);
      background: rgba(31,107,79,0.14); flex-shrink: 0;
    }
    .member-meta { flex: 1; min-width: 0; }
    .member-meta strong { display: block; font-weight: 600; }
    .member-meta span { font-size: 0.8rem; color: var(--muted); word-break: break-all; }
    .user-picker { display: grid; gap: 8px; max-height: 280px; overflow: auto; padding: 8px; }
    .user-option {
      display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px;
      border: 1px solid var(--line); background: rgba(255,255,255,0.55); cursor: pointer;
    }
    .user-option.selected, .user-option:hover {
      border-color: rgba(31,107,79,0.45); background: rgba(31,107,79,0.08);
    }
    .callout {
      border-left: 3px solid var(--accent); padding: 12px 14px; background: rgba(31,107,79,0.08);
      border-radius: 0 10px 10px 0; color: var(--ink-soft); font-size: 0.92rem; margin-top: 14px;
    }
    .callout.warn { border-left-color: var(--warn); background: rgba(154,91,18,0.1); }
    .error {
      margin: 12px 0; padding: 10px 12px; border-radius: 10px;
      background: rgba(139,46,46,0.1); color: var(--danger);
    }
    .yaml-block {
      background: #122019; color: #d5ebe0; border-radius: 14px; padding: 18px 20px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem;
      line-height: 1.55; overflow-x: auto; white-space: pre;
    }
    .stat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 18px 0; }
    .stat {
      padding: 16px 18px; border-radius: 14px; border: 1px solid var(--line);
      background: rgba(255,255,255,0.55);
    }
    .stat .n { font-family: var(--font-display); font-size: 2rem; color: var(--accent-deep); }
    .stat .l { font-size: 0.78rem; color: var(--muted); margin-top: 6px; text-transform: uppercase; }
    .chip-row { display: flex; flex-wrap: wrap; gap: 6px; }
    .footer-note { margin-top: 28px; font-size: 0.8rem; color: var(--muted); }
    .row-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .icon-field { display: flex; gap: 10px; align-items: stretch; }
    .icon-preview {
      width: 46px; flex-shrink: 0; border-radius: 10px; border: 1px solid var(--line);
      background: rgba(255,255,255,0.85); display: grid; place-items: center;
      color: var(--accent-deep);
    }
    .icon-preview ha-icon, .icon-preview .icon-fallback { --mdc-icon-size: 24px; font-size: 1.25rem; }
    .icon-picker {
      margin-top: 10px; border: 1px solid var(--line); border-radius: 12px;
      background: rgba(255,255,255,0.7); overflow: hidden;
    }
    .icon-picker-toolbar { padding: 10px; border-bottom: 1px solid var(--line); }
    .icon-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
      gap: 6px; max-height: 220px; overflow: auto; padding: 10px;
    }
    .icon-cell {
      display: flex; flex-direction: column; align-items: center; gap: 4px;
      padding: 8px 4px; border-radius: 10px; border: 1px solid transparent;
      background: transparent; cursor: pointer; font: inherit; color: var(--ink-soft);
    }
    .icon-cell:hover, .icon-cell.selected {
      border-color: rgba(31,107,79,0.45); background: rgba(31,107,79,0.08);
      color: var(--accent-deep);
    }
    .icon-cell ha-icon, .icon-cell .icon-fallback { --mdc-icon-size: 22px; font-size: 1.15rem; }
    .icon-cell span {
      font-size: 0.62rem; line-height: 1.2; text-align: center; word-break: break-all;
      color: var(--muted); max-width: 100%;
    }
    .icon-empty { padding: 16px; color: var(--muted); font-size: 0.85rem; text-align: center; }
  `;

  constructor() {
    super();
    this._view = "groups";
    this._data = null;
    this._error = "";
    this._selectedGroupId = null;
    this._draft = null;
    this._bindingDraft = null;
    this._busy = false;
    this._unsub = null;
    this._groupIdManual = false;
    this._iconFilter = "";
    this._iconPickerOpen = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this._ensureSub();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._dropSub();
  }

  updated(changed) {
    if (changed.has("hass")) this._ensureSub();
  }

  _ensureSub() {
    if (!this.hass || this._unsub) return;
    this._unsub = this.hass.connection.subscribeMessage(
      (ev) => {
        if (ev && ev.event === "snapshot") {
          this._data = ev;
          this._error = "";
        }
      },
      { type: `${DOMAIN}/subscribe` }
    );
  }

  _dropSub() {
    const pending = this._unsub;
    this._unsub = null;
    if (pending) Promise.resolve(pending).then((u) => u && u());
  }

  async _call(type, payload = {}) {
    this._busy = true;
    this._error = "";
    try {
      const result = await this.hass.connection.sendMessagePromise({
        type: `${DOMAIN}/${type}`,
        ...payload,
      });
      if (result && (result.groups || result.users)) this._data = result;
      return result;
    } catch (err) {
      this._error = err?.message || String(err);
      throw err;
    } finally {
      this._busy = false;
    }
  }

  get _groups() {
    return this._data?.groups || [];
  }

  get _users() {
    return this._data?.users || [];
  }

  get _bindings() {
    return this._data?.bindings || [];
  }

  get _selectedGroup() {
    return this._groups.find((g) => g.id === this._selectedGroupId) || null;
  }

  _initials(name) {
    const parts = String(name || "?").trim().split(/\s+/).slice(0, 2);
    return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
  }

  /** Match backend models._slugify */
  _slugify(value) {
    const out = [];
    let prevDash = false;
    for (const ch of String(value || "").trim().toLowerCase()) {
      if (/[a-z0-9]/.test(ch)) {
        out.push(ch);
        prevDash = false;
      } else if (!prevDash) {
        out.push("-");
        prevDash = true;
      }
    }
    return out.join("").replace(/^-+|-+$/g, "");
  }

  _normalizeIcon(value) {
    const raw = String(value || "").trim();
    if (!raw) return "mdi:account-group";
    if (raw.startsWith("mdi:")) return raw;
    return `mdi:${raw.replace(/^mdi:/, "")}`;
  }

  _renderHaIcon(icon) {
    const name = this._normalizeIcon(icon);
    // ha-icon is provided by HA frontend when the panel is embedded.
    return html`<ha-icon .icon=${name}></ha-icon>`;
  }

  _filteredIcons() {
    const q = String(this._iconFilter || "").trim().toLowerCase().replace(/^mdi:/, "");
    const current = this._normalizeIcon(this._draft?.icon);
    const base = MDI_ICON_CHOICES.includes(current)
      ? MDI_ICON_CHOICES
      : [current, ...MDI_ICON_CHOICES];
    if (!q) return base;
    return base.filter((icon) => icon.toLowerCase().includes(q));
  }

  _onNameInput(e) {
    const name = e.target.value;
    const patch = { ...this._draft, name };
    if (!this._selectedGroupId && !this._groupIdManual) {
      patch.group_id = this._slugify(name);
    }
    this._draft = patch;
  }

  _onGroupIdInput(e) {
    this._groupIdManual = true;
    this._draft = { ...this._draft, group_id: e.target.value };
  }

  _openCreateGroup() {
    this._selectedGroupId = null;
    this._groupIdManual = false;
    this._iconFilter = "";
    this._iconPickerOpen = false;
    this._draft = {
      name: "",
      group_id: "",
      description: "",
      icon: "mdi:account-group",
      member_user_ids: [],
    };
    this._view = "editor";
  }

  _openEditGroup(group) {
    this._selectedGroupId = group.id;
    this._groupIdManual = true;
    this._iconFilter = "";
    this._iconPickerOpen = false;
    this._draft = {
      name: group.name,
      group_id: group.id,
      description: group.description || "",
      icon: group.icon || "mdi:account-group",
      member_user_ids: [...(group.member_user_ids || [])],
    };
    this._view = "editor";
  }

  _toggleMember(userId) {
    if (!this._draft) return;
    const set = new Set(this._draft.member_user_ids || []);
    if (set.has(userId)) set.delete(userId);
    else set.add(userId);
    this._draft = { ...this._draft, member_user_ids: [...set] };
  }

  _pickIcon(icon) {
    this._draft = { ...this._draft, icon: this._normalizeIcon(icon) };
    this._iconFilter = "";
  }

  async _saveGroup() {
    if (!this._draft?.name?.trim()) {
      this._error = "Group name is required";
      return;
    }
    const groupId =
      this._selectedGroupId ||
      this._draft.group_id?.trim() ||
      this._slugify(this._draft.name) ||
      undefined;
    await this._call("save_group", {
      name: this._draft.name.trim(),
      group_id: groupId,
      description: this._draft.description || "",
      icon: this._normalizeIcon(this._draft.icon),
      member_user_ids: this._draft.member_user_ids || [],
    });
    this._view = "groups";
    this._draft = null;
    this._iconPickerOpen = false;
  }

  async _deleteGroup() {
    if (!this._draft?.group_id) return;
    if (!confirm(`Delete group “${this._draft.name}”?`)) return;
    await this._call("delete_group", { group_id: this._draft.group_id });
    this._view = "groups";
    this._draft = null;
  }

  _openBindingCreate() {
    this._bindingDraft = {
      binding_id: "",
      dashboard_url_path: "lovelace",
      include: [],
      exclude: [],
      label: "",
      locator: { kind: "card", view_index: 0, section_index: 0, card_index: 0 },
      merge_mode: "ensure_user_branch",
      fingerprint: "",
    };
    this._view = "bindings";
  }

  _openEditBinding(binding) {
    const loc = binding.locator || {};
    this._bindingDraft = {
      binding_id: binding.id,
      dashboard_url_path: binding.dashboard_url_path || "lovelace",
      include: [...(binding.expression?.include || [])],
      exclude: [...(binding.expression?.exclude || [])],
      label: binding.label || "",
      locator: {
        kind: loc.kind || "card",
        view_path: loc.view_path ?? "",
        view_index: loc.view_index ?? 0,
        section_index: loc.section_index ?? 0,
        card_index: loc.card_index ?? 0,
      },
      merge_mode: binding.merge_mode || "ensure_user_branch",
      fingerprint: binding.fingerprint || "",
    };
    this._view = "bindings";
    this._error = "";
  }

  async _saveBinding() {
    const d = this._bindingDraft;
    if (!d?.include?.length) {
      this._error = "At least one include group is required";
      return;
    }
    const locator = {
      kind: d.locator?.kind || "card",
      view_index: Number(d.locator?.view_index ?? 0),
      section_index: Number(d.locator?.section_index ?? 0),
      card_index: Number(d.locator?.card_index ?? 0),
    };
    if (d.locator?.view_path) locator.view_path = d.locator.view_path;
    await this._call("save_binding", {
      binding_id: d.binding_id || undefined,
      dashboard_url_path: d.dashboard_url_path,
      include: d.include,
      exclude: d.exclude || [],
      locator,
      merge_mode: d.merge_mode || "ensure_user_branch",
      fingerprint: d.fingerprint || "",
      label: d.label || "",
    });
    this._bindingDraft = null;
    // Re-sync so Lovelace visibility reflects the edit immediately.
    await this._sync(false);
  }

  async _deleteBinding(id) {
    if (!confirm("Remove this binding?")) return;
    await this._call("delete_binding", { binding_id: id });
    if (this._bindingDraft?.binding_id === id) this._bindingDraft = null;
  }

  async _sync(dryRun = false) {
    await this._call("sync", { dry_run: dryRun });
  }

  _automationYaml(group) {
    const entity = `sensor.hassio_groups_${group.id}`;
    return `conditions:
  - condition: template
    value_template: >-
      {{ trigger.to_state.context.user_id
         in state_attr('${entity}', 'members') }}`;
  }

  render() {
    return html`
      <div class="shell">
        <nav class="side">
          <div class="brand">HA Groups</div>
          <div class="brand-sub">Home Assistant</div>
          <button class="nav-btn ${this._view === "groups" || this._view === "editor" ? "active" : ""}"
            @click=${() => { this._view = "groups"; this._draft = null; this._iconPickerOpen = false; }}>Groups</button>
          <button class="nav-btn ${this._view === "bindings" ? "active" : ""}"
            @click=${() => { this._view = "bindings"; }}>Bindings</button>
          <button class="nav-btn ${this._view === "automations" ? "active" : ""}"
            @click=${() => { this._view = "automations"; }}>Automations</button>
        </nav>
        <main>
          ${this._error ? html`<div class="error">${this._error}</div>` : nothing}
          ${this._view === "groups" ? this._renderGroups() : nothing}
          ${this._view === "editor" ? this._renderEditor() : nothing}
          ${this._view === "bindings" ? this._renderBindings() : nothing}
          ${this._view === "automations" ? this._renderAutomations() : nothing}
          <p class="footer-note">
            Visibility hides UI only — it is not an access-control list. Empty groups fail closed with <code>users: []</code>.
            Config lives in Home Assistant <code>.storage</code> (covered by HA Backup).
          </p>
        </main>
      </div>
    `;
  }

  _renderGroups() {
    const groups = this._groups;
    return html`
      <div class="hero">
        <h1>Groups</h1>
        <p>Create user groups, then bind them to any Lovelace element that supports visibility.</p>
      </div>
      <div class="stat-row">
        <div class="stat"><div class="n">${groups.length}</div><div class="l">Groups</div></div>
        <div class="stat"><div class="n">${this._bindings.length}</div><div class="l">Bindings</div></div>
        <div class="stat"><div class="n">${this._users.length}</div><div class="l">Users</div></div>
      </div>
      <div class="toolbar">
        <button class="btn btn-primary" ?disabled=${this._busy} @click=${this._openCreateGroup}>New group</button>
        <span class="spacer"></span>
        <button class="btn btn-ghost" ?disabled=${this._busy} @click=${() => this._sync(true)}>Dry-run sync</button>
        <button class="btn btn-ghost" ?disabled=${this._busy} @click=${() => this._sync(false)}>Sync now</button>
      </div>
      <div class="panel">
        <table>
          <thead><tr><th>Name</th><th>Members</th><th>Id</th></tr></thead>
          <tbody>
            ${groups.length === 0
              ? html`<tr><td colspan="3">No groups yet. Create one to get started.</td></tr>`
              : groups.map(
                  (g) => html`
                    <tr class="row-click" @click=${() => this._openEditGroup(g)}>
                      <td>
                        <div style="display:flex;align-items:center;gap:10px">
                          <span class="icon-preview" style="width:34px;height:34px">${this._renderHaIcon(g.icon || "mdi:account-group")}</span>
                          <div>
                            <strong>${g.name}</strong>
                            ${g.description ? html`<div style="color:var(--muted);font-size:0.85rem">${g.description}</div>` : nothing}
                          </div>
                        </div>
                      </td>
                      <td><span class="pill">${g.member_count ?? (g.member_user_ids || []).length}</span></td>
                      <td style="color:var(--muted);font-size:0.85rem">${g.id}</td>
                    </tr>
                  `
                )}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderIconPicker() {
    const d = this._draft;
    if (!d) return nothing;
    const filtered = this._filteredIcons();
    const current = this._normalizeIcon(d.icon);
    return html`
      <div class="field">
        <label>Icon</label>
        <div class="icon-field">
          <div class="icon-preview">${this._renderHaIcon(current)}</div>
          <input
            .value=${current}
            placeholder="mdi:account-group"
            @input=${(e) => {
              this._draft = { ...d, icon: e.target.value };
              this._iconFilter = e.target.value;
              this._iconPickerOpen = true;
            }}
            @focus=${() => { this._iconPickerOpen = true; }}
          />
        </div>
        <button class="btn btn-ghost btn-sm" style="margin-top:8px"
          type="button"
          @click=${() => { this._iconPickerOpen = !this._iconPickerOpen; }}>
          ${this._iconPickerOpen ? "Hide icon list" : "Browse icons"}
        </button>
        ${this._iconPickerOpen
          ? html`<div class="icon-picker">
              <div class="icon-picker-toolbar">
                <input
                  placeholder="Type to filter (e.g. school, shield, home)"
                  .value=${this._iconFilter}
                  @input=${(e) => { this._iconFilter = e.target.value; }}
                />
              </div>
              ${filtered.length === 0
                ? html`<div class="icon-empty">No icons match. Keep typing a full <code>mdi:…</code> name above.</div>`
                : html`<div class="icon-grid">
                    ${filtered.map(
                      (icon) => html`
                        <button
                          type="button"
                          class="icon-cell ${icon === current ? "selected" : ""}"
                          title=${icon}
                          @click=${() => this._pickIcon(icon)}
                        >
                          ${this._renderHaIcon(icon)}
                          <span>${icon.replace(/^mdi:/, "")}</span>
                        </button>
                      `
                    )}
                  </div>`}
            </div>`
          : nothing}
        <span class="hint">Preview uses Home Assistant’s MDI set. Any valid <code>mdi:</code> name works.</span>
      </div>
    `;
  }

  _renderEditor() {
    const d = this._draft;
    if (!d) return nothing;
    const selected = new Set(d.member_user_ids || []);
    const editing = !!this._selectedGroupId;
    const suggested = this._slugify(d.name);
    return html`
      <div class="hero">
        <h1>${editing ? "Edit group" : "New group"}</h1>
        <p>Friendly names are shown first. User IDs appear as subtitles on member rows.</p>
      </div>
      <div class="layout-2">
        <div class="panel" style="padding:18px">
          <h2 class="section-title">Details</h2>
          <div class="field"><label>Name</label>
            <input .value=${d.name} @input=${this._onNameInput} />
          </div>
          <div class="field"><label>Group ID (slug)</label>
            <input
              .value=${d.group_id}
              ?disabled=${editing}
              placeholder=${suggested || "auto-from-name"}
              @input=${this._onGroupIdInput}
            />
            ${editing
              ? html`<span class="hint">ID is fixed after creation.</span>`
              : html`<span class="hint">
                  ${this._groupIdManual
                    ? "Custom ID — clear and rename to resume auto-slug."
                    : suggested
                      ? html`Auto-generated as <code>${suggested}</code> — edit to override.`
                      : "Filled automatically from the name."}
                </span>`}
          </div>
          <div class="field"><label>Description</label>
            <textarea rows="3" .value=${d.description}
              @input=${(e) => (this._draft = { ...d, description: e.target.value })}></textarea>
          </div>
          ${this._renderIconPicker()}
          <div class="toolbar">
            <button class="btn btn-primary" ?disabled=${this._busy} @click=${this._saveGroup}>Save</button>
            <button class="btn btn-ghost" @click=${() => { this._view = "groups"; this._draft = null; this._iconPickerOpen = false; }}>Cancel</button>
            ${editing
              ? html`<span class="spacer"></span>
                  <button class="btn btn-danger" ?disabled=${this._busy} @click=${this._deleteGroup}>Delete</button>`
              : nothing}
          </div>
        </div>
        <div class="panel">
          <div style="padding:18px 18px 8px"><h2 class="section-title">Members</h2></div>
          <div class="user-picker">
            ${this._users.map((u) => {
              const on = selected.has(u.id);
              return html`
                <label class="user-option ${on ? "selected" : ""}">
                  <input type="checkbox" .checked=${on} @change=${() => this._toggleMember(u.id)} />
                  <div class="avatar">${this._initials(u.name)}</div>
                  <div class="member-meta">
                    <strong>${u.name}</strong>
                    <span>${u.id}</span>
                  </div>
                </label>
              `;
            })}
          </div>
          <div style="padding:8px 18px 18px">
            <h3 class="section-title" style="font-size:1.1rem">Selected</h3>
            <ul class="member-list">
              ${(d.member_user_ids || []).map((id) => {
                const u = this._users.find((x) => x.id === id);
                return html`<li>
                  <div class="avatar">${this._initials(u?.name || id)}</div>
                  <div class="member-meta">
                    <strong>${u?.name || id}</strong>
                    <span>${id}</span>
                  </div>
                </li>`;
              })}
            </ul>
          </div>
        </div>
      </div>
    `;
  }

  _renderBindingForm() {
    const d = this._bindingDraft;
    if (!d) return nothing;
    const editing = !!d.binding_id;
    return html`<div class="panel" style="padding:18px;margin-bottom:18px">
      <h2 class="section-title">${editing ? "Edit binding" : "New binding"}</h2>
      <div class="layout-2">
        <div>
          ${editing
            ? html`<div class="field"><label>Binding ID</label>
                <input .value=${d.binding_id} disabled />
              </div>`
            : nothing}
          <div class="field"><label>Label</label>
            <input .value=${d.label || ""} @input=${(e) => (this._bindingDraft = { ...d, label: e.target.value })} />
          </div>
          <div class="field"><label>Dashboard url path</label>
            <input .value=${d.dashboard_url_path}
              @input=${(e) => (this._bindingDraft = { ...d, dashboard_url_path: e.target.value })} />
          </div>
          <div class="field"><label>Include groups (AND)</label>
            <select multiple style="min-height:110px"
              @change=${(e) => {
                const vals = [...e.target.selectedOptions].map((o) => o.value);
                this._bindingDraft = { ...d, include: vals };
              }}>
              ${this._groups.map(
                (g) => html`<option value=${g.id} ?selected=${(d.include || []).includes(g.id)}>${g.name}</option>`
              )}
            </select>
          </div>
          <div class="field"><label>Exclude groups (NOT)</label>
            <select multiple style="min-height:90px"
              @change=${(e) => {
                const vals = [...e.target.selectedOptions].map((o) => o.value);
                this._bindingDraft = { ...d, exclude: vals };
              }}>
              ${this._groups.map(
                (g) => html`<option value=${g.id} ?selected=${(d.exclude || []).includes(g.id)}>${g.name}</option>`
              )}
            </select>
          </div>
        </div>
        <div>
          <div class="field"><label>Locator kind</label>
            <select .value=${d.locator?.kind || "card"}
              @change=${(e) => (this._bindingDraft = { ...d, locator: { ...d.locator, kind: e.target.value } })}>
              <option value="view">view</option>
              <option value="section">section</option>
              <option value="card">card</option>
              <option value="other">other</option>
            </select>
          </div>
          <div class="field"><label>View index</label>
            <input type="number" .value=${d.locator?.view_index ?? 0}
              @input=${(e) => (this._bindingDraft = { ...d, locator: { ...d.locator, view_index: Number(e.target.value) } })} />
          </div>
          <div class="field"><label>Section index</label>
            <input type="number" .value=${d.locator?.section_index ?? 0}
              @input=${(e) => (this._bindingDraft = { ...d, locator: { ...d.locator, section_index: Number(e.target.value) } })} />
          </div>
          <div class="field"><label>Card index</label>
            <input type="number" .value=${d.locator?.card_index ?? 0}
              @input=${(e) => (this._bindingDraft = { ...d, locator: { ...d.locator, card_index: Number(e.target.value) } })} />
          </div>
          <div class="field"><label>Merge mode</label>
            <select .value=${d.merge_mode || "ensure_user_branch"}
              @change=${(e) => (this._bindingDraft = { ...d, merge_mode: e.target.value })}>
              <option value="ensure_user_branch">ensure_user_branch</option>
              <option value="replace_user_condition">replace_user_condition</option>
            </select>
          </div>
          <div class="field"><label>Fingerprint (optional)</label>
            <input .value=${d.fingerprint || ""}
              @input=${(e) => (this._bindingDraft = { ...d, fingerprint: e.target.value })} />
          </div>
          <div class="toolbar">
            <button class="btn btn-primary" ?disabled=${this._busy} @click=${this._saveBinding}>
              ${editing ? "Save & sync" : "Save binding"}
            </button>
            <button class="btn btn-ghost" @click=${() => (this._bindingDraft = null)}>Cancel</button>
          </div>
        </div>
      </div>
      <div class="callout warn">Dashboard browser / live node picker is stubbed for the next phase — enter locator indices manually for now. Saving an edit re-syncs Lovelace.</div>
    </div>`;
  }

  _renderBindings() {
    return html`
      <div class="hero">
        <h1>Visibility bindings</h1>
        <p>AND include groups, NOT exclude groups. Empty effective membership writes <code>users: []</code> (fail closed).</p>
      </div>
      <div class="toolbar">
        <button class="btn btn-primary" @click=${this._openBindingCreate}>New binding</button>
        <span class="spacer"></span>
        <button class="btn btn-ghost" ?disabled=${this._busy} @click=${() => this._sync(false)}>Sync now</button>
      </div>
      ${this._renderBindingForm()}
      <div class="panel">
        <table>
          <thead><tr><th>Label</th><th>Dashboard</th><th>Include ∩</th><th>Exclude</th><th>Status</th><th></th></tr></thead>
          <tbody>
            ${this._bindings.length === 0
              ? html`<tr><td colspan="6">No bindings yet.</td></tr>`
              : this._bindings.map(
                  (b) => html`<tr class="row-click" @click=${() => this._openEditBinding(b)}>
                    <td>${b.label || b.id}</td>
                    <td>${b.dashboard_url_path}</td>
                    <td><div class="chip-row">${(b.expression?.include || []).map((id) => html`<span class="pill">${id}</span>`)}</div></td>
                    <td><div class="chip-row">${(b.expression?.exclude || []).map((id) => html`<span class="pill warn">${id}</span>`)}</div></td>
                    <td>${b.stale ? html`<span class="pill warn">stale</span>` : html`<span class="pill">ok</span>`}</td>
                    <td>
                      <div class="row-actions" @click=${(e) => e.stopPropagation()}>
                        <button class="btn btn-ghost btn-sm" @click=${() => this._openEditBinding(b)}>Edit</button>
                        <button class="btn btn-danger btn-sm" @click=${() => this._deleteBinding(b.id)}>Remove</button>
                      </div>
                    </td>
                  </tr>`
                )}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderAutomations() {
    const g = this._groups[0];
    return html`
      <div class="hero">
        <h1>Automation conditions</h1>
        <p>Use the <code>members</code> attribute on each group sensor. Visibility remains UX-only.</p>
      </div>
      ${g
        ? html`<div class="yaml-block">${this._automationYaml(g)}</div>
            <div class="callout">Entity: <code>sensor.hassio_groups_${g.id}</code> · state = member count · <code>members</code> = user id list</div>`
        : html`<div class="callout">Create a group first to preview the template.</div>`}
      <div class="panel" style="margin-top:18px;padding:18px">
        <h2 class="section-title">All group sensors</h2>
        <ul class="member-list">
          ${this._groups.map(
            (group) => html`<li>
              <div class="member-meta">
                <strong>${group.name}</strong>
                <span>sensor.hassio_groups_${group.id}</span>
              </div>
              <span class="pill">${group.member_count ?? (group.member_user_ids || []).length}</span>
            </li>`
          )}
        </ul>
      </div>
    `;
  }
}

customElements.define("ha-groups-panel", HaGroupsPanel);
