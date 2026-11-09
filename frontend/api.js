/*
  every call to the backend goes thru this file.
  it basically translates between the site and Vrajesh's backend (Candorify-Test/backend)
  so the rest of the front end didnt have to change much

  API_BASE -> set at the bottom of each html page. localhost while we test,
  the render link (or "") when it's live. desktop/phone app sets its own
*/
(function (global) {
  const API_BASE = global.CANDORIFY_API_BASE || "";
  const TOKEN_KEY = "candorify_token";
  const LANG_KEY = "candorify_lang";

  // incognito can block storage so we just keep the login in memory instead of crashing
  const memory = {};
  function store(kind) {
    try {
      const s = global[kind];
      const probe = "__candorify_probe__";
      s.setItem(probe, "1"); s.removeItem(probe);
      return s;
    } catch (e) {
      return {
        getItem: (k) => (k in memory ? memory[k] : null),
        setItem: (k, v) => { memory[k] = String(v); },
        removeItem: (k) => { delete memory[k]; },
      };
    }
  }
  const persistent = store("localStorage");
  const session = store("sessionStorage");

  function getToken() { return session.getItem(TOKEN_KEY) || persistent.getItem(TOKEN_KEY) || ""; }
  function setToken(token, remember) {
    session.removeItem(TOKEN_KEY);
    persistent.removeItem(TOKEN_KEY);
    if (token) (remember ? persistent : session).setItem(TOKEN_KEY, token);
  }
  function isLoggedIn() { return !!getToken(); }

  function authHeaders() {
    const h = {};
    if (getToken()) h["Authorization"] = "Bearer " + getToken();
    return h;
  }

  async function parse(res) {
    const text = await res.text();
    try { return text ? JSON.parse(text) : null; } catch (e) { return text; }
  }

  // backend errors always come back as {"detail": "readable message"}
  function failure(res, data, fallback) {
    const detail = data && data.detail
      ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))
      : (fallback || "Request failed (" + res.status + ")");
    const err = new Error(detail);
    err.status = res.status;
    return err;
  }

  async function request(path, { method = "GET", body, auth = true } = {}) {
    const headers = auth ? authHeaders() : {};
    const opts = { method, headers };
    if (body !== undefined) {
      opts.body = JSON.stringify(body);
      headers["Content-Type"] = "application/json";
    }
    let res;
    try { res = await fetch(API_BASE + path, opts); }
    catch (e) { throw new Error("Can't reach Candorify right now. Check your connection and try again."); }
    const data = await parse(res);
    if (!res.ok) throw failure(res, data);
    return data;
  }

  const notYet = (what) => Promise.reject(Object.assign(new Error(what + " isn't available yet."), { status: 501 }));
  const query = (params) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") q.set(k, v); });
    const s = q.toString();
    return s ? "?" + s : "";
  };
  const lang = (l) => (l && l !== "en" ? l : null);   // english is the default, no point sending it

  // ---------- backend answers -> what the site expects ----------
  // flag statuses: backend = investigating / add_to_letter / dismissed, site = open / confirmed / dismissed. Vrajesh if u rename these on ur end pls tell me
  const STATUS_IN = { investigating: "open", add_to_letter: "confirmed", dismissed: "dismissed" };
  const STATUS_OUT = { open: "investigating", confirmed: "add_to_letter", dismissed: "dismissed" };

  function toLines(bill) {
    return (bill.lines || []).map((l) => ({
      id: l.line_no, position: l.line_no - 1, code: l.code, code_system: "CPT", description: l.description,
      quantity: Number(l.quantity), unit_price: Number(l.unit_price), line_total: Number(l.line_total), plain_english: "",
    }));
  }
  function toFlag(f) {
    const nums = f.line_numbers && f.line_numbers.length ? f.line_numbers : (f.line_no ? [f.line_no] : []);
    return { id: f.id, kind: f.rule, message: f.message, status: STATUS_IN[f.status] || "open",
      line_refs: nums.map((n) => n - 1), question_id: f.question_id || null };
  }
  function toQuestions(qs) {
    return (qs || []).map((q) => ({
      id: q.id, type: q.answer_type, text: q.text,
      choices: q.choices ? q.choices.map((c) => c.value) : undefined,         // english, gets sent back
      choice_labels: q.choices ? q.choices.map((c) => c.label) : undefined,  // the patient's language, shown on screen
      line_refs: (q.line_refs || []).map((n) => n - 1),
    }));
  }
  function toUpload(r) {
    const b = r.bill;
    snapshot(b.id, signature(b.lines, b.stated_subtotal, b.date_of_service));
    return {
      bill_id: b.id, label: b.label, provider_name: "", service_date: b.date_of_service || "",
      stated_total: Number(b.stated_subtotal), line_items: toLines(b),
      flags: ((r.flags && r.flags.flags) || []).map(toFlag), questions: toQuestions(r.questions),
      bill_format: r.bill_format || "itemized", notice: r.notice || null,
    };
  }

  // remembers each uploaded bill the way the backend has it so we can tell if they edited stuff on the charges step
  const snapshots = {};
  const snapshot = (id, sig) => { snapshots[id] = sig; };
  const money = (n) => Number(Number(n || 0).toFixed(2));
  function signature(lines, total, date) {
    return JSON.stringify([(lines || []).map((l) => [String(l.code || ""), String(l.description || ""),
      Number(l.quantity), money(l.unit_price), money(l.line_total)]), money(total), date || ""]);
  }

  const API = {
    getToken, setToken, isLoggedIn,
    // stuff the backend can't do yet. the site hides those buttons until these flip to true
    features: { payments: false, medicare: false, annotatedPdf: false, aiLetters: false },

    health: () => request("/health", { auth: false }),
    disclaimer: () => notYet("The disclaimer"),   // site falls back to its own wording

    // accounts
    register: async (email, password, preferred_language, accept_terms, remember_me = false) => {
      persistent.setItem(LANG_KEY, preferred_language || "en");
      return request("/api/auth/register", { method: "POST", auth: false, body: { email, password, remember_me } });
    },
    login: (email, password, remember_me = false) =>
      request("/api/auth/login", { method: "POST", auth: false, body: { email, password, remember_me } }),
    // no plans or language on accounts in the backend yet so everyone's on free
    // and whatever language they picked at sign up just lives in this browser
    me: async () => Object.assign(await request("/api/me"),
      { tier: "free", preferred_language: persistent.getItem(LANG_KEY) || "en" }),
    oauthUrl: (provider, remember_me) =>
      API_BASE + "/api/auth/" + encodeURIComponent(provider) + "/login?remember_me=" + (remember_me ? "true" : "false"),
    deleteMe: () => request("/api/me", { method: "DELETE" }),
    privacyPolicy: async () => ({ retention_days: 30, summary: "" }),

    // --- the check flow ---
    uploadPdf: async (file, language) => {
      const fd = new FormData();
      fd.append("file", file);
      if (lang(language)) fd.append("language", language);
      let res;
      try { res = await fetch(API_BASE + "/api/upload/pdf", { method: "POST", headers: authHeaders(), body: fd }); }
      catch (e) { throw new Error("Can't reach Candorify right now. Check your connection and try again."); }
      const data = await parse(res);
      if (!res.ok) {
        const err = failure(res, data, "We couldn't read that PDF. Make sure it's an itemized bill and try again.");
        if (/more than one bill/i.test(err.message)) err.message = "This PDF has more than one bill in it. Please upload one bill at a time.";
        throw err;
      }
      return toUpload(data);
    },
    // sample bill gets stored like a real one (flags + follow up qs and all)
    generate: async (opts = {}) => {
      const r = toUpload(await request("/api/upload/sample", { method: "POST",
        body: { defect: opts.inject_errors === false ? "none" : null, language: lang(opts.language) } }));
      return Object.assign(r, { id: r.bill_id, provider_name: "Sample bill" });
    },
    // if they edited the charges the backend needs the new version -> save it as a new bill
    // (delete the old one) then grab that bill's questions
    syncBill: async (billId, { lines, total, date, label, language }) => {
      const sig = signature(lines, total, date);
      if (snapshots[billId] === sig) return { bill_id: billId, changed: false };
      const bill = await request("/api/bills", { method: "POST", body: {
        label: label || null,
        stated_subtotal: money(total),
        date_of_service: /^\d{4}-\d{2}-\d{2}$/.test(date || "") ? date : null,
        lines: lines.map((l) => ({ code: String(l.code || "").trim(), description: String(l.description || "").trim(),
          quantity: Number(Number(l.quantity || 1).toFixed(3)), unit_price: money(l.unit_price), line_total: money(l.line_total) })),
      } });
      request("/api/bills/" + billId, { method: "DELETE" }).catch(() => {});
      snapshot(bill.id, signature(bill.lines, bill.stated_subtotal, bill.date_of_service));
      const q = await request("/api/bills/" + bill.id + "/questions" + query({ language: lang(language) }));
      return { bill_id: bill.id, changed: true, questions: toQuestions(q.questions) };
    },
    // answers go in, every flag on the bill comes out. "not sure" + skipped answers never make a flag
    submitReview: async ({ bill_id, answers }) => {
      const r = await request("/api/upload/review", { method: "POST", body: { bill_id, answers: answers || [] } });
      return { bill_id: r.bill_id, flags: ((r.flags && r.flags.flags) || []).map(toFlag) };
    },
    updateFlag: (flagId, status) =>
      request("/api/bills/flags/" + flagId, { method: "PATCH", body: { status: STATUS_OUT[status] || "investigating" } }),
    deleteBill: (id) => request("/api/bills/" + id, { method: "DELETE" }),
    translateBill: async (id, language) => {
      const r = await request("/api/bills/" + id + "/translate" + query({ language: lang(language) }));
      return { lines: (r.lines || []).map((l) => ({ position: l.line_no - 1, code: l.code,
        plain_english: (l.code_info && l.code_info.plain_english) || l.description, translated: l.plain_english_translated || "" })) };
    },
    benchmarkBill: () => notYet("Medicare price comparison"),
    fetchAnnotatedPdf: () => notYet("The marked-up PDF"),
    // survey isn't stored yet (on hold) so we just delete the bill. if it's already gone thats fine too
    finalizeUpload: async (billId) => {
      try { await request("/api/bills/" + billId, { method: "DELETE" }); }
      catch (e) { if (e.status !== 404) throw e; }
      return { ok: true };
    },

    // ------ code lookup ------
    languages: async () => {
      const list = await request("/api/languages", { auth: false });
      return Object.fromEntries(list.map((l) => [l.code, l.native || l.name]));
    },
    translateCode: async (code, system, language) => {
      const sys = { CPT: "CPT", HCPCS: "HCPCS", ICD: "ICD-10-CM" }[system] || null;
      const info = await request("/api/translate" + query({ code, system: sys }));
      const out = { code: info.code, code_system: info.system, plain_english: info.plain_english || info.description || info.message || "No description found for this code.",
        source: { nlm: "NLM Clinical Tables", fallback: "Candorify's code list", not_found: "" }[info.source] || "", translated: "" };
      if (lang(language) && info.plain_english) {
        const t = await request("/api/translate/text", { method: "POST", body: { language, texts: [info.plain_english] } });
        if (t.items && t.items[0] && t.items[0].translated) out.translated = t.items[0].text;
      }
      return out;
    },

    // LETTERS
    // letters come from the backend templates. w a bill -> dispute letter lists that bill's chosen flags
    // no bill (the letters page) -> lists whatever charges they typed in
    renderTemplate: async (template, ctx) => {
      const dispute = template === "dispute_charge";
      const body = {
        letter_type: dispute ? "dispute" : "request",
        patient_name: ctx.patient_name || null, provider_name: ctx.provider_name || null,
        account_number: ctx.account_number || null, date_of_service: ctx.service_date || null,
      };
      if (ctx.bill_id && (!dispute || (ctx.flag_ids && ctx.flag_ids.length))) {
        body.bill_id = ctx.bill_id;
        if (dispute) body.flag_ids = ctx.flag_ids;
      }
      if (dispute && ctx.items && ctx.items.length) body.items = ctx.items;
      const r = await request("/api/letters", { method: "POST", body });
      return { subject: dispute ? "Request for review of billing errors" : "Request for an itemized bill", body: r.text };
    },

    // plans (not built yet)
    paymentConfig: async () => ({ paid_features: [], mock_mode: true }),
    startCheckout: () => notYet("Paid plans"),
    confirmCheckout: () => notYet("Paid plans"),

    // our results
    // these feed the our results page (performance.html). Nat these are the ones that'll need the survey data once we actually save it
    publicStats: () => request("/api/stats/public", { auth: false }),
    score: () => request("/api/stats/lab-test", { auth: false }),
    submitFollowUp: (payload) => request("/api/survey/follow-up", { method: "POST", body: payload }),
  };

  global.CandorifyAPI = API;
})(window);

/* some AI was used to help assist w writing these features */
