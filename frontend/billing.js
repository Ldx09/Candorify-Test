/* Premium checkout (Stripe embedded Checkout) and the Business "Talk to us" form.
   - checkout.html: main.js calls CandorifyBilling.show(user) when the page opens. Card details are typed into
     Stripe's own secure form (an iframe); they never touch Candorify's servers.
   - plans.html: turns the Business "Coming soon" button into "Talk to us" (a short form sent with Web3Forms).
   Load after main.js:  <script src="billing.js" defer></script> */
(function () {
  "use strict";
  var API = window.CandorifyAPI;
  var STRIPE_JS = "https://js.stripe.com/endive/stripe.js";   // matches the Stripe API version the backend uses
  var WEB3FORMS_URL = "https://api.web3forms.com/submit";
  var WEB3FORMS_KEY = "219d466a-6863-40df-95c5-1f72d5774b7e";
  var TEST_CARD = "4242 4242 4242 4242";
  var INCLUDED = ["Everything in Basic", "Every charge explained in your language", "Letters that question specific charges",
    "New features as they launch"];

  function $(sel, root) { return (root || document).querySelector(sel); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(cents) { return "$" + (cents / 100).toFixed(2); }
  function longDate(d) { return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }); }
  function inAYear() { var d = new Date(); d.setFullYear(d.getFullYear() + 1); return d; }

  var styled = false;
  function style() {
    if (styled) return;
    styled = true;
    var s = document.createElement("style");
    s.textContent =
      "#view-checkout{background:var(--mist-2);min-height:calc(100vh - 68px);padding:40px 0 72px}" +
      ".co-back{display:inline-flex;align-items:center;gap:6px;margin:0 0 22px;padding:0;background:none;border:0;font:inherit;font-size:.95rem;color:var(--green);cursor:pointer;text-decoration:underline;text-underline-offset:4px}" +
      ".co-head{margin:0 0 28px;max-width:640px}" +
      ".co-head h1{margin:0 0 8px;font-size:clamp(2.2rem,4.4vw,3.4rem)}" +
      ".co-head h1 em{font-family:var(--serif);font-style:italic;font-weight:400;letter-spacing:-.01em}" +
      ".co-head p{margin:0;color:var(--muted);font-size:1.08rem}" +
      ".co-grid{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);border:2px solid var(--slate);background:var(--cream)}" +
      ".co-summary{padding:30px 30px 26px;border-right:2px solid var(--slate);display:flex;flex-direction:column;gap:22px}" +
      ".co-pay{padding:24px;min-height:560px;position:relative;background:var(--paper)}" +
      ".co-plan{display:flex;justify-content:space-between;align-items:baseline;gap:12px}" +
      ".co-plan h2{margin:0;font-size:1.5rem}" +
      ".co-price{font-family:var(--serif);font-style:italic;font-size:3.2rem;line-height:1;color:var(--slate)}" +
      ".co-price small{font-family:var(--body);font-style:normal;font-size:1rem;color:var(--muted)}" +
      ".co-list{list-style:none;margin:0;padding:0}" +
      ".co-list li{position:relative;padding:8px 0 8px 28px;border-bottom:1px dashed var(--line);font-size:.98rem}" +
      ".co-list li::before{content:'';position:absolute;left:6px;top:14px;width:7px;height:12px;border:solid var(--teal);border-width:0 2.5px 2.5px 0;transform:rotate(45deg)}" +
      /* the itemized receipt: dotted leaders between label and amount */
      ".co-receipt{margin:0;padding:16px 0 0;border-top:2px solid var(--slate)}" +
      ".co-receipt div{display:flex;align-items:baseline;gap:8px;padding:5px 0;font-size:.98rem}" +
      ".co-receipt dt{margin:0;white-space:nowrap}" +
      ".co-receipt div::after{content:'';order:1;flex:1;border-bottom:1.5px dotted var(--line-strong);transform:translateY(-4px)}" +
      ".co-receipt dd{margin:0;order:2;white-space:nowrap;font-variant-numeric:tabular-nums}" +
      ".co-receipt .co-total{padding-top:10px;font-weight:600;font-size:1.08rem}" +
      ".co-receipt .co-muted{color:var(--muted);font-size:.92rem}" +
      ".co-test{padding:14px 16px;background:var(--marker-soft);border-left:4px solid var(--ochre);font-size:.92rem;line-height:1.5}" +
      ".co-test strong{display:block;margin-bottom:2px}" +
      ".co-card{display:inline-flex;align-items:center;gap:8px;margin-top:6px;font-variant-numeric:tabular-nums;font-weight:600;letter-spacing:.04em}" +
      ".co-copy{padding:2px 10px;border:1px solid var(--slate);border-radius:999px;background:transparent;font:inherit;font-size:.8rem;font-weight:500;letter-spacing:0;color:var(--slate);cursor:pointer}" +
      ".co-copy:hover{background:var(--slate);color:var(--beige)}" +
      ".co-trust{display:grid;gap:8px;margin-top:auto;font-size:.88rem;color:var(--muted)}" +
      ".co-trust span{display:flex;gap:8px;align-items:flex-start}" +
      ".co-trust svg{flex:none;margin-top:3px}" +
      ".co-loading{position:absolute;inset:24px;display:grid;place-content:center;gap:14px;text-align:center;color:var(--muted)}" +
      ".co-spin{width:34px;height:34px;margin:0 auto;border-radius:50%;border:3px solid var(--line);border-top-color:var(--slate);animation:coSpin .8s linear infinite}" +
      "@keyframes coSpin{to{transform:rotate(360deg)}}" +
      ".co-msg{padding:28px;display:grid;gap:12px;align-content:center;min-height:360px;max-width:520px}" +
      ".co-msg h2{margin:0;font-size:1.6rem}" +
      ".co-msg p{margin:0;color:var(--muted)}" +
      ".co-msg .row{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px}" +
      ".co-err{color:#7A2E13}" +
      /* success */
      ".co-done{border:2px solid var(--slate);background:var(--cream);display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr)}" +
      ".co-done-main{padding:44px 40px;display:grid;gap:16px;align-content:start}" +
      ".co-seal{width:64px;height:64px;border-radius:50%;background:var(--slate);color:var(--beige);display:grid;place-items:center;animation:coPop .5s var(--ease) both}" +
      ".co-done h1{margin:0;font-size:clamp(2.2rem,4.4vw,3.4rem)}" +
      ".co-done h1 em{font-family:var(--serif);font-style:italic;font-weight:400}" +
      ".co-done p{margin:0;color:var(--muted);max-width:52ch}" +
      ".co-done .row{display:flex;flex-wrap:wrap;gap:10px;margin-top:8px}" +
      ".co-done-side{padding:40px 32px;border-left:2px solid var(--slate);background:var(--paper);display:grid;align-content:start;gap:14px}" +
      ".co-done-side h2{margin:0;font-size:1.15rem}" +
      "@keyframes coPop{from{transform:scale(.6);opacity:0}to{transform:none;opacity:1}}" +
      "@media (prefers-reduced-motion:reduce){.co-seal,.co-spin{animation:none}}" +
      "@media (max-width:860px){.co-grid,.co-done{grid-template-columns:1fr}.co-summary{border-right:0;border-bottom:2px solid var(--slate)}" +
      ".co-done-side{border-left:0;border-top:2px solid var(--slate)}.co-pay{padding:12px;min-height:640px}.co-summary,.co-done-main{padding:24px 20px}" +
      ".co-summary .co-list,.co-summary .co-trust span:nth-child(n+2){display:none}}" +   /* phones: keep the summary short so the form is close */
      /* Business contact dialog */
      ".biz-dialog{width:min(560px,calc(100vw - 32px));padding:0}" +
      ".biz-dialog::backdrop{background:rgba(18,21,17,.55)}" +
      ".biz-body{padding:24px;display:grid;gap:14px}" +
      ".biz-body p{margin:0;color:var(--muted)}" +
      ".biz-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}" +
      ".biz-grid .wide-field{grid-column:1/-1}" +
      ".biz-body label{display:grid;gap:6px;font-weight:500;font-size:.95rem}" +
      ".biz-body textarea{min-height:96px;resize:vertical}" +
      ".biz-err{color:#7A2E13;font-size:.92rem}" +
      "@media (max-width:560px){.biz-grid{grid-template-columns:1fr}}";
    document.head.appendChild(s);
  }

  var LOCK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';
  var CAL = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>';
  var UNDO = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>';
  var CHECK = '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>';

  // ---------- checkout page ----------
  var mounted = null;   // the Stripe form, so it can be removed before mounting a new one

  function root() { return $("#checkout-root"); }
  function back() { return '<button type="button" class="co-back" data-go="pricing">&larr; Back to plans</button>'; }

  function loadStripe() {
    if (window.Stripe) return Promise.resolve(window.Stripe);
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = STRIPE_JS;
      s.onload = function () { window.Stripe ? resolve(window.Stripe) : reject(new Error("Stripe didn't load")); };
      s.onerror = function () { reject(new Error("We couldn't load the secure payment form. Check your connection and try again.")); };
      document.head.appendChild(s);
    });
  }

  function message(title, text, buttons, isError) {
    root().innerHTML = back() + '<div class="co-grid" style="grid-template-columns:1fr"><div class="co-msg" role="' + (isError ? "alert" : "status") + '">' +
      "<h2>" + esc(title) + "</h2><p" + (isError ? ' class="co-err"' : "") + ">" + esc(text) + "</p>" +
      '<div class="row">' + (buttons || "") + "</div></div></div>";
  }

  function summaryHTML(cfg) {
    var renews = longDate(inAYear());
    return '<aside class="co-summary" aria-label="Order summary">' +
      '<div class="co-plan"><h2>Premium</h2><span class="cap dim">Yearly</span></div>' +
      '<div class="co-price">' + money(cfg.price_cents) + "<small> /" + esc(cfg.interval) + "</small></div>" +
      '<ul class="co-list">' + INCLUDED.map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") + "</ul>" +
      '<dl class="co-receipt">' +
      "<div><dt>Candorify Premium, 1 " + esc(cfg.interval) + "</dt><dd>" + money(cfg.price_cents) + "</dd></div>" +
      '<div class="co-total"><dt>Due today</dt><dd>' + money(cfg.price_cents) + "</dd></div>" +
      '<div class="co-muted"><dt>Renews</dt><dd>' + esc(renews) + "</dd></div></dl>" +
      (cfg.test_mode ? '<div class="co-test"><strong>Test mode: no real money is charged.</strong>' +
        "Pay with this test card, any future expiry date, any 3-digit CVC and any ZIP code." +
        '<div class="co-card"><span>' + TEST_CARD + '</span><button type="button" class="co-copy" data-copy="' +
        TEST_CARD.replace(/ /g, "") + '">Copy</button></div></div>' : "") +
      '<div class="co-trust">' +
      "<span>" + LOCK + "Payments are processed by Stripe. Your card details go straight to Stripe and never touch Candorify.</span>" +
      "<span>" + CAL + "Renews once a year. We'll email a receipt each time.</span>" +
      "<span>" + UNDO + "Cancel anytime from your Account. Premium stays on until the end of your paid year.</span>" +
      "</div></aside>";
  }

  function mountForm(cfg) {
    root().innerHTML = back() +
      '<header class="co-head"><h1>Upgrade to <em>Premium</em></h1><p>One payment a year. Every feature, nothing hidden.</p></header>' +
      '<div class="co-grid">' + summaryHTML(cfg) +
      '<section class="co-pay" aria-label="Payment"><div class="co-loading" id="co-loading"><div class="co-spin"></div><span>Loading secure checkout…</span></div>' +
      '<div id="stripe-checkout"></div></section></div>';
    loadStripe().then(function (Stripe) {
      var stripe = Stripe(cfg.publishable_key);
      var fetchClientSecret = function () { return API.startCheckout().then(function (r) { return r.client_secret; }); };
      var make = stripe.createEmbeddedCheckoutPage || stripe.initEmbeddedCheckout;   // newer / older Stripe.js
      return make.call(stripe, { fetchClientSecret: fetchClientSecret });
    }).then(function (checkout) {
      if (mounted) { try { mounted.destroy(); } catch (e) { /* already gone */ } }
      mounted = checkout;
      checkout.mount("#stripe-checkout");
      var l = $("#co-loading"); if (l) l.remove();
    }).catch(function (err) {
      var pay = $(".co-pay");
      if (pay) pay.innerHTML = '<div class="co-msg" role="alert"><h2>Checkout didn\'t load</h2><p class="co-err">' +
        esc(err.message || "Something went wrong. Please try again.") + '</p><div class="row">' +
        '<button type="button" class="btn btn-primary co-retry">Try again</button></div></div>';
    });
  }

  function success(user, email) {
    var renews = user && user.plan_renews_at ? longDate(new Date(user.plan_renews_at)) : longDate(inAYear());
    root().innerHTML = '<section class="co-done" aria-labelledby="co-done-title">' +
      '<div class="co-done-main"><div class="co-seal">' + CHECK + "</div>" +
      '<h1 id="co-done-title" tabindex="-1">You\'re on <em>Premium</em>.</h1>' +
      "<p>Thank you for supporting Candorify." + (email ? " A receipt is on its way to " + esc(email) + "." : "") + "</p>" +
      '<div class="row"><button type="button" class="btn btn-primary" data-go="check">Check a bill</button>' +
      '<button type="button" class="btn btn-secondary" data-go="account">View my account</button></div></div>' +
      '<aside class="co-done-side"><h2>Your plan</h2>' +
      '<dl class="co-receipt" style="border-top:0;padding-top:0">' +
      "<div><dt>Plan</dt><dd>Premium, yearly</dd></div>" +
      "<div><dt>Renews</dt><dd>" + esc(renews) + "</dd></div>" +
      "<div><dt>Manage or cancel</dt><dd>Account</dd></div></dl>" +
      '<p class="muted" style="margin:0;font-size:.92rem">You can cancel anytime. Premium stays on until the end of your paid year.</p></aside></section>';
    var h = $("#co-done-title"); if (h) h.focus();
  }

  function show(user) {
    style();
    if (!root()) return;
    var params = new URLSearchParams(location.search);
    var sid = params.get("session_id");
    root().innerHTML = '<div class="co-msg" role="status"><div class="co-spin"></div></div>';
    if (sid) {   // back from Stripe after paying
      history.replaceState(null, "", location.pathname);
      root().innerHTML = '<div class="co-msg" role="status"><div class="co-spin"></div><p style="text-align:center">Confirming your payment…</p></div>';
      API.confirmCheckout(sid).then(function (r) {
        if (r.status === "complete") {
          if (window.CandorifyApp && window.CandorifyApp.refreshUser) window.CandorifyApp.refreshUser();
          success(r.user, r.email);
        } else {
          start(user, "Your payment didn't go through, so nothing was charged. You can try again below.");
        }
      }, function (err) { message("We couldn't confirm your payment", err.message, '<button type="button" class="btn btn-secondary" data-go="account">Go to my account</button>', true); });
      return;
    }
    start(user);
  }

  function start(user, note) {
    API.billingConfig().then(function (cfg) {
      if (user && user.plan === "premium") {
        message("You're already on Premium", "Thanks for supporting Candorify. You can manage or cancel your plan from your account.",
          '<button type="button" class="btn btn-primary" data-go="account">Go to my account</button>');
        return;
      }
      if (!cfg.enabled) {
        message("Premium isn't available right now", "Payments aren't set up on this server yet. Everything in Basic is still free to use.",
          '<button type="button" class="btn btn-primary" data-go="check">Check a bill</button>');
        return;
      }
      mountForm(cfg);
      if (note) {
        var head = $(".co-head p");
        if (head) { head.textContent = note; head.className = "co-err"; }
      }
    }, function (err) { message("We couldn't load checkout", err.message, '<button type="button" class="btn btn-primary co-retry">Try again</button>', true); });
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (t.closest && t.closest(".co-retry")) { show(null); return; }
    var copy = t.closest && t.closest(".co-copy");
    if (copy) {
      var done = function () { copy.textContent = "Copied"; setTimeout(function () { copy.textContent = "Copy"; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(copy.dataset.copy).then(done, function () {});
    }
  });

  // ---------- Business: "Talk to us" ----------
  function businessButton() {
    var b = $("#btn-business");
    if (b) return b;
    var all = Array.prototype.slice.call(document.querySelectorAll("#view-pricing button"));
    return all.filter(function (x) { return x.id !== "btn-upgrade" && /coming soon/i.test(x.textContent); })[0] || null;
  }

  function contactDialog() {
    var d = $("#biz-dialog");
    if (d) return d;
    d = document.createElement("dialog");
    d.id = "biz-dialog";
    d.className = "biz-dialog";
    d.setAttribute("aria-labelledby", "biz-title");
    d.innerHTML = '<div class="dialog-head"><h2 id="biz-title" class="h3 no-margin">Candorify for your team</h2>' +
      '<button type="button" class="icon-btn biz-close" aria-label="Close"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button></div>' +
      '<form class="biz-body" novalidate>' +
      "<p>Tell us a little about your company and we'll put together a package for your employees.</p>" +
      '<div class="biz-grid">' +
      '<label>Your name<input name="name" type="text" autocomplete="name" required maxlength="100"></label>' +
      '<label>Work email<input name="email" type="email" autocomplete="email" required maxlength="150"></label>' +
      '<label>Company<input name="company" type="text" autocomplete="organization" required maxlength="150"></label>' +
      '<label>Employees<select name="team_size" required><option value="">Choose</option><option>1 to 49</option><option>50 to 249</option><option>250 to 999</option><option>1,000 or more</option></select></label>' +
      '<label class="wide-field">Anything we should know? <span class="muted" style="font-weight:400">Optional</span><textarea name="message" maxlength="2000"></textarea></label>' +
      "</div>" +
      '<input type="checkbox" name="botcheck" tabindex="-1" autocomplete="off" style="display:none">' +
      '<p class="biz-err" role="alert" hidden></p>' +
      '<div class="row" style="display:flex;gap:10px;flex-wrap:wrap"><button type="submit" class="btn btn-primary">Send</button>' +
      '<button type="button" class="btn btn-secondary biz-close">Cancel</button></div></form>';
    document.body.appendChild(d);
    d.addEventListener("click", function (e) {
      if (e.target === d || (e.target.closest && e.target.closest(".biz-close"))) d.close();
    });
    var form = $("form", d);
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var f = form.elements, err = $(".biz-err", d), btn = $("button[type=submit]", form);
      var data = { name: f.name.value.trim(), email: f.email.value.trim(), company: f.company.value.trim(),
        team_size: f.team_size.value, message: f.message.value.trim() };
      var bad = !data.name ? "Enter your name." : !/^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/.test(data.email) ? "Enter a valid work email." :
        !data.company ? "Enter your company's name." : !data.team_size ? "Choose how many employees you have." : "";
      if (bad) { err.textContent = bad; err.hidden = false; return; }
      if (f.botcheck.checked) return;
      err.hidden = true; btn.disabled = true; btn.textContent = "Sending…";
      fetch(WEB3FORMS_URL, {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(Object.assign({ access_key: WEB3FORMS_KEY, subject: "Candorify Business inquiry: " + data.company,
          from_name: "Candorify website", replyto: data.email }, data)),
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok || j.success === false) throw new Error(j.message || "Not sent"); });
      }).then(function () {
        form.innerHTML = '<div style="display:grid;gap:12px"><h3 style="margin:0">Thanks, ' + esc(data.name.split(" ")[0]) + ".</h3>" +
          "<p>We got your message and will reply to " + esc(data.email) + ' soon.</p><div><button type="button" class="btn btn-primary biz-close">Done</button></div></div>';
      }, function () {
        err.textContent = "We couldn't send that. Check your connection and try again.";
        err.hidden = false; btn.disabled = false; btn.textContent = "Send";
      });
    });
    return d;
  }

  function setupBusiness() {
    var btn = businessButton();
    if (!btn) return;
    style();
    btn.textContent = "Talk to us";
    btn.disabled = false;
    btn.removeAttribute("aria-disabled");
    var card = btn.closest(".price-card") || btn.parentNode;
    var note = $("#biz-note") || (card && Array.prototype.slice.call(card.querySelectorAll("p")).filter(function (p) {
      return /coming soon/i.test(p.textContent);
    })[0]);
    if (note) note.textContent = "Tell us about your team and we'll build a package around it.";
    var tbd = card && card.querySelector(".price-tbd");
    if (tbd) { var span = tbd.querySelector("span") || tbd; span.textContent = "Custom pricing"; }
    btn.addEventListener("click", function () {
      var d = contactDialog();
      if (typeof d.showModal === "function") d.showModal(); else d.setAttribute("open", "");
      var first = $("input[name=name]", d); if (first) first.focus();
    });
  }

  window.CandorifyBilling = { show: show };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setupBusiness);
  else setupBusiness();
})();