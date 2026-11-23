/**
 * HA Groups admin panel (Lit).
 * Friendly names primary; user IDs as subtitle on detail rows only.
 * Visibility is UX, not ACL.
 */
import {
  LitElement,
  html,
  css,
  nothing,
} from "https://unpkg.com/lit@3.2.1/index.js?module";

const DOMAIN = "hassio_groups";

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
    .field input, .field textarea, .field select {
      width: 100%; font: inherit; padding: 10px 12px; border-radius: 10px;
      border: 1px solid var(--line); background: rgba(255,255,255,0.85); color: var(--ink);
    }
    .field input:focus, .field textarea:focus, .field select:focus {
      outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow);
    }
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

  _openCreateGroup() {
    this._selectedGroupId = null;
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

  async _saveGroup() {
    if (!this._draft?.name?.trim()) {
      this._error = "Group name is required";
      return;
    }
    await this._call("save_group", {
      name: this._draft.name.trim(),
      group_id: this._draft.group_id || undefined,
      description: this._draft.description || "",
      icon: this._draft.icon || "mdi:account-group",
      member_user_ids: this._draft.member_user_ids || [],
    });
    this._view = "groups";
    this._draft = null;
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

  async _saveBinding() {
    const d = this._bindingDraft;
    if (!d?.include?.length) {
      this._error = "At least one include group is required";
      return;
    }
    await this._call("save_binding", {
      binding_id: d.binding_id,
      dashboard_url_path: d.dashboard_url_path,
      include: d.include,
      exclude: d.exclude || [],
      locator: d.locator,
      merge_mode: d.merge_mode,
      fingerprint: d.fingerprint || "",
      label: d.label || "",
    });
    this._bindingDraft = null;
  }

  async _deleteBinding(id) {
    if (!confirm("Remove this binding?")) return;
    await this._call("delete_binding", { binding_id: id });
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
            @click=${() => { this._view = "groups"; this._draft = null; }}>Groups</button>
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
                      <td><strong>${g.name}</strong>${g.description ? html`<div style="color:var(--muted);font-size:0.85rem">${g.description}</div>` : nothing}</td>
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

  _renderEditor() {
    const d = this._draft;
    if (!d) return nothing;
    const selected = new Set(d.member_user_ids || []);
    return html`
      <div class="hero">
        <h1>${d.group_id ? "Edit group" : "New group"}</h1>
        <p>Friendly names are shown first. User IDs appear as subtitles on member rows.</p>
      </div>
      <div class="layout-2">
        <div class="panel" style="padding:18px">
          <h2 class="section-title">Details</h2>
          <div class="field"><label>Name</label>
            <input .value=${d.name} @input=${(e) => (this._draft = { ...d, name: e.target.value })} />
          </div>
          <div class="field"><label>Group ID (slug)</label>
            <input .value=${d.group_id} ?disabled=${!!this._selectedGroupId}
              @input=${(e) => (this._draft = { ...d, group_id: e.target.value })} />
          </div>
          <div class="field"><label>Description</label>
            <textarea rows="3" .value=${d.description}
              @input=${(e) => (this._draft = { ...d, description: e.target.value })}></textarea>
          </div>
          <div class="field"><label>Icon</label>
            <input .value=${d.icon} @input=${(e) => (this._draft = { ...d, icon: e.target.value })} />
          </div>
          <div class="toolbar">
            <button class="btn btn-primary" ?disabled=${this._busy} @click=${this._saveGroup}>Save</button>
            <button class="btn btn-ghost" @click=${() => { this._view = "groups"; this._draft = null; }}>Cancel</button>
            ${this._selectedGroupId
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

  _renderBindings() {
    const d = this._bindingDraft;
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
      ${d
        ? html`<div class="panel" style="padding:18px;margin-bottom:18px">
            <h2 class="section-title">${d.binding_id ? "Edit binding" : "New binding"}</h2>
            <div class="layout-2">
              <div>
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
                <div class="field"><label>Fingerprint (optional)</label>
                  <input .value=${d.fingerprint || ""}
                    @input=${(e) => (this._bindingDraft = { ...d, fingerprint: e.target.value })} />
                </div>
                <div class="toolbar">
                  <button class="btn btn-primary" ?disabled=${this._busy} @click=${this._saveBinding}>Save binding</button>
                  <button class="btn btn-ghost" @click=${() => (this._bindingDraft = null)}>Cancel</button>
                </div>
              </div>
            </div>
            <div class="callout warn">Dashboard browser / live node picker is stubbed for the next phase — enter locator indices manually for now.</div>
          </div>`
        : nothing}
      <div class="panel">
        <table>
          <thead><tr><th>Label</th><th>Dashboard</th><th>Include ∩</th><th>Exclude</th><th>Status</th><th></th></tr></thead>
          <tbody>
            ${this._bindings.length === 0
              ? html`<tr><td colspan="6">No bindings yet.</td></tr>`
              : this._bindings.map(
                  (b) => html`<tr>
                    <td>${b.label || b.id}</td>
                    <td>${b.dashboard_url_path}</td>
                    <td><div class="chip-row">${(b.expression?.include || []).map((id) => html`<span class="pill">${id}</span>`)}</div></td>
                    <td><div class="chip-row">${(b.expression?.exclude || []).map((id) => html`<span class="pill warn">${id}</span>`)}</div></td>
                    <td>${b.stale ? html`<span class="pill warn">stale</span>` : html`<span class="pill">ok</span>`}</td>
                    <td><button class="btn btn-danger" @click=${() => this._deleteBinding(b.id)}>Remove</button></td>
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
