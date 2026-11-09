/* ok so this is basically the brain of the whole site lol
   - every page
   - the 6 step check (upload > charges > questions > review > letter > survey)
   - login, results page, pricing, account... all of it
   website AND the phone app both run off this same file so test both if u change stuff */
(function () {
  "use strict";

  const API = window.CandorifyAPI;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // google/apple login stays OFF til Vrajesh adds the backend routes. just flip it to true when he does
  const OAUTH_ENABLED = { google: false, apple: false };

  // pages anyone can see w/o an account. everything else makes u sign up first
  const PUBLIC_VIEWS = new Set(["home", "pricing", "auth", "team", "legal", "results"]);
  const STEPS = ["start", "charges", "questions", "flags", "letter", "finish"];
  const STEP_LABELS = { start: "Upload", charges: "Charges", questions: "Questions", flags: "Review", letter: "Letter", finish: "Finish" };
  const VIEW_PURPOSE = { check: "check a bill", letters: "write a letter", account: "see your account", lookup: "look up a code" };

  // site is split into separate pages now, this is just which file each one lives in
  const PAGES = {
    home: "home.html", check: "bill.html", letters: "dispute.html", lookup: "look_up.html", pricing: "plans.html",
    account: "profile.html", results: "performance.html", team: "team.html", legal: "terms.html",
  };
  const onThisPage = (view) => !!document.getElementById("view-" + view);

  // flag types from the backend (matched by part of the name)
  const KIND_LABELS = [
    [/dup/, "Possible duplicate charge"],
    [/arith|math/, "Math doesn't add up"],
    [/quantit/, "Unusual quantity"],
    [/total/, "Total doesn't match the charges"],
    [/answer/, "Doesn't match what you told us"],
    [/not_received/, "A service you don't remember"],
  ];

  const ICON_INFO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>';
  const ICON_FILE = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>';

  const state = {
    user: null,
    languages: { en: "English" },
    view: null,
    pendingView: null,
    authMode: "login",
    letterMode: null,
    manualItems: [{ code: "", description: "", note: "" }],
    lastFocus: null,
  };

  let flow = newFlow();
  let selectedFile = null;

  function newFlow() {
    return {
      source: null,          // "upload" or "sample"
      billId: null,
      provider: "",
      date: "",
      total: 0,
      lines: [],             // { id, code, code_system, description, quantity, unit_price, line_total, plain_english }
      questions: [],         // { id, text, hint, type, choices, line_refs, local, check, expected }
      questionsFromServer: false,
      answers: {},           // question id -> value
      sampleFlags: [],
      flags: [],             // { key, id, kind, message, status, include, lineRefs, local }
      step: "start",
      editing: new Set(),
      finished: false,
    };
  }

  // --- utilities ---
  function money(n) {
    return "$" + Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function num(v) { const n = parseFloat(v); return isFinite(n) ? n : 0; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function fmtQty(n) { n = num(n); return Number.isInteger(n) ? String(n) : n.toFixed(2); }
  function plural(n, one, many) { return n === 1 ? one : (many || one + "s"); }
  function prefLang() { return (state.user && state.user.preferred_language) || "en"; }
  function isPaid() { return !!(state.user && state.user.tier === "paid"); }
  function kindLabel(k) {
    const key = String(k || "").toLowerCase();
    const hit = KIND_LABELS.find(([re]) => re.test(key));
    if (hit) return hit[1];
    const words = key.replace(/_/g, " ").trim();
    return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Worth a second look";
  }

  let toastTimer;
  function toast(msg, isErr = false) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.toggle("err", !!isErr);
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), isErr ? 5000 : 3500);
  }

  function setBusy(btn, busy, label) {
    if (!btn) return;
    if (busy) {
      if (!btn.dataset.idle) btn.dataset.idle = btn.innerHTML;
      btn.innerHTML = '<span class="spinner" aria-hidden="true"></span>' + esc(label || "Working…");
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
    } else {
      if (btn.dataset.idle) { btn.innerHTML = btn.dataset.idle; delete btn.dataset.idle; }
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
    }
  }

  function focusHeading(root) {
    const h = root && root.querySelector("h1:not(.sr-only), h2");
    if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); }
  }

  function populateLangSelect(sel) {
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = Object.entries(state.languages).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join("");
    sel.value = current && state.languages[current] ? current : prefLang();
    if (!sel.value) sel.value = "en";
  }

  // ========== NAVIGATION ==========
  function go(view) {
    if (!PUBLIC_VIEWS.has(view) && !API.isLoggedIn()) {
      state.pendingView = view;
      showAuth("register", "Create a free account to " + (VIEW_PURPOSE[view] || "continue") + ". It only takes a minute.");
      return;
    }
    // logged in ppl skip the login page but the logo ALWAYS goes home now (was bouncing to bill.html before)
    if (view === "auth" && API.isLoggedIn()) view = "check";
    if (!onThisPage(view)) { window.location.href = PAGES[view] || "home.html"; return; }
    showView(view);
  }

  function showView(view) {
    state.view = view;
    $$(".view").forEach((v) => { v.hidden = v.id !== "view-" + view; });
    $$("[data-go]").forEach((b) => {
      if (b.classList.contains("brand")) return;
      if (b.dataset.go === view) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    if (view === "letters") mountLetter("letters");
    if (view === "check" && flow.step === "letter") mountLetter("flow");
    if (view === "pricing") renderPricing();
    if (view === "account") renderAccount();
    if (view === "results") renderResults(); else stopStatsRefresh();
    window.scrollTo(0, 0);
    if (view === "check") focusHeading($("#step-" + flow.step));
    else focusHeading($("#view-" + view));
  }

  // auth
  function renderHeader() {
    const inApp = !!state.user;
    $$("#site-menu [data-when]").forEach((el) => { el.hidden = el.dataset.when !== (inApp ? "in" : "out"); });
    document.body.classList.toggle("logged-in", inApp);
    $("#public-nav").hidden = inApp;
    $("#app-nav").hidden = !inApp;
    $("#header-user").hidden = !inApp;
    if (inApp) {
      const badge = $("#plan-badge");
      badge.textContent = isPaid() ? "Paid" : "Free";
      badge.className = "badge" + (isPaid() ? " badge-brand" : "");
      $("#user-email").textContent = state.user.email || "Account";
    }
  }

  async function refreshUser() {
    if (!API.isLoggedIn()) { state.user = null; renderHeader(); return; }
    try { state.user = await API.me(); }
    catch (e) { API.setToken(""); state.user = null; }
    renderHeader();
    populateLangSelect($("#tc-lang"));
    populateLangSelect($("#translate-lang"));
  }

  function showAuth(mode, message) {
    // not on a sign in/up page -> send them there + remember where to come back to
    if (!onThisPage("auth")) {
      const q = new URLSearchParams();
      if (state.pendingView) q.set("next", state.pendingView);
      if (message) q.set("msg", message);
      window.location.href = (mode === "register" ? "signup.html" : "signin.html") + (q.toString() ? "?" + q : "");
      return;
    }
    setAuthMode(mode);
    const p = $("#auth-prompt");
    p.textContent = message || "";
    p.hidden = !message;
    showView("auth");
    $("#auth-email").focus();
  }

  function setAuthMode(mode) {
    state.authMode = mode;
    const reg = mode === "register";
    $("#tab-login").setAttribute("aria-selected", String(!reg));
    $("#tab-register").setAttribute("aria-selected", String(reg));
    $$("[data-signup-only]").forEach((el) => { el.hidden = !reg; });
    $("#auth-title").textContent = reg ? "Create your free account" : "Welcome back";
    $("#auth-submit").textContent = reg ? "Create account" : "Log in";
    $("#auth-password").setAttribute("autocomplete", reg ? "new-password" : "current-password");
    $("#auth-error").hidden = true;
  }

  function authError(msg) {
    const el = $("#auth-error");
    el.textContent = msg;
    el.hidden = false;
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    const email = $("#auth-email").value.trim();
    const password = $("#auth-password").value;
    const remember = $("#auth-remember").checked;
    const isRegister = state.authMode === "register";
    $("#auth-error").hidden = true;

    if (!email || !/^\S+@\S+\.\S+$/.test(email)) { authError("Enter a valid email address."); $("#auth-email").focus(); return; }
    if (password.length < 8) { authError("Your password needs at least 8 characters."); $("#auth-password").focus(); return; }
    if (isRegister && !$("#auth-terms").checked) { authError("Please agree to the Terms and Privacy Notice to create an account."); $("#auth-terms").focus(); return; }

    const btn = $("#auth-submit");
    setBusy(btn, true, isRegister ? "Creating account…" : "Logging in…");
    try {
      const res = isRegister
        ? await API.register(email, password, $("#auth-lang").value, true, remember)
        : await API.login(email, password, remember);
      API.setToken(res.access_token, remember);
      await refreshUser();
      $("#auth-password").value = "";
      toast(isRegister ? "Account created. Welcome to Candorify!" : "Welcome back!");
      const dest = state.pendingView || "check";
      state.pendingView = null;
      go(dest);
    } catch (err) {
      authError(err.status === 401 ? "That email and password don't match. Try again." : err.message);
    } finally { setBusy(btn, false); }
  }

  function startOAuth(provider) {
    const name = provider === "google" ? "Google" : "Apple";
    if (!OAUTH_ENABLED[provider]) { toast(name + " sign-in is coming soon. Please use your email for now."); return; }
    window.location.href = API.oauthUrl(provider, $("#auth-remember").checked);
  }

  // the backend's oauth callback should redirect to /#access_token=...&remember_me=true
  function handleOAuthReturn() {
    if (!window.location.hash || window.location.hash.indexOf("access_token=") === -1) return;
    const params = new URLSearchParams(window.location.hash.slice(1));
    API.setToken(params.get("access_token"), params.get("remember_me") === "true");
    history.replaceState(null, "", window.location.pathname + window.location.search);
  }

  function signOut() {
    API.setToken("");
    state.user = null;
    window.location.href = "home.html";
  }

  // ----- flow: the steps -----
  function setStep(step) {
    flow.step = step;
    STEPS.forEach((s) => { $("#step-" + s).hidden = s !== step; });
    renderStepper();
    if (step === "letter") mountLetter("flow");
    if (step === "finish") renderFinish();
    window.scrollTo(0, 0);
    focusHeading($("#step-" + step));
  }

  function renderStepper() {
    const cur = STEPS.indexOf(flow.step);
    $$("#stepper li").forEach((li, i) => {
      li.classList.toggle("done", i < cur);
      li.classList.toggle("current", i === cur);
      const b = li.querySelector("button");
      b.disabled = !(i < cur) || flow.step === "finish" || (i === 0 && cur > 0);
      if (i === cur) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
      b.setAttribute("aria-label", "Step " + (i + 1) + ": " + STEP_LABELS[STEPS[i]] + (i < cur ? " (done)" : i === cur ? " (current)" : ""));
    });
    $("#step-count").textContent = "Step " + (cur + 1) + " of " + STEPS.length + ": " + STEP_LABELS[flow.step];
    $("#btn-start-over").hidden = cur === 0 || flow.finished;
  }

  function prevStep() {
    let i = STEPS.indexOf(flow.step) - 1;
    if (STEPS[i] === "questions" && !flow.questions.length) i -= 1;
    if (i >= 0) setStep(STEPS[i]);
  }

  function resetFlow() {
    flow = newFlow();
    selectedFile = null;
    const input = $("#pdf-file");
    if (input) input.value = "";
    $("#file-name").hidden = true;
    $("#btn-upload").disabled = true;
    $("#upload-status").textContent = "";
    $("#translations").innerHTML = "";
    $("#benchmarks").innerHTML = "";
    $("#tpl-subject").value = "";
    $("#tpl-body").value = "";
    setStep("start");
  }

  async function startOver() {
    if (!confirm("Start over? This bill and your answers will be cleared.")) return;
    if (flow.billId) API.deleteBill(flow.billId).catch(() => {});
    resetFlow();
    toast("Cleared. You can start a new bill.");
  }

  // STEP 1 - upload or sample
  const MAX_PDF_MB = 5;    // 5mb, same as the backend so nobody waits around just to get rejected

  function chooseFile(file) {
    $("#pdf-file").value = "";          // so picking the same file twice still works
    if (!file) return;
    const isPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name);
    if (!isPdf) { toast("Please choose a PDF file.", true); return; }
    if (file.size > MAX_PDF_MB * 1024 * 1024) { toast(`That PDF is over ${MAX_PDF_MB} MB. Try a smaller file, or only the itemized pages.`, true); return; }
    if (file.size === 0) { toast("That file is empty. Please choose another PDF.", true); return; }
    selectedFile = file;
    $("#file-name").innerHTML = ICON_FILE + "<span>" + esc(file.name) + "</span>";
    $("#file-row").hidden = false;
    $("#btn-upload").disabled = false;
    $("#upload-status").textContent = "";
  }

  function clearFile() {
    selectedFile = null;
    $("#pdf-file").value = "";
    $("#file-row").hidden = true;
    $("#btn-upload").disabled = true;
    $("#upload-status").textContent = "";
    $("#pdf-file").focus();
  }

  function normalizeLine(li) {
    return {
      id: li.id != null ? li.id : null,
      code: li.code || "",
      code_system: li.code_system || "CPT",
      description: li.description || "",
      quantity: num(li.quantity) || 1,
      unit_price: num(li.unit_price),
      line_total: num(li.line_total),
      plain_english: li.plain_english || "",
      position: li.position,
    };
  }

  function normalizeQuestion(q, i) {
    const type = ["number", "yes_no", "choice"].includes(q.type) ? q.type : "yes_no";
    // `choices` = english values the backend compares. `choice_labels` = what the patient actually reads
    const choices = Array.isArray(q.choices) && q.choices.length ? q.choices
      : (type === "yes_no" ? ["Yes", "No", "Not sure"] : []);
    const labels = Array.isArray(q.choice_labels) && q.choice_labels.length === choices.length ? q.choice_labels : choices;
    return {
      id: String(q.id != null ? q.id : "q" + (i + 1)),
      text: q.text || q.question || "",
      hint: q.hint || "",
      type,
      choices,
      labels,
      line_refs: Array.isArray(q.line_refs) ? q.line_refs : [],
      notSureLabel: q.not_sure_label || "",
      local: false,
    };
  }

  async function doUpload() {
    if (!selectedFile) { toast("Choose your PDF first.", true); return; }
    const btn = $("#btn-upload");
    setBusy(btn, true, "Reading your bill…");
    $("#upload-status").textContent = "This can take up to a minute.";
    try {
      const res = await API.uploadPdf(selectedFile, prefLang());
      const keepFile = selectedFile;
      flow = newFlow();
      selectedFile = keepFile;
      flow.source = "upload";
      flow.billId = res.bill_id;
      flow.label = res.label || "";
      flow.provider = res.provider_name || "";
      flow.date = res.service_date || "";
      flow.total = num(res.stated_total);
      flow.lines = (res.line_items || []).map(normalizeLine);
      if (Array.isArray(res.questions) && res.questions.length) {
        flow.questions = res.questions.map(normalizeQuestion).filter((q) => q.text);
        flow.questionsFromServer = true;
      }
      $("#upload-status").textContent = "";
      toast("Found " + flow.lines.length + " " + plural(flow.lines.length, "charge") + "." + (res.notice ? " " + res.notice : ""));
      setStep("charges");
      renderCharges();
    } catch (err) {
      $("#upload-status").textContent = err.message;
      toast(err.message, true);
    } finally { setBusy(btn, false); }
  }

  async function loadSample() {
    const btn = $("#btn-sample");
    setBusy(btn, true, "Making a sample bill…");
    try {
      const withErrors = $("#sample-errors").checked;
      const bill = await API.generate({ inject_errors: withErrors, language: prefLang() });
      flow = newFlow();
      flow.source = "sample";
      flow.billId = bill.id;
      flow.provider = bill.provider_name || "Sample provider";
      flow.date = bill.service_date || "";
      flow.total = num(bill.stated_total);
      flow.lines = (bill.line_items || []).slice().sort((a, b) => num(a.position) - num(b.position)).map(normalizeLine);
      flow.sampleFlags = (bill.flags || []).map(normalizeFlag);
      if (Array.isArray(bill.questions) && bill.questions.length) {
        flow.questions = bill.questions.map(normalizeQuestion).filter((q) => q.text);
        flow.questionsFromServer = true;
      }
      setStep("charges");
      renderCharges();
    } catch (err) { toast(err.message, true); }
    finally { setBusy(btn, false); }
  }

  // step 2 / charges
  function renderCharges() {
    const sample = flow.source === "sample";
    $("#charges-intro").textContent = sample
      ? "A made-up sample bill. Tap a code to see what it means."
      : "Tap a code to see what it means. Fix anything we misread.";
    $("#rev-provider").value = flow.provider;
    $("#rev-date").value = flow.date;
    $("#rev-total").value = flow.total ? flow.total.toFixed(2) : "";
    ["#rev-provider", "#rev-date", "#rev-total"].forEach((s) => { $(s).disabled = sample; });
    $("#btn-add-line").hidden = sample;
    renderLines();
  }

  function renderLines(focusIndex) {
    const readOnly = flow.source === "sample";
    $("#lines").innerHTML = flow.lines.length
      ? flow.lines.map((li, i) => lineCardHTML(li, i, readOnly)).join("")
      : '<p class="muted">No charges yet. Add the charges from your bill below.</p>';
    renderTotals();
    if (focusIndex != null) {
      const first = $(`#li-${focusIndex}-code`);
      if (first) first.focus();
    }
  }

  function lineCardHTML(li, i, readOnly) {
    const editing = flow.editing.has(i);
    const code = li.code
      ? `<button type="button" class="code-chip" data-act="code" data-i="${i}" aria-label="What does code ${esc(li.code)} mean?">${esc(li.code)}${ICON_INFO}</button>`
      : '<span class="badge">No code</span>';
    const plain = li.plain_english && li.plain_english !== li.description
      ? `<div class="line-plain">${esc(li.plain_english)}</div>` : "";
    const tools = readOnly ? "" : `<div class="line-tools">
        <button type="button" class="btn btn-quiet btn-sm" data-act="edit" data-i="${i}" aria-expanded="${editing}">${editing ? "Done" : "Edit"}</button>
        <button type="button" class="btn btn-quiet btn-sm" data-act="remove" data-i="${i}" aria-label="Remove charge ${i + 1}">Remove</button>
      </div>`;
    const edit = editing ? `<div class="line-edit"><div class="form-row">
        ${fieldHTML(i, "code", "Code", "text", li.code)}
        ${fieldHTML(i, "description", "Description", "text", li.description)}
        ${fieldHTML(i, "quantity", "Quantity", "number", li.quantity)}
        ${fieldHTML(i, "unit_price", "Price each ($)", "number", li.unit_price)}
        ${fieldHTML(i, "line_total", "Line total ($)", "number", li.line_total)}
      </div></div>` : "";
    return `<article class="line-card" data-i="${i}">
      <div class="line-main">
        <div>${code}</div>
        <div><div class="line-title">${esc(li.description || "Untitled charge")}</div>${plain}</div>
        <div class="line-amt"><span class="line-math">${fmtQty(li.quantity)} × ${money(li.unit_price)}</span><strong>${money(li.line_total)}</strong></div>
      </div>${tools}${edit}</article>`;
  }

  function fieldHTML(i, f, label, type, val) {
    const id = `li-${i}-${f}`;
    const extra = type === "number" ? ' step="0.01" inputmode="decimal"' : "";
    return `<div class="field${f === "description" ? " span-2" : ""}"><label for="${id}">${label}</label><input id="${id}" type="${type}"${extra} data-i="${i}" data-f="${f}" value="${esc(val)}"></div>`;
  }

  function renderTotals() {
    const sum = flow.lines.reduce((s, l) => s + num(l.line_total), 0);
    const stated = num($("#rev-total").value);
    const off = stated && Math.abs(sum - stated) > 0.009;
    $("#totals-bar").innerHTML = `
      <div class="total-item"><span>Charges add up to</span><strong>${money(sum)}</strong></div>
      <div class="total-item"><span>Total on your bill</span><strong>${stated ? money(stated) : "Not entered"}</strong></div>
      ${off ? `<p class="totals-note"><mark>${money(Math.abs(sum - stated))} doesn't add up.</mark> We'll flag it.</p>` : ""}`;
  }

  function onLinesClick(e) {
    const btn = e.target.closest("button[data-act]");
    if (!btn) return;
    const i = parseInt(btn.dataset.i, 10);
    const act = btn.dataset.act;
    if (act === "code") {
      const li = flow.lines[i];
      openLookup(li.code, li.code_system);
    } else if (act === "edit") {
      if (flow.editing.has(i)) { flow.editing.delete(i); renderLines(); $(`.line-card[data-i="${i}"] [data-act="edit"]`).focus(); }
      else { flow.editing.add(i); renderLines(i); }
    } else if (act === "remove") {
      const removed = flow.lines.splice(i, 1)[0];
      flow.editing.clear();
      renderLines();
      toast("Removed " + (removed.description || removed.code || "the charge") + ".");
    }
  }

  function onLinesInput(e) {
    const input = e.target.closest("input[data-f]");
    if (!input) return;
    const li = flow.lines[parseInt(input.dataset.i, 10)];
    const f = input.dataset.f;
    li[f] = input.type === "number" ? num(input.value) : input.value;
    if (f === "code" || f === "description") li.plain_english = "";
    renderTotals();
  }

  function addLine() {
    flow.lines.push({ id: null, code: "", code_system: "CPT", description: "", quantity: 1, unit_price: 0, line_total: 0, plain_english: "" });
    const i = flow.lines.length - 1;
    flow.editing.add(i);
    renderLines(i);
  }

  async function continueFromCharges() {
    if (flow.source === "upload") {
      flow.provider = $("#rev-provider").value.trim();
      flow.date = $("#rev-date").value.trim();
      flow.total = num($("#rev-total").value);
    }
    flow.lines = flow.lines.filter((l) => l.code || l.description || num(l.line_total));
    flow.editing.clear();
    if (!flow.lines.length) { renderLines(); toast("Add at least one charge to continue.", true); return; }
    // if they fixed the charges the backend saves the fixed bill and asks about that one instead
    if (flow.source === "upload" && flow.billId) {
      const btn = $("#btn-charges-next");
      setBusy(btn, true, "Saving your changes…");
      try {
        const r = await API.syncBill(flow.billId, { lines: flow.lines, total: flow.total, date: flow.date, label: flow.label, language: prefLang() });
        if (r.changed) {
          flow.billId = r.bill_id;
          flow.answers = {};
          flow.questions = (r.questions || []).map(normalizeQuestion).filter((q) => q.text);
          flow.questionsFromServer = flow.questions.length > 0;
        }
      } catch (err) { toast(err.message, true); return; }
      finally { setBusy(btn, false); }
    }
    if (!flow.questionsFromServer) flow.questions = buildFallbackQuestions(flow.lines);
    if (flow.questions.length) { setStep("questions"); renderQuestions(); }
    else runChecks($("#btn-charges-next"));
  }

  // === step 3: questions ===
  // backup questions, used until the backend sends the AI written ones
  const ROOM_RE = /(room\s*(&|and)?\s*board|semi-?private|private room|\bbed\b|r&b|accommodation|ward room|room charge)/i;
  const NOT_ROOM_RE = /(operating|emergency|recovery|treatment|procedure)\s*room/i;

  function buildFallbackQuestions(lines) {
    const qs = [];
    const roomIdx = [];
    lines.forEach((l, i) => {
      const text = l.description + " " + (l.plain_english || "");
      if (ROOM_RE.test(text) && !NOT_ROOM_RE.test(text)) roomIdx.push(i);
    });
    if (roomIdx.length) {
      const days = roomIdx.reduce((s, i) => s + num(lines[i].quantity), 0);
      qs.push({
        id: "local-stay",
        text: `The bill charges for ${fmtQty(days)} ${plural(days, "day")} in a room. How many nights did you stay?`,
        hint: "Count the nights you slept there.",
        type: "number", choices: [], line_refs: roomIdx, local: true, check: "quantity_matches", expected: days,
      });
    }
    lines
      .map((l, i) => ({ l, i }))
      .filter((x) => !roomIdx.includes(x.i) && num(x.l.line_total) > 0)
      .sort((a, b) => num(b.l.line_total) - num(a.l.line_total))
      .slice(0, 3)
      .forEach(({ l, i }) => {
        const name = l.plain_english || l.description || ("code " + l.code);
        qs.push({
          id: "local-recv-" + i,
          text: `Did you get this: ${name}?`,
          hint: `Charged ${money(l.line_total)}${l.code ? " (code " + l.code + ")" : ""}.`,
          type: "yes_no", choices: ["Yes", "No", "Not sure"], line_refs: [i], local: true, check: "received",
        });
      });
    return qs;
  }

  // "not sure" always goes back in english and NEVER turns into a flag. promise
  const NOT_SURE = "Not sure";
  function isNotSure(v) { return String(v == null ? "" : v).trim().toLowerCase() === "not sure"; }

  function renderQuestions() {
    $("#questions-list").innerHTML = flow.questions.map((q, n) => {
      const saved = flow.answers[q.id];
      const hint = q.hint ? `<p class="hint" id="qh-${n}">${esc(q.hint)}</p>` : "";
      if (q.type === "number") {
        return `<div class="question">
          <label class="legend" for="q-${n}" dir="auto">${esc(q.text)}</label>${hint}
          <div class="num-row">
            <input id="q-${n}" type="number" min="0" step="1" inputmode="numeric" data-q="${esc(q.id)}" value="${saved != null && !isNotSure(saved) ? esc(saved) : ""}" ${isNotSure(saved) ? "disabled" : ""} ${q.hint ? `aria-describedby="qh-${n}"` : ""}>
            <label class="pill-option"><input type="checkbox" id="qns-${n}" data-not-sure="${n}" ${isNotSure(saved) ? "checked" : ""}><span dir="auto">${esc(q.notSureLabel || NOT_SURE)}</span></label>
          </div>
        </div>`;
      }
      return `<fieldset class="question">
        <legend dir="auto">${esc(q.text)}</legend>${hint}
        <div class="pill-group">${q.choices.map((c, k) => `
          <label class="pill-option"><input type="radio" name="q-${n}" value="${esc(c)}" data-q="${esc(q.id)}" ${saved === c ? "checked" : ""}><span dir="auto">${esc((q.labels || q.choices)[k])}</span></label>`).join("")}
        </div>
      </fieldset>`;
    }).join("");
  }

  function collectAnswers() {
    flow.questions.forEach((q, n) => {
      if (q.type === "number") {
        const v = $(`#q-${n}`).value.trim();
        flow.answers[q.id] = $(`#qns-${n}`).checked ? NOT_SURE : (v === "" ? null : num(v));
      } else {
        const picked = $(`input[name="q-${n}"]:checked`);
        flow.answers[q.id] = picked ? picked.value : null;
      }
    });
  }

  // plain code checks for the backup qs (the AI written ones get
  // checked on the backend, mismatches come back as flags)
  function evaluateLocalAnswers() {
    const out = [];
    flow.questions.filter((q) => q.local).forEach((q) => {
      const a = flow.answers[q.id];
      if (a == null || isNotSure(a)) return;
      if (q.check === "quantity_matches" && num(a) !== num(q.expected)) {
        out.push({
          kind: "answer_mismatch",
          message: `You said you stayed ${fmtQty(a)} ${plural(num(a), "night")}, but the bill charges for ${fmtQty(q.expected)} room ${plural(num(q.expected), "day")}. Ask the hospital to confirm how many days you were charged for.`,
          lineRefs: q.line_refs,
        });
      }
      if (q.check === "received" && a === "No") {
        const l = flow.lines[q.line_refs[0]] || {};
        out.push({
          kind: "not_received",
          message: `You don't remember getting "${l.plain_english || l.description || l.code}" (${money(l.line_total)}). It's worth asking what this charge was for.`,
          lineRefs: q.line_refs,
        });
      }
    });
    return out.map((f, i) => ({ key: "local-" + i, id: null, status: "open", include: true, local: true, ...f }));
  }

  // run the checks
  function normalizeFlag(f, i) {
    const ids = String(f.line_item_ids || "").split(",").map((s) => parseInt(s, 10)).filter((n) => !isNaN(n));
    const lineRefs = Array.isArray(f.line_refs) ? f.line_refs
      : ids.map((id) => flow.lines.findIndex((l) => l.id === id)).filter((n) => n >= 0);
    const status = f.status || "open";
    return {
      key: f.id != null ? "s" + f.id : "f" + i,
      id: f.id != null ? f.id : null,
      kind: f.kind || "",
      message: f.message || "",
      questionId: f.question_id != null ? String(f.question_id) : null,
      status,
      include: status !== "dismissed",
      lineRefs,
      local: false,
    };
  }

  async function runChecks(btn) {
    setBusy(btn, true, "Checking your bill…");
    try {
      const prev = new Map(flow.flags.map((f) => [f.key, f]));
      let flags;
      if (flow.billId) {
        const answers = flow.questions.filter((q) => !q.local)
          .map((q) => ({ question_id: q.id, value: flow.answers[q.id] != null ? flow.answers[q.id] : null }));
        const res = await API.submitReview({ bill_id: flow.billId, answers });
        flow.billId = res.bill_id;
        // safety net: never show a flag for something they answered "not sure" to
        flags = (res.flags || []).map(normalizeFlag)
          .filter((f) => !(f.questionId && isNotSure(flow.answers[f.questionId])));
      } else {
        flags = flow.sampleFlags.map((f) => ({ ...f }));
      }
      flags = flags.concat(evaluateLocalAnswers()).map((f) => {
        const old = prev.get(f.key);
        return old ? { ...f, status: old.status, include: old.include } : f;
      });
      flow.flags = flags;
      $("#translations").innerHTML = "";
      $("#benchmarks").innerHTML = "";
      setStep("flags");
      renderFlags();
    } catch (err) { toast(err.message, true); }
    finally { setBusy(btn, false); }
  }

  // step 4 - flags (review)
  function renderFlags() {
    const open = flow.flags.filter((f) => f.status !== "dismissed").length;
    const summary = $("#flag-summary");
    if (!flow.flags.length) {
      summary.className = "flag-summary is-ok";
      summary.textContent = "Nothing looks off. It's still worth a quick read.";
    } else {
      summary.className = "flag-summary";
      summary.textContent = `${flow.flags.length} ${plural(flow.flags.length, "thing")} to look at` +
        (open !== flow.flags.length ? ` · ${flow.flags.length - open} marked fine` : "");
    }
    $("#flags-list").innerHTML = flow.flags.map(flagCardHTML).join("");
    updateFlagsNext();
  }

  function flagCardHTML(f) {
    const dismissed = f.status === "dismissed";
    const lines = f.lineRefs.map((i) => flow.lines[i]).filter(Boolean)
      .map((l) => `<span class="flag-line">${esc(l.code || "No code")} · ${esc(l.description || l.plain_english)} · ${money(l.line_total)}</span>`).join("");
    const inputId = "inc-" + f.key;
    return `<article class="flag-card${dismissed ? " is-dismissed" : ""}" data-key="${esc(f.key)}">
      <div class="flag-kind">${esc(kindLabel(f.kind))}${dismissed ? '<span class="flag-tag">Marked as fine</span>' : ""}</div>
      <p class="flag-msg">${esc(f.message)}</p>
      ${lines ? `<div class="flag-lines">${lines}</div>` : ""}
      <div class="flag-actions">
        ${dismissed ? "<span></span>" : `<label class="check" for="${esc(inputId)}"><input id="${esc(inputId)}" type="checkbox" data-include ${f.include ? "checked" : ""}><span>Include in my letter</span></label>`}
        <button type="button" class="btn btn-quiet btn-sm" data-act="${dismissed ? "undo" : "dismiss"}">${dismissed ? "Undo" : "This one is fine"}</button>
      </div>
    </article>`;
  }

  function setFlagStatus(f, status) {
    f.status = status;
    if (f.id != null) API.updateFlag(f.id, status).catch((err) => toast(err.message, true));
  }

  function onFlagsChange(e) {
    const box = e.target.closest("input[data-include]");
    if (!box) return;
    const f = flow.flags.find((x) => x.key === box.closest(".flag-card").dataset.key);
    if (!f) return;
    f.include = box.checked;
    setFlagStatus(f, box.checked ? "confirmed" : "open");
    updateFlagsNext();
  }

  function onFlagsClick(e) {
    const btn = e.target.closest("button[data-act]");
    if (!btn) return;
    const key = btn.closest(".flag-card").dataset.key;
    const f = flow.flags.find((x) => x.key === key);
    if (!f) return;
    if (btn.dataset.act === "dismiss") { f.include = false; setFlagStatus(f, "dismissed"); }
    else { f.include = true; setFlagStatus(f, "confirmed"); }
    renderFlags();
    const again = $(`.flag-card[data-key="${CSS.escape(key)}"] button[data-act]`);
    if (again) again.focus();
  }

  function updateFlagsNext() {
    const n = flow.flags.filter((f) => f.include && f.status !== "dismissed").length;
    $("#btn-flags-next").textContent = n ? `Write my letter (${n} ${plural(n, "charge")})` : "Continue to letter";
    updateSurveyShortcut();
  }

  // only if NOTHING got flagged: lets them skip the letter and go straight to the survey
  function updateSurveyShortcut() {
    let btn = $("#btn-flags-survey");
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.id = "btn-flags-survey";
      btn.className = "btn btn-quiet";
      btn.textContent = "Skip to survey";
      btn.style.marginLeft = "auto";
      btn.style.marginRight = "12px";
      btn.addEventListener("click", () => setStep("finish"));
      $("#btn-flags-next").before(btn);
    }
    const show = flow.flags.length === 0 && flow.source !== "sample";
    btn.style.display = show ? "" : "none";
    $("#btn-flags-next").style.marginLeft = show ? "0" : "";   // keeps skip to survey right next to continue on desktop
  }

  // paid extras
  async function translateLines() {
    if (!flow.billId) return;
    if (API.features.payments && !isPaid()) { toast("Explaining every charge is part of the paid plan.", true); go("pricing"); return; }
    const lang = $("#translate-lang").value || "en";
    const out = $("#translations");
    out.innerHTML = '<p class="loading">Explaining each charge…</p>';
    try {
      const res = await API.translateBill(flow.billId, lang);
      const langName = state.languages[lang] || lang;
      out.innerHTML = '<div class="explain-list">' + (res.lines || []).map((l) => `
        <div class="explain-item">
          <strong>${esc(l.code)}</strong> · ${esc(l.plain_english)}
          ${lang !== "en" && l.translated ? `<div class="muted">${esc(langName)}: ${esc(l.translated)}</div>` : ""}
        </div>`).join("") + "</div>";
    } catch (err) {
      out.innerHTML = "";
      if (err.status === 402) { toast("This is part of the paid plan.", true); go("pricing"); }
      else toast(err.message, true);
    }
  }

  async function benchmarkLines() {
    if (!flow.billId) return;
    if (!isPaid()) { toast("Medicare price comparison is part of the paid plan.", true); go("pricing"); return; }
    const out = $("#benchmarks");
    out.innerHTML = '<p class="loading">Comparing to Medicare prices…</p>';
    try {
      const res = await API.benchmarkBill(flow.billId);
      const rows = (res.lines || []).map((l) => {
        const high = l.ratio != null && l.ratio >= 5;
        return `<tr class="${high ? "is-high" : ""}">
          <td><strong>${esc(l.code)}</strong></td><td>${esc(l.description)}</td>
          <td class="num">${money(l.charged_unit_price)}</td>
          <td class="num">${l.medicare_rate == null ? "Not listed" : money(l.medicare_rate)}</td>
          <td class="num">${l.ratio == null ? "–" : esc(l.ratio) + "×"}</td></tr>`;
      }).join("");
      out.innerHTML = `<p class="hint">${esc(res.disclaimer || "")}</p>
        <div class="table-wrap"><table>
          <thead><tr><th scope="col">Code</th><th scope="col">Charge</th><th scope="col" class="num">You were charged</th><th scope="col" class="num">Medicare pays</th><th scope="col" class="num">Times more</th></tr></thead>
          <tbody>${rows}</tbody></table></div>`;
    } catch (err) {
      out.innerHTML = "";
      if (err.status === 402) { toast("This is part of the paid plan.", true); go("pricing"); }
      else toast(err.message, true);
    }
  }

  // ---------- step 5 + the letters page: letter builder ----------
  function itemsFromFlags(list) {
    const items = [];
    (list || flow.flags.filter((f) => f.include && f.status !== "dismissed")).forEach((f) => {
      const lines = f.lineRefs.map((i) => flow.lines[i]).filter(Boolean);
      if (lines.length) lines.forEach((l) => items.push({ code: l.code || "", description: l.description || l.plain_english || "", note: f.message }));
      else items.push({ code: "", description: kindLabel(f.kind), note: f.message });
    });
    return items;
  }

  function letterType() { const r = $('input[name="letter-type"]:checked'); return r ? r.value : "request"; }
  function setLetterType(t) {
    $$('input[name="letter-type"]').forEach((r) => { r.checked = r.value === t; });
    $("#letter-items-wrap").hidden = t !== "dispute";
  }

  function mountLetter(mode) {
    const slot = mode === "flow" ? $("#letter-slot-flow") : $("#letter-slot-letters");
    const builder = $("#letter-builder");
    const changedMode = state.letterMode !== mode;
    if (builder.parentElement !== slot) slot.appendChild(builder);
    state.letterMode = mode;
    if (mode === "flow") {
      setLetterType(itemsFromFlags().length ? "dispute" : "request");
      if (flow.provider) $("#tpl-provider").value = flow.provider;
      if (flow.date) $("#tpl-date").value = flow.date;
      $("#btn-download-annotated").hidden = !(API.features.annotatedPdf && flow.source === "upload" && flow.billId);
      if (changedMode) { $("#tpl-subject").value = ""; $("#tpl-body").value = ""; }
    } else {
      $("#btn-download-annotated").hidden = true;
      setLetterType(letterType());
    }
    renderLetterItems();
  }

  function renderLetterItems() {
    const wrap = $("#letter-items");
    if (state.letterMode === "flow") {
      const items = itemsFromFlags();
      wrap.innerHTML = items.length
        ? `<ul class="letter-flag-items">${items.map((it) => `<li><strong>${esc(it.code ? it.code + " · " : "")}${esc(it.description)}</strong><span class="muted">${esc(it.note)}</span></li>`).join("")}</ul>
           <button type="button" class="link-btn" data-change-flags>Change</button>`
        : `<p class="muted">No charges picked. <button type="button" class="link-btn" data-change-flags>Pick some</button></p>`;
      return;
    }
    wrap.innerHTML = state.manualItems.map((it, i) => `
      <div class="item-row" data-item="${i}">
        <div class="row"><strong>Charge ${i + 1}</strong>${state.manualItems.length > 1 ? `<button type="button" class="btn btn-quiet btn-sm" data-remove-item="${i}" aria-label="Remove charge ${i + 1}">Remove</button>` : ""}</div>
        <div class="form-row">
          <div class="field"><label for="mi-${i}-code">Code</label><input id="mi-${i}-code" type="text" data-mi="${i}" data-f="code" value="${esc(it.code)}" placeholder="85025"></div>
          <div class="field"><label for="mi-${i}-description">What it's for</label><input id="mi-${i}-description" type="text" data-mi="${i}" data-f="description" value="${esc(it.description)}" placeholder="Blood test"></div>
        </div>
        <div class="field"><label for="mi-${i}-note">Your question</label><input id="mi-${i}-note" type="text" data-mi="${i}" data-f="note" value="${esc(it.note)}" placeholder="This shows up twice. Can you check it?"></div>
      </div>`).join("") + '<button type="button" class="btn btn-quiet btn-sm" id="btn-add-item">+ Add another charge</button>';
  }

  function onLetterItemsClick(e) {
    if (e.target.closest("[data-change-flags]")) { setStep("flags"); return; }
    if (e.target.closest("#btn-add-item")) {
      state.manualItems.push({ code: "", description: "", note: "" });
      renderLetterItems();
      $(`#mi-${state.manualItems.length - 1}-code`).focus();
      return;
    }
    const rm = e.target.closest("[data-remove-item]");
    if (rm) { state.manualItems.splice(parseInt(rm.dataset.removeItem, 10), 1); renderLetterItems(); }
  }

  function onLetterItemsInput(e) {
    const input = e.target.closest("input[data-mi]");
    if (input) state.manualItems[parseInt(input.dataset.mi, 10)][input.dataset.f] = input.value;
  }

  async function writeLetter() {
    const type = letterType();
    const ctx = {
      provider_name: $("#tpl-provider").value.trim(),
      patient_name: $("#tpl-patient").value.trim(),
      account_number: $("#tpl-account").value.trim(),
      service_date: $("#tpl-date").value.trim(),
      patient_contact: $("#tpl-contact").value.trim(),
    };
    if (type === "dispute") {
      const items = state.letterMode === "flow"
        ? itemsFromFlags()
        : state.manualItems.filter((it) => it.code || it.description).map((it) => ({ ...it, note: it.note || "Please confirm this charge." }));
      if (!items.length) { toast("Add at least one charge to ask about.", true); return; }
      ctx.items = items;
      if (state.letterMode === "flow" && flow.billId) {
        const picked = flow.flags.filter((f) => f.include && f.status !== "dismissed");
        ctx.flag_ids = picked.filter((f) => f.id != null).map((f) => f.id);
        ctx.items = itemsFromFlags(picked.filter((f) => f.id == null));   // the ones the browser caught by itself
      }
    }
    if (state.letterMode === "flow" && flow.billId) ctx.bill_id = flow.billId;
    const useAi = $("#tpl-use-ai").checked;
    const btn = $("#btn-write-letter");
    setBusy(btn, true, useAi ? "Writing with AI…" : "Writing your letter…");
    try {
      const r = await API.renderTemplate(type === "dispute" ? "dispute_charge" : "request_itemized_bill", ctx, useAi);
      $("#tpl-subject").value = r.subject || "";
      $("#tpl-body").value = r.body || "";
      toast("Your letter is ready. Edit anything you like.");
      if (window.innerWidth < 820) $("#tpl-subject").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      if (err.status === 402) { toast("Letters about specific charges are part of the paid plan.", true); go("pricing"); }
      else toast(err.message, true);
    } finally { setBusy(btn, false); }
  }

  function sendLetterEmail() {
    const to = $("#tpl-to").value.trim();
    const subject = $("#tpl-subject").value;
    const body = $("#tpl-body").value;
    if (!body) { toast("Write your letter first.", true); return; }
    window.location.href = "mailto:" + encodeURIComponent(to) + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
    toast("Opening your email app…");
  }

  function copyLetter() {
    const text = ($("#tpl-subject").value ? $("#tpl-subject").value + "\n\n" : "") + $("#tpl-body").value;
    if (!text.trim()) { toast("Write your letter first.", true); return; }
    const done = () => toast("Letter copied.");
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text) ? done() : toast("Couldn't copy. Select the text and copy it yourself.", true));
    } else if (fallbackCopy(text)) done();
    else toast("Couldn't copy. Select the text and copy it yourself.", true);
  }
  function fallbackCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    ta.remove();
    return ok;
  }

  async function downloadAnnotated() {
    if (!flow.billId) return;
    const btn = $("#btn-download-annotated");
    setBusy(btn, true, "Making your PDF…");
    try {
      const blob = await API.fetchAnnotatedPdf(flow.billId, prefLang());
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "candorify-review.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast("Downloaded. Your original bill is unchanged.");
    } catch (err) { toast(err.message, true); }
    finally { setBusy(btn, false); }
  }

  // step 6, finish + survey
  // options can be plain strings or [value, label] pairs (value gets sent, label is what ppl read)
  function pillsHTML(name, options, checked, required) {
    return options.map((o, i) => {
      const [value, label] = Array.isArray(o) ? o : [o, o];
      return `<label class="pill-option"><input type="radio" name="${name}" value="${esc(value)}" ${value === checked ? "checked" : ""} ${required && i === 0 ? "required" : ""}><span>${esc(label)}</span></label>`;
    }).join("");
  }
  const picked = (name) => { const el = $(`input[name="${name}"]:checked`); return el ? el.value : null; };

  // these english codes are what get counted on the results page. dont rename them w/o telling Vrajesh!!
  const SV = {
    flag: [["accurate", "Accurate"], ["inaccurate", "Not accurate"], ["unsure", "Not sure"]],
    missed: [["yes", "Yes"], ["no", "No"], ["unsure", "Not sure"]],
    contact: [["yes", "Yes, already"], ["planning", "Planning to"], ["no", "No"]],
    confirmed: [["no", "My estimate"], ["yes", "Confirmed by my provider"]],
    helped: [["yes", "Yes"], ["somewhat", "A little"], ["no", "No"]],
  };

  function renderFinish() {
    const sample = flow.source === "sample";
    $("#finish-done").hidden = true;
    $("#survey-form").hidden = sample;
    $("#sample-finish").hidden = !sample;
    $("#survey-error").hidden = true;
    if (sample) return;
    $("#survey-flags").innerHTML = flow.flags.length
      ? `<h3 class="no-margin">Were our suggestions accurate?</h3><p class="muted no-margin">Your best guess is fine.</p>` +
        flow.flags.map((f, n) => `<fieldset class="question">
          <legend>${esc(kindLabel(f.kind))}</legend>
          <p class="hint">${esc(f.message)}</p>
          <div class="pill-group">${pillsHTML("sv-flag-" + n, SV.flag, f.status === "dismissed" ? "inaccurate" : null, true)}</div>
        </fieldset>`).join("")
      : `<p class="muted no-margin">We didn't flag anything on this bill.</p>`;
    $("#sv-missed").innerHTML = pillsHTML("sv-missed", SV.missed, null);
    $("#sv-contact").innerHTML = pillsHTML("sv-contact", SV.contact, null, true);
    $("#sv-confirmed").innerHTML = pillsHTML("sv-confirmed", SV.confirmed, "no");
    $("#sv-helped").innerHTML = pillsHTML("sv-helped", SV.helped, null, true);
    $("#sv-sat").innerHTML = pillsHTML("sv-sat", ["1", "2", "3", "4", "5"], null, true);
  }

  async function submitSurvey(e) {
    e.preventDefault();
    const err = $("#survey-error");
    const missingFlag = flow.flags.findIndex((f, n) => !picked("sv-flag-" + n));
    const checks = [
      [missingFlag >= 0, "Please answer every question about our suggestions.", `sv-flag-${missingFlag}`],
      [!picked("sv-contact"), "Please tell us if you've contacted your provider.", "sv-contact"],
      [!picked("sv-helped"), "Please tell us if Candorify helped you.", "sv-helped"],
      [!picked("sv-sat"), "Please rate Candorify from 1 to 5.", "sv-sat"],
    ];
    const problem = checks.find((c) => c[0]);
    if (problem) {
      err.textContent = problem[1];
      err.hidden = false;
      const target = $(`input[name="${problem[2]}"]`);
      if (target) target.focus();
      return;
    }
    err.hidden = true;
    const answers = flow.flags.map((f, n) => picked("sv-flag-" + n));
    const count = (v) => answers.filter((a) => a === v).length;
    await finalize({
      // og fields, backend already stores these
      estimated_savings: Math.max(0, num($("#sv-savings").value)),
      flags_shown: flow.flags.length,
      flags_marked_helpful: count("accurate"),
      satisfaction: parseInt(picked("sv-sat"), 10) || 0,
      // new ones for the results page
      flags_accurate: count("accurate"),
      flags_inaccurate: count("inaccurate"),
      flags_unsure: count("unsure"),
      missed_errors: picked("sv-missed"),          // "yes" | "no" | "unsure" | null
      contacted_provider: picked("sv-contact"),    // "yes" | "planning" | "no"
      savings_confirmed: picked("sv-confirmed") === "yes",
      helped: picked("sv-helped"),                 // "yes" | "somewhat" | "no"
    }, $("#btn-survey-submit"));
  }

  async function finalize(survey, btn) {
    setBusy(btn, true, "Deleting your data…");
    try {
      if (flow.billId) await API.finalizeUpload(flow.billId, survey);
      flow.billId = null;
      flow.finished = true;
      $("#survey-form").hidden = true;
      $("#finish-done").hidden = false;
      renderStepper();
      focusHeading($("#finish-done"));
    } catch (err) { toast(err.message, true); }
    finally { setBusy(btn, false); }
  }

  async function finishSample() {
    if (flow.billId) API.deleteBill(flow.billId).catch(() => {});
    resetFlow();
    toast("Sample deleted. Upload your own bill whenever you're ready.");
  }

  // code lookup drawer
  function openLookup(code, system) {
    if (!$("#lookup-drawer")) { go("lookup"); return; }   // drawer only exists on bill.html, everywhere else just go to the lookup page
    if (!API.isLoggedIn()) { go("check"); return; }
    state.lastFocus = document.activeElement;
    const drawer = $("#lookup-drawer");
    $("#drawer-backdrop").hidden = false;
    drawer.hidden = false;
    requestAnimationFrame(() => drawer.classList.add("is-open"));
    populateLangSelect($("#tc-lang"));
    if (code) {
      $("#tc-code").value = code;
      const sys = String(system || "").toUpperCase();
      if (["CPT", "HCPCS", "ICD"].includes(sys)) $("#tc-system").value = sys;
      lookupCode();
    } else {
      $("#tc-result").innerHTML = "";
    }
    setTimeout(() => $("#tc-code").focus(), 50);
    document.addEventListener("keydown", drawerKeys);
  }

  function closeLookup() {
    const drawer = $("#lookup-drawer");
    drawer.classList.remove("is-open");
    $("#drawer-backdrop").hidden = true;
    document.removeEventListener("keydown", drawerKeys);
    setTimeout(() => { drawer.hidden = true; }, 220);
    if (state.lastFocus && document.contains(state.lastFocus)) state.lastFocus.focus();
  }

  function drawerKeys(e) {
    if (e.key === "Escape") { closeLookup(); return; }
    if (e.key !== "Tab") return;
    const items = $$("#lookup-drawer button, #lookup-drawer input, #lookup-drawer select").filter((el) => !el.disabled && el.offsetParent !== null);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  async function lookupCode(e) {
    if (e) e.preventDefault();
    const code = $("#tc-code").value.trim();
    const system = $("#tc-system").value;
    const lang = $("#tc-lang").value || "en";
    const out = $("#tc-result");
    if (!code) { toast("Enter a billing code first.", true); $("#tc-code").focus(); return; }
    out.innerHTML = '<p class="loading">Looking it up…</p>';
    try {
      const r = await API.translateCode(code, system, lang);
      out.innerHTML = `<div class="lookup-result">
        <div class="meta">${esc(r.code)} · ${esc(r.code_system)}${r.source ? " · source: " + esc(r.source) : ""}</div>
        <p><strong>${esc(r.plain_english)}</strong></p>
        ${lang !== "en" && r.translated ? `<p>${esc(state.languages[lang] || lang)}: ${esc(r.translated)}</p>` : ""}
      </div>`;
    } catch (err) {
      out.innerHTML = `<p class="form-error">${esc(err.message)}</p>`;
    }
  }

  // --- terms ---
  // terms popup just copies the terms page so we only ever edit the text in terms.html
  function termsHTML() {
    const body = $("#legal-body");
    if (!body) return "";
    const copy = body.cloneNode(true);
    copy.querySelectorAll("[id]").forEach((el) => el.removeAttribute("id"));
    return copy.innerHTML;
  }
  async function openTerms() {
    const d = $("#terms-dialog");
    let html = termsHTML();
    if (!html) {
      // not on terms.html? borrow the text from it. if that fails just open the page
      try {
        const page = new DOMParser().parseFromString(await (await fetch(PAGES.legal)).text(), "text/html");
        const body = page.getElementById("legal-body");
        if (body) { body.querySelectorAll("[id]").forEach((el) => el.removeAttribute("id")); html = body.innerHTML; }
      } catch (e) { /* fall through */ }
    }
    if (!html) { window.open(PAGES.legal, "_blank", "noopener"); return; }
    $("#terms-text").innerHTML = html;
    if (typeof d.showModal === "function") d.showModal(); else d.setAttribute("open", "");
  }
  function closeTerms() {
    const d = $("#terms-dialog");
    if (typeof d.close === "function") d.close(); else d.removeAttribute("open");
  }

  // PRICING
  async function renderPricing() {
    let cfg = { paid_features: [], mock_mode: true };
    try { cfg = await API.paymentConfig(); } catch (e) { /* keep defaults */ }
    // basic / premium / business lists live in plans.html now. only swap the premium list if the backend sends its own
    if (cfg.paid_features && cfg.paid_features.length) $("#paid-features").innerHTML = cfg.paid_features.map((f) => `<li>${esc(f)}</li>`).join("");
    $("#pay-mode-note").textContent = cfg.mock_mode ? "Test mode: no real charge is made." : "Secure checkout with Stripe.";
    const btn = $("#btn-upgrade");
    btn.textContent = isPaid() ? "You're on the paid plan" : (API.features.payments ? "Upgrade" : "Coming soon");
    btn.disabled = isPaid() || !API.features.payments;
    if (!API.features.payments) $("#pay-mode-note").textContent = "Paid plans are coming soon. Everything here is free for now.";
  }

  async function startUpgrade() {
    if (!API.isLoggedIn()) { state.pendingView = "pricing"; showAuth("register", "Create a free account first, then you can upgrade."); return; }
    const btn = $("#btn-upgrade");
    setBusy(btn, true, "Starting checkout…");
    try {
      const res = await API.startCheckout();
      if (res.mock) {
        const sid = new URL(res.checkout_url, window.location.origin).searchParams.get("session_id");
        await API.confirmCheckout(sid);
        await refreshUser();
        toast("Upgraded (test mode). Paid features are unlocked.");
        go("account");
      } else {
        window.location.href = res.checkout_url;
      }
    } catch (err) { toast(err.message, true); }
    finally { setBusy(btn, false); renderPricing(); }
  }

  // account
  async function renderAccount() {
    const wrap = $("#account-detail");
    if (!state.user) { wrap.innerHTML = '<p class="muted">Log in to see your account.</p>'; return; }
    let policy = { retention_days: 30, summary: "" };
    try { policy = await API.privacyPolicy(); } catch (e) { /* keep defaults */ }
    const lang = state.languages[prefLang()] || prefLang();
    wrap.innerHTML = `
      <div class="card">
        <div class="account-row"><span class="muted">Email</span><strong>${esc(state.user.email)}</strong></div>
        <div class="account-row"><span class="muted">Plan</span><span class="badge ${isPaid() ? "badge-brand" : ""}">${isPaid() ? "Paid" : "Free"}</span></div>
        <div class="account-row"><span class="muted">Explanations in</span><strong>${esc(lang)}</strong></div>
        <div class="row" style="margin-top:16px">
          ${isPaid() ? "" : '<button type="button" class="btn btn-primary" id="acc-upgrade">See paid plan</button>'}
          <button type="button" class="btn btn-secondary" id="acc-signout">Sign out</button>
        </div>
      </div>
      <div class="card" style="margin-top:16px">
        <h2 class="h3">Your privacy</h2>
        ${policy.summary ? `<p class="muted">${esc(policy.summary)}</p>` : ""}
        <p class="muted">Uploaded bills are deleted when you finish, or automatically after <strong>${esc(policy.retention_days)} days</strong>.</p>
      </div>
      <div class="card danger-zone">
        <h2 class="h3">Delete your account</h2>
        <p class="muted">This permanently deletes your account and everything connected to it. It can't be undone.</p>
        <button type="button" class="btn btn-danger" id="acc-delete">Delete my account and data</button>
      </div>`;
    if ($("#acc-upgrade")) $("#acc-upgrade").onclick = () => go("pricing");
    $("#acc-signout").onclick = signOut;
    $("#acc-delete").onclick = async () => {
      if (!confirm("Permanently delete your account and all your data? This can't be undone.")) return;
      try {
        await API.deleteMe();
        API.setToken("");
        state.user = null;
        window.location.href = "home.html";
      } catch (err) { toast(err.message, true); }
    };
  }

  // ========== results page (public) ==========
  // numbers ONLY come from real surveys and the page stays hidden til we have 10 reviews
  // no fake stats on the live site. ever.
  const STATS_MIN_REVIEWS = 10;
  const STATS_REFRESH_MS = 60000;
  const FU_OUTCOMES = [
    ["corrected", "They fixed some or all of it"],
    ["charges_were_right", "They said the charges were right"],
    ["waiting", "Still waiting"],
    ["not_contacted", "I didn't contact them"],
  ];
  let statsTimer = null;

  function stopStatsRefresh() { clearInterval(statsTimer); statsTimer = null; }

  function renderResults() {
    loadStats();
    stopStatsRefresh();
    statsTimer = setInterval(() => { if (state.view === "results" && !document.hidden) loadStats(); }, STATS_REFRESH_MS);
    const loggedIn = API.isLoggedIn();
    $("#followup-form").hidden = !loggedIn;
    $("#followup-login").hidden = loggedIn;
    if (loggedIn && !$("#fu-outcome").children.length) {
      $("#fu-outcome").innerHTML = pillsHTML("fu-outcome", FU_OUTCOMES, null, true);
    }
  }

  const pct = (part, whole) => (whole > 0 ? (part / whole) * 100 : 0);
  const fmtPct = (x) => (x >= 99.95 || x === 0 ? x.toFixed(0) : x.toFixed(1)) + "%";
  const usd = (n) => "$" + Math.round(num(n)).toLocaleString("en-US");

  async function loadStats() {
    const out = $("#stats-live");
    let s;
    try { s = await API.publicStats(); }
    catch (e) {
      out.innerHTML = '<p class="muted stats-empty">Our results aren\'t available right now. Please try again later.</p>';
      return;
    }
    const n = (k) => num(s[k]);
    const reviews = n("reviews");
    const when = s.updated_at ? new Date(s.updated_at) : new Date();
    $("#stats-updated").textContent = "Updated " + when.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

    if (reviews < STATS_MIN_REVIEWS) {
      out.innerHTML = `<div class="stats-empty"><p class="nlist-big">Not enough reviews yet</p>
        <p class="muted">We'll share numbers once ${STATS_MIN_REVIEWS} people have finished a review. So far: ${reviews}.</p></div>`;
      return;
    }

    const acc = n("flags_accurate"), inacc = n("flags_inaccurate"), rated = acc + inacc;
    const accRate = pct(acc, rated), wrongRate = pct(inacc, rated);
    const helped = n("helped_yes") + n("helped_somewhat"), notHelped = n("helped_no");
    const contacted = n("contacted_yes"), contactAnswers = contacted + n("contacted_planning") + n("contacted_no");
    const missedAnswers = n("missed_yes") + n("missed_no");
    const satAvg = n("satisfaction_count") ? n("satisfaction_total") / n("satisfaction_count") : 0;
    const confirmed = n("savings_confirmed_total"), reported = confirmed + n("savings_estimated_total");
    const fu = n("followups");

    const meter = (value, goal, goalText, met, scaleMax) => `
      <div class="meter" role="img" aria-label="${fmtPct(value)}. ${goalText}">
        <span style="width:${Math.min(100, (value / scaleMax) * 100).toFixed(1)}%"></span>
        <i style="left:${((goal / scaleMax) * 100).toFixed(1)}%"></i>
      </div>
      <p class="cap meter-goal ${met ? "is-met" : ""}">${goalText} · ${met ? "Goal met" : "Not there yet"}</p>`;

    out.innerHTML = `
      ${s.sample ? '<p class="stats-sample">Preview: these are sample numbers, not real results.</p>' : ""}
      <div class="stats-meters">
        <div class="stats-meter">
          <p class="cap">Suggestions rated accurate</p>
          <p class="stats-big">${fmtPct(accRate)}</p>
          ${meter(accRate, 95, "Goal: 95% or more", accRate >= 95, 100)}
          <p class="muted small">${acc.toLocaleString("en-US")} of ${rated.toLocaleString("en-US")} rated suggestions</p>
        </div>
        <div class="stats-meter">
          <p class="cap">Suggestions rated not accurate</p>
          <p class="stats-big">${fmtPct(wrongRate)}</p>
          ${meter(wrongRate, 5, "Goal: under 5%", wrongRate < 5, 20)}
          <p class="muted small">${inacc.toLocaleString("en-US")} of ${rated.toLocaleString("en-US")} rated suggestions</p>
        </div>
      </div>
      <ol class="nlist-rows stats-rows">
        <li><p class="nlist-big">${helped.toLocaleString("en-US")} helped</p><p class="nlist-meta">People who said Candorify helped them, at least a little</p><p class="nlist-year">${fmtPct(pct(helped, helped + notHelped))}</p></li>
        <li><p class="nlist-big">${notHelped.toLocaleString("en-US")} not helped</p><p class="nlist-meta">People who said it didn't help this time</p><p class="nlist-year">${fmtPct(pct(notHelped, helped + notHelped))}</p></li>
        <li><p class="nlist-big">${usd(reported)}</p><p class="nlist-meta">Savings patients reported, mostly their own estimates. ${usd(confirmed)} confirmed by providers</p><p class="nlist-year">(Reported)</p></li>
        <li><p class="nlist-big">${fmtPct(pct(contacted, contactAnswers))} reached out</p><p class="nlist-meta">Had already contacted their provider by the end of the review</p><p class="nlist-year">(Contact)</p></li>
        ${fu ? `<li><p class="nlist-big">${n("followup_corrected").toLocaleString("en-US")} of ${fu.toLocaleString("en-US")} fixed</p><p class="nlist-meta">Follow-ups where the provider fixed some or all of the charges</p><p class="nlist-year">(Follow-up)</p></li>` : ""}
        ${missedAnswers ? `<li><p class="nlist-big">${fmtPct(pct(n("missed_yes"), missedAnswers))} missed</p><p class="nlist-meta">People who found a mistake we didn't flag</p><p class="nlist-year">(Missed)</p></li>` : ""}
        <li><p class="nlist-big">${satAvg.toFixed(1)} / 5</p><p class="nlist-meta">Average rating</p><p class="nlist-year">(Rating)</p></li>
        <li><p class="nlist-big">${reviews.toLocaleString("en-US")} reviews</p><p class="nlist-meta">Finished reviews with a completed survey</p><p class="nlist-year">(Total)</p></li>
      </ol>`;
  }

  async function submitFollowUp(e) {
    e.preventDefault();
    const outcome = picked("fu-outcome");
    const err = $("#fu-error");
    if (!outcome) { err.textContent = "Please choose what your provider said."; err.hidden = false; $('input[name="fu-outcome"]').focus(); return; }
    err.hidden = true;
    const btn = $("#btn-followup");
    setBusy(btn, true, "Sending…");
    try {
      await API.submitFollowUp({ outcome, amount_saved: outcome === "corrected" ? Math.max(0, num($("#fu-amount").value)) : 0 });
      $("#followup-out").innerHTML = '<p class="followup-thanks">Thank you. Your answer is now part of our results.</p>';
      loadStats();
    } catch (err2) { toast(err2.message, true); }
    finally { setBusy(btn, false); }
  }

  // lab test on made up bills (needs an account bc it runs on the server)
  async function runAccuracy() {
    const out = $("#accuracy-result");
    const btn = $("#btn-run-accuracy");
    setBusy(btn, true, "Testing…");
    out.innerHTML = '<p class="loading">Checking 100 sample bills with known mistakes…</p>';
    try {
      const r = await API.score(100);
      const p = (x) => (num(x) * 100).toFixed(1) + "%";
      out.innerHTML = `
        <div class="stat-grid">
          <div class="stat"><strong>${p(r.recall)}</strong><span>of mistakes caught</span></div>
          <div class="stat"><strong>${p(r.precision)}</strong><span>of flags were real mistakes</span></div>
          <div class="stat"><strong>${p(r.false_positive_rate)}</strong><span>false alarm rate</span></div>
        </div>
        <p class="target ${r.meets_target ? "met" : "not-met"}">${r.meets_target ? "Goal met" : "Goal not met yet"}: catch at least 95% of mistakes with under 5% false alarms.</p>
        <p class="hint">Tested on ${esc(r.bills_evaluated)} sample bills. Caught ${esc(r.true_positives)}, missed ${esc(r.false_negatives)}, false alarms ${esc(r.false_positives)}.</p>`;
    } catch (err) { out.innerHTML = ""; toast(err.message, true); }
    finally { setBusy(btn, false); }
  }

  // startup data
  async function loadDisclaimer() {
    try { const d = await API.disclaimer(); $$(".disclaimer-text").forEach((el) => { el.textContent = d.text; }); }
    catch (e) {
      $$(".disclaimer-text").forEach((el) => { el.textContent = "Candorify points out possible billing issues for you to review. It does not confirm errors or give legal, medical, or financial advice."; });
    }
  }
  async function loadLanguages() {
    try { state.languages = await API.languages(); } catch (e) { /* keep English */ }
    ["#tc-lang", "#auth-lang", "#translate-lang"].forEach((s) => populateLangSelect($(s)));
  }

  // hamburger menu
  function openMenu() {
    state.lastFocus = document.activeElement;
    $("#menu-backdrop").hidden = false;
    const m = $("#site-menu");
    m.hidden = false;
    requestAnimationFrame(() => m.classList.add("is-open"));
    $("#menu-btn").setAttribute("aria-expanded", "true");
    document.addEventListener("keydown", menuKeys);
    setTimeout(() => { const first = $("#site-menu .menu-list li:not([hidden]) button"); if (first) first.focus(); }, 60);
  }
  function closeMenu(restoreFocus = true) {
    const m = $("#site-menu");
    if (m.hidden) return;
    m.classList.remove("is-open");
    $("#menu-backdrop").hidden = true;
    $("#menu-btn").setAttribute("aria-expanded", "false");
    document.removeEventListener("keydown", menuKeys);
    setTimeout(() => { m.hidden = true; }, 220);
    if (restoreFocus && state.lastFocus && document.contains(state.lastFocus)) state.lastFocus.focus();
  }
  function menuKeys(e) {
    if (e.key === "Escape") { closeMenu(); return; }
    if (e.key !== "Tab") return;
    const items = $$("#site-menu button").filter((el) => el.offsetParent !== null);
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  function scrollToId(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - 76;
    window.scrollTo({ top, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  // ---------- wiring (connecting buttons to stuff) ----------
  // each page only has some of these buttons so on() just skips the ones that arent there
  function on(sel, ev, fn) { const el = $(sel); if (el) el.addEventListener(ev, fn); }

  function wire() {
    document.addEventListener("click", (e) => {
      if (e.target.closest("#site-menu button")) closeMenu(false);
      const scrollBtn = e.target.closest("[data-scroll]");
      if (scrollBtn) {
        if (onThisPage("home")) { showView("home"); scrollToId(scrollBtn.dataset.scroll); }
        else window.location.href = PAGES.home + "#" + scrollBtn.dataset.scroll;
        return;
      }
      if (e.target.closest("[data-founder]")) {
        if (onThisPage("team")) { go("team"); scrollToId("founder"); }
        else window.location.href = PAGES.team + "#founder";
        return;
      }
      const goBtn = e.target.closest("[data-go]");
      if (goBtn) { if (goBtn.closest("#terms-dialog")) closeTerms(); go(goBtn.dataset.go); return; }
      const authBtn = e.target.closest("[data-auth]");
      if (authBtn) { state.pendingView = null; showAuth(authBtn.dataset.auth); return; }
      if (e.target.closest("[data-lookup]")) { openLookup(); return; }
      if (e.target.closest("[data-terms]")) { e.preventDefault(); openTerms(); return; }
      if (e.target.closest("[data-step-back]")) { prevStep(); return; }
      const stepBtn = e.target.closest("[data-step-go]");
      if (stepBtn && !stepBtn.disabled) { setStep(stepBtn.dataset.stepGo); return; }
    });

    // auth
    $$("[data-auth-tab]").forEach((b) => b.addEventListener("click", () => setAuthMode(b.dataset.authTab)));
    on("#auth-form", "submit", handleAuthSubmit);
    $$("[data-oauth]").forEach((b) => b.addEventListener("click", () => startOAuth(b.dataset.oauth)));
    on("#pw-toggle", "click", () => {
      const pw = $("#auth-password");
      const show = pw.type === "password";
      pw.type = show ? "text" : "password";
      $("#pw-toggle").textContent = show ? "Hide" : "Show";
      $("#pw-toggle").setAttribute("aria-pressed", String(show));
    });

    // step 1
    on("#pdf-file", "change", (e) => chooseFile(e.target.files[0]));
    on("#btn-clear-file", "click", clearFile);
    const dz = $("#dropzone");
    if (dz) {
      ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("is-over"); }));
      ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("is-over"); }));
      dz.addEventListener("drop", (e) => chooseFile(e.dataTransfer.files[0]));
    }
    on("#btn-upload", "click", doUpload);
    on("#btn-sample", "click", loadSample);
    on("#btn-need-itemized", "click", () => { go("letters"); setLetterType("request"); });
    on("#btn-start-over", "click", startOver);

    // step 2
    on("#lines", "click", onLinesClick);
    on("#lines", "input", onLinesInput);
    on("#rev-total", "input", renderTotals);
    on("#btn-add-line", "click", addLine);
    on("#btn-charges-next", "click", continueFromCharges);

    // step 3
    on("#questions-form", "submit", (e) => { e.preventDefault(); collectAnswers(); runChecks($("#btn-questions-next")); });

    // step 4
    on("#flags-list", "change", onFlagsChange);
    on("#questions-list", "change", (e) => {
      const box = e.target.closest("input[data-not-sure]");
      if (!box) return;
      const field = $("#q-" + box.dataset.notSure);
      field.disabled = box.checked;
      if (box.checked) field.value = "";
      else field.focus();
    });
    on("#flags-list", "click", onFlagsClick);
    on("#btn-translate", "click", translateLines);
    on("#btn-benchmark", "click", benchmarkLines);
    on("#btn-flags-next", "click", () => setStep("letter"));

    // step 5 / letters
    $$('input[name="letter-type"]').forEach((r) => r.addEventListener("change", () => { setLetterType(r.value); renderLetterItems(); }));
    on("#letter-items", "click", onLetterItemsClick);
    on("#letter-items", "input", onLetterItemsInput);
    on("#btn-write-letter", "click", writeLetter);
    on("#btn-send-email", "click", sendLetterEmail);
    on("#btn-copy-letter", "click", copyLetter);
    on("#btn-download-annotated", "click", downloadAnnotated);
    on("#btn-letter-next", "click", () => setStep("finish"));

    // step 6
    on("#survey-form", "submit", submitSurvey);
    on("#survey-form", "change", () => { $("#survey-error").hidden = true; });
    // skipping still deletes the bill. skipped: true tells the backend not to count it in the results
    on("#btn-survey-skip", "click", () => finalize({ skipped: true, estimated_savings: 0, flags_shown: 0, flags_marked_helpful: 0, satisfaction: 0 }, $("#btn-survey-skip")));
    on("#btn-sample-done", "click", finishSample);
    on("#btn-check-another", "click", resetFlow);

    // lookup drawer
    on("#tc-form", "submit", lookupCode);
    on("#lookup-close", "click", closeLookup);
    on("#drawer-backdrop", "click", closeLookup);

    // menu
    on("#menu-btn", "click", openMenu);
    on("#menu-close", "click", () => closeMenu());
    on("#menu-backdrop", "click", () => closeMenu());

    // terms
    on("#terms-close", "click", closeTerms);
    on("#terms-dialog", "click", (e) => { if (e.target.id === "terms-dialog") closeTerms(); });

    // pricing + results
    on("#btn-upgrade", "click", startUpgrade);
    on("#btn-run-accuracy", "click", runAccuracy);
    on("#followup-form", "submit", submitFollowUp);
    on("#fu-outcome", "change", () => { $("#fu-amount-wrap").hidden = picked("fu-outcome") !== "corrected"; });
  }

  // the phone app's back button uses this (js/mobile.js)
  function back() {
    if (!$("#site-menu").hidden) { closeMenu(); return true; }
    if ($("#lookup-drawer") && !$("#lookup-drawer").hidden) { closeLookup(); return true; }
    if (state.view === "check") {
      const i = STEPS.indexOf(flow.step);
      if (i > 0 && !flow.finished && flow.step !== "finish") { prevStep(); return true; }
      return false;
    }
    if (API.isLoggedIn()) { go("check"); return true; }
    if (state.view !== "home") { go("home"); return true; }
    return false;
  }

  // hides buttons for stuff the backend cant do yet (API.features in api.js)
  function hideUnfinished() {
    const f = API.features;
    const hide = (sel) => { const el = $(sel); if (el) el.hidden = true; };
    if (!f.aiLetters && $("#tpl-use-ai")) { $("#tpl-use-ai").checked = false; hide("label:has(#tpl-use-ai)"); }
    if (!f.medicare) hide("#btn-benchmark");
    if (!f.payments) hide("#tools-card .badge");
  }

  async function init() {
    wire();
    hideUnfinished();
    const page = document.body.dataset.view;   // which page this is (set on <body> in each html file)
    if (onThisPage("auth")) setAuthMode(document.body.dataset.authMode || "login");
    if (onThisPage("check")) setStep("start");
    handleOAuthReturn();
    loadDisclaimer();
    loadLanguages();
    await refreshUser();

    // stripe sends ppl back here w ?session_id=
    const params = new URLSearchParams(window.location.search);
    if (params.get("session_id") && API.isLoggedIn()) {
      try {
        await API.confirmCheckout(params.get("session_id"));
        await refreshUser();
        history.replaceState(null, "", window.location.pathname);
        toast("Payment confirmed. Paid features are unlocked!");
        go("account");
        return;
      } catch (e) { /* fall through */ }
    }
    if (page === "auth") {
      state.pendingView = params.get("next");
      go("auth");
      const msg = params.get("msg");
      if (msg && onThisPage("auth")) { $("#auth-prompt").textContent = msg; $("#auth-prompt").hidden = false; }
      return;
    }
    // links like home.html#why or team.html#founder -> show the page + scroll there
    const target = window.location.hash.slice(1);
    if (page === "home" && target) showView("home"); else go(page || "home");
    if (target && document.getElementById(target)) setTimeout(() => scrollToId(target), 80);
  }

  window.CandorifyApp = { go, back };
  document.addEventListener("DOMContentLoaded", init);
})();

// just so everyone knows - SOME AI was used to help assist in writing a few of these features
