/* Clara: Candorify's help assistant + contact form.
   Add to a page (after api.js / main.js):  <script src="clara.js" defer></script>
   - Loads clara.css from the same folder by itself.
   - Answers come from the backend (/api/clara/...), which uses our FAQ file.
   - "Contact us" messages go straight to the team's email through Web3Forms.
   - Any page form posting to Web3Forms is also sent without leaving the page. */
(function () {
  "use strict";
  if (window.__claraLoaded) return;
  window.__claraLoaded = true;

  var API = (window.CANDORIFY_API_BASE || "").replace(/\/+$/, "");
  var WEB3FORMS_URL = "https://api.web3forms.com/submit";
  var WEB3FORMS_KEY = "219d466a-6863-40df-95c5-1f72d5774b7e";   // only lets people send messages TO us
  var SAVE_KEY = "clara-chat-v1";            // this tab only (sessionStorage); cleared when the tab closes
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- styles ----------
  var me = document.currentScript;
  var cssHref = me && me.src ? me.src.replace(/clara\.js(\?.*)?$/, "clara.css") : "clara.css";
  if (!document.querySelector('link[data-clara]')) {
    var link = document.createElement("link");
    link.rel = "stylesheet"; link.href = cssHref; link.setAttribute("data-clara", "");
    document.head.appendChild(link);
  }

  // ---------- small helpers ----------
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function load() { try { return JSON.parse(sessionStorage.getItem(SAVE_KEY)) || null; } catch (e) { return null; } }
  function save() {
    try { sessionStorage.setItem(SAVE_KEY, JSON.stringify({ open: state.open, log: state.log.slice(-30) })); } catch (e) {}
  }
  function api(path, body) {
    return fetch(API + path, body ? {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    } : undefined).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Request failed");
        return data;
      });
    });
  }
  var LENS = '<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="11" fill="none" stroke="currentColor" stroke-width="2.2"/>' +
             '<path d="M14.5 17.5a6.5 6.5 0 0 1 5-4.6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';

  // ---------- build the widget ----------
  var root = el("div", "clara");
  root.innerHTML =
    '<button type="button" class="clara-launch" aria-expanded="false" aria-controls="clara-panel">' +
      '<span class="clara-lens">' + LENS + '</span><span class="clara-launch-text">Ask Clara</span>' +
    '</button>' +
    '<p class="clara-nudge" hidden>Questions about your bill? I can help.</p>' +
    '<section class="clara-panel" id="clara-panel" role="dialog" aria-modal="false" aria-labelledby="clara-name" hidden>' +
      '<header class="clara-head">' +
        '<span class="clara-lens clara-lens-sm">' + LENS + '</span>' +
        '<div class="clara-who"><h2 id="clara-name">Clara</h2><p>Answers from our help guide</p></div>' +
        '<button type="button" class="clara-icon clara-reset" aria-label="Start a new chat" title="New chat">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4.5h4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>' +
        '<button type="button" class="clara-icon clara-close" aria-label="Close Clara">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button>' +
      '</header>' +
      '<div class="clara-body">' +
        '<div class="clara-log" aria-live="polite"></div>' +
        '<form class="clara-contact" novalidate hidden>' +
          '<h3>Message the team</h3>' +
          '<p class="clara-sub">We\'ll reply by email. Please leave out medical details and account numbers.</p>' +
          '<label>Your name<input name="name" type="text" autocomplete="name" maxlength="80" required></label>' +
          '<label>Your email<input name="email" type="email" autocomplete="email" maxlength="120" required></label>' +
          '<label>Message<textarea name="message" rows="4" maxlength="2000" required></textarea></label>' +
          '<input type="checkbox" name="botcheck" class="clara-hp" tabindex="-1" autocomplete="off" aria-hidden="true">' +
          '<p class="clara-error" role="alert" hidden></p>' +
          '<div class="clara-row"><button type="button" class="clara-ghost clara-back">Back to chat</button>' +
          '<button type="submit" class="clara-primary">Send message</button></div>' +
        '</form>' +
        '<div class="clara-done" hidden>' +
          '<svg viewBox="0 0 52 52" aria-hidden="true"><circle cx="26" cy="26" r="23"/><path d="M15 27l7 7 15-16"/></svg>' +
          '<h3>Message sent</h3><p class="clara-sub"></p>' +
          '<button type="button" class="clara-ghost clara-back">Back to chat</button>' +
        '</div>' +
      '</div>' +
      '<form class="clara-compose">' +
        '<label class="clara-sr" for="clara-input">Ask Clara a question</label>' +
        '<input id="clara-input" type="text" maxlength="500" autocomplete="off" placeholder="Ask about your bill or Candorify">' +
        '<button type="submit" class="clara-send" aria-label="Send">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>' +
      '</form>' +
      '<p class="clara-note">Please don\'t share personal or medical details. Clara can\'t see your bill.</p>' +
    '</section>';

  var $ = function (s) { return root.querySelector(s); };
  var launch = $(".clara-launch"), panel = $(".clara-panel"), nudge = $(".clara-nudge");
  var log = $(".clara-log"), compose = $(".clara-compose"), input = $("#clara-input");
  var contact = $(".clara-contact"), done = $(".clara-done");

  var saved = load();
  var state = { open: false, started: false, busy: false, chips: [], log: (saved && saved.log) || [] };

  // ---------- chat log ----------
  function scrollDown() { log.scrollTop = log.scrollHeight; }

  function addBubble(who, text, animate) {
    var b = el("div", "clara-msg clara-" + who + (animate && !reduceMotion ? " is-new" : ""), text);
    log.appendChild(b);
    scrollDown();
    return b;
  }

  function addChips(list, withContact) {
    var old = log.querySelector(".clara-chips:last-child");
    if (old) old.remove();
    if (!list.length && !withContact) return;
    var row = el("div", "clara-chips");
    list.forEach(function (c, i) {
      var b = el("button", "clara-chip", c.label);
      b.type = "button"; b.style.setProperty("--i", i);
      b.addEventListener("click", function () { ask({ faq_id: c.id }, c.label); });
      row.appendChild(b);
    });
    if (withContact) {
      var m = el("button", "clara-chip clara-chip-contact", "Message the team");
      m.type = "button"; m.style.setProperty("--i", list.length);
      m.addEventListener("click", showContact);
      row.appendChild(m);
    }
    log.appendChild(row);
    scrollDown();
  }

  function remember(who, text) { state.log.push({ who: who, text: text }); save(); }

  function typing() {
    var t = el("div", "clara-msg clara-bot clara-typing");
    t.setAttribute("aria-label", "Clara is typing");
    t.innerHTML = "<i></i><i></i><i></i>";
    log.appendChild(t); scrollDown();
    return t;
  }

  function ask(body, shownText) {
    if (state.busy) return;
    state.busy = true;
    addBubble("user", shownText, true); remember("user", shownText);
    var dots = typing(), started = Date.now();
    api("/api/clara/ask", body).then(function (r) {
      return { answer: r.answer, related: r.related || [], contact: !!r.show_contact, source: r.source };
    }, function (err) {
      var busy = /break/.test(err.message);
      return { answer: busy ? err.message : "I can't reach our help service right now. You can still send the team a message.",
               related: [], contact: !busy };
    }).then(function (r) {
      var wait = Math.max(0, 450 - (Date.now() - started));   // a short pause reads more naturally
      setTimeout(function () {
        dots.remove();
        var b = addBubble("bot", r.answer, true); remember("bot", r.answer);
        if (r.source === "ai") b.appendChild(el("span", "clara-tag", "Worded with AI from our help guide"));
        addChips(r.related, r.contact);
        state.busy = false;
      }, reduceMotion ? 0 : wait);
    });
  }

  function start() {
    if (state.started) return;
    state.started = true;
    state.log.forEach(function (m) { addBubble(m.who, m.text, false); });
    api("/api/clara/start").then(function (r) {
      state.chips = r.chips || [];
      if (!state.log.length) { addBubble("bot", r.greeting, true); remember("bot", r.greeting); }
      addChips(state.chips, false);
    }, function () {
      if (!state.log.length) addBubble("bot", "Hi, I'm Clara. I can't reach our help service right now, but you can still message the team.", true);
      addChips([], true);
    });
  }

  function reset() {
    state.log = []; save();
    log.innerHTML = ""; state.started = false;
    showChat(); start(); input.focus();
  }

  // ---------- open / close ----------
  function open() {
    if (state.open) return;
    state.open = true; save();
    nudge.hidden = true;
    panel.hidden = false;
    void panel.offsetWidth;            // let the browser draw it closed first, so the opening animates
    root.classList.add("is-open");
    launch.setAttribute("aria-expanded", "true");
    start();
    setTimeout(function () { input.focus(); }, reduceMotion ? 0 : 260);
  }
  function close() {
    if (!state.open) return;
    state.open = false; save();
    root.classList.remove("is-open");
    launch.setAttribute("aria-expanded", "false");
    setTimeout(function () { if (!state.open) panel.hidden = true; }, reduceMotion ? 0 : 380);
    launch.focus();
  }

  // ---------- contact form ----------
  function showChat() { contact.hidden = true; done.hidden = true; log.hidden = false; compose.hidden = false; scrollDown(); }
  function showContact() {
    log.hidden = true; compose.hidden = true; done.hidden = true; contact.hidden = false;
    contact.querySelector("input[name=name]").focus();
  }

  function sendToTeam(fields) {
    return fetch(WEB3FORMS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(Object.assign({
        access_key: WEB3FORMS_KEY,
        subject: "New Candorify message from " + (fields.name || "the website"),
        from_name: "Candorify website",
        page: location.pathname
      }, fields))
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok || d.success === false) throw new Error(d.message || "Not sent");
        return d;
      });
    });
  }

  contact.addEventListener("submit", function (e) {
    e.preventDefault();
    var f = contact.elements, err = contact.querySelector(".clara-error"), btn = contact.querySelector(".clara-primary");
    var name = f.name.value.trim(), email = f.email.value.trim(), message = f.message.value.trim();
    var problem = !name ? "Add your name so we know who to reply to."
      : !/^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/.test(email) ? "Add an email like name@example.com so we can reply."
      : message.length < 5 ? "Write a short message for the team." : "";
    if (problem) { err.textContent = problem; err.hidden = false; return; }
    if (f.botcheck.checked) return;   // a bot filled the hidden box
    err.hidden = true; btn.disabled = true; btn.textContent = "Sending";
    sendToTeam({ name: name, email: email, message: message, botcheck: false }).then(function () {
      contact.reset(); contact.hidden = true; done.hidden = false;
      done.querySelector(".clara-sub").textContent = "We'll reply to " + email + ".";
      done.querySelector(".clara-back").focus();
      remember("bot", "Your message was sent. We'll reply to " + email + ".");
      addBubble("bot", "Your message was sent. We'll reply to " + email + ".", false);
    }, function () {
      err.textContent = "Your message didn't send. Check your connection and try again.";
      err.hidden = false;
    }).then(function () { btn.disabled = false; btn.textContent = "Send message"; });
  });

  // Page contact forms that post to Web3Forms: send them without leaving the page.
  function enhancePageForms() {
    document.querySelectorAll('form[action="' + WEB3FORMS_URL + '"]').forEach(function (form) {
      if (form.dataset.claraReady) return;
      form.dataset.claraReady = "1";
      if (!form.querySelector('[name="botcheck"]')) {
        var hp = el("input", "clara-hp"); hp.type = "checkbox"; hp.name = "botcheck"; hp.tabIndex = -1;
        hp.setAttribute("aria-hidden", "true"); form.appendChild(hp);
      }
      var status = el("p", "clara-form-status"); status.setAttribute("role", "status");
      form.appendChild(status);
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!form.reportValidity()) return;
        var data = {}, btn = form.querySelector('[type="submit"]');
        new FormData(form).forEach(function (v, k) { if (k !== "access_key") data[k] = String(v).trim(); });
        if (data.botcheck) return;
        data.botcheck = false;
        if (btn) btn.disabled = true;
        status.textContent = "Sending your message";
        sendToTeam(data).then(function () {
          form.reset();
          status.textContent = "Message sent. We'll reply to " + (data.email || "you") + " by email.";
        }, function () {
          status.textContent = "Your message didn't send. Check your connection and try again.";
        }).then(function () { if (btn) btn.disabled = false; });
      });
    });
  }

  // ---------- events ----------
  launch.addEventListener("click", function () { state.open ? close() : open(); });
  $(".clara-close").addEventListener("click", close);
  $(".clara-reset").addEventListener("click", reset);
  root.querySelectorAll(".clara-back").forEach(function (b) { b.addEventListener("click", function () { showChat(); input.focus(); }); });
  compose.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text || state.busy) return;
    input.value = "";
    ask({ message: text }, text);
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && state.open) close(); });
  // Any element with data-clara opens Clara; data-clara="contact" opens the contact form.
  document.addEventListener("click", function (e) {
    var t = e.target.closest && e.target.closest("[data-clara]");
    if (!t || root.contains(t)) return;
    e.preventDefault();
    open();
    if (t.getAttribute("data-clara") === "contact") showContact();
  });

  function mount() {
    document.body.appendChild(root);
    enhancePageForms();
    if (saved && saved.open) open();
    else {
      var seen = false;
      try { seen = sessionStorage.getItem("clara-nudged") === "1"; sessionStorage.setItem("clara-nudged", "1"); } catch (e) {}
      if (!seen) {
        setTimeout(function () { if (!state.open) { nudge.hidden = false; root.classList.add("show-nudge"); } }, 4000);
        setTimeout(function () { root.classList.remove("show-nudge"); setTimeout(function () { nudge.hidden = true; }, 400); }, 11000);
      }
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();