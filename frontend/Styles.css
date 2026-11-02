/* mnm44: base styles for the app screens (login, the check flow, letters, pricing, account).
   the new look + colors are further down this file and override the colors */
:root {
  --slate: #213B3F;
  --slate-2: #2D4C51;
  --slate-ink: #142629;
  --mist: #EEF3F2;
  --mist-2: #F6F9F8;
  --paper: #FFFFFF;
  --ink: #1A2B2E;
  --muted: #52666A;
  --line: #D3DDDC;
  --line-strong: #A9BAB9;
  --marker: #F6E05E;
  --marker-soft: #FCF3BF;
  --teal: #2F7F76;
  --danger: #B42318;
  --danger-soft: #FDECEA;
  --offwhite: #F9F9F9;
  --on-slate: #BCD0CF;
  --ring: 0 0 0 3px rgba(47, 127, 118, .45);
  --display: "Crimson Pro", Georgia, "Times New Roman", serif;
  --body: "Lexend", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  --pen: "Caveat", "Comic Sans MS", cursive;
  --print: 4px 4px 0 var(--slate-ink);
}

*, *::before, *::after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; font-family: var(--body); font-size: 1rem; line-height: 1.65;
  color: var(--ink); background: var(--paper);
  min-height: 100vh; display: flex; flex-direction: column; overflow-x: clip;
}
main { flex: 1; width: 100%; }
img, svg { display: block; flex: none; }
a { color: var(--teal); text-underline-offset: 3px; }
h1, h2, h3 { font-family: var(--display); font-weight: 600; line-height: 1.08; margin: 0 0 .4em; color: var(--slate); letter-spacing: -.01em; }
h1 { font-size: clamp(2.7rem, 6.4vw, 4.6rem); font-weight: 600; }
h2, .h2 { font-size: clamp(1.9rem, 3.8vw, 2.6rem); }
h3, .h3 { font-size: 1.45rem; }
.h2, .h3 { font-family: var(--display); font-weight: 600; color: var(--slate); }
p { margin: 0 0 1em; }

.container { max-width: 1120px; margin: 0 auto; padding: 0 24px; }
.narrow { max-width: 640px; }
.sr-only { position: absolute !important; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
[hidden], .hidden { display: none !important; }
:focus-visible { outline: 3px solid var(--teal); outline-offset: 2px; }
h1[tabindex="-1"]:focus, h2[tabindex="-1"]:focus { outline: none; }
.skip-link { position: absolute; left: 12px; top: -80px; z-index: 200; background: var(--marker); color: var(--slate-ink); padding: 10px 16px; font-weight: 700; }
.skip-link:focus { top: 12px; }
.muted { color: var(--muted); }
.small { font-size: .92rem; }
.big { font-size: 1.15rem; }
.no-margin { margin: 0 !important; }
.row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.auto-width { width: auto !important; }

/* ---------- Header: the logo's slate block ---------- */
.site-header { position: sticky; top: 0; z-index: 60; background: var(--slate); color: var(--offwhite); }
.header-bar { display: flex; align-items: center; gap: 16px; min-height: 68px; }
.brand {
  background: none; border: 0; padding: 4px 0; cursor: pointer;
  font-family: var(--display); font-weight: 500; font-size: 1.85rem; letter-spacing: .01em; color: var(--offwhite); line-height: 1;
}
.public-nav, .app-nav { display: flex; align-items: center; gap: 2px; margin-left: auto; }
.header-user { display: flex; align-items: center; gap: 6px; }
.nav-link, .app-nav button {
  display: inline-flex; align-items: center; gap: 8px; background: none; border: 0; cursor: pointer; white-space: nowrap;
  font: inherit; font-size: .98rem; color: var(--on-slate); padding: 10px 14px; min-height: 44px; position: relative;
}
.nav-link svg, .app-nav svg { width: 20px; height: 20px; }
.nav-link:hover, .app-nav button:hover { color: #fff; }
.nav-link[aria-current="page"], .app-nav button[aria-current="page"] { color: #fff; }
.nav-link[aria-current="page"]::after, .app-nav button[aria-current="page"]::after {
  content: ""; position: absolute; left: 14px; right: 14px; bottom: 4px; height: 3px; background: var(--marker);
}
.site-header .btn-primary { background: var(--marker); color: var(--slate-ink); box-shadow: none; }
.site-header .btn-primary:hover { background: #FAE97F; }
#user-email { max-width: 180px; overflow: hidden; text-overflow: ellipsis; }
.header-user .badge { background: var(--slate-2); color: var(--offwhite); }
.header-user .badge-brand { background: var(--marker); color: var(--slate-ink); }
.show-sm { display: none !important; }

/* ---------- Buttons ---------- */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; white-space: nowrap;
  font: inherit; font-weight: 600; font-size: 1rem; line-height: 1.2;
  padding: 12px 22px; min-height: 48px; border: 2px solid transparent; border-radius: 0; cursor: pointer;
  transition: transform .1s, box-shadow .1s, background-color .15s, border-color .15s;
}
.btn-sm { min-height: 40px; padding: 8px 16px; font-size: .95rem; }
.btn-block { width: 100%; }
.btn-primary { background: var(--slate); color: var(--offwhite); border-color: var(--slate-ink); box-shadow: var(--print); }
.btn-primary:hover:not(:disabled) { background: var(--slate-2); }
.btn-primary:active:not(:disabled) { transform: translate(3px, 3px); box-shadow: 1px 1px 0 var(--slate-ink); }
.btn-secondary { background: var(--paper); color: var(--slate); border-color: var(--slate); }
.btn-secondary:hover:not(:disabled) { background: var(--mist-2); }
.btn-quiet { background: transparent; color: var(--teal); padding-left: 10px; padding-right: 10px; text-decoration: underline; text-underline-offset: 4px; text-decoration-thickness: 1.5px; }
.btn-quiet:hover:not(:disabled) { color: var(--slate); }
.btn-danger { background: var(--paper); color: var(--danger); border-color: var(--danger); }
.btn-danger:hover:not(:disabled) { background: var(--danger-soft); }
.btn-oauth { background: var(--paper); color: var(--ink); border: 1.5px solid var(--line-strong); }
.btn-oauth:hover { border-color: var(--slate); }
.btn-oauth svg { width: 20px; height: 20px; }
.btn:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }
.link-btn { background: none; border: 0; padding: 0; cursor: pointer; font: inherit; color: var(--teal); text-decoration: underline; text-underline-offset: 3px; }
.spinner { width: 18px; height: 18px; border-radius: 50%; display: inline-block; border: 2.5px solid currentColor; border-right-color: transparent; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.badge { display: inline-flex; align-items: center; padding: 3px 12px; border-radius: 999px; font-size: .82rem; font-weight: 600; background: var(--mist); color: var(--slate); }
.badge-brand { background: var(--marker); color: var(--slate-ink); }

/* ---------- Surfaces ---------- */
.view { padding: 44px 0 96px; }
.view-home, .view-team { padding: 0; }
.panel { background: var(--paper); border: 1.5px solid var(--line); padding: 28px; }
.center-card { text-align: center; max-width: 520px; margin: 0 auto; padding: 44px 28px; border-top: 6px solid var(--slate); }

/* ---------- Forms ---------- */
.field { margin-bottom: 16px; }
.field > label, .legend { display: block; font-weight: 600; margin-bottom: 6px; padding: 0; }
.hint { font-size: .92rem; color: var(--muted); margin: 6px 0 0; }
input[type="text"], input[type="email"], input[type="password"], input[type="number"], input[type="date"], select, textarea {
  width: 100%; font: inherit; font-size: 1rem; color: var(--ink); background: var(--paper);
  border: 1.5px solid var(--line-strong); border-radius: 0; padding: 11px 14px; min-height: 48px;
}
input:focus, select:focus, textarea:focus { outline: none; border-color: var(--slate); box-shadow: var(--ring); }
input:disabled, select:disabled { background: var(--mist-2); color: var(--muted); }
textarea { min-height: 300px; resize: vertical; line-height: 1.65; }
.form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 0 14px; }
.form-error { color: var(--danger); font-weight: 600; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.check { display: flex; align-items: flex-start; gap: 12px; cursor: pointer; margin: 4px 0 18px; }
.check input { width: 22px; height: 22px; margin: 1px 0 0; accent-color: var(--slate); flex: none; cursor: pointer; }
.pw-wrap { position: relative; }
.pw-wrap input { padding-right: 84px; }
.pw-toggle { position: absolute; right: 4px; top: 4px; }

.pill-group { display: flex; flex-wrap: wrap; gap: 8px; }
.pill-option { position: relative; }
.pill-option input { position: absolute; opacity: 0; width: 100%; height: 100%; margin: 0; cursor: pointer; }
.pill-option span {
  display: inline-flex; align-items: center; justify-content: center; min-width: 64px; min-height: 46px; padding: 8px 20px;
  border: 1.5px solid var(--line-strong); border-radius: 999px; background: var(--paper); cursor: pointer;
}
.pill-option:hover span { border-color: var(--slate); }
.pill-option input:checked + span { background: var(--slate); border-color: var(--slate); color: var(--offwhite); font-weight: 600; }
.pill-option input:focus-visible + span { box-shadow: var(--ring); }

/* Segmented control: square tabs with an underline, not a rounded pill tray */
.segmented { display: flex; gap: 0; margin-bottom: 20px; border-bottom: 1.5px solid var(--line); }
.segmented label, .segmented > button { flex: 1; position: relative; }
.segmented input { position: absolute; opacity: 0; }
.segmented span, .segmented > button {
  display: block; text-align: center; padding: 12px; min-height: 46px; margin-bottom: -1.5px;
  font: inherit; font-weight: 600; font-size: .98rem; color: var(--muted); cursor: pointer; background: none; border: 0;
  border-bottom: 3px solid transparent;
}
.segmented input:checked + span, .segmented > button[aria-selected="true"] { color: var(--slate); border-bottom-color: var(--slate); }
.segmented input:focus-visible + span { box-shadow: var(--ring); }
.money-input { display: flex; align-items: center; gap: 8px; max-width: 220px; }
.money-input span { font-weight: 600; color: var(--muted); }

/* ---------- Auth ---------- */
.auth-wrap { max-width: 460px; margin: 0 auto; padding: 34px; border: 2px solid var(--slate); box-shadow: 10px 10px 0 var(--mist); }
.oauth { display: grid; gap: 10px; }
.divider { display: flex; align-items: center; gap: 12px; color: var(--muted); margin: 20px 0; }
.divider::before, .divider::after { content: ""; flex: 1; height: 1px; background: var(--line); }
.notice-box { padding: 12px 14px; background: var(--marker-soft); color: var(--slate-ink); border-left: 4px solid var(--marker); }

/* ---------- App views ---------- */
#view-check, #view-letters, #view-results, #view-pricing, #view-account, #view-auth { background: var(--mist-2); min-height: calc(100vh - 68px); }
.flow-top { margin-bottom: 34px; }
.stepper { list-style: none; margin: 0; padding: 0; display: flex; gap: 4px; }
.stepper li { flex: 1; min-width: 0; }
.stepper .step { display: flex; flex-direction: column; gap: 8px; width: 100%; padding: 4px 0; background: none; border: 0; font: inherit; text-align: left; color: var(--muted); cursor: default; }
.stepper .bar { height: 5px; background: var(--line); }
.stepper .label { font-size: .9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stepper li.done .bar { background: var(--teal); }
.stepper li.current .bar { background: var(--slate); }
.stepper li.current .label { color: var(--slate); font-weight: 600; }
.stepper li.done .step:not(:disabled) { cursor: pointer; }
.stepper li.done .step:not(:disabled):hover .label { color: var(--slate); text-decoration: underline; }
.flow-meta { display: flex; align-items: center; gap: 12px; margin-top: 6px; min-height: 40px; }
.step-count { display: none; margin: 0; font-weight: 600; }
#btn-start-over { margin-left: auto; }
@media (max-width: 640px) { .stepper .label { display: none; } .step-count { display: block; } }

.step-head { margin-bottom: 28px; max-width: 640px; }
.step-head p { color: var(--muted); font-size: 1.1rem; margin: 0; }
.step-actions { display: flex; gap: 14px; align-items: center; margin-top: 32px; flex-wrap: wrap; }
.step-actions .btn-primary { margin-left: auto; }
@media (max-width: 600px) {
  .step-actions { flex-direction: column-reverse; align-items: stretch; }
  .step-actions .btn { width: 100%; }
  .step-actions .btn-primary { margin-left: 0; }
  .step-actions .link-btn { align-self: center; padding: 8px; }
}

/* Upload */
.upload-layout { display: grid; grid-template-columns: 1.6fr 1fr; gap: 0; align-items: stretch; border: 2px solid var(--slate); background: var(--paper); }
.upload-layout .panel { border: 0; border-right: 2px solid var(--slate); }
.dropzone { border: 2px dashed var(--line-strong); background: var(--mist-2); margin-bottom: 18px; transition: border-color .15s, background-color .15s; }
.dropzone:hover, .dropzone.is-over, .dropzone:focus-within { border-color: var(--slate); background: var(--marker-soft); }
.dropzone:focus-within { box-shadow: var(--ring); }
.dropzone-inner { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 46px 16px; cursor: pointer; text-align: center; }
.dropzone-inner svg { width: 42px; height: 42px; color: var(--slate); margin-bottom: 10px; }
.dz-title { font-family: var(--display); font-weight: 600; font-size: 1.7rem; color: var(--slate); line-height: 1.1; }
.dz-sub { color: var(--muted); }
.file-name { display: flex; align-items: center; gap: 8px; font-weight: 600; background: var(--marker-soft); color: var(--slate-ink); padding: 10px 14px; margin: 0 0 14px; word-break: break-all; border-left: 4px solid var(--marker); }
.status { margin: 12px 0 0; color: var(--muted); }
.status:empty { display: none; }
.privacy-line { display: flex; gap: 8px; align-items: flex-start; margin: 20px 0 0; color: var(--muted); font-size: .95rem; }
.privacy-line svg { margin-top: 3px; color: var(--teal); }
.upload-side { display: flex; flex-direction: column; }
.side-option { display: block; width: 100%; flex: 1; text-align: left; font: inherit; cursor: pointer; color: var(--ink); background: var(--paper); border: 0; border-bottom: 1px solid var(--line); padding: 26px 28px; }
.side-option:last-child { border-bottom: 0; }
.side-option:hover { background: var(--mist-2); }
.side-option strong { display: block; font-family: var(--display); font-weight: 600; font-size: 1.45rem; color: var(--slate); margin-bottom: 2px; }
.side-option span { color: var(--muted); }
@media (max-width: 760px) {
  .upload-layout { grid-template-columns: 1fr; }
  .upload-layout .panel { border-right: 0; border-bottom: 2px solid var(--slate); }
}

/* Charges: one printed bill with rows */
.bill-sheet { background: var(--paper); border: 1px solid var(--line); padding: 28px 30px 24px; box-shadow: 10px 10px 0 rgba(33, 59, 63, .1); }
.bill-meta { padding-bottom: 8px; border-bottom: 2px solid var(--ink); margin-bottom: 4px; }
.line-list { display: flex; flex-direction: column; }
.line-card { padding: 14px 0; border-bottom: 1px dashed var(--line-strong); }
.line-main { display: grid; grid-template-columns: auto 1fr auto; gap: 16px; align-items: start; }
.code-chip {
  display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 5px 12px;
  font: inherit; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--slate);
  background: var(--mist); border: 1.5px solid transparent; border-radius: 999px; cursor: pointer;
}
.code-chip:hover { border-color: var(--slate); background: var(--marker-soft); }
.code-chip svg { width: 15px; height: 15px; }
.line-title { font-weight: 600; overflow-wrap: anywhere; }
.line-plain { color: var(--muted); }
.line-amt { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.line-amt strong { display: block; font-size: 1.08rem; }
.line-math { font-size: .9rem; color: var(--muted); }
.line-tools { display: flex; gap: 2px; justify-content: flex-end; margin-top: 4px; }
.line-tools .btn { min-height: 34px; padding: 4px 10px; font-size: .9rem; }
.line-edit { margin-top: 12px; padding: 16px; background: var(--mist-2); border-left: 4px solid var(--slate); }
.line-edit .form-row { grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }
.line-edit .span-2 { grid-column: span 2; }
.add-line { margin-top: 10px; }
.totals-bar { margin-top: 14px; padding-top: 16px; border-top: 2px solid var(--ink); display: flex; flex-wrap: wrap; gap: 8px 36px; align-items: flex-end; }
.total-item span { display: block; font-size: .9rem; color: var(--muted); }
.total-item strong { font-size: 1.3rem; font-variant-numeric: tabular-nums; }
.totals-note { flex-basis: 100%; margin: 4px 0 0; }
@media (max-width: 560px) {
  .bill-sheet { padding: 18px 16px; }
  .line-main { grid-template-columns: auto 1fr; }
  .line-amt { grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: baseline; text-align: left; }
  .line-edit .span-2 { grid-column: 1 / -1; }
}

/* Highlighter marks */
mark, .flag-kind { background: linear-gradient(100deg, transparent 2%, var(--marker) 4% 96%, transparent 98%); color: var(--slate-ink); font-weight: 600; padding: 1px 6px; }

/* Questions */
.q-list { display: flex; flex-direction: column; gap: 14px; }
.question { background: var(--paper); border: 1.5px solid var(--line); border-left: 4px solid var(--slate); padding: 22px 24px; }
.question legend { float: left; width: 100%; font-weight: 600; font-size: 1.08rem; padding: 0; margin-bottom: 4px; }
.question legend + * { clear: both; }
.question .hint { margin: 0 0 14px; }
.question input[type="number"] { max-width: 160px; }
.survey-more { margin-top: 14px; }

/* Flags */
/* mnm44: the cards on the review step that say what looks off */
.flag-summary { font-family: var(--display); font-weight: 600; font-size: 1.6rem; color: var(--slate); margin-bottom: 16px; }
.flag-list { display: flex; flex-direction: column; gap: 14px; }
.flag-card { background: var(--paper); border: 1.5px solid var(--line); padding: 22px 24px; position: relative; }
.flag-card::before { content: ""; position: absolute; left: -1.5px; top: -1.5px; bottom: -1.5px; width: 6px; background: var(--marker); }
.flag-kind { display: inline; font-size: 1rem; }
.flag-msg { margin: 12px 0 12px; font-size: 1.05rem; }
.flag-lines { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.flag-line { font-size: .9rem; background: var(--mist); border-radius: 999px; padding: 4px 12px; font-variant-numeric: tabular-nums; }
.flag-actions { display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: center; justify-content: space-between; border-top: 1px dashed var(--line); padding-top: 12px; }
.flag-actions .check { margin: 0; font-weight: 600; }
.flag-card.is-dismissed { background: transparent; border-style: dashed; }
.flag-card.is-dismissed::before { background: var(--line); }
.flag-card.is-dismissed .flag-kind { background: none; color: var(--muted); padding: 0; }
.flag-card.is-dismissed .flag-msg { color: var(--muted); text-decoration: line-through; text-decoration-color: var(--line-strong); }
.flag-tag { font-weight: 400; color: var(--muted); margin-left: 8px; }
.tools-card { margin-top: 26px; border: 1.5px dashed var(--line-strong); padding: 20px 24px; }
.tools-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.tools-head h3 { font-size: 1.35rem; }
.tools-card select { min-height: 40px; padding: 6px 12px; }
.table-wrap { overflow-x: auto; margin-top: 14px; border: 1px solid var(--line); background: var(--paper); }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); }
tr:last-child td { border-bottom: 0; }
th { font-size: .9rem; color: var(--muted); background: var(--mist-2); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
tr.is-high td { background: var(--marker-soft); }
.explain-list { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; }
.explain-item { background: var(--paper); padding: 12px 14px; border: 1px solid var(--line); }
.loading { color: var(--muted); font-style: italic; margin-top: 12px; }

/* Letter */
.letter-grid { display: grid; grid-template-columns: .9fr 1.1fr; gap: 24px; align-items: start; }
.paper-letter { background: var(--paper); border: 1px solid var(--line); padding: 28px 30px; box-shadow: 10px 10px 0 rgba(33, 59, 63, .1); }
.paper-letter textarea { border-style: dashed; }
.sub-head { margin-top: 24px; font-size: 1.3rem; }
.letter-flag-items { list-style: none; padding: 0; margin: 0 0 10px; display: flex; flex-direction: column; gap: 8px; }
.letter-flag-items li { background: var(--mist-2); border-left: 4px solid var(--marker); padding: 10px 12px; }
.letter-flag-items strong { display: block; }
.item-row { background: var(--mist-2); padding: 14px 14px 2px; margin-bottom: 10px; border-left: 4px solid var(--slate); }
.item-row .row { justify-content: space-between; margin-bottom: 8px; }
@media (max-width: 860px) { .letter-grid { grid-template-columns: 1fr; } }

/* Pricing / results / account */
.price-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; max-width: 820px; border: 2px solid var(--slate); }
.price-grid .panel { border: 0; }
.price-grid .panel + .panel { border-left: 2px solid var(--slate); }
.price { font-family: var(--display); font-size: 3.4rem; font-weight: 600; color: var(--slate); margin: 4px 0 12px; line-height: 1; }
.price small { font-family: var(--body); font-size: 1rem; color: var(--muted); font-weight: 400; }
.price-card-paid { background: var(--mist-2) !important; }
.check-list { list-style: none; padding: 0; margin: 0 0 24px; }
.check-list li { position: relative; padding: 7px 0 7px 30px; border-bottom: 1px dashed var(--line); }
.check-list li::before { content: ""; position: absolute; left: 6px; top: 13px; width: 7px; height: 12px; border: solid var(--teal); border-width: 0 2.5px 2.5px 0; transform: rotate(45deg); }
@media (max-width: 700px) { .price-grid { grid-template-columns: 1fr; } .price-grid .panel + .panel { border-left: 0; border-top: 2px solid var(--slate); } }
.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; margin-top: 24px; border: 1.5px solid var(--slate); }
.stat { padding: 22px; border-right: 1px solid var(--line); }
.stat:last-child { border-right: 0; }
.stat strong { display: block; font-family: var(--display); font-weight: 600; font-size: 3rem; line-height: 1; color: var(--slate); font-variant-numeric: tabular-nums; margin-bottom: 6px; }
.stat span { color: var(--muted); }
.target { margin-top: 16px; font-weight: 600; }
.target.met { color: var(--teal); }
.target.not-met { color: var(--danger); }
@media (max-width: 640px) { .stat-grid { grid-template-columns: 1fr; } .stat { border-right: 0; border-bottom: 1px solid var(--line); } }
#account-detail .card { background: var(--paper); border: 1.5px solid var(--line); padding: 24px; }
.account-row { display: flex; justify-content: space-between; gap: 12px; padding: 12px 0; border-bottom: 1px dashed var(--line); }
.account-row:last-of-type { border-bottom: 0; }
.danger-zone { margin-top: 16px; border-left: 4px solid var(--danger) !important; }

.done-mark { width: 64px; height: 64px; border-radius: 50%; background: var(--marker); margin: 0 auto 16px; position: relative; }
.done-mark::after { content: ""; position: absolute; left: 23px; top: 13px; width: 14px; height: 26px; border: solid var(--slate-ink); border-width: 0 4px 4px 0; transform: rotate(45deg); }

/* Drawer, dialog, toast */
.drawer-backdrop { position: fixed; inset: 0; background: rgba(20, 38, 41, .45); z-index: 80; }
.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(440px, 100%); z-index: 90; background: var(--paper); border-left: 2px solid var(--slate); display: flex; flex-direction: column; transform: translateX(100%); transition: transform .25s ease; }
.drawer.is-open { transform: none; }
.drawer-head, .dialog-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px; background: var(--slate); }
.drawer-head h2, .dialog-head h2 { color: var(--offwhite); }
.drawer-head .icon-btn, .dialog-head .icon-btn { color: var(--offwhite); }
.drawer-body { padding: 22px; overflow-y: auto; flex: 1; }
.icon-btn { width: 44px; height: 44px; border-radius: 50%; border: 0; background: transparent; color: var(--ink); cursor: pointer; display: inline-flex; align-items: center; justify-content: center; flex: none; }
.icon-btn:hover { background: rgba(255, 255, 255, .12); }
.lookup-result { margin-top: 22px; background: var(--mist-2); border-left: 6px solid var(--marker); padding: 18px 20px; }
.lookup-result .meta { font-size: .9rem; color: var(--muted); }
.lookup-result p { margin: 8px 0 0; font-family: var(--display); font-size: 1.45rem; line-height: 1.25; color: var(--slate); }
dialog { border: 2px solid var(--slate); padding: 0; width: calc(100% - 32px); max-width: 620px; color: var(--ink); }
dialog::backdrop { background: rgba(20, 38, 41, .5); }
.dialog-body { padding: 20px 24px 24px; max-height: 70vh; overflow-y: auto; }
.dialog-body ol { padding-left: 20px; }
.dialog-body li { margin-bottom: 10px; }
#toast { position: fixed; left: 50%; bottom: 24px; z-index: 120; transform: translate(-50%, 16px); opacity: 0; pointer-events: none; background: var(--slate); color: var(--offwhite); padding: 12px 20px; font-weight: 600; max-width: calc(100% - 32px); text-align: center; transition: opacity .2s, transform .2s; box-shadow: 4px 4px 0 var(--marker); }
#toast.show { opacity: 1; transform: translate(-50%, 0); }
#toast.err { background: var(--danger); box-shadow: 4px 4px 0 var(--slate-ink); }

.site-footer { background: var(--slate); color: var(--on-slate); padding: 44px 0; font-size: .95rem; }
.site-footer .link-btn { color: var(--offwhite); }

/* Phones */
@media (max-width: 760px) {
  .hide-sm { display: none !important; }
  .show-sm { display: inline-flex !important; }
  .header-bar { gap: 8px; }
  .header-user { margin-left: auto; }
  .app-nav { position: fixed; left: 0; right: 0; bottom: 0; z-index: 70; margin: 0; gap: 0; justify-content: space-around; background: var(--slate); padding: 4px 4px calc(4px + env(safe-area-inset-bottom)); }
  .app-nav button { flex: 1; flex-direction: column; gap: 2px; font-size: .7rem; padding: 8px 2px; }
  .app-nav button[aria-current="page"]::after { top: 0; bottom: auto; left: 20%; right: 20%; }
  body.logged-in { padding-bottom: 72px; }
  body.logged-in #toast { bottom: 92px; }
  .view { padding-top: 28px; }
  .view-home, .view-team { padding-top: 0; }
  .panel, .question, .flag-card { padding: 20px; }
  .auth-wrap { padding: 24px; box-shadow: none; }
  .container { padding: 0 18px; }
}
@media (max-width: 520px) {
  .brand { font-size: 1.6rem; }
  .public-nav .btn-sm { padding: 8px 14px; }
  .public-nav .nav-link { padding: 10px 8px; }
}

/* mnm44: turns off ALL animations for ppl who ask their device for less motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}


/* Number questions: "Not sure" pill beside the field */
.num-row { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.num-row input[type="number"] { max-width: 160px; margin: 0; }
.num-row input[type="number"]:disabled { opacity: .45; }
/* Sample bill settings (from the old "Try a demo bill" page) */
.sample-opts { padding: 14px 28px 22px; font-size: .92rem; }
.sample-opts summary { cursor: pointer; color: var(--teal); font-weight: 600; padding: 6px 0; }
.sample-opts label:not(.check) { display: block; margin: 10px 0 6px; font-weight: 600; }
.sample-opts input[type="number"] { max-width: 120px; }
.sample-opts .check { margin: 12px 0 4px; }


/* mnm44: the whole new look lives here. inspired by studio-noun.com (grain, giant wordmark,
   sliding cards, glass box, big menu) but in our beige, green and black.
   rule of thumb: boxes holding stuff are square, buttons you tap are round */
:root {
  --beige: #EFE8D9;
  --beige-2: #E5DCC8;
  --cream: #FAF6EE;
  --black: #121511;
  --night: #18211B;
  --forest: #1F3B2D;
  --green: #2E5A43;
  --sage: #A7BFA2;
  --sage-pale: #C9D8C2;
  --ochre: #DDB65F;
  --clay: #B9643A;
  --hh: 64px;

  /* mnm44: the app screens use these old names, i just pointed them at the new colors */
  --slate: #1F3B2D;
  --slate-2: #2E5A43;
  --slate-ink: #121511;
  --mist: #E5DCC8;
  --mist-2: #F1EBDD;
  --paper: #FAF6EE;
  --ink: #161A14;
  --muted: #595D51;
  --line: #D7CDB7;
  --line-strong: #A99F88;
  --marker: #E6C76F;
  --marker-soft: #F3E6BF;
  --teal: #2E5A43;
  --offwhite: #EFE8D9;
  --on-slate: #CFC7B4;
  --ring: 0 0 0 3px rgba(46, 90, 67, .35);
  --display: "Inter Tight", "Helvetica Neue", Arial, sans-serif;
  --body: "Inter Tight", "Helvetica Neue", Arial, sans-serif;
  --serif: "Instrument Serif", Georgia, "Times New Roman", serif;
  --print: none;
  --ease: cubic-bezier(.2, .7, .2, 1);
}

/* ---------- Base ---------- */
body { background: var(--beige); color: var(--ink); font-family: var(--body); font-size: 1.0625rem; letter-spacing: -.005em; line-height: 1.6; }
h1, h2, h3, .h2, .h3 { font-family: var(--display); font-weight: 500; letter-spacing: -.035em; color: var(--ink); line-height: 1.02; }
h1 { font-size: clamp(2.4rem, 5vw, 4rem); }
h2, .h2 { font-size: clamp(1.8rem, 3.4vw, 2.6rem); }
h3, .h3 { font-size: 1.4rem; letter-spacing: -.02em; }
a { color: var(--green); text-underline-offset: 4px; text-decoration-thickness: 1px; }
:focus-visible { outline: 2px solid var(--green); outline-offset: 3px; }
mark { background: var(--marker-soft); color: inherit; padding: 0 .15em; }
.skip-link { background: var(--black); color: var(--beige); }
.muted { color: var(--muted); }

.wide { width: 100%; max-width: 1680px; margin: 0 auto; padding-left: clamp(16px, 2.6vw, 40px); padding-right: clamp(16px, 2.6vw, 40px); }
.cap { font-size: .78rem; font-weight: 500; letter-spacing: .08em; text-transform: uppercase; line-height: 1.5; margin: 0; color: inherit; }
.cap.dim, .dim { opacity: .72; }
.cap-body { font-size: .92rem; font-weight: 400; letter-spacing: .045em; text-transform: uppercase; line-height: 1.6; margin: 0; max-width: 46ch; }
.cap-body em { font-family: var(--serif); font-style: italic; text-transform: none; font-size: 1.35em; letter-spacing: 0; }

/* mnm44: the little film grain over the whole site. pointer-events none so it never blocks clicks */
.grain {
  position: fixed; inset: -50%; width: 200%; height: 200%; z-index: 300; pointer-events: none; opacity: .16;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 1.4 -.45'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  animation: grain 1s steps(6) infinite;
}
@keyframes grain {
  0% { transform: translate(0, 0); } 20% { transform: translate(-3%, 2%); } 40% { transform: translate(2%, -4%); }
  60% { transform: translate(-4%, -1%); } 80% { transform: translate(3%, 3%); } 100% { transform: translate(0, 0); }
}

/* Tick bars */
.ticks { display: inline-flex; gap: 3px; height: 14px; align-items: stretch; flex: none; }
.ticks i { width: 1px; background: currentColor; opacity: .3; transition: opacity .2s; }
.ticks i.on { opacity: 1; }
.nh-checks .ticks i { animation: tick 2.6s ease-in-out infinite; animation-delay: calc(var(--i) * 70ms); }
@keyframes tick { 0%, 100% { opacity: .25; } 35% { opacity: 1; } }

/* ---------- Buttons ---------- */
.btn { border-radius: 999px; border: 1px solid transparent; box-shadow: none; font-family: var(--body); font-weight: 500; letter-spacing: .01em; min-height: 48px; padding: 12px 26px; transition: background-color .2s, color .2s, transform .2s var(--ease); }
.btn:active:not(:disabled) { transform: scale(.98); }
.btn-sm { min-height: 40px; padding: 8px 18px; font-size: .95rem; }
.btn-primary { background: var(--forest); color: var(--beige); border-color: transparent; box-shadow: none; }
.btn-primary:hover:not(:disabled) { background: var(--green); }
.btn-primary:active:not(:disabled) { box-shadow: none; }
.btn-light { background: var(--beige); color: var(--black); }
.btn-light:hover { background: #FFFDF7; }
.btn-dark { background: var(--black); color: var(--beige); }
.btn-dark:hover { background: var(--forest); }
.btn-secondary { background: transparent; color: var(--ink); border-color: var(--ink); }
.btn-secondary:hover:not(:disabled) { background: var(--ink); color: var(--beige); }
.btn-quiet { color: var(--green); text-decoration-thickness: 1px; }
.btn-quiet:hover:not(:disabled) { color: var(--ink); }
.btn-oauth { border: 1px solid var(--line-strong); background: var(--cream); }
.btn-oauth:hover { border-color: var(--ink); }
.text-link {
  display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 8px 0; border: 0; background: none; color: inherit; cursor: pointer;
  font: inherit; font-size: .82rem; font-weight: 500; letter-spacing: .08em; text-transform: uppercase;
  text-decoration: underline; text-underline-offset: 7px; text-decoration-thickness: 1px;
}
.text-link:hover { text-decoration-thickness: 2px; }
.text-link .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; display: inline-block; }

/* ---------- Header ---------- */
.site-header { position: sticky; top: 0; z-index: 60; background: rgba(239, 232, 217, .88); color: var(--ink); backdrop-filter: blur(14px) saturate(1.1); -webkit-backdrop-filter: blur(14px) saturate(1.1); border-bottom: 1px solid transparent; transition: background-color .35s, color .35s, border-color .35s; }
.site-header.is-scrolled { border-bottom-color: var(--line); }
.site-header .header-bar { max-width: 1680px; min-height: var(--hh); padding-left: clamp(16px, 2.6vw, 40px); padding-right: clamp(16px, 2.6vw, 40px); }
.site-header.is-over-hero { background: transparent; color: var(--beige); border-bottom-color: transparent; backdrop-filter: none; -webkit-backdrop-filter: none; }
.brand { font-family: var(--body); font-weight: 500; font-size: 1.6rem; letter-spacing: -.055em; color: inherit; text-transform: lowercase; padding: 6px 0; background: none; border: 0; cursor: pointer; line-height: 1; }
.nav-link, .app-nav button { color: inherit; font-size: .8rem; font-weight: 500; letter-spacing: .07em; text-transform: uppercase; opacity: .8; }
.nav-link:hover, .app-nav button:hover, .nav-link[aria-current="page"], .app-nav button[aria-current="page"] { color: inherit; opacity: 1; }
.nav-link[aria-current="page"]::after, .app-nav button[aria-current="page"]::after { background: currentColor; height: 1px; }
.site-header .btn-primary { background: var(--forest); color: var(--beige); }
.site-header .btn-primary:hover { background: var(--green); }
.site-header.is-over-hero .btn-primary { background: var(--beige); color: var(--black); }
.header-user .badge { background: transparent; color: inherit; border: 1px solid currentColor; opacity: .8; }
.header-user .badge-brand { background: var(--ochre); color: var(--black); border-color: var(--ochre); opacity: 1; }
.menu-btn {
  width: auto; height: auto; min-height: 44px; min-width: 44px; padding: 8px 2px 8px 10px; margin-left: 10px; border: 0; background: none; color: inherit; cursor: pointer;
  font: inherit; font-size: .9rem; font-weight: 500; letter-spacing: .06em; text-transform: uppercase;
}
.menu-btn:hover { opacity: .7; }

/* mnm44: pulls the hero up under the header so the green runs all the way to the top */
#view-home { margin-top: calc(-1 * var(--hh)); }

/* ---------- Home: hero ---------- */
/* No photos for now: the hero, gallery and panels use soft gradients in the brand colours. */
.nh { position: relative; isolation: isolate; overflow: hidden; min-height: 100svh; display: flex; flex-direction: column; color: var(--beige); background: var(--night); padding-top: calc(var(--hh) + 18px); }
.nh-bg {
  position: absolute; inset: -8%; z-index: -1; transform: scale(1.15); will-change: transform;
  background:
    radial-gradient(45% 55% at 28% 38%, rgba(214, 190, 140, .75), transparent 70%),
    radial-gradient(40% 50% at 78% 62%, rgba(58, 104, 76, .85), transparent 70%),
    radial-gradient(55% 45% at 60% 10%, rgba(18, 21, 17, .9), transparent 70%),
    linear-gradient(rgba(24, 33, 27, .35), rgba(18, 21, 17, .55)),
    var(--night);
  filter: blur(34px) saturate(.9);
}
.nh-bg::after {
  content: ""; position: absolute; inset: 0;
  background: radial-gradient(35% 40% at 50% 50%, rgba(167, 191, 162, .35), transparent 70%);
  animation: drift 18s ease-in-out infinite alternate;
}
@keyframes drift { from { transform: translate(-18%, -6%); } to { transform: translate(22%, 12%); } }
.nh-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; padding-top: 18px; }
.nh-tag { margin-left: 18vw; }
.nh-clock { font-size: 1rem; letter-spacing: .02em; text-transform: none; }
.nh-mid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(260px, 400px); gap: 32px 6vw; align-items: end; margin-top: auto; padding-top: 9vh; }
.nh-title { color: var(--beige); font-weight: 400; font-size: clamp(2.3rem, 4.6vw, 4.6rem); letter-spacing: -.045em; line-height: .98; max-width: 15ch; margin: 0; }
.nh-side { display: grid; gap: 22px; padding-bottom: 6px; }
.nh-cta { display: flex; flex-wrap: wrap; align-items: center; gap: 14px 26px; }
.nh-checks { margin-top: 7vh; }
.nh-checks-head { display: flex; align-items: center; gap: 14px; margin-bottom: 26px; }
.nh-check-list { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 0 16px; }
.nh-check-list button {
  display: grid; gap: 10px; width: 100%; text-align: left; background: none; border: 0; color: inherit; cursor: pointer; padding: 8px 0;
  font: inherit; font-size: .78rem; font-weight: 500; letter-spacing: .08em; text-transform: uppercase; opacity: .85; transition: opacity .2s, transform .3s var(--ease);
}
.nh-check-list button span { font-size: .8rem; opacity: .6; }
.nh-check-list button:hover { opacity: 1; transform: translateY(-3px); }
.nh-word { width: calc(100% - 2 * clamp(16px, 2.6vw, 40px)); height: auto; margin: 2vh auto -1.2vw; overflow: visible; pointer-events: none; }
.nh-word text, .foot-word text { font-family: var(--body); font-weight: 500; font-size: 240px; letter-spacing: -.04em; }
.nh-word text { fill: var(--sage-pale); }

/* ---------- Home: about table ---------- */
.ninfo { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); gap: 48px 8vw; padding-top: clamp(80px, 14vh, 160px); padding-bottom: clamp(40px, 8vh, 90px); }
.ninfo-left { display: grid; gap: 22px; align-content: start; }
.ninfo-left .cap-body { margin-top: 20px; }
.ninfo-table { margin: 0; display: grid; align-content: start; }
.ninfo-table div { display: grid; grid-template-columns: 150px 1fr; gap: 20px; padding: 14px 0; border-top: 1px solid var(--line); }
.ninfo-table div:last-child { border-bottom: 1px solid var(--line); }
.ninfo-table dt { font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); font-weight: 500; }
.ninfo-table dd { margin: 0; font-size: .86rem; letter-spacing: .06em; text-transform: uppercase; }

/* ---------- Home: split statements ---------- */
.nsay { display: grid; grid-template-columns: 1fr 1fr; align-items: end; gap: 24px; padding-top: clamp(50px, 10vh, 120px); padding-bottom: clamp(60px, 12vh, 140px); }
.nsay-l, .nsay-r { margin: 0; font-size: clamp(3rem, 9.6vw, 9.4rem); font-weight: 400; letter-spacing: -.055em; line-height: .86; text-transform: uppercase; color: var(--green); }
.nsay-r { text-align: right; }
.nsay-src { grid-column: 1 / -1; margin-top: 14px; }
.nsay-src a { color: inherit; }
.nsay-dark { max-width: none; background: var(--night); }
.nsay-dark .nsay-l, .nsay-dark .nsay-r { color: var(--sage); }

/* ---------- Home: why list (like an awards list) ---------- */
.nlist { padding-bottom: clamp(70px, 12vh, 140px); }
.nlist-rows { list-style: none; margin: 18px 0 0; padding: 0; border-top: 1px solid var(--line); }
.nlist-rows li { display: grid; grid-template-columns: minmax(0, 1fr) minmax(200px, 360px) 120px; gap: 24px; align-items: center; padding: 20px 0; border-bottom: 1px solid var(--line); position: relative; }
.nlist-rows li::before { content: ""; position: absolute; left: 0; right: 0; bottom: -1px; height: 1px; background: var(--ink); transform: scaleX(0); transform-origin: left; transition: transform .6s var(--ease); }
.nlist-rows li:hover::before { transform: scaleX(1); }
.nlist-big { margin: 0; font-size: clamp(1.9rem, 4.6vw, 4.2rem); font-weight: 400; letter-spacing: -.045em; line-height: .95; text-transform: uppercase; transition: transform .45s var(--ease), color .3s; }
.nlist-rows li:hover .nlist-big { transform: translateX(14px); color: var(--green); }
.nlist-meta, .nlist-year { margin: 0; font-size: .78rem; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); }
.nlist-year { text-align: right; }
.nlist-year a { color: inherit; }
.nlist-cta { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 18px 30px; margin-top: 44px; }

/* ---------- Home: sideways gallery ---------- */
/* mnm44: the section is extra tall on purpose, scrolling thru it is what slides the cards */
.ngal { position: relative; background: var(--night); color: var(--beige); }
.ngal-pin { position: sticky; top: 0; height: 100vh; height: 100svh; overflow: hidden; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; padding: calc(var(--hh) + 14px) 0 26px; }
.ngal-title { margin: 0; padding: 0 clamp(16px, 2.6vw, 40px); color: var(--sage-pale); font-size: clamp(2.2rem, 4.8vw, 4.4rem); font-weight: 400; letter-spacing: -.045em; text-transform: uppercase; line-height: 1; }
.ngal-window { min-height: 0; display: flex; align-items: center; overflow: hidden; }
.ngal-track { list-style: none; margin: 0; display: flex; align-items: center; gap: clamp(28px, 5vw, 96px); padding: 0 clamp(20px, 8vw, 140px) 0 38vw; will-change: transform; transform-origin: center; }
.ngal-card { flex: none; width: clamp(210px, 20vw, 320px); transition: transform .8s var(--ease); }
.ngal-card:nth-child(3n+1) { transform: translateY(9%) rotate(-1.4deg); }
.ngal-card:nth-child(3n+2) { transform: translateY(-11%) rotate(1deg); }
.ngal-card:nth-child(3n) { transform: translateY(4%) rotate(.5deg); }
.frame-card { margin: 0; padding: 12px; border: 1px solid rgba(239, 232, 217, .2); background: rgba(239, 232, 217, .02); transition: border-color .4s; }
.ngal-card.is-active .frame-card { border-color: rgba(239, 232, 217, .55); }
.ngal-img { aspect-ratio: 4 / 5; display: flex; align-items: flex-end; padding: 14px 16px; background: radial-gradient(70% 60% at 30% 25%, rgba(214, 190, 140, .35), transparent 70%), linear-gradient(150deg, #3A5A47, #1E2A22); }
.ngal-card:nth-child(2) .ngal-img { background: radial-gradient(70% 60% at 70% 30%, rgba(167, 191, 162, .4), transparent 70%), linear-gradient(160deg, #2C4436, #141A15); }
.ngal-card:nth-child(3) .ngal-img { background: radial-gradient(70% 60% at 40% 70%, rgba(221, 182, 95, .3), transparent 70%), linear-gradient(140deg, #34503F, #18211B); }
.ngal-card:nth-child(4) .ngal-img { background: radial-gradient(70% 60% at 65% 65%, rgba(214, 190, 140, .3), transparent 70%), linear-gradient(170deg, #263B2F, #121511); }
.ngal-card:nth-child(5) .ngal-img { background: radial-gradient(70% 60% at 25% 70%, rgba(167, 191, 162, .35), transparent 70%), linear-gradient(130deg, #3A5A47, #18211B); }
.ngal-card:nth-child(6) .ngal-img { background: radial-gradient(70% 60% at 75% 25%, rgba(221, 182, 95, .28), transparent 70%), linear-gradient(155deg, #2E4A3A, #141A15); }
.ngal-img span { font-family: var(--serif); font-style: italic; font-size: clamp(4rem, 7vw, 6.5rem); line-height: .8; color: var(--beige); opacity: .85; }
.frame-card figcaption { margin-top: 12px; }
.frame-card figcaption i { font-family: var(--serif); font-size: 1.05rem; letter-spacing: 0; margin-right: 4px; }
.ngal-card-text { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.ngal-foot { display: flex; justify-content: space-between; align-items: flex-end; gap: 30px; padding: 0 clamp(16px, 2.6vw, 40px); }
.ngal-cap { text-align: right; max-width: 430px; }
.ngal-cap p { margin: 0; }
.ngal-name { font-family: var(--serif); font-size: clamp(2.1rem, 3.4vw, 3.3rem); line-height: 1; letter-spacing: -.01em; margin: 6px 0 10px !important; color: var(--beige); }
.ngal-text { font-size: .98rem; line-height: 1.5; opacity: .88; }
.ngal-ex { margin-top: 10px !important; font-size: .95rem; color: var(--ochre); }
.ngal-ex .cap { color: var(--beige); opacity: .7; margin-right: 6px; }
.ngal-cap.swap > * { animation: capIn .55s var(--ease) both; }
.ngal-cap.swap > *:nth-child(2) { animation-delay: .05s; }
.ngal-cap.swap > *:nth-child(3) { animation-delay: .1s; }
.ngal-cap.swap > *:nth-child(4) { animation-delay: .15s; }
@keyframes capIn { from { opacity: 0; transform: translateY(12px); filter: blur(4px); } to { opacity: 1; transform: none; filter: none; } }
.ngal.is-static .ngal-pin { position: static; height: auto; padding-bottom: 40px; }
.ngal.is-static .ngal-window { overflow-x: auto; scroll-snap-type: x mandatory; padding: 40px 0; }
.ngal.is-static .ngal-track { padding-left: clamp(16px, 2.6vw, 40px); }
.ngal.is-static .ngal-card { transform: none; scroll-snap-align: start; }
.ngal.is-static .ngal-card-text { position: static; width: auto; height: auto; clip: auto; white-space: normal; display: block; margin-top: 8px; font-size: .92rem; line-height: 1.5; }

/* ---------- Home: turning glass box ---------- */
.nbox { position: relative; height: 420vh; color: var(--beige); background: radial-gradient(70% 60% at 72% 45%, #2C4A38 0%, #1A2820 55%, var(--night) 100%); }
.nbox-pin { position: sticky; top: 0; height: 100vh; height: 100svh; overflow: hidden; }
.nbox-side { position: absolute; left: clamp(16px, 2.6vw, 40px); top: calc(var(--hh) + 16px); display: grid; gap: 12px; z-index: 2; }
.vticks { display: grid; gap: 5px; margin-bottom: 18px; }
.vticks i { display: block; height: 1px; width: calc(10px + var(--w, 0) * 34px); background: currentColor; opacity: calc(.35 + var(--w, 0) * .65); transition: width .3s var(--ease); }
.nbox-side h2 { color: inherit; }
.nbox-stage { position: absolute; inset: 0; display: grid; place-items: center; perspective: 1500px; perspective-origin: 50% 45%; }
.nbox-cube { --h: clamp(230px, 36vh, 330px); position: relative; width: min(660px, 84vw); height: var(--h); transform-style: preserve-3d; }
.nbox-face {
  position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: space-between; gap: 18px;
  padding: 9% 7%; background: rgba(239, 232, 217, .08); border: 1px solid rgba(239, 232, 217, .38);
  transform: rotateX(calc(var(--k) * -90deg)) translateZ(calc(var(--h) / 2)); backface-visibility: visible;
  opacity: .14; transition: opacity .45s;
}
.nbox-face:nth-child(1) { --k: 0; } .nbox-face:nth-child(2) { --k: 1; } .nbox-face:nth-child(3) { --k: 2; } .nbox-face:nth-child(4) { --k: 3; }
.nbox-face.is-front { opacity: 1; }
.nbox-face::before { content: ""; position: absolute; inset: 6% 3.5%; border: 1px solid rgba(239, 232, 217, .22); pointer-events: none; }
.nbox-face::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'%3E%3Cpath d='M0 0L3.5 6M100 0L96.5 6M0 100L3.5 94M100 100L96.5 94' stroke='%23EFE8D9' stroke-opacity='.3' stroke-width='1' vector-effect='non-scaling-stroke' fill='none'/%3E%3C/svg%3E") 0 0 / 100% 100%;
}
.nbox-face h3 { margin: 0; font-family: var(--serif); font-style: italic; font-weight: 400; font-size: clamp(1.9rem, 3.2vw, 2.8rem); letter-spacing: -.01em; color: var(--beige); }
.nbox-face p { margin: 0; font-size: clamp(1rem, 1.3vw, 1.15rem); line-height: 1.55; max-width: 48ch; color: rgba(239, 232, 217, .92); }
.nbox-index { position: absolute; left: 0; right: 0; bottom: 22px; list-style: none; margin: 0; padding: 0 clamp(16px, 2.6vw, 40px); display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; z-index: 2; }
.nbox-index li:nth-child(n+2) { text-align: center; }
.nbox-index li:last-child { text-align: right; }
.nbox-index button { background: none; border: 0; color: inherit; cursor: pointer; padding: 10px 0; min-height: 44px; font: inherit; font-size: .78rem; font-weight: 500; letter-spacing: .08em; text-transform: uppercase; opacity: .55; transition: opacity .3s; }
.nbox-index button i { font-family: var(--serif); font-size: 1.05rem; letter-spacing: 0; text-transform: none; margin-right: 8px; }
.nbox-index button[aria-current], .nbox-index button:hover { opacity: 1; }
.nbox.is-static { height: auto; }
.nbox.is-static .nbox-pin { position: static; height: auto; padding: calc(var(--hh) + 30px) 0 60px; }
.nbox.is-static .nbox-side { position: static; padding: 0 clamp(16px, 2.6vw, 40px); margin-bottom: 30px; }
.nbox.is-static .vticks, .nbox.is-static .nbox-index { display: none; }
.nbox.is-static .nbox-stage { position: static; display: block; perspective: none; }
.nbox.is-static .nbox-cube { height: auto; margin: 0 auto; display: grid; gap: 18px; transform: none !important; }
.nbox.is-static .nbox-face { position: relative; transform: none; opacity: 1; min-height: 230px; }

/* ---------- Home: what you get back ---------- */
.ncases { padding-top: clamp(80px, 14vh, 160px); background: var(--beige); }
.ncases > h2 { margin-bottom: 8vh; }
.ncase { position: relative; }
.ncase-head { position: sticky; top: 26vh; z-index: 0; display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 20px; align-items: start; }
.ncase-meta { list-style: none; margin: 0; padding: 6px 0 0; display: grid; gap: 12px; color: var(--green); font-weight: 600; }
.ncase-title { margin: 0; color: var(--green); font-size: clamp(2.6rem, 7.6vw, 7.4rem); font-weight: 400; letter-spacing: -.055em; line-height: .9; text-transform: uppercase; }
.ncase-media { position: relative; z-index: 1; margin-top: 28vh; min-height: 100vh; min-height: 100svh; overflow: hidden; color: var(--beige); background: var(--night); }
.ncase-media::before {
  content: ""; position: absolute; inset: 0;
  background: radial-gradient(60% 70% at 25% 30%, rgba(214, 190, 140, .28), transparent 70%), radial-gradient(55% 60% at 80% 75%, rgba(167, 191, 162, .22), transparent 70%), linear-gradient(150deg, #2E4A3A, #16201A);
}
.ncase-inner { position: relative; min-height: 100vh; min-height: 100svh; display: flex; align-items: center; justify-content: flex-end; padding-top: 80px; padding-bottom: 80px; }

/* Code and language card */
.lang-card { width: 100%; max-width: 460px; padding: 30px; color: var(--beige); background: rgba(18, 21, 17, .72); border: 1px solid rgba(239, 232, 217, .25); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); display: grid; gap: 18px; }
.lang-row { display: flex; flex-wrap: wrap; gap: 8px; }
.code-pick { min-height: 40px; padding: 6px 16px; border-radius: 999px; border: 1px solid rgba(239, 232, 217, .45); background: transparent; color: var(--beige); font: inherit; font-size: .92rem; cursor: pointer; letter-spacing: .04em; }
.code-pick[aria-checked="true"] { background: var(--beige); color: var(--black); border-color: var(--beige); }
.lang-out { margin: 4px 0; font-family: var(--serif); font-size: clamp(1.7rem, 2.6vw, 2.2rem); line-height: 1.12; min-height: 2.3em; }
.lang-tabs { gap: 18px; border-top: 1px solid rgba(239, 232, 217, .22); padding-top: 12px; }
.lang-tabs button { background: none; border: 0; color: var(--beige); opacity: .65; cursor: pointer; padding: 8px 0; min-height: 40px; font: inherit; font-size: .82rem; letter-spacing: .08em; text-transform: uppercase; }
.lang-tabs button[aria-checked="true"] { opacity: 1; text-decoration: underline; text-underline-offset: 7px; }

/* Product example */
.review-mock { width: min(440px, 100%); margin: 0; background: var(--cream); color: var(--ink); border: 1px solid var(--line); box-shadow: 0 40px 80px -40px rgba(0, 0, 0, .6); }
.mock-bar { display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; background: var(--black); color: var(--beige); }
.mock-brand { font-weight: 500; letter-spacing: -.04em; font-size: 1.1rem; }
.mock-step { font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; opacity: .75; }
.mock-title { margin: 18px 18px 8px; font-family: var(--serif); font-size: 1.7rem; line-height: 1; }
.mock-flag { margin: 0 18px; padding: 14px 0 14px 14px; border-top: 1px solid var(--line); position: relative; }
.mock-flag::before { content: ""; position: absolute; left: 0; top: 14px; bottom: 14px; width: 3px; background: var(--ochre); }
.mock-flag p { margin: 2px 0 8px; font-size: .92rem; color: var(--muted); }
.mock-kind { display: inline-block; font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; font-weight: 600; background: var(--marker-soft); padding: 2px 8px; margin-bottom: 6px; }
.mock-line { display: flex; justify-content: space-between; gap: 12px; font-size: .98rem; }
.mock-check { display: flex; align-items: center; gap: 8px; font-size: .88rem; font-weight: 500; }
.mock-check .box { width: 16px; height: 16px; border-radius: 3px; background: var(--forest); position: relative; }
.mock-check .box::after { content: ""; position: absolute; left: 5px; top: 2px; width: 4px; height: 8px; border: solid var(--beige); border-width: 0 2px 2px 0; transform: rotate(45deg); }
.mock-flag.is-faded { opacity: .5; }
.mock-flag.is-faded::before { background: var(--line-strong); }
.mock-caption { margin: 0; padding: 12px 18px 16px; font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); border-top: 1px solid var(--line); }

/* Letter demo */
.ask-card { width: 100%; max-width: 460px; padding: 30px; background: var(--cream); color: var(--ink); border: 1px solid var(--line); box-shadow: 0 40px 80px -40px rgba(0, 0, 0, .6); }
.ask-list { border: 0; margin: 0 0 8px; padding: 0; }
.ask-list legend { margin-bottom: 14px; padding: 0; }
.ask-list .check { margin: 0 0 10px; font-weight: 500; }
.demo-letter { border-top: 1px solid var(--line); padding-top: 16px; font-family: var(--serif); font-size: 1.25rem; line-height: 1.35; }
.demo-letter p { margin: 0 0 8px; }
.demo-letter ul { margin: 0; padding-left: 1.1em; }
.demo-letter li { margin-bottom: 6px; }
.demo-letter .muted { font-family: var(--body); font-size: .95rem; list-style: none; margin-left: -1.1em; }

/* Closing */
.ncta { background: var(--forest); color: var(--beige); padding: clamp(90px, 16vh, 180px) 0; }
.ncta-inner { display: grid; gap: 40px; }
.nsay-pair { margin: 0; display: flex; flex-direction: column; color: var(--beige); font-size: clamp(2.6rem, 7.6vw, 7.4rem); font-weight: 400; letter-spacing: -.055em; line-height: .9; text-transform: uppercase; }
.nsay-pair span:last-child { align-self: flex-end; text-align: right; color: var(--sage-pale); }
.ncta .btn { justify-self: end; }

/* ---------- Footer ---------- */
.site-footer { background: var(--black); color: var(--beige); padding: 56px 0 30px; font-size: .9rem; }
.foot-nav { display: flex; align-items: center; gap: 18px; }
.foot-nav button { background: none; border: 0; color: inherit; cursor: pointer; padding: 10px 0; min-height: 44px; font: inherit; font-size: 1rem; letter-spacing: .02em; text-transform: uppercase; white-space: nowrap; opacity: .9; }
.foot-nav button:hover { opacity: 1; text-decoration: underline; text-underline-offset: 6px; text-decoration-thickness: 1px; }
.foot-nav span { flex: 1; height: 1px; background: rgba(239, 232, 217, .22); }
.foot-word { width: 100%; height: auto; margin: 20px 0 10px; overflow: visible; pointer-events: none; }
.foot-word text { fill: var(--sage); opacity: .35; }
.foot-cta { text-align: center; margin: 0 0 18px; }
.site-footer .disclaimer-text, .foot-copy { text-align: center; max-width: 760px; margin: 0 auto 10px; color: rgba(239, 232, 217, .72); font-size: .82rem; }
.foot-copy { margin-top: 18px; }

/* ---------- Full-screen menu ---------- */
.menu-backdrop { background: transparent; }
.site-menu {
  position: fixed; inset: 0; z-index: 120; width: auto; max-width: none; height: auto; transform: none; border: 0; border-radius: 0; box-shadow: none;
  display: flex; flex-direction: column; padding: 0 clamp(16px, 2.6vw, 40px); background: var(--night); color: var(--beige);
  clip-path: inset(0 0 100% 0); transition: clip-path .22s ease-in;
}
.site-menu.is-open { clip-path: inset(0 0 0 0); transition: clip-path .6s var(--ease); }
.menu-head { min-height: var(--hh); padding: 0; border: 0; display: flex; justify-content: space-between; align-items: center; }
.menu-head .brand { cursor: default; }
.menu-head .menu-btn { margin: 0; }
.menu-body { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) min(26vw, 360px); gap: 40px; align-items: center; overflow-y: auto; padding: 2vh 0; }
.menu-list { list-style: none; margin: 0; padding: 0; counter-reset: m; overflow: visible; }
.menu-list li:not([hidden]) { counter-increment: m; }
.menu-list button {
  display: flex; align-items: baseline; gap: clamp(14px, 2.6vw, 34px); width: auto; padding: 2px 0; background: none; border: 0; color: var(--sage-pale); cursor: pointer; text-align: left;
  font: inherit; font-size: clamp(1.9rem, 6.6vh, 4.8rem); font-weight: 400; letter-spacing: -.045em; line-height: 1.04; text-transform: uppercase; transition: color .25s, transform .4s var(--ease);
}
.menu-list button::before { content: "(" counter(m, decimal-leading-zero) ")"; position: static; width: 2.6rem; flex: none; background: none; font-size: .72rem; letter-spacing: .06em; color: var(--beige); opacity: .7; transform: translateY(-.9em); }
.menu-list button:hover, .menu-list button:focus-visible { color: var(--beige); transform: translateX(10px); }
.menu-list button:hover::before { content: "(" counter(m, decimal-leading-zero) ")"; position: static; top: auto; bottom: auto; width: 2.6rem; background: none; }
.site-menu.is-open .menu-list li { animation: menuIn .7s var(--ease) both; }
.site-menu.is-open .menu-list li:nth-child(2) { animation-delay: .04s; } .site-menu.is-open .menu-list li:nth-child(3) { animation-delay: .08s; }
.site-menu.is-open .menu-list li:nth-child(4) { animation-delay: .12s; } .site-menu.is-open .menu-list li:nth-child(5) { animation-delay: .16s; }
.site-menu.is-open .menu-list li:nth-child(6) { animation-delay: .2s; } .site-menu.is-open .menu-list li:nth-child(7) { animation-delay: .24s; }
.site-menu.is-open .menu-list li:nth-child(8) { animation-delay: .28s; } .site-menu.is-open .menu-list li:nth-child(9) { animation-delay: .32s; }
.site-menu.is-open .menu-list li:nth-child(10) { animation-delay: .36s; } .site-menu.is-open .menu-list li:nth-child(11) { animation-delay: .4s; }
@keyframes menuIn { from { opacity: 0; transform: translateY(40%); } to { opacity: 1; transform: none; } }
.menu-preview { margin: 0; align-self: center; }
.menu-img { aspect-ratio: 4 / 5; border: 1px solid rgba(239, 232, 217, .25); padding: 10px; background-clip: content-box; background-image: radial-gradient(70% 60% at 30% 30%, rgba(214, 190, 140, .32), transparent 70%), linear-gradient(150deg, #3A5A47, #1E2A22); }
.menu-img.swap { animation: imgIn .5s var(--ease); }
.menu-img { display: flex; align-items: flex-end; }
.menu-img span { padding: 18px 20px; font-family: var(--serif); font-style: italic; font-size: clamp(2rem, 3vw, 3rem); line-height: 1; color: var(--beige); }
@keyframes imgIn { from { opacity: .3; transform: scale(.97); } to { opacity: 1; transform: none; } }
.menu-preview figcaption { display: flex; justify-content: space-between; margin-top: 10px; font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; opacity: .75; }
.menu-foot { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px 30px; padding: 16px 0 22px; border-top: 1px solid rgba(239, 232, 217, .18); }
.menu-foot > div { display: flex; }
.menu-auth { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 26px; }

/* ---------- Floating sign-up pill + progress ---------- */
.scroll-progress { position: fixed; top: 0; left: 0; right: 0; height: 2px; z-index: 70; pointer-events: none; }
.scroll-progress span { display: block; height: 100%; background: var(--ochre); transform-origin: left; transform: scaleX(0); }
.float-cta {
  position: fixed; left: 50%; bottom: 20px; z-index: 65; display: flex; align-items: center; gap: 14px; max-width: calc(100% - 24px);
  padding: 7px 7px 7px 22px; border-radius: 999px; color: var(--beige); background: rgba(18, 21, 17, .9); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  transform: translate(-50%, 150%); opacity: 0; transition: transform .5s var(--ease), opacity .5s var(--ease);
}
.float-cta.is-on { transform: translate(-50%, 0); opacity: 1; }
.float-cta span { font-size: .78rem; letter-spacing: .07em; text-transform: uppercase; white-space: nowrap; }

/* ---------- Reveal on scroll ---------- */
html.js-reveal [data-reveal], html.js-reveal [data-reveal-group] > * { opacity: 0; transform: translateY(34px); filter: blur(6px); transition: opacity .9s var(--ease), transform .9s var(--ease), filter .9s var(--ease); transition-delay: var(--delay, 0s); }
html.js-reveal [data-reveal].is-in, html.js-reveal [data-reveal-group] > .is-in { opacity: 1; transform: none; filter: none; }

/* ---------- Team ---------- */
.view-team { background: var(--beige); }
.team-hero { background: var(--night); color: var(--beige); padding: clamp(70px, 14vh, 150px) 0 clamp(50px, 9vh, 100px); }
.team-hero h1 { color: var(--sage-pale); margin: 14px 0 26px; font-size: clamp(3.4rem, 13vw, 12.5rem); font-weight: 400; letter-spacing: -.06em; line-height: .84; text-transform: uppercase; }
.team-body { padding-top: clamp(60px, 10vh, 110px); padding-bottom: clamp(70px, 12vh, 140px); }
.founder { display: grid; grid-template-columns: minmax(200px, 340px) minmax(0, 1fr); gap: 32px 6vw; align-items: end; padding-bottom: 70px; margin-bottom: 70px; border-bottom: 1px solid var(--line); }
.founder h2 { margin: 12px 0 14px; font-size: clamp(2.6rem, 7vw, 6.4rem); font-weight: 400; letter-spacing: -.055em; line-height: .9; text-transform: uppercase; }
.founder .cap:first-child { color: var(--green); font-weight: 600; }
.frame { padding: 10px; border: 1px solid var(--line-strong); background: var(--cream); transform: rotate(-1.2deg); transition: transform .5s var(--ease); }
.frame img { width: 100%; height: auto; aspect-ratio: 1; object-fit: cover; border-radius: 50%; background: var(--mist); }
.frame-lg { transform: rotate(1.4deg); }
.frame:hover { transform: rotate(0) scale(1.02); }
.frame-empty { display: block; }
.frame-empty span { aspect-ratio: 1; display: grid; place-items: center; border-radius: 50%; background: var(--mist); }
.frame-empty span { font-family: var(--serif); font-style: italic; font-size: 5rem; color: var(--muted); }
.team-grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 40px 4vw; border: 0; }
.member { border: 0; padding: 0; text-align: left; background: none; }
.member:nth-child(2) .frame { transform: rotate(1deg); }
.member:nth-child(3) .frame { transform: rotate(-.6deg); }
.member h2 { margin: 22px 0 6px; font-size: clamp(1.6rem, 2.6vw, 2.4rem); font-weight: 400; letter-spacing: -.045em; text-transform: uppercase; }

/* ---------- Terms and Privacy ---------- */
.view-legal { background: var(--beige); padding: 0; }
.legal-hero h1 { font-size: clamp(3rem, 10vw, 9.5rem); }
.legal-layout { display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 40px 6vw; padding-top: clamp(50px, 9vh, 100px); padding-bottom: clamp(70px, 12vh, 140px); }
.legal-toc { position: sticky; top: calc(var(--hh) + 24px); align-self: start; }
.legal-toc ol { list-style: none; margin: 14px 0 0; padding: 0; border-top: 1px solid var(--line); counter-reset: t; }
.legal-toc li { counter-increment: t; border-bottom: 1px solid var(--line); }
.legal-toc a { display: flex; gap: 10px; padding: 10px 0; color: var(--ink); text-decoration: none; font-size: .78rem; letter-spacing: .07em; text-transform: uppercase; }
.legal-toc a::before { content: counter(t, decimal-leading-zero); color: var(--muted); }
.legal-toc a:hover { color: var(--green); }
.legal-body { max-width: 760px; }
.legal-sec { padding: 0 0 46px; margin-bottom: 46px; border-bottom: 1px solid var(--line); scroll-margin-top: calc(var(--hh) + 24px); }
.legal-sec:last-child { border-bottom: 0; margin-bottom: 0; }
.legal-n { color: var(--green); font-weight: 600; margin-bottom: 10px; }
.legal-sec h2 { margin: 0 0 18px; font-size: clamp(1.7rem, 3.2vw, 2.6rem); font-weight: 400; letter-spacing: -.045em; text-transform: uppercase; }
.legal-sec p, .legal-sec li { font-size: 1.05rem; line-height: 1.65; max-width: 66ch; }
.legal-sec ul { margin: 0 0 1em; padding-left: 1.2em; }
.legal-sec li { margin-bottom: 8px; }
.legal-sec li::marker { color: var(--green); }
.legal-short { background: var(--cream); border: 1px solid var(--line); border-left: 3px solid var(--ochre); padding: 30px 32px; }
.legal-short:last-child, .legal-short { margin-bottom: 46px; }
#terms-text .legal-sec { padding-bottom: 20px; margin-bottom: 20px; }
#terms-text .legal-sec h2 { font-size: 1.3rem; text-transform: none; letter-spacing: -.02em; font-weight: 500; }
#terms-text .legal-short { padding: 20px; }
#terms-text .legal-sec p, #terms-text .legal-sec li { font-size: .98rem; }
.dialog-foot { padding: 4px 24px 18px; border-top: 1px solid var(--line); }

/* ---------- Our results ---------- */
/* mnm44: the yellow line on each bar is the goal (95% / 5%) */
.view-results { background: var(--beige); padding: 0; }
.results-hero h1 { font-size: clamp(3rem, 11vw, 10rem); }
.results-body { padding-top: clamp(50px, 9vh, 100px); padding-bottom: clamp(70px, 12vh, 140px); }
.stats-sample { display: inline-block; margin: 0 0 28px; padding: 6px 14px; background: var(--marker-soft); font-size: .78rem; letter-spacing: .07em; text-transform: uppercase; font-weight: 600; }
.stats-empty { padding: 40px 0 60px; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.stats-empty .nlist-big { margin-bottom: 14px; }
.stats-meters { display: grid; grid-template-columns: 1fr 1fr; gap: 40px 6vw; margin-bottom: clamp(50px, 8vh, 90px); }
.stats-meter .cap { color: var(--muted); }
.stats-big { margin: 6px 0 18px; font-size: clamp(4rem, 11vw, 9.5rem); font-weight: 400; letter-spacing: -.06em; line-height: .85; color: var(--green); }
.meter { position: relative; height: 6px; background: var(--beige-2); margin-bottom: 12px; }
.meter span { position: absolute; left: 0; top: 0; bottom: 0; background: var(--forest); }
.meter i { position: absolute; top: -6px; bottom: -6px; width: 2px; background: var(--ochre); }
.meter-goal { color: var(--muted); }
.meter-goal.is-met { color: var(--green); font-weight: 600; }
.stats-rows { margin-top: 0; }
.stats-rows .nlist-big { font-size: clamp(1.8rem, 4.2vw, 3.8rem); }
.results-sec { padding-top: clamp(50px, 8vh, 80px); margin-top: clamp(50px, 8vh, 80px); border-top: 1px solid var(--line); max-width: 860px; }
.results-sec h2 { margin: 0 0 12px; font-size: clamp(1.7rem, 3.2vw, 2.6rem); font-weight: 400; letter-spacing: -.045em; text-transform: uppercase; }
.results-sec .btn { margin-top: 10px; }
.results-how ul { padding-left: 1.2em; margin: 0; }
.results-how li { margin-bottom: 8px; max-width: 66ch; }
.results-how li::marker { color: var(--green); }
.followup-form { display: grid; gap: 16px; margin-top: 20px; max-width: 640px; }
.followup-form .btn { justify-self: start; margin-top: 0; }
.followup-thanks { margin-top: 20px; padding: 18px 22px; background: var(--cream); border-left: 3px solid var(--green); }
.sv-confirmed { margin-top: 14px; }
.file-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 14px 0; }
.file-row .file-name { margin: 0; min-width: 0; }
.center-row { justify-content: center; margin-top: 8px; }
.nlist-cta-btns { display: flex; flex-wrap: wrap; align-items: center; gap: 14px 26px; }

/* ---------- App screens ---------- */
.view:not(.view-home):not(.view-team) { background: var(--beige); }
.panel, #account-detail .card { background: var(--cream); border: 1px solid var(--line); border-radius: 0; box-shadow: none; }
.auth-wrap { background: var(--cream); border: 1px solid var(--line); box-shadow: none; }
input[type="text"], input[type="email"], input[type="password"], input[type="number"], input[type="date"], select, textarea {
  background: #FFFDF8; border: 1px solid var(--line-strong); border-radius: 2px; color: var(--ink); font-family: var(--body);
}
input:focus, select:focus, textarea:focus { border-color: var(--ink); box-shadow: var(--ring); outline: none; }
label, .label { color: var(--ink); }
.badge { background: var(--mist); color: var(--ink); }
.pill-option span { border: 1px solid var(--line-strong); border-radius: 999px; background: #FFFDF8; }
.pill-option:hover span { border-color: var(--ink); }
.pill-option input:checked + span { background: var(--forest); border-color: var(--forest); color: var(--beige); }
.stepper .bar { border-radius: 0; height: 2px; }
.dropzone { border: 1px dashed var(--line-strong); background: var(--mist-2); border-radius: 0; }
.dropzone:hover, .dropzone.is-over { border-color: var(--ink); background: var(--beige-2); }
.side-option { background: var(--cream); }
.side-option:hover { background: var(--mist-2); }
.bill-sheet, .paper-letter { border: 1px solid var(--line); box-shadow: none; background: #FFFDF8; }
.question { background: var(--cream); border: 1px solid var(--line); box-shadow: none; }
.flag-card { background: var(--cream); border: 1px solid var(--line); overflow: hidden; }
.flag-card::before { left: 0; top: 0; bottom: 0; width: 3px; background: var(--ochre); }
.flag-card.is-dismissed { background: transparent; border-style: dashed; }
.flag-card.is-dismissed::before { background: var(--line-strong); }
.flag-kind { letter-spacing: .06em; text-transform: uppercase; font-size: .74rem; }
.notice-box { border-radius: 0; }
dialog { border: 1px solid var(--line); border-radius: 0; box-shadow: 0 40px 90px -40px rgba(0, 0, 0, .55); background: var(--cream); }
.dialog-head, .drawer-head { background: var(--black); color: var(--beige); }
.dialog-head h2, .drawer-head h2 { color: var(--beige); }
.dialog-head .icon-btn, .drawer-head .icon-btn { color: var(--beige); }
.drawer { background: var(--cream); border-left: 1px solid var(--line); box-shadow: -40px 0 90px -40px rgba(0, 0, 0, .45); }
#toast { background: var(--black); color: var(--beige); border-radius: 999px; box-shadow: none; }
.upload-layout { border: 1px solid var(--line); background: var(--cream); }
.upload-layout .panel { border: 0; border-right: 1px solid var(--line); }
.stat { background: var(--mist-2); border: 0; }
.price-card-paid { outline: 1px solid var(--ink); }

/* Number questions: "Not sure" beside the field */
.num-row input[type="number"]:disabled { opacity: .45; }

/* ---------- Phones and tablets ---------- */
/* mnm44: everything below is just making it fit on phones */
@media (max-width: 760px) {
  /* the blur would trap the bottom tab bar inside the header, so phones get a plain header */
  .site-header { backdrop-filter: none; -webkit-backdrop-filter: none; background: var(--beige); }
  .site-header.is-over-hero { background: transparent; }
  .app-nav { background: var(--black); color: var(--beige); }
  .app-nav button { opacity: .75; letter-spacing: .02em; font-size: .62rem; padding-left: 0; padding-right: 0; }
}
@media (max-width: 1100px) {
  .nh-check-list { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px 16px; }
  .nlist-rows li { grid-template-columns: minmax(0, 1fr) 120px; }
  .nlist-meta { grid-column: 1 / -1; grid-row: 2; }
  .nlist-year { grid-row: 1; grid-column: 2; }
}
@media (max-width: 860px) {
  :root { --hh: 58px; }
  .upload-layout .panel { border-right: 0; border-bottom: 1px solid var(--line); }
  .nh-tag { margin-left: 0; }
  .nh-mid { grid-template-columns: 1fr; padding-top: 6vh; }
  .ninfo { grid-template-columns: 1fr; }
  .ninfo-table div { grid-template-columns: 120px 1fr; }
  .ncase-head { grid-template-columns: 1fr; top: 18vh; }
  .ncase-meta { display: flex; flex-wrap: wrap; gap: 6px 16px; }
  .menu-body { grid-template-columns: 1fr; align-items: start; }
  .menu-preview { display: none; }
  .founder { grid-template-columns: 1fr; }
  .founder .frame { max-width: 320px; }
  .team-grid { grid-template-columns: 1fr 1fr; }
  .foot-nav { flex-wrap: wrap; justify-content: center; gap: 0 22px; }
  .foot-nav span { display: none; }
  .legal-layout { grid-template-columns: 1fr; }
  .stats-meters { grid-template-columns: 1fr; }
  .legal-toc { position: static; }
}
@media (max-width: 600px) {
  body { font-size: 1rem; }
  .nh-check-list { grid-template-columns: 1fr 1fr; }
  .nh-check-list button { grid-template-columns: auto 1fr; gap: 10px; align-items: baseline; }
  .nh-checks { margin-top: 5vh; }
  .nsay { grid-template-columns: 1fr; gap: 6px; }
  .nsay-r { text-align: left; }
  .nlist-rows li { grid-template-columns: 1fr; gap: 8px; }
  .nlist-meta { grid-row: auto; }
  .nlist-year { grid-row: auto; grid-column: auto; text-align: left; }
  .ngal-card { width: 64vw; }
  .ngal-track { padding-left: 18vw; }
  .ngal-foot { flex-direction: column; align-items: stretch; gap: 14px; }
  .ngal-cap { text-align: left; max-width: none; }
  .ngal-name { font-size: 2rem; margin: 4px 0 6px !important; }
  .ngal-text { font-size: .92rem; }
  .nbox-cube { --h: clamp(270px, 44vh, 330px); width: 80vw; }
  .nbox-side { right: clamp(16px, 2.6vw, 40px); grid-template-columns: 1fr auto; align-items: baseline; }
  .nbox-side .vticks { display: none; }
  .nbox-stage { top: 40px; }
  .menu-list button { font-size: clamp(1.7rem, 8.6vw, 2.6rem); gap: 12px; }
  .menu-list button::before { width: 1.9rem; }
  .nbox-face { padding: 10% 8%; }
  .nbox-face p { font-size: .98rem; }
  .nbox-index button { font-size: .7rem; letter-spacing: .05em; }
  .nbox-index button i { display: block; margin: 0 0 2px; }
  .ncase-media { margin-top: 30vh; }
  .ncase-inner { justify-content: center; }
  .lang-card, .ask-card { padding: 22px; }
  .team-grid { grid-template-columns: 1fr; }
  .team-grid .frame { max-width: 300px; }
  .float-cta span { display: none; }
  .float-cta { padding: 6px; }
  .ncta .btn { justify-self: start; }
  .legal-short { padding: 22px 20px; }
}

@media (prefers-reduced-motion: reduce) {
  .grain { animation: none; }
  html.js-reveal [data-reveal], html.js-reveal [data-reveal-group] > * { opacity: 1; transform: none; filter: none; }
  .nh-bg { transform: none !important; }
}
