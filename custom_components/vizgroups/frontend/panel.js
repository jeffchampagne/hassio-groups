/**
 * Viz Groups admin panel (Lit).
 * Friendly names primary; user IDs as subtitle on detail rows only.
 * Visibility is UX, not ACL.
 *
 * UX: edit bindings + visual dashboard preview picker; editable group IDs; MDI icon picker.
 * Live hotfix 2026-11-24: member autosave + picker under selected target + table friendly names.
 * Live 2026-11-24: Convert audit Manual Dashboard Config → Viz Groups (PR #10 + normalizeLocator).
 * Live 2026-11-24: Manage visibility breadcrumbs (PR #13).
 */
import {
  LitElement,
  html,
  css,
  nothing,
} from "https://unpkg.com/lit@3.2.1/index.js?module";

const DOMAIN = "vizgroups";

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

class VizGroupsPanel extends LitElement {
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
    _userSearch: { state: true },
    _auditDashboard: { state: true },
    _auditBusy: { state: true },
    _auditReport: { state: true },
    _auditExpanded: { state: true },
    _refreshAuditAfterSave: { state: true },
    _clipStatus: { state: true },
    _pasteOpen: { state: true },
    _pasteDraft: { state: true },
  };

  static styles = css`
    :host {
      /* Bridge to Home Assistant theme tokens (light + dark). */
      --hg-text: var(--primary-text-color);
      --hg-text-secondary: var(--secondary-text-color);
      --hg-primary: var(--primary-color);
      --hg-on-primary: var(--text-primary-color, #fff);
      --hg-bg: var(--primary-background-color);
      --hg-bg-secondary: var(--secondary-background-color, var(--card-background-color));
      --hg-card: var(--card-background-color);
      --hg-divider: var(--divider-color);
      --hg-error: var(--error-color);
      --hg-warning: var(--warning-color, var(--accent-color, #ff9800));
      --hg-disabled: var(--disabled-text-color, var(--disabled-color));
      --hg-hover: color-mix(in srgb, var(--hg-primary) 12%, transparent);
      --hg-hover-strong: color-mix(in srgb, var(--hg-primary) 20%, transparent);
      --hg-ring: color-mix(in srgb, var(--hg-primary) 28%, transparent);
      --hg-radius: var(--ha-card-border-radius, 12px);
      --hg-font: var(--ha-font-family-body, Roboto, Noto Sans, system-ui, -apple-system, sans-serif);
      --hg-font-display: var(--ha-font-family-heading, var(--hg-font));
      display: block;
      font-family: var(--hg-font);
      color: var(--hg-text);
      background: var(--hg-bg);
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
      nav.side { border-right: 0; border-bottom: 1px solid var(--hg-divider); }
      .layout-2 { grid-template-columns: 1fr !important; }
    }
    nav.side {
      padding: 28px 18px;
      border-right: 1px solid var(--hg-divider);
      background: var(--hg-bg-secondary);
    }
    .brand {
      font-family: var(--hg-font-display);
      font-size: 1.65rem;
      line-height: 1.1;
      color: var(--hg-text);
      margin: 0 0 28px;
      font-weight: 500;
    }
    .brand-sub {
      font-size: 0.75rem;
      color: var(--hg-text-secondary);
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 28px;
    }
    .nav-btn {
      display: block; width: 100%; text-align: left; border: 0;
      background: transparent; font: inherit; color: var(--hg-text);
      padding: 10px 12px; border-radius: 10px; cursor: pointer; margin-bottom: 4px;
    }
    .nav-btn:hover { background: var(--hg-hover); }
    .nav-btn.active { background: var(--hg-primary); color: var(--hg-on-primary); }
    main { padding: 28px 32px 48px; }
    .hero h1 {
      font-family: var(--hg-font-display); font-weight: 500;
      font-size: clamp(1.75rem, 2.8vw, 2.35rem); margin: 0 0 8px; color: var(--hg-text);
    }
    .hero p { margin: 0; color: var(--hg-text-secondary); line-height: 1.45; }
    .toolbar { display: flex; gap: 10px; align-items: center; margin: 18px 0; flex-wrap: wrap; }
    .spacer { flex: 1; }
    .btn {
      font: inherit; border: 1px solid transparent; border-radius: 999px;
      padding: 9px 16px; cursor: pointer;
    }
    .btn-primary { background: var(--hg-primary); color: var(--hg-on-primary); }
    .btn-ghost {
      background: transparent; border-color: var(--hg-divider); color: var(--hg-text);
    }
    .btn-ghost:hover { background: var(--hg-hover); }
    .btn-danger {
      background: transparent;
      border-color: color-mix(in srgb, var(--hg-error) 40%, transparent);
      color: var(--hg-error);
    }
    .btn-sm { padding: 6px 12px; font-size: 0.85rem; }
    .btn-x {
      width: 30px; height: 30px; padding: 0; border-radius: 8px;
      display: inline-grid; place-items: center;
      font-size: 1.15rem; line-height: 1; font-weight: 700;
    }
    .btn:disabled { opacity: 0.55; cursor: not-allowed; color: var(--hg-disabled); }
    .panel {
      background: var(--hg-card); border: 1px solid var(--hg-divider);
      border-radius: var(--hg-radius); overflow: hidden;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
    th {
      text-align: left; font-size: 0.72rem; letter-spacing: 0.07em; text-transform: uppercase;
      color: var(--hg-text-secondary); padding: 14px 16px; border-bottom: 1px solid var(--hg-divider);
    }
    td { padding: 14px 16px; border-bottom: 1px solid var(--hg-divider); vertical-align: middle; }
    tr:last-child td { border-bottom: 0; }
    tr.row-click { cursor: pointer; }
    tr.row-click:hover { background: var(--hg-hover); }
    .pill {
      display: inline-flex; align-items: center; gap: 6px; font-size: 0.78rem;
      padding: 4px 10px; border-radius: 999px;
      background: var(--hg-hover); color: var(--hg-text); font-weight: 500;
    }
    .pill.warn {
      background: color-mix(in srgb, var(--hg-warning) 18%, transparent);
      color: var(--hg-warning);
    }
    .pill.ok {
      background: color-mix(in srgb, var(--success-color, #4caf50) 18%, transparent);
      color: var(--success-color, #4caf50);
    }
    .has-tip {
      position: relative;
    }
    .has-tip::after {
      content: attr(data-tip);
      position: absolute;
      right: 0;
      bottom: calc(100% + 8px);
      z-index: 80;
      min-width: 12rem;
      max-width: min(18rem, calc(100vw - 2rem));
      padding: 8px 10px;
      border-radius: 8px;
      background: var(--hg-text);
      color: var(--hg-card);
      font-size: 0.78rem;
      font-weight: 500;
      line-height: 1.35;
      white-space: normal;
      text-align: left;
      box-shadow: 0 6px 18px color-mix(in srgb, var(--hg-text) 18%, transparent);
      opacity: 0;
      pointer-events: none;
      transform: translateY(4px);
      transition: opacity 0.12s ease, transform 0.12s ease;
    }
    .has-tip:hover::after, .has-tip:focus-visible::after {
      opacity: 1;
      transform: translateY(0);
    }
    .layout-2 { display: grid; grid-template-columns: minmax(180px, 0.72fr) minmax(0, 1.28fr); gap: 18px; }
    .layout-3 {
      display: grid; grid-template-columns: minmax(200px, 0.85fr) 1fr 1fr; gap: 18px; align-items: start;
    }
    @media (max-width: 1100px) {
      .layout-3 { grid-template-columns: 1fr; }
    }
    .panel-col-body { max-height: min(62vh, 560px); overflow: auto; }
    .member-list .row-actions { margin-left: auto; }
    .section-title {
      font-family: var(--hg-font-display); font-size: 1.25rem; margin: 0 0 12px;
      color: var(--hg-text); font-weight: 500;
    }
    .field { margin-bottom: 14px; }
    .field label {
      display: block; font-size: 0.75rem; letter-spacing: 0.06em; text-transform: uppercase;
      color: var(--hg-text-secondary); margin-bottom: 6px;
    }
    .field .hint {
      display: block; margin-top: 6px; font-size: 0.78rem; color: var(--hg-text-secondary);
      text-transform: none; letter-spacing: 0;
    }
    .field input, .field textarea, .field select {
      width: 100%; font: inherit; padding: 10px 12px; border-radius: 10px;
      border: 1px solid var(--hg-divider); background: var(--hg-card); color: var(--hg-text);
    }
    .field input:focus, .field textarea:focus, .field select:focus {
      outline: none; border-color: var(--hg-primary); box-shadow: 0 0 0 3px var(--hg-ring);
    }
    .field input:disabled {
      opacity: 0.7; background: var(--hg-bg-secondary); color: var(--hg-disabled);
    }
    .member-list { list-style: none; margin: 0; padding: 0; overflow: visible; }
    .member-list li {
      display: flex; align-items: center; gap: 12px; padding: 10px 12px;
      border-bottom: 1px solid var(--hg-divider);
      position: relative;
    }
    .member-list li:last-child { border-bottom: 0; }
    .member-list li:hover,
    .member-list li:focus-within { z-index: 60; }
    .members-col-head {
      position: relative;
      z-index: 1;
      padding: 18px 18px 8px;
    }
    .panel-col-body.members-body {
      overflow: visible;
      position: relative;
      z-index: 2;
    }
    /* Remove-X tip paints above the Group Members heading */
    .member-list .btn-x.has-tip::after {
      z-index: 120;
      bottom: calc(100% + 8px);
      right: 0;
      left: auto;
      min-width: 10rem;
    }
    .avatar {
      width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center;
      font-size: 0.8rem; font-weight: 600; color: var(--hg-text);
      background: var(--hg-hover-strong); flex-shrink: 0;
    }
    .member-meta { flex: 1; min-width: 0; }
    .member-meta strong { display: block; font-weight: 600; color: var(--hg-text); }
    .member-meta span { font-size: 0.8rem; color: var(--hg-text-secondary); word-break: break-all; }
    .sensor-item { display: block; padding: 14px 0; border-bottom: 1px solid var(--hg-divider); }
    .sensor-item:last-child { border-bottom: 0; }
    .sensor-entity {
      margin-top: 4px; font-size: 0.85rem; color: var(--hg-text-secondary);
    }
    .sensor-more {
      margin-top: 8px;
    }
    .sensor-more > summary {
      cursor: pointer; list-style: none; display: inline-flex; align-items: center; gap: 6px;
      font-size: 0.82rem; color: var(--hg-text-secondary); user-select: none;
    }
    .sensor-more > summary::-webkit-details-marker { display: none; }
    .sensor-more > summary::before {
      content: "";
      width: 0.4em; height: 0.4em;
      border-right: 2px solid var(--hg-text-secondary);
      border-bottom: 2px solid var(--hg-text-secondary);
      transform: rotate(-45deg);
      transition: transform 0.15s ease;
    }
    .sensor-more[open] > summary::before { transform: rotate(45deg); }
    .audit-toggle {
      display: inline-flex; align-items: flex-start; gap: 8px;
      background: none; border: 0; padding: 0; margin: 0;
      color: inherit; font: inherit; text-align: left; cursor: pointer; width: 100%;
    }
    .audit-chevron {
      flex: 0 0 auto; width: 0.4em; height: 0.4em; margin-top: 0.45em;
      border-right: 2px solid var(--hg-text-secondary);
      border-bottom: 2px solid var(--hg-text-secondary);
      transform: rotate(-45deg);
      transition: transform 0.15s ease;
    }
    .audit-chevron.open { transform: rotate(45deg); }
    .audit-toggle-label { min-width: 0; flex: 1; }
    tr.audit-detail td {
      padding-top: 0; background: color-mix(in srgb, var(--hg-primary) 4%, transparent);
    }
    .audit-users-block { padding: 4px 0 8px 1.25rem; }
    .audit-users-head {
      display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
      margin: 0 0 8px;
    }
    .audit-users-subhead {
      font-size: 0.78rem; font-weight: 600; letter-spacing: 0.02em;
      text-transform: uppercase; color: var(--hg-text-secondary);
      margin: 0;
    }
    .clip-status {
      font-size: 0.78rem; color: var(--hg-primary); font-weight: 500;
    }
    .editor-col-head {
      display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
      padding: 18px 18px 8px;
      position: relative;
      z-index: 40;
      overflow: visible;
    }
    .editor-col-head .section-title { margin: 0; flex: 1; }
    /* Tip below Paste — when layout-3 stacks, Members sits above and would cover an upward tip. */
    .editor-col-head .has-tip { position: relative; z-index: 41; }
    .editor-col-head .has-tip::after {
      top: calc(100% + 8px);
      bottom: auto;
      right: 0;
      left: auto;
      z-index: 90;
      transform: translateY(-4px);
    }
    .editor-col-head .has-tip:hover::after,
    .editor-col-head .has-tip:focus-visible::after {
      transform: translateY(0);
    }
    .panel.panel-flush {
      overflow: visible;
    }
    .paste-box {
      margin: 0 18px 12px; padding: 12px; border: 1px solid var(--hg-divider);
      border-radius: 12px; background: var(--hg-bg-secondary, var(--hg-card));
    }
    .paste-box textarea {
      width: 100%; min-height: 96px; resize: vertical; font: inherit;
      box-sizing: border-box;
    }
    .paste-box .toolbar { margin: 10px 0 0; }
    .audit-users { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
    .audit-users li { display: flex; align-items: center; gap: 10px; }
    .audit-users .member-meta strong { font-weight: 600; }
    .audit-users .member-meta span { font-size: 0.8rem; color: var(--hg-text-secondary); word-break: break-all; }
    .audit-source { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
    .audit-source .pill,
    .audit-source .btn {
      text-transform: none;
      letter-spacing: normal;
    }
    .sensor-attrs { margin: 8px 0 0; padding: 0; list-style: none; display: grid; gap: 4px; }
    .sensor-attrs li {
      display: grid; grid-template-columns: 8.5rem 1fr; gap: 10px;
      border: 0; padding: 0; font-size: 0.82rem; color: var(--hg-text);
    }
    .sensor-attrs .k { color: var(--hg-text-secondary); }
    .sensor-attrs .v { word-break: break-word; color: var(--hg-text); }
    .user-search { padding: 0 18px 8px; }
    .user-search input { width: 100%; }
    .user-picker { display: grid; gap: 8px; max-height: 280px; overflow: auto; padding: 8px; }
    .user-option {
      display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px;
      border: 1px solid var(--hg-divider); background: var(--hg-card); cursor: pointer;
      color: var(--hg-text); width: 100%; text-align: left; font: inherit;
    }
    .user-option.selected, .user-option:hover {
      border-color: var(--hg-primary); background: var(--hg-hover);
    }
    .callout {
      border-left: 3px solid var(--hg-primary); padding: 12px 14px; background: var(--hg-hover);
      border-radius: 0 10px 10px 0; color: var(--hg-text); font-size: 0.92rem; margin-top: 14px;
    }
    .callout.warn {
      border-left-color: var(--hg-warning);
      background: color-mix(in srgb, var(--hg-warning) 12%, transparent);
    }
    .error {
      margin: 12px 0; padding: 10px 12px; border-radius: 10px;
      background: color-mix(in srgb, var(--hg-error) 14%, transparent); color: var(--hg-error);
    }
    .yaml-block {
      background: var(--code-editor-background-color, var(--hg-bg-secondary));
      color: var(--hg-text); border: 1px solid var(--hg-divider);
      border-radius: var(--hg-radius); padding: 18px 20px;
      font-family: var(--ha-font-family-code, ui-monospace, SFMono-Regular, Menlo, monospace);
      font-size: 0.82rem; line-height: 1.55; overflow-x: auto; white-space: pre;
    }
    .stat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 18px 0; }
    .stat {
      padding: 16px 18px; border-radius: var(--hg-radius); border: 1px solid var(--hg-divider);
      background: var(--hg-card);
    }
    .stat .n { font-family: var(--hg-font-display); font-size: 2rem; color: var(--hg-text); font-weight: 500; }
    .stat .l { font-size: 0.78rem; color: var(--hg-text-secondary); margin-top: 6px; text-transform: uppercase; }
    .chip-row { display: flex; flex-wrap: wrap; gap: 6px; }
    .row-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .icon-field { display: flex; gap: 10px; align-items: stretch; }
    .icon-preview {
      width: 46px; flex-shrink: 0; border-radius: 10px; border: 1px solid var(--hg-divider);
      background: var(--hg-card); display: grid; place-items: center; color: var(--hg-text);
    }
    .icon-preview ha-icon, .icon-preview .icon-fallback { --mdc-icon-size: 24px; font-size: 1.25rem; }
    .icon-picker {
      margin-top: 10px; border: 1px solid var(--hg-divider); border-radius: 12px;
      background: var(--hg-card); overflow: hidden;
    }
    .icon-picker-toolbar { padding: 10px; border-bottom: 1px solid var(--hg-divider); }
    .icon-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
      gap: 6px; max-height: 220px; overflow: auto; padding: 10px;
    }
    .icon-cell {
      display: flex; flex-direction: column; align-items: center; gap: 4px;
      padding: 8px 4px; border-radius: 10px; border: 1px solid transparent;
      background: transparent; cursor: pointer; font: inherit; color: var(--hg-text);
    }
    .icon-cell:hover, .icon-cell.selected {
      border-color: var(--hg-primary); background: var(--hg-hover); color: var(--hg-text);
    }
    .icon-cell ha-icon, .icon-cell .icon-fallback { --mdc-icon-size: 22px; font-size: 1.15rem; }
    .icon-cell span {
      font-size: 0.62rem; line-height: 1.2; text-align: center; word-break: break-all;
      color: var(--hg-text-secondary); max-width: 100%;
    }
    .icon-empty { padding: 16px; color: var(--hg-text-secondary); font-size: 0.85rem; text-align: center; }
    .selected-node {
      margin-top: 10px; padding: 12px 14px; border-radius: 12px;
      border: 1px solid color-mix(in srgb, var(--hg-primary) 35%, var(--hg-divider));
      background: var(--hg-hover);
    }
    .selected-node .k {
      font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase;
      color: var(--hg-text-secondary);
    }
    .selected-node .sub { margin-top: 4px; font-size: 0.82rem; color: var(--hg-text-secondary); line-height: 1.35; }
    .selected-node strong { color: var(--hg-text); }
    .toggle-row {
      display: inline-flex; align-items: center; gap: 8px; font-size: 0.88rem; color: var(--hg-text);
    }
    .toggle-row input { accent-color: var(--hg-primary); width: 16px; height: 16px; }
    details.advanced {
      margin-top: 12px; border: 1px solid var(--hg-divider); border-radius: 12px; padding: 10px 12px;
      background: var(--hg-bg-secondary);
    }
    details.advanced > summary {
      cursor: pointer; font-size: 0.85rem; color: var(--hg-text); font-weight: 600;
    }
    .dash-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 10px; margin-top: 10px;
    }
    .dash-tile {
      display: flex; flex-direction: column; gap: 8px; text-align: left;
      padding: 14px; border-radius: var(--hg-radius); border: 1px solid var(--hg-divider);
      background: var(--hg-card); cursor: pointer; font: inherit; color: var(--hg-text);
      min-height: 96px;
    }
    .dash-tile:hover, .dash-tile.selected {
      border-color: var(--hg-primary); background: var(--hg-hover);
      box-shadow: 0 0 0 3px var(--hg-ring);
    }
    .dash-tile strong { font-size: 0.98rem; }
    .dash-tile span { font-size: 0.78rem; color: var(--hg-text-secondary); }
    .preview-shell {
      margin-top: 12px; border: 1px solid var(--hg-divider); border-radius: 16px;
      background: var(--hg-card); overflow: hidden;
    }
    .preview-toolbar {
      display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
      padding: 12px 14px; border-bottom: 1px solid var(--hg-divider);
      background: var(--hg-bg-secondary);
    }
    .preview-toolbar .title { font-weight: 600; color: var(--hg-text); }
    .view-tabs {
      display: flex; gap: 6px; flex-wrap: wrap; padding: 10px 12px;
      border-bottom: 1px solid var(--hg-divider);
    }
    .view-tab {
      border: 1px solid var(--hg-divider); background: var(--hg-card); color: var(--hg-text);
      border-radius: 999px; padding: 7px 12px; font: inherit; cursor: pointer;
      display: inline-flex; align-items: center; gap: 6px;
    }
    .view-tab:hover { border-color: var(--hg-primary); background: var(--hg-hover); }
    .view-tab.active {
      background: var(--hg-primary); color: var(--hg-on-primary); border-color: transparent;
    }
    .view-tab.selected-target { box-shadow: 0 0 0 2px var(--hg-ring); }
    .preview-canvas { padding: 14px; max-height: 520px; overflow: auto; }
    .preview-view-frame {
      border: 2px dashed transparent; border-radius: 16px; padding: 8px;
      transition: border-color 0.15s ease, background 0.15s ease;
    }
    .preview-view-frame:hover, .preview-view-frame.hot {
      border-color: color-mix(in srgb, var(--hg-primary) 45%, transparent);
      background: var(--hg-hover);
    }
    .preview-view-frame.selected {
      border-style: solid; border-color: var(--hg-primary); background: var(--hg-hover);
    }
    .preview-view-hit {
      display: flex; justify-content: space-between; align-items: center; gap: 8px;
      width: 100%; border: 0; background: transparent; font: inherit; color: inherit;
      cursor: pointer; padding: 4px 6px 10px; text-align: left;
    }
    .preview-view-hit .hint { font-size: 0.75rem; color: var(--hg-text-secondary); }
    .section-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .preview-section {
      border: 1px solid var(--hg-divider); border-radius: 14px; padding: 10px;
      background: var(--hg-bg-secondary); cursor: pointer;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
    }
    .preview-section:hover, .preview-section.hot {
      border-color: var(--hg-primary); box-shadow: 0 0 0 3px var(--hg-ring);
      transform: translateY(-1px);
    }
    .preview-section.selected {
      border-color: var(--hg-primary); box-shadow: 0 0 0 3px var(--hg-ring);
    }
    .preview-section-head {
      display: flex; justify-content: space-between; gap: 8px; align-items: center;
      margin-bottom: 8px; font-size: 0.78rem; color: var(--hg-text-secondary);
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .preview-cards { display: grid; gap: 8px; }
    .preview-card {
      display: grid; grid-template-columns: 28px 1fr; gap: 10px; align-items: start;
      text-align: left; width: 100%; border: 1px solid var(--hg-divider); border-radius: 12px;
      padding: 10px 12px; background: var(--hg-card); cursor: pointer; font: inherit;
      color: var(--hg-text);
      transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
    }
    .preview-card:hover, .preview-card.hot {
      border-color: var(--hg-primary); box-shadow: 0 0 0 3px var(--hg-ring);
      transform: translateY(-1px);
    }
    .preview-card.selected {
      border-color: var(--hg-primary); background: var(--hg-hover);
      box-shadow: 0 0 0 3px var(--hg-ring);
    }
    .preview-card strong { display: block; font-size: 0.92rem; color: var(--hg-text); }
    .preview-card .snip {
      display: block; margin-top: 3px; font-size: 0.78rem; color: var(--hg-text-secondary); line-height: 1.35;
    }
    .preview-card .meta {
      display: block; margin-top: 4px; font-size: 0.7rem; color: var(--hg-text-secondary);
    }
    .preview-empty { padding: 28px; text-align: center; color: var(--hg-text-secondary); }
    .vis-pill {
      font-size: 0.65rem; padding: 2px 7px; border-radius: 999px;
      background: color-mix(in srgb, var(--hg-warning) 18%, transparent); color: var(--hg-warning);
    }
    .bind-sheet {
      margin-top: 14px; border: 1px solid color-mix(in srgb, var(--hg-primary) 30%, var(--hg-divider));
      border-radius: 16px; background: var(--hg-card); padding: 16px 16px 14px;
      box-shadow: 0 8px 24px color-mix(in srgb, var(--hg-text) 8%, transparent);
    }
    .bind-sheet h3 {
      margin: 0 0 4px; font-family: var(--hg-font-display); font-size: 1.25rem;
      color: var(--hg-text); font-weight: 500;
    }
    .bind-sheet h4 {
      margin: 0 0 8px; font-family: var(--hg-font-display); font-size: 1.05rem;
      color: var(--hg-text); font-weight: 500; line-height: 1.3;
    }
    .bind-sheet .target-line {
      font-size: 0.88rem; color: var(--hg-text-secondary); margin: 0 0 14px; line-height: 1.4;
    }
    .group-chip-grid { display: flex; flex-wrap: wrap; gap: 8px; }
    .group-chip {
      display: inline-flex; align-items: center; gap: 8px;
      border: 1px solid var(--hg-divider); border-radius: 999px; padding: 8px 14px;
      background: var(--hg-card); cursor: pointer; font: inherit; color: var(--hg-text);
      transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
    }
    .group-chip:hover { border-color: var(--hg-primary); background: var(--hg-hover); }
    .group-chip.on {
      border-color: var(--hg-primary); background: var(--hg-hover-strong);
      box-shadow: 0 0 0 3px var(--hg-ring); color: var(--hg-text); font-weight: 600;
    }
    .group-chip.warn.on {
      border-color: var(--hg-warning);
      background: color-mix(in srgb, var(--hg-warning) 16%, transparent);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--hg-warning) 22%, transparent);
      color: var(--hg-warning);
    }
    .group-chip .dot {
      width: 8px; height: 8px; border-radius: 50%; background: var(--hg-divider);
    }
    .group-chip.on .dot { background: var(--hg-primary); }
    .group-chip.warn.on .dot { background: var(--hg-warning); }
    details.exclude-block {
      margin: 12px 0 4px; border-top: 1px dashed var(--hg-divider); padding-top: 10px;
    }
    details.exclude-block > summary {
      cursor: pointer; color: var(--hg-text-secondary); font-size: 0.88rem; list-style: none;
    }
    details.exclude-block > summary::-webkit-details-marker { display: none; }
    details.exclude-toggle {
      margin: 14px 0 4px;
    }
    details.exclude-toggle > summary {
      list-style: none;
      display: inline-flex; align-items: center; gap: 8px;
      font: inherit; cursor: pointer; user-select: none;
      border: 1px solid var(--hg-divider); border-radius: 999px;
      padding: 9px 16px; background: transparent; color: var(--hg-text);
    }
    details.exclude-toggle > summary::-webkit-details-marker { display: none; }
    details.exclude-toggle > summary::before {
      content: "";
      width: 0.45em; height: 0.45em;
      border-right: 2px solid var(--hg-text-secondary);
      border-bottom: 2px solid var(--hg-text-secondary);
      transform: rotate(-45deg);
      transition: transform 0.15s ease;
    }
    details.exclude-toggle[open] > summary {
      background: var(--hg-hover);
      border-color: color-mix(in srgb, var(--hg-warning) 40%, var(--hg-divider));
    }
    details.exclude-toggle[open] > summary::before {
      transform: rotate(45deg);
    }
    details.exclude-toggle > summary:hover {
      background: var(--hg-hover);
    }
    code {
      font-family: var(--ha-font-family-code, ui-monospace, SFMono-Regular, Menlo, monospace);
      font-size: 0.9em;
    }
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
    this._userSearch = "";
    this._auditDashboard = "";
    this._auditBusy = false;
    this._auditReport = null;
    this._auditExpanded = {};
    this._refreshAuditAfterSave = false;
    this._clipStatus = "";
    this._clipStatusTimer = null;
    this._pasteOpen = false;
    this._pasteDraft = "";
    this._memberSaveSeq = 0;
    this._memberSavePromise = null;
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
          void this._enrichBindingBreadcrumbs();
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
      if (result && (result.groups || result.users)) {
        this._data = result;
        void this._enrichBindingBreadcrumbs();
      }
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

  get _selectedGroup() {
    return this._groups.find((g) => g.id === this._selectedGroupId) || null;
  }



  _locatorsMatch(a = {}, b = {}) {
    const kind = a.kind || b.kind || "card";
    if ((a.kind || "card") !== (b.kind || "card")) return false;
    const pathA = a.view_path || null;
    const pathB = b.view_path || null;
    if (pathA && pathB) {
      if (pathA !== pathB) return false;
    } else if (a.view_index !== b.view_index) {
      return false;
    }
    if (kind === "view") return true;
    if (a.section_index !== b.section_index) return false;
    if (kind === "section") return true;
    if (a.card_index !== b.card_index) return false;
    const nestA = (a.extra && a.extra.nested_path) || a.nested_path || [];
    const nestB = (b.extra && b.extra.nested_path) || b.nested_path || [];
    return JSON.stringify(nestA) === JSON.stringify(nestB);
  }

  async _enrichBindingBreadcrumbs() {
    const bindings = this._data?.bindings || [];
    const missing = bindings.filter((b) => !(b.breadcrumb && String(b.breadcrumb).trim()));
    if (!this.hass) return;
    if (!missing.length) {
      this.requestUpdate();
      return;
    }
    const byDash = {};
    for (const b of missing) {
      const path = b.dashboard_url_path || "lovelace";
      (byDash[path] || (byDash[path] = [])).push(b);
    }
    for (const [path, list] of Object.entries(byDash)) {
      let nodes = [];
      try {
        const res = await this.hass.connection.sendMessagePromise({
          type: `${DOMAIN}/dashboard_nodes`,
          dashboard_url_path: path,
        });
        nodes = res?.nodes || [];
      } catch (_err) {
        continue;
      }
      for (const b of list) {
        const match = nodes.find((n) => this._locatorsMatch(b.locator || {}, n.locator || {}));
        if (match?.breadcrumb) b.breadcrumb = match.breadcrumb;
      }
    }
    this.requestUpdate();
  }


  /** Prefer HA friendly_name when a label looks like domain.object_id. */
  _looksLikeEntityId(text = "") {
    const raw = String(text || "").trim();
    if (!raw || raw.includes(" ") || (raw.match(/\./g) || []).length !== 1) return false;
    const [domain, objectId] = raw.split(".");
    return !!(domain && objectId && /^[a-z0-9_]+$/i.test(domain) && /^[a-z0-9_]+$/i.test(objectId));
  }

  _entityFriendlyName(entityId) {
    const state = this.hass?.states?.[entityId];
    const name = state?.attributes?.friendly_name;
    return (typeof name === "string" && name.trim()) ? name.trim() : "";
  }

  _displayLabel(text = "") {
    const raw = String(text || "").trim();
    if (!raw) return raw;
    if (raw.includes(" › ")) {
      return raw.split(" › ").map((part) => this._displayLabel(part)).join(" › ");
    }
    if (this._looksLikeEntityId(raw)) {
      return this._entityFriendlyName(raw) || raw;
    }
    return raw;
  }

  /** Dashboard title from WS list_dashboards payload; fall back to url_path. */
  _dashboardTitle(urlPath) {
    const path = urlPath || "lovelace";
    const dash = this._dashboards.find((d) => d.url_path === path);
    if (dash?.title) return dash.title;
    if (path === "lovelace") return "Overview";
    return path;
  }

  /** Group friendly name; fall back to id when the group is missing. */
  _groupName(groupId) {
    const g = this._groups.find((x) => x.id === groupId);
    return g?.name || groupId;
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
    this._pasteOpen = false;
    this._pasteDraft = "";
    this._draft = {
      name: "",
      group_id: "",
      description: "",
      icon: "mdi:account-group",
      member_user_ids: [],
    };
    this._userSearch = "";
    this._view = "editor";
  }

  _openEditGroup(group) {
    this._selectedGroupId = group.id;
    this._groupIdManual = true;
    this._iconFilter = "";
    this._iconPickerOpen = false;
    this._pasteOpen = false;
    this._pasteDraft = "";
    this._draft = {
      name: group.name,
      group_id: group.id,
      description: group.description || "",
      icon: group.icon || "mdi:account-group",
      member_user_ids: [...(group.member_user_ids || [])],
    };
    this._userSearch = "";
    this._view = "editor";
  }

  _toggleMember(userId) {
    if (!this._draft) return;
    const set = new Set(this._draft.member_user_ids || []);
    const removing = set.has(userId);
    if (removing) set.delete(userId);
    else set.add(userId);
    this._draft = { ...this._draft, member_user_ids: [...set] };
    void this._persistMembers({
      successMsg: removing ? "Member removed" : "Member added",
    });
  }

  _addMember(userId) {
    if (!this._draft || !userId) return;
    const set = new Set(this._draft.member_user_ids || []);
    if (set.has(userId)) return;
    set.add(userId);
    this._draft = { ...this._draft, member_user_ids: [...set] };
    void this._persistMembers({ successMsg: "Member added" });
  }

  _removeMember(userId) {
    if (!this._draft) return;
    const before = this._draft.member_user_ids || [];
    if (!before.includes(userId)) return;
    this._draft = {
      ...this._draft,
      member_user_ids: before.filter((id) => id !== userId),
    };
    void this._persistMembers({ successMsg: "Member removed" });
  }

  /**
   * Persist membership for an existing group immediately (no full-panel busy).
   * Uses saved group details so unsaved name/description/icon edits stay draft-only.
   * New (unsaved) groups stay local until Save.
   */
  async _persistMembers({ successMsg = "Members saved" } = {}) {
    const groupId = this._selectedGroupId;
    if (!groupId || !this._draft) return false;
    // Full Save owns the write — skip to avoid racing / double-saving.
    if (this._busy) return false;

    const existing = this._groups.find((g) => g.id === groupId);
    if (!existing) return false;

    const seq = ++this._memberSaveSeq;
    const member_user_ids = [...(this._draft.member_user_ids || [])];
    const run = (async () => {
      try {
        const result = await this.hass.connection.sendMessagePromise({
          type: `${DOMAIN}/save_group`,
          name: existing.name,
          group_id: groupId,
          previous_group_id: groupId,
          description: existing.description || "",
          icon: existing.icon || "mdi:account-group",
          member_user_ids,
        });
        if (seq !== this._memberSaveSeq) return false;
        if (result && (result.groups || result.users)) this._data = result;
        this._error = "";
        this._setClipStatus(successMsg);
        return true;
      } catch (err) {
        if (seq !== this._memberSaveSeq) return false;
        this._error = err?.message || String(err);
        this._setClipStatus("Could not save members");
        // Revert membership to last known saved snapshot; keep detail draft edits.
        const saved = (this._data?.groups || []).find((g) => g.id === groupId);
        if (saved && this._draft && this._selectedGroupId === groupId) {
          this._draft = {
            ...this._draft,
            member_user_ids: [...(saved.member_user_ids || [])],
          };
        }
        return false;
      }
    })();
    this._memberSavePromise = run;
    try {
      return await run;
    } finally {
      if (this._memberSavePromise === run) this._memberSavePromise = null;
    }
  }


  _setClipStatus(msg) {
    this._clipStatus = msg || "";
    if (this._clipStatusTimer) clearTimeout(this._clipStatusTimer);
    if (!msg) return;
    this._clipStatusTimer = setTimeout(() => {
      this._clipStatus = "";
      this.requestUpdate();
    }, 2200);
  }

  _parseUserIdsFromText(text) {
    let raw = String(text || "").trim();
    if (!raw) return [];
    if ((raw.startsWith("[") && raw.endsWith("]")) || (raw.startsWith("{") && raw.endsWith("}"))) {
      try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          raw = parsed.map((x) => (typeof x === "string" ? x : x?.id || "")).join("\n");
        } else if (parsed && typeof parsed === "object") {
          const arr = parsed.ids || parsed.users || parsed.member_user_ids || [];
          if (Array.isArray(arr)) {
            raw = arr.map((x) => (typeof x === "string" ? x : x?.id || "")).join("\n");
          }
        }
      } catch (_e) {
        /* fall through to delimiter parse */
      }
    }
    const out = [];
    const seen = new Set();
    for (const part of raw.split(/[\s,;]+/)) {
      const id = part.trim().replace(/^["']|["']$/g, "");
      if (!id || seen.has(id)) continue;
      seen.add(id);
      out.push(id);
    }
    return out;
  }

  async _copyAuditUserIds(userIds) {
    const ids = (userIds || []).filter(Boolean);
    if (!ids.length) {
      this._setClipStatus("Nothing to copy");
      return;
    }
    const text = ids.join("\n");
    const fallbackCopy = () => {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    };
    try {
      let ok = false;
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(text);
          ok = true;
        }
      } catch (_err) {
        ok = false;
      }
      if (!ok) ok = fallbackCopy();
      if (!ok) {
        // Last resort: show prompt so user can copy manually in WebView.
        window.prompt("Copy these user IDs:", text);
      }
      this._setClipStatus(`Copied ${ids.length} ID${ids.length === 1 ? "" : "s"}`);
    } catch (err) {
      this._error = err?.message || "Could not copy user IDs";
    }
  }

  async _readClipboardText() {
    try {
      if (navigator.clipboard?.readText) {
        return await navigator.clipboard.readText();
      }
    } catch (_err) {
      /* HA WebView / insecure context often blocks clipboard read */
    }
    return "";
  }

  _applyMemberIdsFromText(text) {
    if (!this._draft) return 0;
    const ids = this._parseUserIdsFromText(text);
    if (!ids.length) return 0;
    const set = new Set(this._draft.member_user_ids || []);
    let added = 0;
    for (const id of ids) {
      if (!set.has(id)) {
        set.add(id);
        added += 1;
      }
    }
    this._draft = { ...this._draft, member_user_ids: [...set] };
    if (added) {
      void this._persistMembers({
        successMsg: `Added ${added} member${added === 1 ? "" : "s"}`,
      });
    }
    return added;
  }

  async _openPasteBox(prefill = "") {
    this._pasteDraft = prefill || "";
    this._pasteOpen = true;
    this._setClipStatus("Paste IDs into the box, then Apply");
    await this.updateComplete;
    const ta = this.renderRoot?.querySelector?.("#hg-paste-ids");
    if (ta) {
      ta.focus();
      ta.select();
    }
  }

  async _pasteGroupMembers() {
    if (!this._draft) return;
    this._error = "";

    // 1) Silent clipboard read when the browser allows it.
    const clip = (await this._readClipboardText()).trim();
    if (clip && this._parseUserIdsFromText(clip).length) {
      const added = this._applyMemberIdsFromText(clip);
      this._pasteOpen = false;
      this._pasteDraft = "";
      this._setClipStatus(
        added
          ? `Selected ${added} user${added === 1 ? "" : "s"}`
          : "Already selected",
      );
      return;
    }

    // 2) window.prompt — quick path in some Companion WebViews.
    let prompted;
    let promptOk = true;
    try {
      prompted = window.prompt(
        "Paste Home Assistant user IDs (one per line, or comma-separated). Leave blank and OK for the paste box.",
        clip || this._pasteDraft || "",
      );
    } catch (_err) {
      promptOk = false;
      prompted = null;
    }
    if (promptOk && prompted === null) {
      // User cancelled — do not force the textarea.
      return;
    }
    if (typeof prompted === "string" && prompted.trim()) {
      const ids = this._parseUserIdsFromText(prompted);
      if (!ids.length) {
        this._setClipStatus("No user IDs found");
        await this._openPasteBox(prompted);
        return;
      }
      const added = this._applyMemberIdsFromText(prompted);
      this._pasteOpen = false;
      this._pasteDraft = "";
      this._setClipStatus(
        added
          ? `Selected ${added} user${added === 1 ? "" : "s"}`
          : "Already selected",
      );
      return;
    }

    // 3) Textarea — native long-press/Ctrl+V paste works in HA WebView.
    await this._openPasteBox(clip || this._pasteDraft || "");
  }

  _applyPasteMembers() {
    if (!this._draft) return;
    const text = this._pasteDraft || "";
    const ids = this._parseUserIdsFromText(text);
    if (!ids.length) {
      this._setClipStatus("No user IDs found");
      return;
    }
    const added = this._applyMemberIdsFromText(text);
    this._pasteOpen = false;
    this._pasteDraft = "";
    this._error = "";
    this._setClipStatus(
      added
        ? `Selected ${added} user${added === 1 ? "" : "s"}`
        : "Already selected",
    );
  }

  _cancelPasteMembers() {
    this._pasteOpen = false;
    this._pasteDraft = "";
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
    // Let any in-flight membership autosave finish (or be superseded by this write).
    this._memberSaveSeq += 1;
    if (this._memberSavePromise) {
      try {
        await this._memberSavePromise;
      } catch (_err) {
        /* membership error already surfaced; full save continues */
      }
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
    const loc = this._normalizeLocator(node.locator);
    this._bindingDraft = {
      ...this._bindingDraft,
      locator: loc,
      fingerprint: node.fingerprint || "",
      label: this._bindingDraft.label || node.label || "",
      breadcrumb: node.breadcrumb || "",
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
      breadcrumb: "",
      locator: { kind: "card", view_index: 0, section_index: 0, card_index: 0 },
      merge_mode: "ensure_user_branch",
      fingerprint: "",
    };
    this._view = "bindings";
  }


  /** Drop indices that do not apply to the locator kind (section must not keep card_index). */
  _normalizeLocator(loc = {}) {
    const kind = loc.kind || "card";
    const out = { kind };
    if (loc.view_path) out.view_path = loc.view_path;
    if (loc.view_index != null && loc.view_index !== "") out.view_index = Number(loc.view_index);
    else if (!out.view_path) out.view_index = 0;
    // Preserve nested expander/stack/conditional path from audit/picker.
    const nested = (loc.extra && Array.isArray(loc.extra.nested_path))
      ? loc.extra.nested_path
      : (Array.isArray(loc.nested_path) ? loc.nested_path : null);
    if (kind === "view") {
      return out;
    }
    if (loc.section_index != null && loc.section_index !== "") {
      out.section_index = Number(loc.section_index);
    }
    if (kind === "section") {
      return out;
    }
    if (loc.card_index != null && loc.card_index !== "") {
      out.card_index = Number(loc.card_index);
    } else {
      out.card_index = 0;
    }
    if (nested && nested.length) {
      out.extra = { nested_path: nested.map((step) => (step === "card" ? "card" : Number(step))) };
    }
    return out;
  }


  /** Open Set visibility with audit row target preselected (manual → Viz Groups). */
  _openConvertFromAudit(row) {
    if (!row || row.status === "managed") return;
    const loc = row.locator || {};
    const dashboard =
      this._auditDashboard
      || this._auditReport?.dashboard_url_path
      || this._dashboards[0]?.url_path
      || "lovelace";
    this._bindingDraft = {
      binding_id: "",
      dashboard_url_path: dashboard,
      include: [],
      exclude: [],
      label: this._displayLabel(row.label || ""),
      breadcrumb: this._displayLabel(row.breadcrumb || ""),
      locator: this._normalizeLocator(loc),
      merge_mode: "ensure_user_branch",
      fingerprint: row.fingerprint || "",
    };
    this._resetNodeBrowser();
    const title = this._displayLabel(row.label || "") || this._locatorSummary(
      this._bindingDraft.locator,
      this._bindingDraft.fingerprint,
      "",
    );
    this._selectedNodeLabel = title;
    const bits = [];
    if (row.breadcrumb && this._displayLabel(row.breadcrumb) !== title) bits.push(this._displayLabel(row.breadcrumb));
    else {
      const summary = this._locatorSummary(
        this._bindingDraft.locator,
        this._bindingDraft.fingerprint,
        "",
      );
      if (summary && summary !== title) bits.push(summary);
    }
    if (row.type || loc.kind) bits.push(row.type || loc.kind);
    this._selectedNodeSubtitle = bits.join(" · ");
    this._selectedNodeKey = this._nodeKey({
      locator: this._bindingDraft.locator,
      fingerprint: this._bindingDraft.fingerprint,
    });
    this._advancedLocatorOpen = false;
    this._excludeOpen = false;
    this._pickerStep = "groups";
    this._view = "bindings";
    this._error = "";
    this._refreshAuditAfterSave = true;
    this.updateComplete.then(() => {
      const el = this.renderRoot?.querySelector?.(".binding-form");
      el?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    });
  }

  _openEditBinding(binding) {

    const loc = binding.locator || {};
    this._bindingDraft = {
      binding_id: binding.id,
      dashboard_url_path: binding.dashboard_url_path || "lovelace",
      include: [...(binding.expression?.include || [])],
      exclude: [...(binding.expression?.exclude || [])],
      label: this._displayLabel(binding.label || ""),
      breadcrumb: this._displayLabel(binding.breadcrumb || ""),
      locator: this._normalizeLocator(loc),
      merge_mode: binding.merge_mode || "ensure_user_branch",
      fingerprint: binding.fingerprint || "",
    };
    this._resetNodeBrowser();
    const editTitle = this._displayLabel(binding.label || "") || this._locatorSummary(
      this._bindingDraft.locator,
      this._bindingDraft.fingerprint,
      "",
    );
    this._selectedNodeLabel = editTitle;
    const editBits = [];
    const crumb = this._displayLabel(binding.breadcrumb || "");
    if (crumb && crumb !== editTitle) editBits.push(crumb);
    else {
      const summary = this._locatorSummary(this._bindingDraft.locator, this._bindingDraft.fingerprint, "");
      if (summary && summary !== editTitle) editBits.push(summary);
    }
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
    const locator = this._normalizeLocator(d.locator || {});
    const dashboard = d.dashboard_url_path || "lovelace";
    const refreshAudit =
      this._refreshAuditAfterSave
      || (this._auditReport
        && (this._auditReport.dashboard_url_path || this._auditDashboard || "lovelace") === dashboard);
    await this._call("save_binding", {
      binding_id: d.binding_id || undefined,
      dashboard_url_path: dashboard,
      include: d.include,
      exclude: d.exclude || [],
      locator,
      merge_mode: d.merge_mode || "ensure_user_branch",
      fingerprint: d.fingerprint || "",
      label: d.label || "",
      breadcrumb: d.breadcrumb || "",
    });
    this._bindingDraft = null;
    this._refreshAuditAfterSave = false;
    this._resetNodeBrowser?.();
    this._pickerStep = "closed";
    // Re-sync so Lovelace visibility reflects the edit immediately.
    await this._sync(false);
    // After Convert (or any save on the audited dashboard), refresh audit rows.
    if (refreshAudit) {
      this._auditDashboard = dashboard;
      await this._runVisibilityAudit();
    }
  }

  async _deleteBinding(id) {
    if (!confirm("Remove this visibility rule?")) return;
    await this._call("delete_binding", { binding_id: id });
    if (this._bindingDraft?.binding_id === id) this._bindingDraft = null;
  }

  async _sync(dryRun = false) {
    await this._call("sync", { dry_run: dryRun });
  }

  _automationYaml(group) {
    const entity = `sensor.vizgroups_${group.id}`;
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
          <div class="brand">Viz Groups</div>
          <button class="nav-btn ${this._view === "groups" || this._view === "editor" ? "active" : ""}"
            @click=${() => { this._view = "groups"; this._draft = null; this._iconPickerOpen = false; }}>Groups</button>
          <button class="nav-btn ${this._view === "bindings" ? "active" : ""}"
            @click=${() => { this._view = "bindings"; }}>Manage visibility</button>
          <button class="nav-btn ${this._view === "automations" ? "active" : ""}"
            @click=${() => { this._view = "automations"; }}>Conditionals</button>
        </nav>
        <main>
          ${this._error ? html`<div class="error">${this._error}</div>` : nothing}
          ${this._view === "groups" ? this._renderGroups() : nothing}
          ${this._view === "editor" ? this._renderEditor() : nothing}
          ${this._view === "bindings" ? this._renderBindings() : nothing}
          ${this._view === "automations" ? this._renderAutomations() : nothing}
        </main>
      </div>
    `;
  }

  _renderGroups() {
    const groups = this._groups;
    return html`
      <div class="hero">
        <h1>Groups</h1>
        <p>Create user groups, then manage visibility on any dashboard element.</p>
      </div>
      <div class="stat-row">
        <div class="stat"><div class="n">${this._users.length}</div><div class="l">Users</div></div>
        <div class="stat"><div class="n">${groups.length}</div><div class="l">Groups</div></div>
        <div class="stat"><div class="n">${this._bindings.length}</div><div class="l">${this._bindings.length === 1 ? "Dashboard Element Managed" : "Dashboard Elements Managed"}</div></div>
      </div>
      <div class="toolbar">
        <button class="btn btn-primary" ?disabled=${this._busy} @click=${this._openCreateGroup}>New group</button>
        <span class="spacer"></span>
        <button class="btn btn-ghost" ?disabled=${this._busy} @click=${() => this._sync(false)}>Sync now</button>
      </div>
      <div class="panel">
        <table>
          <thead><tr><th>Name</th><th>Members</th></tr></thead>
          <tbody>
            ${groups.length === 0
              ? html`<tr><td colspan="2">No groups yet. Create one to get started.</td></tr>`
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
      </div>
      <div class="layout-3">
        <div class="panel" style="padding:18px">
          <h2 class="section-title">Details</h2>
          <div class="field"><label>Name</label>
            <input .value=${d.name} @input=${this._onNameInput} />
          </div>
          <div class="field"><label>Description</label>
            <textarea rows="3" .value=${d.description}
              @input=${(e) => (this._draft = { ...d, description: e.target.value })}></textarea>
          </div>
          ${this._renderIconPicker()}
          <details class="exclude-block">
            <summary>Advanced</summary>
            <div class="field" style="margin-top:10px"><label>Group ID</label>
              <input
                .value=${d.group_id}
                placeholder=${suggested || "auto-from-name"}
                readonly
              />
            </div>
          </details>
          <div class="toolbar">
            <button class="btn btn-primary" ?disabled=${this._busy} @click=${this._saveGroup}>Save</button>
            <button class="btn btn-ghost" @click=${() => { this._view = "groups"; this._draft = null; this._iconPickerOpen = false; }}>Cancel</button>
            ${editing
              ? html`<span class="spacer"></span>
                  <button class="btn btn-danger" ?disabled=${this._busy} @click=${this._deleteGroup}>Delete</button>`
              : nothing}
          </div>
        </div>

        <div class="panel panel-flush">
          <div class="members-col-head"><h2 class="section-title">Group Members</h2></div>
          <div class="panel-col-body members-body" style="padding:0 8px 12px">
            <ul class="member-list">
              ${(d.member_user_ids || []).length === 0
                ? html`<li style="color:var(--hg-text-secondary)">No members yet — click a user on the right.</li>`
                : (d.member_user_ids || []).map((id) => {
                    const u = this._users.find((x) => x.id === id);
                    return html`<li>
                      <div class="avatar">${this._initials(u?.name || id)}</div>
                      <div class="member-meta">
                        <strong>${u?.name || id}</strong>
                        <span>${id}</span>
                      </div>
                      <div class="row-actions">
                        <button type="button" class="btn btn-danger btn-x has-tip"
                          data-tip="Remove user from group"
                          aria-label="Remove user from group"
                          @click=${() => this._removeMember(id)}>×</button>
                      </div>
                    </li>`;
                  })}
            </ul>
          </div>
        </div>

        <div class="panel panel-flush">
          <div class="editor-col-head">
            <h2 class="section-title">Home Assistant Users</h2>
            <button type="button" class="btn btn-ghost btn-sm has-tip tip-below"
              data-tip="Paste user IDs (clipboard, prompt, or paste box)"
              @click=${this._pasteGroupMembers}>Paste</button>
            ${this._clipStatus && this._view === "editor"
              ? html`<span class="clip-status">${this._clipStatus}</span>`
              : nothing}
          </div>
          ${this._pasteOpen
            ? html`<div class="paste-box">
                <label class="hint" style="display:block;margin:0 0 8px"
                  for="hg-paste-ids">Paste user IDs here (one per line), then Apply. Long-press → Paste works in the Companion app.</label>
                <textarea id="hg-paste-ids"
                  .value=${this._pasteDraft}
                  @input=${(e) => (this._pasteDraft = e.target.value)}
                  placeholder="user-id-1&#10;user-id-2"></textarea>
                <div class="toolbar">
                  <button type="button" class="btn btn-primary btn-sm" @click=${this._applyPasteMembers}>Apply</button>
                  <button type="button" class="btn btn-ghost btn-sm" @click=${this._cancelPasteMembers}>Cancel</button>
                </div>
              </div>`
            : nothing}
          <div class="user-search">
            <input
              type="search"
              placeholder="Filter users…"
              .value=${this._userSearch}
              @input=${(e) => (this._userSearch = e.target.value)}
            />
            <span class="hint" style="display:block;margin-top:8px">${editing
              ? "Click to add — membership saves immediately. Detail fields still use Save."
              : "Click to add a user to the group. Paste selects IDs copied from Visibility audit. Save the group to keep members."}</span>
          </div>
          <div class="user-picker panel-col-body">
            ${this._users
              .filter((u) => !selected.has(u.id))
              .filter((u) => {
                const q = (this._userSearch || "").trim().toLowerCase();
                if (!q) return true;
                return (u.name || "").toLowerCase().includes(q) || (u.id || "").toLowerCase().includes(q);
              })
              .map((u) => html`
                <button type="button" class="user-option"
                  @click=${() => this._addMember(u.id)}>
                  <div class="avatar">${this._initials(u.name)}</div>
                  <div class="member-meta">
                    <strong>${u.name}</strong>
                    <span>${u.id}</span>
                  </div>
                </button>
              `)}
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
          : html`<div style="margin-top:8px">Overview is often empty — pick <strong>Viz Groups Lab</strong>, Main Floor, or another tile with real views. Hard-refresh if a new YAML dashboard just appeared.</div>`}
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
        <strong>${this._displayLabel(card.label)}</strong>
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
          Visibility for <strong>${this._selectedNodeLabel || "selected target"}</strong>
          on <code>${d.dashboard_url_path}</code>.
        </p>
        <div class="field">
          <h4>These groups can see this dashboard element.</h4>
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
        <details class="exclude-toggle" ?open=${this._excludeOpen}
          @toggle=${(e) => (this._excludeOpen = e.target.open)}>
          <summary>Exclude groups</summary>
          <div class="field" style="margin-top:10px">
            <h4>These groups cannot see this dashboard element.</h4>
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
              placeholder="Friendly name for this visibility" />
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
            ${editing ? "Save & sync" : "Save visibility"}
          </button>
          <button class="btn btn-ghost" type="button"
            @click=${() => (this._pickerStep = "preview")}>Select a different element</button>
          <button class="btn btn-ghost" type="button"
            @click=${() => { this._bindingDraft = null; this._refreshAuditAfterSave = false; this._resetNodeBrowser(); }}>Cancel</button>
        </div>
      </div>
    `;
  }

  _renderBindingForm() {
    const d = this._bindingDraft;
    if (!d) return nothing;
    const editing = !!d.binding_id;
    const inGroupsStep = this._pickerStep === "groups";
    return html`<div class="panel binding-form" style="padding:18px;margin-bottom:18px">
      <h2 class="section-title">${editing ? "Edit visibility" : "Set visibility"}</h2>
      <div class="layout-2">
        <div>
          ${this._selectedNodeLabel
            ? html`<div class="selected-node">
                <div class="k">Selected target</div>
                <strong>${this._selectedNodeLabel}</strong>
                <div style="margin-top:6px;font-size:0.8rem;color:var(--muted)">${this._dashboardTitle(d.dashboard_url_path)}</div>
                ${(d.include || []).length
                  ? html`<div class="chip-row" style="margin-top:10px">
                      ${(d.include || []).map((id) => html`<span class="pill">${this._groupName(id)}</span>`)}
                    </div>`
                  : nothing}
                ${(d.exclude || []).length
                  ? html`<div class="chip-row" style="margin-top:6px">
                      ${(d.exclude || []).map((id) => html`<span class="pill warn">not ${this._groupName(id)}</span>`)}
                    </div>`
                  : nothing}
              </div>`
            : html`<div class="hint">Open the visual picker and choose the dashboard, and then dashboard element you want to manage visibility for.</div>`}
          <div class="toolbar" style="margin-top:14px">
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
          ${!inGroupsStep
            ? html`<div class="toolbar" style="margin-top:10px">
                <button class="btn btn-ghost" @click=${() => { this._bindingDraft = null; this._refreshAuditAfterSave = false; this._resetNodeBrowser(); }}>Cancel</button>
              </div>`
            : nothing}
        </div>
        <div>
          ${this._renderLocatorPicker()}
        </div>
      </div>
    </div>`;
  }

  async _runVisibilityAudit() {
    const path = (this._auditDashboard || this._dashboards[0]?.url_path || "lovelace").trim();
    if (!path) {
      this._error = "Pick a dashboard to audit";
      return;
    }
    this._auditDashboard = path;
    this._auditBusy = true;
    this._error = "";
    try {
      const result = await this.hass.connection.sendMessagePromise({
        type: `${DOMAIN}/visibility_audit`,
        dashboard_url_path: path,
      });
      this._auditReport = result || null;
      this._auditExpanded = {};
    } catch (err) {
      this._auditReport = null;
      this._error = err?.message || String(err);
    } finally {
      this._auditBusy = false;
    }
  }

  _renderVisibilityAudit() {
    const dashes = this._dashboards.length
      ? this._dashboards
      : [{ url_path: "lovelace", title: "Overview" }];
    const current = this._auditDashboard || dashes[0]?.url_path || "lovelace";
    const report = this._auditReport;
    const rows = report?.elements || [];
    const summary = report?.summary;
    return html`
      <div class="panel" style="margin-top:18px;padding:18px">
        <h2 class="section-title">Visibility audit</h2>
        <p class="hint" style="margin:0 0 12px">
          Pick a dashboard to list elements that already have people condition visibility. Source will be Viz Groups when visibility is managed by this integration, or Manual Dashboard Config when visibility was set directly on the dashboard.
        </p>
        <div class="toolbar" style="margin:0 0 12px">
          <div class="field" style="margin:0;min-width:220px;flex:1">
            <label>Dashboard</label>
            <select .value=${current}
              @change=${(e) => { this._auditDashboard = e.target.value; this._auditReport = null; this._auditExpanded = {}; }}>
              ${dashes.map((d) => html`<option value=${d.url_path}>${d.title || d.url_path}</option>`)}
            </select>
          </div>
          <button class="btn btn-primary" type="button"
            ?disabled=${this._busy || this._auditBusy}
            @click=${this._runVisibilityAudit}>
            ${this._auditBusy ? "Scanning…" : "Run audit"}
          </button>
        </div>
        ${summary
          ? html`<div class="chip-row" style="margin-bottom:12px">
              <span class="pill">${summary.with_user_visibility} with people visibility</span>
              <span class="pill ok">${summary.managed} Viz Groups</span>
              <span class="pill warn">${summary.outside} Manual Dashboard Config</span>
            </div>`
          : nothing}
        <div class="panel" style="border:0;border-top:1px solid var(--hg-divider);border-radius:0">
          <table>
            <thead>
              <tr>
                <th>Element</th>
                <th>Type</th>
                <th>Home Assistant Users</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              ${!report
                ? html`<tr><td colspan="4">Run an audit to scan this dashboard.</td></tr>`
                : rows.length === 0
                  ? html`<tr><td colspan="4">No elements with people visibility on this dashboard.</td></tr>`
                  : rows.map((row, idx) => {
                      const userIds = row.lovelace_users || [];
                      const rowKey = row.fingerprint
                        || row.binding_id
                        || `${row.label || "row"}-${idx}`;
                      const open = !!this._auditExpanded[rowKey];
                      return html`
                      <tr>
                        <td>
                          <button type="button" class="audit-toggle"
                            aria-expanded=${open ? "true" : "false"}
                            @click=${() => {
                              this._auditExpanded = {
                                ...this._auditExpanded,
                                [rowKey]: !open,
                              };
                            }}>
                            <span class="audit-chevron ${open ? "open" : ""}" aria-hidden="true"></span>
                            <span class="audit-toggle-label">
                              <strong>${this._displayLabel(row.label || "Untitled")}</strong>
                              ${row.breadcrumb && this._displayLabel(row.breadcrumb) !== this._displayLabel(row.label || "")
                                ? html`<div style="font-size:0.8rem;color:var(--hg-text-secondary)">${this._displayLabel(row.breadcrumb)}</div>`
                                : nothing}
                            </span>
                          </button>
                        </td>
                        <td><code>${row.type || row.kind || "—"}</code></td>
                        <td>${userIds.length
                          ? html`<span class="pill">${userIds.length}</span>`
                          : "—"}</td>
                        <td>
                          ${row.status === "managed"
                            ? html`<span class="pill ok has-tip"
                                data-tip=${`Managed by Viz Groups binding ${row.binding_id || ""}${row.binding_label ? ` (${row.binding_label})` : ""}${row.binding_stale ? " — stale" : ""}`}>
                                Viz Groups
                              </span>`
                            : html`<div class="audit-source">
                                <span class="pill warn has-tip"
                                  data-tip="People visibility exists in the dashboard YAML/UI, but no matching Viz Groups binding.">
                                  Manual Dashboard Config
                                </span>
                                <button type="button" class="btn btn-primary btn-sm has-tip"
                                  data-tip="Open Set visibility with this element already selected"
                                  @click=${() => this._openConvertFromAudit(row)}>
                                  Convert
                                </button>
                              </div>`}
                        </td>
                      </tr>
                      ${open
                        ? html`<tr class="audit-detail">
                            <td colspan="4">
                              <div class="audit-users-block">
                                <div class="audit-users-head">
                                  <div class="audit-users-subhead">Home Assistant Users</div>
                                  ${userIds.length
                                    ? html`<button type="button" class="btn btn-ghost btn-sm has-tip"
                                        data-tip="Copy granted user IDs to clipboard"
                                        @click=${() => this._copyAuditUserIds(userIds)}>Copy</button>`
                                    : nothing}
                                  ${this._clipStatus
                                    ? html`<span class="clip-status">${this._clipStatus}</span>`
                                    : nothing}
                                </div>
                                ${userIds.length
                                  ? html`<ul class="audit-users">
                                      ${userIds.map((id) => {
                                        const u = this._users.find((x) => x.id === id);
                                        return html`<li>
                                          <div class="avatar">${this._initials(u?.name || id)}</div>
                                          <div class="member-meta">
                                            <strong>${u?.name || id}</strong>
                                            <span>${id}</span>
                                          </div>
                                        </li>`;
                                      })}
                                    </ul>`
                                  : html`<div class="hint" style="margin:0">No Home Assistant users on this visibility rule.</div>`}
                              </div>
                            </td>
                          </tr>`
                        : nothing}`;
                    })}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

    _renderBindings() {
    return html`
      <div class="hero">
        <h1>Manage visibility</h1>
        <p>You can control access to any dashboard element by setting the visibility on this page.</p>
      </div>
      <div class="toolbar">
        <button class="btn btn-primary" @click=${this._openBindingCreate}>Set visibility</button>
        <span class="spacer"></span>
        <button class="btn btn-ghost has-tip" data-tip="Refreshes the status column."
          ?disabled=${this._busy} @click=${() => this._sync(true)}>Refresh statuses</button>
        <button class="btn btn-ghost has-tip" data-tip="Synchronize visibility settings with dashboards."
          ?disabled=${this._busy} @click=${() => this._sync(false)}>Sync now</button>
      </div>
      ${this._renderBindingForm()}
      <div class="panel">
        <table>
          <thead><tr><th>Element</th><th>Dashboard</th><th>Include</th><th>Exclude</th><th>Status</th><th></th></tr></thead>
          <tbody>
            ${this._bindings.length === 0
              ? html`<tr><td colspan="6">No visibility rules yet.</td></tr>`
              : this._bindings.map(
                  (b) => {
                    const label = this._displayLabel(b.label || b.id);
                    const crumb = this._displayLabel(
                      b.breadcrumb ||
                      this._locatorSummary(b.locator, b.fingerprint, "") ||
                      ""
                    );
                    return html`<tr class="row-click" @click=${() => this._openEditBinding(b)}>
                    <td>
                      <strong>${label}</strong>
                      ${crumb && crumb !== label
                        ? html`<div class="muted" style="font-size:0.8rem;opacity:0.75;margin-top:2px">${crumb}</div>`
                        : nothing}
                    </td>
                    <td>${this._dashboardTitle(b.dashboard_url_path)}</td>
                    <td><div class="chip-row">${(b.expression?.include || []).map((id) => html`<span class="pill">${this._groupName(id)}</span>`)}</div></td>
                    <td><div class="chip-row">${(b.expression?.exclude || []).map((id) => html`<span class="pill warn">${this._groupName(id)}</span>`)}</div></td>
                    <td>${b.stale ? html`<span class="pill warn">stale</span>` : html`<span class="pill ok">OK</span>`}</td>
                    <td>
                      <div class="row-actions" @click=${(e) => e.stopPropagation()}>
                        <button class="btn btn-ghost btn-sm" @click=${() => this._openEditBinding(b)}>Edit</button>
                        <button class="btn btn-danger btn-sm" @click=${() => this._deleteBinding(b.id)}>Remove</button>
                      </div>
                    </td>
                  </tr>`;
                  })}
          </tbody>
        </table>
      </div>
      ${this._renderVisibilityAudit()}
    `;
  }

  _renderAutomations() {
    const g = this._groups[0];
    return html`
      <div class="hero">
        <h1>Conditionals</h1>
        <p>As an advanced feature, you can use membership in a group or non-membership in a group as a condition to your automations and scripts.</p>
      </div>
      ${g
        ? html`<div class="yaml-block">${this._automationYaml(g)}</div>`
        : html`<div class="callout">Create a group first to preview the template.</div>`}
      <div class="panel" style="margin-top:18px;padding:18px">
        <h2 class="section-title">All group sensors</h2>
        <div>
          ${this._groups.map((group) => {
            const entityId = `sensor.vizgroups_${group.id}`;
            const memberIds = (group.members || []).map((m) => m.id).filter(Boolean);
            const ids = memberIds.length ? memberIds : (group.member_user_ids || []);
            const names = (group.members || []).map((m) => m.name || m.id).filter(Boolean);
            const count = group.member_count ?? ids.length;
            return html`<div class="sensor-item">
              <strong>${group.name}</strong>
              <div class="sensor-entity"><code>${entityId}</code></div>
              <details class="sensor-more">
                <summary>More attributes</summary>
                <ul class="sensor-attrs">
                  <li><span class="k">State</span><span class="v">${count} (member count)</span></li>
                  <li><span class="k">Group ID</span><span class="v"><code>${group.id}</code></span></li>
                  <li><span class="k">Members</span><span class="v">${ids.length ? ids.join(", ") : "—"}</span></li>
                  <li><span class="k">Member names</span><span class="v">${names.length ? names.join(", ") : "—"}</span></li>
                  <li><span class="k">Description</span><span class="v">${group.description || "—"}</span></li>
                  <li><span class="k">Icon</span><span class="v"><code>${group.icon || "mdi:account-group"}</code></span></li>
                </ul>
              </details>
            </div>`;
          })}
        </div>
      </div>
    `;
  }
}

if (!customElements.get("vizgroups-panel")) {
  customElements.define("vizgroups-panel", VizGroupsPanel);
} else {
  // Soft-reload / cache-bust: keep existing element class.
}

