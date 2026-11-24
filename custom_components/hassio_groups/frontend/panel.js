/**
 * HA Groups admin panel (Lit).
 * Friendly names primary; user IDs as subtitle on detail rows only.
 * Visibility is UX, not ACL.
 *
 * UX: edit bindings + visual dashboard preview picker; editable group IDs; MDI icon picker.
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
    _nodes: { state: true },
    _previewTree: { state: true },
    _nodesBusy: { state: true },
    _pickerStep: { state: true },
    _previewViewIndex: { state: true },
    _hoverKey: { state: true },
    _selectedNodeLabel: { state: true },
    _selectedNodeSubtitle: { state: true },
    _selectedNodeKey: { state: true },
    _advancedLocatorOpen: { state: true },
    _excludeOpen: { state: true },
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
    .selected-node {
      margin-top: 10px; padding: 12px 14px; border-radius: 12px; border: 1px solid rgba(31,107,79,0.28);
      background: rgba(31,107,79,0.08);
    }
    .selected-node .k { font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
    .selected-node .sub { margin-top: 4px; font-size: 0.82rem; color: var(--muted); line-height: 1.35; }
    .toggle-row { display: inline-flex; align-items: center; gap: 8px; font-size: 0.88rem; color: var(--ink-soft); }
    .toggle-row input { accent-color: var(--accent); width: 16px; height: 16px; }
    details.advanced {
      margin-top: 12px; border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px;
      background: rgba(255,255,255,0.45);
    }
    details.advanced > summary {
      cursor: pointer; font-size: 0.85rem; color: var(--ink-soft); font-weight: 600;
    }
    .dash-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 10px; margin-top: 10px;
    }
    .dash-tile {
      display: flex; flex-direction: column; gap: 8px; text-align: left;
      padding: 14px; border-radius: 14px; border: 1px solid var(--line);
      background: rgba(255,255,255,0.75); cursor: pointer; font: inherit; color: inherit;
      min-height: 96px;
    }
    .dash-tile:hover, .dash-tile.selected {
      border-color: rgba(31,107,79,0.5); background: rgba(31,107,79,0.1);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }
    .dash-tile strong { font-size: 0.98rem; }
    .dash-tile span { font-size: 0.78rem; color: var(--muted); }
    .preview-shell {
      margin-top: 12px; border: 1px solid var(--line); border-radius: 16px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.82), rgba(245,249,246,0.9));
      overflow: hidden;
    }
    .preview-toolbar {
      display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
      padding: 12px 14px; border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.55);
    }
    .preview-toolbar .title { font-weight: 600; color: var(--accent-deep); }
    .view-tabs { display: flex; gap: 6px; flex-wrap: wrap; padding: 10px 12px; border-bottom: 1px solid var(--line); }
    .view-tab {
      border: 1px solid var(--line); background: rgba(255,255,255,0.7); color: var(--ink-soft);
      border-radius: 999px; padding: 7px 12px; font: inherit; cursor: pointer;
      display: inline-flex; align-items: center; gap: 6px;
    }
    .view-tab:hover { border-color: rgba(31,107,79,0.4); }
    .view-tab.active { background: var(--accent); color: #f5faf7; border-color: transparent; }
    .view-tab.selected-target { box-shadow: 0 0 0 2px var(--accent-glow); }
    .preview-canvas { padding: 14px; max-height: 520px; overflow: auto; }
    .preview-view-frame {
      border: 2px dashed transparent; border-radius: 16px; padding: 8px;
      transition: border-color 0.15s ease, background 0.15s ease;
    }
    .preview-view-frame:hover, .preview-view-frame.hot {
      border-color: rgba(31,107,79,0.45); background: rgba(31,107,79,0.04);
    }
    .preview-view-frame.selected {
      border-style: solid; border-color: var(--accent); background: rgba(31,107,79,0.07);
    }
    .preview-view-hit {
      display: flex; justify-content: space-between; align-items: center; gap: 8px;
      width: 100%; border: 0; background: transparent; font: inherit; color: inherit;
      cursor: pointer; padding: 4px 6px 10px; text-align: left;
    }
    .preview-view-hit .hint { font-size: 0.75rem; color: var(--muted); }
    .section-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .preview-section {
      border: 1px solid var(--line); border-radius: 14px; padding: 10px;
      background: rgba(255,255,255,0.65); cursor: pointer;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
    }
    .preview-section:hover, .preview-section.hot {
      border-color: rgba(31,107,79,0.45); box-shadow: 0 0 0 3px var(--accent-glow);
      transform: translateY(-1px);
    }
    .preview-section.selected {
      border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow);
    }
    .preview-section-head {
      display: flex; justify-content: space-between; gap: 8px; align-items: center;
      margin-bottom: 8px; font-size: 0.78rem; color: var(--muted); text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .preview-cards { display: grid; gap: 8px; }
    .preview-card {
      display: grid; grid-template-columns: 28px 1fr; gap: 10px; align-items: start;
      text-align: left; width: 100%; border: 1px solid var(--line); border-radius: 12px;
      padding: 10px 12px; background: rgba(255,255,255,0.9); cursor: pointer; font: inherit; color: inherit;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
    }
    .preview-card:hover, .preview-card.hot {
      border-color: rgba(31,107,79,0.5); box-shadow: 0 0 0 3px var(--accent-glow);
      transform: translateY(-1px);
    }
    .preview-card.selected {
      border-color: var(--accent); background: rgba(31,107,79,0.1);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }
    .preview-card strong { display: block; font-size: 0.92rem; }
    .preview-card .snip { display: block; margin-top: 3px; font-size: 0.78rem; color: var(--muted); line-height: 1.35; }
    .preview-card .meta { display: block; margin-top: 4px; font-size: 0.7rem; color: var(--accent-deep); }
    .preview-empty { padding: 28px; text-align: center; color: var(--muted); }
    .vis-pill {
      font-size: 0.65rem; padding: 2px 7px; border-radius: 999px;
      background: rgba(154,91,18,0.12); color: var(--warn);
    }
    .bind-sheet {
      margin-top: 14px; border: 1px solid rgba(31,107,79,0.28); border-radius: 16px;
      background: rgba(255,255,255,0.92); padding: 16px 16px 14px;
      box-shadow: 0 10px 30px rgba(15,61,46,0.08);
    }
    .bind-sheet h3 {
      margin: 0 0 4px; font-family: var(--font-display); font-size: 1.35rem;
      color: var(--accent-deep); font-weight: 400;
    }
    .bind-sheet .target-line {
      font-size: 0.88rem; color: var(--muted); margin: 0 0 14px; line-height: 1.4;
    }
    .group-chip-grid { display: flex; flex-wrap: wrap; gap: 8px; }
    .group-chip {
      display: inline-flex; align-items: center; gap: 8px;
      border: 1px solid var(--line); border-radius: 999px; padding: 8px 14px;
      background: rgba(255,255,255,0.85); cursor: pointer; font: inherit; color: inherit;
      transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
    }
    .group-chip:hover { border-color: rgba(31,107,79,0.45); }
    .group-chip.on {
      border-color: var(--accent); background: rgba(31,107,79,0.12);
      box-shadow: 0 0 0 3px var(--accent-glow); color: var(--accent-deep); font-weight: 600;
    }
    .group-chip.warn.on {
      border-color: var(--warn); background: rgba(154,91,18,0.14);
      box-shadow: 0 0 0 3px rgba(154,91,18,0.15); color: var(--warn);
    }
    .group-chip .dot {
      width: 8px; height: 8px; border-radius: 50%; background: var(--line);
    }
    .group-chip.on .dot { background: var(--accent); }
    .group-chip.warn.on .dot { background: var(--warn); }
    details.exclude-block {
      margin: 12px 0 4px; border-top: 1px dashed var(--line); padding-top: 10px;
    }
    details.exclude-block > summary {
      cursor: pointer; color: var(--muted); font-size: 0.88rem; list-style: none;
    }
    details.exclude-block > summary::-webkit-details-marker { display: none; }
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
    this._nodes = [];
    this._previewTree = [];
    this._nodesBusy = false;
    this._pickerStep = "closed"; // closed | dashboards | preview | groups
    this._previewViewIndex = 0;
    this._hoverKey = "";
    this._selectedNodeLabel = "";
    this._selectedNodeSubtitle = "";
    this._selectedNodeKey = "";
    this._advancedLocatorOpen = false;
    this._excludeOpen = false;
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

  get _dashboards() {
    return this._data?.dashboards || [];
  }

  get _options() {
    return this._data?.options || {};
  }

  get _autoSync() {
    const v = this._options.auto_sync;
    return v === undefined ? true : !!v;
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
      this._draft.group_id?.trim() ||
      this._slugify(this._draft.name) ||
      undefined;
    if (!groupId) {
      this._error = "Group ID is required";
      return;
    }
    await this._call("save_group", {
      name: this._draft.name.trim(),
      group_id: groupId,
      previous_group_id: this._selectedGroupId || undefined,
      description: this._draft.description || "",
      icon: this._normalizeIcon(this._draft.icon),
      member_user_ids: this._draft.member_user_ids || [],
    });
    this._view = "groups";
    this._draft = null;
    this._selectedGroupId = null;
    this._iconPickerOpen = false;
  }

  async _deleteGroup() {
    const gid = this._selectedGroupId || this._draft?.group_id;
    if (!gid) return;
    if (!confirm(`Delete group “${this._draft?.name || gid}”?`)) return;
    await this._call("delete_group", { group_id: gid });
    this._view = "groups";
    this._draft = null;
    this._selectedGroupId = null;
  }

  _resetNodeBrowser() {
    this._nodes = [];
    this._previewTree = [];
    this._pickerStep = "closed";
    this._previewViewIndex = 0;
    this._hoverKey = "";
    this._selectedNodeLabel = "";
    this._selectedNodeSubtitle = "";
    this._selectedNodeKey = "";
    this._advancedLocatorOpen = false;
    this._excludeOpen = false;
    this._nodesBusy = false;
  }

  _locatorSummary(locator = {}, fingerprint = "", label = "") {
    if (label) return label;
    if (!locator) return "";
    const bits = [locator.kind || "node"];
    if (locator.view_path) bits.push(`path:${locator.view_path}`);
    else if (locator.view_index != null) bits.push(`view:${locator.view_index}`);
    if (locator.section_index != null) bits.push(`section:${locator.section_index}`);
    if (locator.card_index != null) bits.push(`card:${locator.card_index}`);
    if (fingerprint) bits.push(fingerprint.split("|")[0]);
    return bits.join(" · ");
  }

  _nodeKey(node) {
    if (!node?.locator) return "";
    const l = node.locator;
    return [l.kind, l.view_path || l.view_index, l.section_index, l.card_index, node.fingerprint || ""].join("|");
  }

  _openDashboardPicker() {
    this._pickerStep = "dashboards";
    this._previewTree = [];
    this._nodes = [];
    this._error = "";
  }

  async _pickDashboard(urlPath) {
    if (!urlPath) return;
    this._bindingDraft = { ...this._bindingDraft, dashboard_url_path: urlPath };
    this._selectedNodeLabel = "";
    this._selectedNodeSubtitle = "";
    this._selectedNodeKey = "";
    await this._loadDashboardPreview(urlPath);
  }

  async _loadDashboardPreview(urlPath) {
    const path = (urlPath || this._bindingDraft?.dashboard_url_path || "").trim();
    if (!path) {
      this._error = "Pick a dashboard first";
      return;
    }
    this._nodesBusy = true;
    this._error = "";
    this._pickerStep = "preview";
    try {
      const result = await this.hass.connection.sendMessagePromise({
        type: `${DOMAIN}/dashboard_nodes`,
        dashboard_url_path: path,
      });
      this._nodes = result?.nodes || [];
      let tree = result?.tree || [];
      if (!tree.length && this._nodes.length) {
        tree = this._treeFromNodes(this._nodes);
      }
      this._previewTree = tree;
      this._previewViewIndex = 0;
      if (!tree.length) {
        this._error = this._error || `No views in preview for '${path}' (nodes=${this._nodes.length})`;
      }
    } catch (err) {
      this._nodes = [];
      this._previewTree = [];
      this._error = err?.message || String(err);
    } finally {
      this._nodesBusy = false;
    }
  }

  _treeFromNodes(nodes) {
    // Fallback when backend omitted tree (stale websocket handler).
    const views = new Map();
    for (const n of nodes || []) {
      const loc = n.locator || {};
      const vKey = loc.view_path != null && loc.view_path !== "" ? `p:${loc.view_path}` : `i:${loc.view_index}`;
      if (!views.has(vKey)) {
        views.set(vKey, {
          kind: "view",
          label: n.kind === "view" ? n.label : (loc.view_path || `View ${loc.view_index ?? "?"}`),
          path: loc.view_path,
          icon: "mdi:view-dashboard",
          locator: { kind: "view", view_index: loc.view_index, view_path: loc.view_path },
          fingerprint: n.kind === "view" ? n.fingerprint : "",
          has_visibility: n.kind === "view" ? !!n.has_visibility : false,
          sections: [],
          cards: [],
          _sectionMap: new Map(),
        });
      }
      const view = views.get(vKey);
      if (n.kind === "view") {
        view.label = n.label || view.label;
        view.fingerprint = n.fingerprint || "";
        view.has_visibility = !!n.has_visibility;
        view.locator = { ...n.locator };
        continue;
      }
      if (n.kind === "section") {
        const sKey = String(loc.section_index);
        const section = {
          kind: "section",
          label: n.label,
          breadcrumb: n.breadcrumb,
          icon: "mdi:view-grid-plus",
          locator: { ...n.locator },
          fingerprint: n.fingerprint || "",
          has_visibility: !!n.has_visibility,
          cards: [],
        };
        view._sectionMap.set(sKey, section);
        view.sections.push(section);
        continue;
      }
      if (n.kind === "card") {
        const card = {
          kind: "card",
          label: n.label,
          snippet: n.detail || "",
          type: n.type || "card",
          icon: "mdi:card",
          breadcrumb: n.breadcrumb,
          locator: { ...n.locator },
          fingerprint: n.fingerprint || "",
          has_visibility: !!n.has_visibility,
        };
        if (loc.section_index != null && loc.section_index !== "") {
          const sKey = String(loc.section_index);
          if (!view._sectionMap.has(sKey)) {
            const section = {
              kind: "section",
              label: `Section ${loc.section_index}`,
              locator: {
                kind: "section",
                view_index: loc.view_index,
                view_path: loc.view_path,
                section_index: loc.section_index,
              },
              fingerprint: "",
              has_visibility: false,
              cards: [],
            };
            view._sectionMap.set(sKey, section);
            view.sections.push(section);
          }
          view._sectionMap.get(sKey).cards.push(card);
        } else {
          view.cards.push(card);
        }
      }
    }
    return [...views.values()].map((v) => {
      delete v._sectionMap;
      return v;
    });
  }

  _selectNode(node) {
    if (!node?.locator) return;
    const loc = { ...node.locator };
    // Avoid undefined keys polluting locator
    Object.keys(loc).forEach((k) => {
      if (loc[k] === undefined || loc[k] === null || loc[k] === "") {
        if (k !== "view_path") delete loc[k];
      }
    });
    this._bindingDraft = {
      ...this._bindingDraft,
      locator: loc,
      fingerprint: node.fingerprint || "",
      label: this._bindingDraft.label || node.label || "",
    };
    const title = node.label || node.snippet || loc.kind || "Target";
    const crumb = node.breadcrumb || "";
    const ntype = node.type || loc.kind || "";
    const subBits = [];
    if (crumb && crumb !== title) subBits.push(crumb);
    else if (crumb) subBits.push(crumb);
    if (ntype) subBits.push(ntype);
    this._selectedNodeLabel = title;
    this._selectedNodeSubtitle = subBits.join(" · ");
    this._selectedNodeKey = this._nodeKey(node);
    this._hoverKey = "";
    this._excludeOpen = !!(this._bindingDraft.exclude && this._bindingDraft.exclude.length);
    this._advancedLocatorOpen = false;
    this._pickerStep = "groups"; // next step: choose include groups
  }

  _toggleDraftGroup(field, groupId) {
    const d = this._bindingDraft;
    if (!d) return;
    const cur = new Set(d[field] || []);
    if (cur.has(groupId)) cur.delete(groupId);
    else cur.add(groupId);
    this._bindingDraft = { ...d, [field]: [...cur] };
  }

  _onDashboardPathChange(e) {
    const path = e.target.value;
    this._bindingDraft = { ...this._bindingDraft, dashboard_url_path: path };
    this._previewTree = [];
    this._nodes = [];
    this._selectedNodeLabel = "";
    this._selectedNodeSubtitle = "";
    this._selectedNodeKey = "";
    if (this._pickerStep === "preview") this._pickerStep = "dashboards";
  }

  _openBindingCreate() {
    this._resetNodeBrowser();
    this._bindingDraft = {
      binding_id: "",
      dashboard_url_path: (this._dashboards[0]?.url_path) || "lovelace",
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
    this._resetNodeBrowser();
    const editTitle = binding.label || this._locatorSummary(
      this._bindingDraft.locator,
      this._bindingDraft.fingerprint,
      "",
    );
    this._selectedNodeLabel = editTitle;
    const editBits = [];
    const summary = this._locatorSummary(this._bindingDraft.locator, this._bindingDraft.fingerprint, "");
    if (summary && summary !== editTitle) editBits.push(summary);
    if (loc.kind) editBits.push(loc.kind);
    this._selectedNodeSubtitle = editBits.join(" · ");
    this._selectedNodeKey = this._nodeKey({
      locator: this._bindingDraft.locator,
      fingerprint: this._bindingDraft.fingerprint,
    });
    this._advancedLocatorOpen = false;
    this._excludeOpen = !!(binding.expression?.exclude || []).length;
    this._pickerStep = "groups";
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

  async _setAutoSync(enabled) {
    await this._call("update_options", { auto_sync: !!enabled });
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
              placeholder=${suggested || "auto-from-name"}
              @input=${this._onGroupIdInput}
            />
            <span class="hint">
              ${editing
                ? (d.group_id && d.group_id !== this._selectedGroupId
                    ? html`Renaming from <code>${this._selectedGroupId}</code> → <code>${d.group_id}</code> (bindings update).`
                    : "Editable — change to rename; bindings that reference this group update.")
                : this._groupIdManual
                  ? "Custom ID — clear the field and retype the name to resume auto-slug."
                  : suggested
                    ? html`Auto-generated as <code>${suggested}</code> — edit to override.`
                    : "Filled automatically from the name."}
            </span>
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

  _renderDashboardChooser() {
    const current = this._bindingDraft?.dashboard_url_path;
    const dashes = this._dashboards.length
      ? this._dashboards
      : [{ url_path: "lovelace", title: "Overview", mode: "storage" }];
    return html`
      <div class="dash-grid">
        ${dashes.map(
          (d) => html`<button type="button"
            class="dash-tile ${d.url_path === current ? "selected" : ""}"
            @click=${() => this._pickDashboard(d.url_path)}>
            <ha-icon .icon=${"mdi:view-dashboard-variant"}></ha-icon>
            <strong>${d.title || d.url_path}</strong>
            <span>${d.url_path}${d.mode ? ` · ${d.mode}` : ""}</span>
          </button>`
        )}
      </div>
      <span class="hint">Choosing a dashboard opens a visual preview — click a view, section, or card.</span>
    `;
  }

  _renderVisualPreview() {
    if (this._nodesBusy) {
      return html`<div class="preview-empty">Loading dashboard layout…</div>`;
    }
    const tree = this._previewTree || [];
    if (!tree.length) {
      return html`<div class="preview-empty">
        No views found on this dashboard (<code>${this._bindingDraft?.dashboard_url_path || "?"}</code>).
        ${this._error
          ? html`<div style="margin-top:8px;color:var(--danger)">${this._error}</div>`
          : html`<div style="margin-top:8px">Overview is often empty — pick <strong>HA Groups Lab</strong>, Main Floor, or another tile with real views. Hard-refresh if a new YAML dashboard just appeared.</div>`}
      </div>`;
    }
    const viewIdx = Math.min(this._previewViewIndex, tree.length - 1);
    const view = tree[viewIdx];
    const viewKey = this._nodeKey(view);
    const selectedKey = this._selectedNodeKey;
    const hoverKey = this._hoverKey;
    return html`
      <div class="preview-shell">
        <div class="preview-toolbar">
          <button class="btn btn-ghost btn-sm" type="button" @click=${() => (this._pickerStep = "dashboards")}>← Dashboards</button>
          <span class="title">${this._bindingDraft?.dashboard_url_path}</span>
          <span class="spacer"></span>
          <button class="btn btn-ghost btn-sm" type="button" ?disabled=${this._nodesBusy}
            @click=${() => this._loadDashboardPreview()}>Refresh</button>
        </div>
        <div class="view-tabs">
          ${tree.map((v, idx) => {
            const key = this._nodeKey(v);
            return html`<button type="button"
              class="view-tab ${idx === viewIdx ? "active" : ""} ${key === selectedKey ? "selected-target" : ""}"
              @click=${() => { this._previewViewIndex = idx; }}
              @dblclick=${() => this._selectNode(v)}
              title="Single-click to show · double-click to bind this view">
              <ha-icon .icon=${v.icon || "mdi:view-dashboard"}></ha-icon>
              ${v.label}
              ${v.has_visibility ? html`<span class="vis-pill">vis</span>` : nothing}
            </button>`;
          })}
        </div>
        <div class="preview-canvas">
          <div class="preview-view-frame ${viewKey === selectedKey ? "selected" : ""} ${viewKey === hoverKey ? "hot" : ""}"
            @mouseenter=${() => (this._hoverKey = viewKey)}
            @mouseleave=${() => (this._hoverKey = "")}>
            <button type="button" class="preview-view-hit" @click=${() => this._selectNode(view)}>
              <div>
                <strong>View: ${view.label}</strong>
                <div class="hint">Click here to bind the whole view${view.path ? ` · path ${view.path}` : ""}</div>
              </div>
              ${view.has_visibility ? html`<span class="vis-pill">has visibility</span>` : nothing}
            </button>
            ${view.sections?.length
              ? html`<div class="section-grid">
                  ${view.sections.map((section) => {
                    const sKey = this._nodeKey(section);
                    return html`<div
                      class="preview-section ${sKey === selectedKey ? "selected" : ""} ${sKey === hoverKey ? "hot" : ""}"
                      @mouseenter=${() => (this._hoverKey = sKey)}
                      @mouseleave=${() => (this._hoverKey = "")}
                      @click=${() => this._selectNode(section)}
                    >
                      <div class="preview-section-head">
                        <span>Section · ${section.label}</span>
                        ${section.has_visibility ? html`<span class="vis-pill">vis</span>` : nothing}
                      </div>
                      <div class="preview-cards" @click=${(e) => e.stopPropagation()}>
                        ${(section.cards || []).map((card) => this._renderPreviewCard(card))}
                      </div>
                    </div>`;
                  })}
                </div>`
              : nothing}
            ${view.cards?.length
              ? html`<div class="preview-cards" style="margin-top:10px">
                  ${view.cards.map((card) => this._renderPreviewCard(card))}
                </div>`
              : nothing}
            ${!view.sections?.length && !view.cards?.length
              ? html`<div class="preview-empty">This view has no sections/cards to preview.</div>`
              : nothing}
          </div>
        </div>
      </div>
    `;
  }

  _renderPreviewCard(card) {
    const key = this._nodeKey(card);
    return html`<button type="button"
      class="preview-card ${key === this._selectedNodeKey ? "selected" : ""} ${key === this._hoverKey ? "hot" : ""}"
      @mouseenter=${() => (this._hoverKey = key)}
      @mouseleave=${() => (this._hoverKey = "")}
      @click=${(e) => { e.stopPropagation(); this._selectNode(card); }}>
      <ha-icon .icon=${card.icon || "mdi:card"}></ha-icon>
      <div>
        <strong>${card.label}</strong>
        ${card.snippet ? html`<span class="snip">${card.snippet}</span>` : nothing}
        <span class="meta">${card.type || "card"}${card.has_visibility ? " · visibility" : ""}</span>
      </div>
    </button>`;
  }

  _renderLocatorPicker() {
    if (this._pickerStep === "dashboards") return this._renderDashboardChooser();
    if (this._pickerStep === "preview") return this._renderVisualPreview();
    if (this._pickerStep === "groups") return this._renderBindGroupsStep();
    return nothing;
  }

  _renderBindGroupsStep() {
    const d = this._bindingDraft;
    if (!d) return nothing;
    const include = new Set(d.include || []);
    const exclude = new Set(d.exclude || []);
    const editing = !!d.binding_id;
    return html`
      <div class="bind-sheet">
        <div class="toolbar" style="margin:0 0 10px">
          <button class="btn btn-ghost btn-sm" type="button"
            @click=${() => (this._pickerStep = "preview")}>← Back to preview</button>
          <span class="spacer"></span>
        </div>
        <h3>Who can see this?</h3>
        <p class="target-line">
          Binding <strong>${this._selectedNodeLabel || "selected target"}</strong>
          on <code>${d.dashboard_url_path}</code>.
          ${this._selectedNodeSubtitle
            ? html`<br /><span class="sub">${this._selectedNodeSubtitle}</span>`
            : nothing}
          Pick the groups that should include this element.
        </p>
        <div class="field">
          <label>Include groups</label>
          <span class="hint">Primary — people in these groups can see it (AND).</span>
          <div class="group-chip-grid" style="margin-top:8px">
            ${this._groups.length
              ? this._groups.map(
                  (g) => html`<button type="button"
                    class="group-chip ${include.has(g.id) ? "on" : ""}"
                    @click=${() => this._toggleDraftGroup("include", g.id)}>
                    <span class="dot"></span>${g.name}
                  </button>`
                )
              : html`<span class="hint">Create a group first.</span>`}
          </div>
        </div>
        <details class="exclude-block" ?open=${this._excludeOpen}
          @toggle=${(e) => (this._excludeOpen = e.target.open)}>
          <summary>Exclude groups (optional — rarer)</summary>
          <div class="field" style="margin-top:10px">
            <span class="hint">People in these groups are removed even if included above (NOT).</span>
            <div class="group-chip-grid" style="margin-top:8px">
              ${this._groups.map(
                (g) => html`<button type="button"
                  class="group-chip warn ${exclude.has(g.id) ? "on" : ""}"
                  @click=${() => this._toggleDraftGroup("exclude", g.id)}>
                  <span class="dot"></span>${g.name}
                </button>`
              )}
            </div>
          </div>
        </details>
        <details class="advanced" ?open=${this._advancedLocatorOpen}
          @toggle=${(e) => (this._advancedLocatorOpen = e.target.open)}>
          <summary>Advanced</summary>
          <div class="field" style="margin-top:12px">
            <label>Label (optional)</label>
            <input .value=${d.label || ""}
              @input=${(e) => (this._bindingDraft = { ...d, label: e.target.value })}
              placeholder="Friendly name for this binding" />
          </div>
          <div class="field"><label>Merge mode</label>
            <select .value=${d.merge_mode || "ensure_user_branch"}
              @change=${(e) => (this._bindingDraft = { ...d, merge_mode: e.target.value })}>
              <option value="ensure_user_branch">Update people rule only (keep other conditions)</option>
              <option value="replace_user_condition">Replace people visibility with these groups</option>
            </select>
          </div>
          <div class="field"><label>Locator kind</label>
            <select .value=${d.locator?.kind || "card"}
              @change=${(e) => (this._bindingDraft = { ...d, locator: { ...d.locator, kind: e.target.value } })}>
              <option value="view">view</option>
              <option value="section">section</option>
              <option value="card">card</option>
              <option value="other">other</option>
            </select>
          </div>
          <div class="field"><label>View path (optional)</label>
            <input .value=${d.locator?.view_path || ""}
              @input=${(e) => (this._bindingDraft = { ...d, locator: { ...d.locator, view_path: e.target.value } })} />
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
          <div class="field"><label>Fingerprint</label>
            <input .value=${d.fingerprint || ""}
              @input=${(e) => (this._bindingDraft = { ...d, fingerprint: e.target.value })} />
          </div>
        </details>
        <div class="toolbar" style="margin-top:14px">
          <button class="btn btn-primary" ?disabled=${this._busy || !(d.include || []).length}
            @click=${this._saveBinding}>
            ${editing ? "Save & sync" : "Save binding"}
          </button>
          <button class="btn btn-ghost" type="button"
            @click=${() => (this._pickerStep = "preview")}>Select a different target</button>
          <button class="btn btn-ghost" type="button"
            @click=${() => { this._bindingDraft = null; this._resetNodeBrowser(); }}>Cancel</button>
        </div>
      </div>
    `;
  }

  _renderBindingForm() {
    const d = this._bindingDraft;
    if (!d) return nothing;
    const editing = !!d.binding_id;
    const inGroupsStep = this._pickerStep === "groups";
    return html`<div class="panel" style="padding:18px;margin-bottom:18px">
      <h2 class="section-title">${editing ? "Edit binding" : "New binding"}</h2>
      <div class="layout-2">
        <div>
          ${this._selectedNodeLabel
            ? html`<div class="selected-node">
                <div class="k">Selected target</div>
                <strong>${this._selectedNodeLabel}</strong>
                ${this._selectedNodeSubtitle
                  ? html`<div class="sub">${this._selectedNodeSubtitle}</div>`
                  : nothing}
                <div style="margin-top:6px;font-size:0.8rem;color:var(--muted)">${d.dashboard_url_path || ""}</div>
                ${(d.include || []).length
                  ? html`<div class="chip-row" style="margin-top:10px">
                      ${(d.include || []).map((id) => {
                        const g = this._groups.find((x) => x.id === id);
                        return html`<span class="pill">${g?.name || id}</span>`;
                      })}
                    </div>`
                  : html`<div class="hint" style="margin-top:8px">Choose include groups in the next step.</div>`}
                ${(d.exclude || []).length
                  ? html`<div class="chip-row" style="margin-top:6px">
                      ${(d.exclude || []).map((id) => {
                        const g = this._groups.find((x) => x.id === id);
                        return html`<span class="pill warn">not ${g?.name || id}</span>`;
                      })}
                    </div>`
                  : nothing}
              </div>`
            : html`<div class="hint">Open the visual picker and click a view, section, or card — then choose groups.</div>`}
          ${!inGroupsStep
            ? html`<div class="toolbar" style="margin-top:14px">
                <button class="btn btn-ghost" @click=${() => { this._bindingDraft = null; this._resetNodeBrowser(); }}>Cancel</button>
              </div>`
            : nothing}
        </div>
        <div>
          <div class="field"><label>Visual picker</label>
            <div class="toolbar" style="margin:0 0 8px">
              <button class="btn btn-primary btn-sm" type="button" ?disabled=${this._busy}
                @click=${() => this._openDashboardPicker()}>
                ${this._pickerStep === "closed" ? "Open visual picker" : "Show dashboards"}
              </button>
              ${this._pickerStep !== "closed"
                ? html`<button class="btn btn-ghost btn-sm" type="button"
                    @click=${() => (this._pickerStep = "closed")}>Hide picker</button>`
                : nothing}
              ${this._selectedNodeLabel && this._pickerStep !== "groups"
                ? html`<button class="btn btn-ghost btn-sm" type="button"
                    @click=${() => (this._pickerStep = "groups")}>Choose groups →</button>`
                : nothing}
            </div>
            ${this._renderLocatorPicker()}
          </div>
        </div>
      </div>
      <div class="callout">Click a dashboard tile, then pick include groups. Technical locator / merge options stay under Advanced on that step.</div>
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
        <label class="toggle-row" title="Automatically re-sync Lovelace when groups or bindings change">
          <input type="checkbox" .checked=${this._autoSync} ?disabled=${this._busy}
            @change=${(e) => this._setAutoSync(e.target.checked)} />
          Auto sync
        </label>
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
