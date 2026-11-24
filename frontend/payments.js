/* "Who paid what": insurance, discounts, the patient's share, the patient's payments and what's still owed.
   The backend reads these from the bill when it shows them (bill.payments). This file draws:
     - editor(): the card on the Charges step, where the user can check and fix the amounts
     - summary(): the card at the top of the Review step
   Used on bill.html (add after main.js):  <script src="payments.js" defer></script> */
(function () {
  "use strict";
  var FIELDS = [
    ["insurance_paid", "Insurance paid", "Paid by your insurance plan"],
    ["adjustments", "Discount (adjustment)", "Taken off by the hospital or your plan"],
    ["patient_responsibility", "Your share", "What you were asked to pay after insurance"],
    ["patient_paid", "You paid", "Payments you already made"],
    ["other_payments", "Payments (payer not shown)", "Paid, but the bill doesn't say by whom"],
    ["prior_balance", "Earlier balance", "Left unpaid from an earlier visit and added to this bill"],
    ["balance_due", "Still owed", "What the bill says is left to pay. Below 0 means a credit"],
  ];

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(n) {
    var v = Number(n || 0);
    return (v < 0 ? "-$" : "$") + Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function has(p, k) { return !!p && p[k] != null && p[k] !== "" && !isNaN(Number(p[k])); }
  function any(p) { return !!p && FIELDS.some(function (f) { return has(p, f[0]); }); }

  // From the API (strings) to numbers; null when the bill shows nothing.
  function fromApi(p) {
    if (!p) return null;
    var out = {};
    FIELDS.forEach(function (f) { out[f[0]] = has(p, f[0]) ? Number(p[f[0]]) : null; });
    return any(out) ? out : null;
  }
  // To the API: only filled amounts, 2 decimals; null when empty.
  function toApi(p) {
    if (!any(p)) return null;
    var out = {};
    FIELDS.forEach(function (f) {
      if (has(p, f[0])) out[f[0]] = Number(Number(p[f[0]]).toFixed(2));
    });
    return out;
  }

  var styled = false;
  function style() {
    if (styled) return;
    styled = true;
    var s = document.createElement("style");
    s.textContent =
      ".pay-card{margin:22px 0 4px;padding:18px 18px 16px;border:1px solid var(--line,rgba(31,59,45,.18));border-radius:14px;background:var(--paper,#FBF8F1)}" +
      ".pay-card h3{margin:0 0 4px;font-size:1.05rem}" +
      ".pay-card .pay-sub{margin:0 0 14px;font-size:.88rem;color:var(--muted,#595D51)}" +
      ".pay-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px 14px}" +
      ".pay-grid label{display:grid;gap:4px;font-size:.86rem;font-weight:500}" +
      ".pay-grid small{font-weight:400;color:var(--muted,#595D51);font-size:.76rem;line-height:1.3}" +
      ".pay-in{display:flex;align-items:center;border:1px solid rgba(31,59,45,.28);border-radius:10px;background:#fff;padding:0 10px}" +
      ".pay-in span{color:var(--muted,#595D51)}" +
      ".pay-in input{border:0;outline:0;background:transparent;padding:9px 6px;width:100%;font:inherit;font-size:16px}" +
      ".pay-in:focus-within{border-color:var(--green,#2E5A43);box-shadow:0 0 0 3px rgba(46,90,67,.16)}" +
      ".pay-add{margin-top:18px}" +
      ".pay-sum{margin:0 0 18px;padding:18px;border-radius:14px;background:var(--forest,#1F3B2D);color:var(--beige,#EFE8D9)}" +
      ".pay-sum-top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:6px 16px;margin-bottom:12px}" +
      ".pay-sum-top h3{margin:0;font-size:1rem;font-weight:500;color:var(--sage-pale,#C9D8C2)}" +
      ".pay-status{font-size:1.35rem;font-weight:600}" +
      ".pay-bar{display:flex;height:12px;border-radius:999px;overflow:hidden;background:rgba(239,232,217,.16)}" +
      ".pay-bar i{display:block;height:100%;transform-origin:left;animation:payGrow .7s cubic-bezier(.2,.8,.2,1) both}" +
      ".pay-legend{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px 16px;margin:14px 0 0;padding:0;list-style:none;font-size:.9rem}" +
      ".pay-legend li{display:flex;align-items:center;gap:8px}" +
      ".pay-legend b{margin-left:auto;font-weight:600}" +
      ".pay-dot{width:10px;height:10px;border-radius:3px;flex:none}" +
      ".pay-sum .pay-note{margin:12px 0 0;font-size:.82rem;color:var(--sage-pale,#C9D8C2)}" +
      "@keyframes payGrow{from{transform:scaleX(0)}to{transform:scaleX(1)}}" +
      "@media (prefers-reduced-motion:reduce){.pay-bar i{animation:none}}";
    document.head.appendChild(s);
  }

  // Charges step: check and fix the amounts. onChange(newPayments) is called on every edit.
  function editor(container, payments, onChange) {
    style();
    var open = any(payments);
    var p = payments ? Object.assign({}, payments) : {};
    function draw() {
      if (!open) {
        container.innerHTML = '<button type="button" class="btn btn-quiet btn-sm pay-add">+ Add what was paid (optional)</button>';
        container.querySelector("button").addEventListener("click", function () { open = true; draw(); container.querySelector("input").focus(); });
        return;
      }
      container.innerHTML =
        '<section class="pay-card" aria-labelledby="pay-title"><h3 id="pay-title">Who paid what</h3>' +
        '<p class="pay-sub">' + (any(payments) ? "From your bill. Fix anything we misread, and leave a box empty if your bill doesn't show it."
          : "Optional. Fill in what your bill shows, and we'll check that the payments add up.") + "</p>" +
        '<div class="pay-grid">' + FIELDS.map(function (f) {
          var id = "pay-" + f[0];
          return '<label for="' + id + '">' + esc(f[1]) + '<small>' + esc(f[2]) + '</small>' +
            '<span class="pay-in"><span aria-hidden="true">$</span><input id="' + id + '" data-k="' + f[0] + '" type="number" step="0.01" inputmode="decimal"' +
            (f[0] === "balance_due" ? "" : ' min="0"') + ' value="' + (has(p, f[0]) ? Number(p[f[0]]).toFixed(2) : "") + '"></span></label>';
        }).join("") + "</div></section>";
      container.querySelectorAll("input[data-k]").forEach(function (inp) {
        inp.addEventListener("input", function () {
          var v = inp.value.trim();
          p[inp.dataset.k] = v === "" || isNaN(Number(v)) ? null : Number(v);
          onChange(any(p) ? Object.assign({}, p) : null);
        });
      });
    }
    draw();
  }

  // Review step: what was charged, who paid it, and what's left.
  var COLORS = { insurance_paid: "#A7BFA2", adjustments: "#C9D8C2", patient_paid: "#DDB65F", other_payments: "#8FA88A", balance_due: "#EFE8D9" };
  function summary(container, payments, total) {
    style();
    if (!any(payments)) { container.innerHTML = ""; container.hidden = true; return; }
    container.hidden = false;
    var p = payments, owed = has(p, "balance_due") ? Number(p.balance_due) : null;
    var status = owed == null ? "" : Math.abs(owed) < 0.005 ? "Paid off" : owed < 0 ? "Credit of " + money(-owed) : "You still owe " + money(owed);
    var parts = ["insurance_paid", "adjustments", "other_payments", "patient_paid"].filter(function (k) { return has(p, k) && Number(p[k]) > 0; })
      .map(function (k) { return [k, Number(p[k])]; });
    if (owed != null && owed > 0) parts.push(["balance_due", owed]);
    var whole = Math.max(Number(total || 0), parts.reduce(function (s, x) { return s + x[1]; }, 0)) || 1;
    var bar = parts.map(function (x, i) {
      return '<i style="width:' + (x[1] / whole * 100).toFixed(2) + "%;background:" + COLORS[x[0]] + ";animation-delay:" + (i * 90) + 'ms"></i>';
    }).join("");
    var rows = FIELDS.filter(function (f) { return has(p, f[0]) && (f[0] === "balance_due" || Number(p[f[0]]) !== 0); }).map(function (f) {
        var color = COLORS[f[0]] || "transparent";
      return '<li><span class="pay-dot" style="background:' + color + (f[0] === "patient_responsibility" ? ";border:1px solid #EFE8D9;background:transparent" : "") + '"></span>' +
        esc(f[1]) + "<b>" + money(p[f[0]]) + "</b></li>";
    }).join("");
    container.innerHTML =
      '<section class="pay-sum" aria-label="Who paid what"><div class="pay-sum-top"><h3>Who paid what on ' + money(total) + " in charges</h3>" +
      (status ? '<span class="pay-status">' + esc(status) + "</span>" : "") + "</div>" +
      (bar ? '<div class="pay-bar" aria-hidden="true">' + bar + "</div>" : "") +
      '<ul class="pay-legend">' + rows + "</ul>" +
      '<p class="pay-note">From your bill. Change these on the Charges step if anything is wrong.</p></section>';
  }

  window.CandorifyPayments = { editor: editor, summary: summary, fromApi: fromApi, toApi: toApi, any: any };
})();