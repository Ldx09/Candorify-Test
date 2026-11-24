/* Financial assistance checker: household size + yearly income (+ state, insurance, amount owed) ->
   what the patient may pay, their state's rules, Medicaid, their rights, next steps and a ready letter.
   Nothing is saved: the answers are sent once to /api/assistance/check and forgotten.
   bill.html: main.js calls CandorifyAssist.render(box, { amount, hospital, date }) on the Review step.
   Any other page (e.g. Letters): add <div id="assistance-slot"></div> and <script src="assistance.js" defer></script>;
   there it reads the hospital and date from the letter form (#tpl-provider, #tpl-date) if they're filled in. */
(function () {
  "use strict";
  var STATES = [["", "Choose your state"], ["AL", "Alabama"], ["AK", "Alaska"], ["AZ", "Arizona"], ["AR", "Arkansas"],
    ["CA", "California"], ["CO", "Colorado"], ["CT", "Connecticut"], ["DE", "Delaware"], ["DC", "District of Columbia"],
    ["FL", "Florida"], ["GA", "Georgia"], ["HI", "Hawaii"], ["ID", "Idaho"], ["IL", "Illinois"], ["IN", "Indiana"],
    ["IA", "Iowa"], ["KS", "Kansas"], ["KY", "Kentucky"], ["LA", "Louisiana"], ["ME", "Maine"], ["MD", "Maryland"],
    ["MA", "Massachusetts"], ["MI", "Michigan"], ["MN", "Minnesota"], ["MS", "Mississippi"], ["MO", "Missouri"],
    ["MT", "Montana"], ["NE", "Nebraska"], ["NV", "Nevada"], ["NH", "New Hampshire"], ["NJ", "New Jersey"],
    ["NM", "New Mexico"], ["NY", "New York"], ["NC", "North Carolina"], ["ND", "North Dakota"], ["OH", "Ohio"],
    ["OK", "Oklahoma"], ["OR", "Oregon"], ["PA", "Pennsylvania"], ["RI", "Rhode Island"], ["SC", "South Carolina"],
    ["SD", "South Dakota"], ["TN", "Tennessee"], ["TX", "Texas"], ["UT", "Utah"], ["VT", "Vermont"], ["VA", "Virginia"],
    ["WA", "Washington"], ["WV", "West Virginia"], ["WI", "Wisconsin"], ["WY", "Wyoming"]];
  var HELP = "Most hospitals must offer free or cheaper care to people with lower incomes, and many people qualify " +
    "without knowing it. Enter your household and income, and we'll show what you may pay, your state's rules, " +
    "whether Medicaid could cover the bill, and a letter to send. Nothing you type here is saved. " +
    "These are estimates based on published rules, so always confirm with your hospital.";
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(n) {
    return "$" + Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  /* "?" next to a title: shows what the card does on hover, keyboard focus or tap. Shared with eob.js. */
  if (!window.CandorifyHelp) {
    var helpId = 0;
    var helpStyled = false;
    window.CandorifyHelp = {
      html: function (text, label) {
        if (!helpStyled) {
          helpStyled = true;
          var hs = document.createElement("style");
          hs.textContent =
            ".qhelp{position:relative;display:inline-flex;vertical-align:middle;margin-left:8px}" +
            ".qhelp-btn{width:22px;height:22px;border-radius:50%;border:1.5px solid var(--forest,#1F3B2D);background:transparent;color:var(--forest,#1F3B2D);font:600 .78rem/1 inherit;cursor:help;display:grid;place-items:center;padding:0}" +
            ".qhelp-btn:hover,.qhelp.open .qhelp-btn{background:var(--forest,#1F3B2D);color:var(--beige,#EFE8D9)}" +
            ".qhelp-btn:focus-visible{outline:2px solid var(--ochre,#DDB65F);outline-offset:2px}" +
            ".qhelp-tip{position:fixed;left:0;top:0;width:min(320px,calc(100vw - 24px));box-sizing:border-box;padding:12px 14px;border-radius:10px;background:var(--forest,#1F3B2D);color:var(--beige,#EFE8D9);font-size:.85rem;font-weight:400;line-height:1.45;letter-spacing:0;text-transform:none;box-shadow:0 10px 30px rgba(20,24,19,.22);opacity:0;visibility:hidden;transition:opacity .15s;z-index:60;pointer-events:none}" +
            ".qhelp:hover .qhelp-tip,.qhelp:focus-within .qhelp-tip,.qhelp.open .qhelp-tip{opacity:1;visibility:visible}" +
            "@media (prefers-reduced-motion:reduce){.qhelp-tip{transition:none}}";
          document.head.appendChild(hs);
          document.addEventListener("click", function (e) {   // tap to open on phones, tap anywhere else to close
            var btn = e.target.closest && e.target.closest(".qhelp-btn");
            document.querySelectorAll(".qhelp.open").forEach(function (q) { if (!btn || q !== btn.parentNode) q.classList.remove("open"); });
            if (btn) { btn.parentNode.classList.toggle("open"); btn.setAttribute("aria-expanded", btn.parentNode.classList.contains("open")); }
          });
          // Place the tip under its "?" and keep it fully on screen (also on narrow phones).
          var place = function (e) {
            var q = e.target.closest && e.target.closest(".qhelp");
            if (!q) return;
            var r = q.querySelector(".qhelp-btn").getBoundingClientRect(), tip = q.querySelector(".qhelp-tip");
            var w = tip.offsetWidth, vw = document.documentElement.clientWidth, vh = window.innerHeight;
            var left = Math.max(12, Math.min(r.left + r.width / 2 - w / 2, vw - w - 12));
            var top = r.bottom + 10;
            if (top + tip.offsetHeight > vh - 12) top = Math.max(12, r.top - tip.offsetHeight - 10);   // no room below: show above
            tip.style.left = left + "px";
            tip.style.top = top + "px";
          };
          document.addEventListener("mouseover", place);
          document.addEventListener("focusin", place);
          document.addEventListener("click", place, true);
          window.addEventListener("scroll", function () {   // a tip opened by tapping follows the page
            document.querySelectorAll(".qhelp.open .qhelp-btn").forEach(function (b) { place({ target: b }); });
          }, { passive: true });
          document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") document.querySelectorAll(".qhelp.open").forEach(function (q) { q.classList.remove("open"); });
          });
        }
        var id = "qhelp-" + (++helpId);
        return '<span class="qhelp"><button type="button" class="qhelp-btn" aria-label="' + esc(label || "What does this do?") +
          '" aria-describedby="' + id + '" aria-expanded="false">?</button><span class="qhelp-tip" role="tooltip" id="' + id + '">' +
          esc(text) + "</span></span>";
      },
    };
  }

  var styled = false;
  function style() {
    if (styled) return;
    styled = true;
    var s = document.createElement("style");
    s.textContent =
      ".acard{margin:22px 0 0;padding:20px;border:1px solid rgba(31,59,45,.18);border-radius:14px;background:var(--paper,#FBF8F1)}" +
      ".acard h3{margin:0 0 6px;font-size:1.1rem;display:flex;align-items:center}" +
      ".acard .asub{margin:0 0 14px;font-size:.92rem;color:var(--muted,#595D51);max-width:64ch}" +
      ".aform{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px;align-items:end}" +
      ".aform label{display:grid;gap:5px;font-size:.88rem;font-weight:500}" +
      ".aform input,.aform select{padding:10px 12px;border:1px solid rgba(31,59,45,.28);border-radius:10px;background:#fff;font:inherit;font-size:16px;width:100%;box-sizing:border-box}" +
      ".aerr{margin:10px 0 0;color:#7A2E13;font-size:.9rem}" +
      ".ares{margin-top:18px;padding-top:16px;border-top:1px solid rgba(31,59,45,.14);animation:aIn .4s cubic-bezier(.2,.8,.2,1) both}" +
      ".ahead{margin:0 0 10px;font-size:1.35rem;font-weight:600;color:var(--forest,#1F3B2D);outline:none}" +
      ".asave{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 14px;margin:0 0 14px;padding:14px 16px;border-radius:12px;background:var(--forest,#1F3B2D);color:var(--beige,#EFE8D9)}" +
      ".asave strong{font-size:1.9rem;line-height:1.1;font-weight:600}" +
      ".asave span{font-size:.95rem;opacity:.92;max-width:52ch}" +
      ".abox{margin:0 0 14px;padding:12px 14px;border-radius:12px;background:#fff;border:1px solid rgba(31,59,45,.14);font-size:.92rem;line-height:1.5}" +
      ".abox h4{margin:0 0 4px;font-size:.95rem}" +
      ".abox p{margin:0}" +
      ".abox .anote{margin-top:6px;color:#7A2E13}" +
      ".abox a{color:var(--forest,#1F3B2D)}" +
      ".abox.amed{border-left:4px solid var(--ochre,#DDB65F)}" +
      ".ares ul,.ares ol{margin:6px 0 14px;padding-left:20px;font-size:.93rem;line-height:1.5}" +
      ".ares h4{margin:12px 0 4px;font-size:.95rem}" +
      ".ares details{margin:0 0 12px;font-size:.93rem}" +
      ".ares summary{cursor:pointer;font-weight:600;padding:4px 0}" +
      ".adead{margin:0 0 14px;font-size:.9rem;color:var(--muted,#595D51)}" +
      ".ares textarea{width:100%;min-height:240px;padding:12px;border:1px solid rgba(31,59,45,.25);border-radius:10px;font:inherit;font-size:.92rem;background:#fff;box-sizing:border-box}" +
      ".abtns{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}" +
      ".afine{margin:10px 0 0;font-size:.8rem;color:var(--muted,#595D51)}" +
      "@keyframes aIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}" +
      "@media (prefers-reduced-motion:reduce){.ares{animation:none}}";
    document.head.appendChild(s);
  }

  function val(x) { return typeof x === "function" ? x() : x; }
  function fromPage(sel) { var el = document.querySelector(sel); return el && el.value ? el.value.trim() : ""; }

  function render(box, opts) {
    style();
    opts = opts || {};
    var open = !!opts.open;
    var values = {};
    var help = window.CandorifyHelp.html(HELP, "What does the financial assistance check do?");
    function draw(result, error) {
      if (!open) {
        box.innerHTML = '<section class="acard"><h3>Need help paying this bill?' + help + "</h3>" +
          '<p class="asub">Most hospitals must offer financial assistance, and many people qualify for free or reduced bills ' +
          "without knowing it, even after paying. It takes 30 seconds to check.</p>" +
          '<button type="button" class="btn btn-secondary btn-sm a-open">Check for financial assistance</button></section>';
        box.querySelector(".a-open").addEventListener("click", function () { open = true; draw(); box.querySelector("#a-size").focus(); });
        return;
      }
      var amount = values.amount != null ? values.amount : (val(opts.amount) != null ? Number(val(opts.amount)).toFixed(2) : "");
      box.innerHTML = '<section class="acard" aria-labelledby="a-title"><h3 id="a-title">Check for financial assistance' + help + "</h3>" +
        '<p class="asub">Use your household\'s total yearly income before taxes. We don\'t save anything you type here.</p>' +
        '<form class="aform" novalidate>' +
        '<label for="a-size">People in your household<input id="a-size" type="number" min="1" max="20" step="1" inputmode="numeric" value="' + esc(values.size || 1) + '"></label>' +
        '<label for="a-income">Yearly household income ($)<input id="a-income" type="number" min="0" step="100" inputmode="decimal" value="' + esc(values.income || "") + '" placeholder="42000"></label>' +
        '<label for="a-state">State<select id="a-state">' + STATES.map(function (s) {
          return '<option value="' + s[0] + '"' + (s[0] === (values.state || "") ? " selected" : "") + ">" + s[1] + "</option>";
        }).join("") + "</select></label>" +
        '<label for="a-ins">Health insurance?<select id="a-ins">' +
        [["", "Not sure"], ["yes", "Yes, I have insurance"], ["no", "No insurance"]].map(function (o) {
          return '<option value="' + o[0] + '"' + (o[0] === (values.ins || "") ? " selected" : "") + ">" + o[1] + "</option>";
        }).join("") + "</select></label>" +
        '<label for="a-amount">Amount you owe ($)<input id="a-amount" type="number" min="0" step="0.01" inputmode="decimal" value="' + esc(amount) + '" placeholder="Optional"></label>' +
        '<button type="submit" class="btn btn-primary">Check</button></form>' +
        (error ? '<p class="aerr" role="alert">' + esc(error) + "</p>" : "") +
        (result ? resultHTML(result) : "") +
        '<p class="afine">* Candorify isn\'t a financial assistance provider. These results are estimates based on published rules, ' +
        'with sources linked. Please confirm with your hospital\'s billing office, which makes the final decision. ' +
        'This is general information, not financial or legal advice.</p></section>';
        
      var form = box.querySelector("form");
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        values = { size: box.querySelector("#a-size").value, income: box.querySelector("#a-income").value,
          state: box.querySelector("#a-state").value, ins: box.querySelector("#a-ins").value, amount: box.querySelector("#a-amount").value };
        var size = parseInt(values.size, 10), income = Number(values.income), amt = values.amount === "" ? null : Number(values.amount);
        if (!(size >= 1 && size <= 20)) { draw(null, "Enter how many people are in your household (1 to 20)."); return; }
        if (values.income === "" || !(income >= 0)) { draw(null, "Enter your household's yearly income. Use 0 if you have none."); return; }
        if (amt != null && !(amt >= 0)) { draw(null, "Enter the amount you're asked to pay, or leave it empty."); return; }
        var btn = form.querySelector("button");
        btn.disabled = true; btn.textContent = "Checking…";
        window.CandorifyAPI.checkAssistance({
          household_size: size, yearly_income: Math.round(income * 100) / 100, state: values.state || null,
          insured: values.ins === "" ? null : values.ins === "yes", amount: amt == null ? null : Math.round(amt * 100) / 100,
          hospital: (val(opts.hospital) || fromPage("#tpl-provider") || "").slice(0, 120) || null,
          date_of_service: (val(opts.date) || fromPage("#tpl-date") || "").slice(0, 20) || null,
        }).then(function (r) { draw(r, null); var h = box.querySelector(".ahead"); if (h) h.focus(); },
                function (err) { draw(null, err.message || "We couldn't check right now. Try again."); });
      });
      var copy = box.querySelector(".a-copy"), mail = box.querySelector(".a-mail");
      if (copy) copy.addEventListener("click", function () {
        var t = box.querySelector("#a-letter");
        (navigator.clipboard ? navigator.clipboard.writeText(t.value) : Promise.reject()).then(function () {
          copy.textContent = "Copied";
        }, function () { t.select(); document.execCommand("copy"); copy.textContent = "Copied"; });
      });
      if (mail && result) mail.addEventListener("click", function () {
        location.href = "mailto:?subject=" + encodeURIComponent(result.letter_subject) + "&body=" + encodeURIComponent(box.querySelector("#a-letter").value);
      });
    }
    draw();
  }

  function list(items, tag) {
    return "<" + tag + ">" + items.map(function (d) { return "<li>" + esc(d) + "</li>"; }).join("") + "</" + tag + ">";
  }

  function resultHTML(r) {
    var h = '<div class="ares" aria-live="polite"><p class="ahead" tabindex="-1">' + esc(r.headline) + "</p>";
    if (r.savings) {
      var big = r.savings.may_pay != null ? money(r.savings.may_pay) : null;
      h += '<div class="asave">' + (big ? "<strong>" + esc(big) + "</strong>" : "") + "<span>" + esc(r.savings.text) + "</span></div>";
    }
    if (r.medicaid) h += '<div class="abox amed"><h4>Medicaid</h4><p>' + esc(r.medicaid.text) + "</p></div>";
    if (r.state_program) {
      var sp = r.state_program;
      h += '<div class="abox"><h4>' + esc(sp.name) + "</h4><p>" + esc(sp.summary) + "</p>" +
        (sp.note ? '<p class="anote">' + esc(sp.note) + "</p>" : "") +
        '<p style="margin-top:6px"><a href="' + esc(sp.source) + '" target="_blank" rel="noopener">Read the official rules</a></p></div>';
    }
    h += list(r.details, "ul");
    if (r.payment_plan) h += '<div class="abox"><h4>' + (r.payment_plan.legal_cap ? "Payment plan limit" : "A fair payment plan") + "</h4><p>" + esc(r.payment_plan.text) + "</p></div>";
    h += "<h4>What to do</h4>" + list(r.next_steps, "ol");
    h += '<p class="adead"><strong>Deadline:</strong> ' + esc(r.deadline) + "</p>";
    h += "<details><summary>Your rights at nonprofit hospitals</summary>" + list(r.rights, "ul") + "</details>";
    h += '<h4><label for="a-letter">Your letter to the billing office</label></h4>' +
      '<textarea id="a-letter">' + esc(r.letter) + "</textarea>" +
      '<div class="abtns"><button type="button" class="btn btn-primary btn-sm a-mail">Open in my email</button>' +
      '<button type="button" class="btn btn-secondary btn-sm a-copy">Copy</button></div>' +
      '<p class="afine">Fill in the parts in [brackets] before you send it. <a href="' + esc(r.more_info) +
      '" target="_blank" rel="noopener">Compare state charity care laws</a></p></div>';
    return h;
  }

  window.CandorifyAssist = { render: render };
  function auto() {
    var slot = document.getElementById("assistance-slot");
    if (slot) render(slot);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", auto);
  else auto();
})();