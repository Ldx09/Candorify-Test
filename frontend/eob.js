/* Compare the bill with the patient's insurance EOB (Explanation of Benefits).
   Card on the Review step. The EOB PDF is read on our server in memory and deleted; EOB photos are read on
   the device (photo.js) and only their text is sent. Only the totals and dates are kept on the bill.
   Used on bill.html (add after main.js):  <script src="eob.js" defer></script>
   main.js calls CandorifyEob.render(box, { billId, eob, onResult }). */
(function () {
  "use strict";
  var API = window.CandorifyAPI;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(n) {
    return "$" + Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function date(iso) { var p = String(iso).split("-"); return p.length === 3 ? p[1] + "/" + p[2] + "/" + p[0] : iso; }

  var styled = false;
  function style() {
    if (styled) return;
    styled = true;
    var s = document.createElement("style");
    s.textContent =
      ".xcard{margin:22px 0 0;padding:20px;border:1px solid rgba(31,59,45,.18);border-radius:14px;background:var(--paper,#FBF8F1)}" +
      ".xcard h3{margin:0 0 6px;font-size:1.1rem;display:flex;align-items:center}" +
      ".xcard .xsub{margin:0 0 14px;font-size:.92rem;color:var(--muted,#595D51);max-width:64ch}" +
      ".xrow{display:flex;flex-wrap:wrap;gap:10px;align-items:center}" +
      ".xrow label{cursor:pointer}" +
      ".xstatus{margin:10px 0 0;font-size:.9rem;min-height:1.2em}" +
      ".xstatus.err{color:#7A2E13}" +
      ".xgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin:4px 0 12px}" +
      ".xgrid div{padding:12px 14px;border-radius:10px;background:#fff;border:1px solid rgba(31,59,45,.12)}" +
      ".xgrid span{display:block;font-size:.8rem;color:var(--muted,#595D51)}" +
      ".xgrid strong{font-size:1.1rem}" +
      ".xnote{margin:0 0 12px;padding:10px 12px;border-left:3px solid var(--ochre,#DDB65F);background:rgba(221,182,95,.14);border-radius:0 10px 10px 0;font-size:.9rem}" +
      ".xok{margin:0 0 12px;font-size:.92rem}" +
      ".xfine{margin:10px 0 0;font-size:.8rem;color:var(--muted,#595D51)}";
    document.head.appendChild(s);
  }

  var HELP = "After a visit, your insurance company sends an Explanation of Benefits (EOB) saying what it paid and " +
    "what you may owe. Add yours and we compare it with this bill: if the bill asks for more than the EOB says, or " +
    "the insurance payment doesn't match, we flag it and add it to your letter. Your EOB file is never stored.";
  function help() {   // the "?" next to the title (from assistance.js, which this page also loads)
    return window.CandorifyHelp ? window.CandorifyHelp.html(HELP, "What does the EOB comparison do?") : "";
  }

  function render(box, ctx) {
    style();
    var r = ctx.result || null;
    var eob = r ? r.eob : ctx.eob;
    box.innerHTML = '<section class="xcard" aria-labelledby="eob-title"><h3 id="eob-title">Compare with your insurance EOB' +
      help() + "</h3>" + (eob ? summaryHTML(eob, r) : introHTML()) + "</section>";
    var status = box.querySelector(".xstatus");
    function busy(msg) { status.className = "xstatus"; status.textContent = msg; }
    function fail(err) { status.className = "xstatus err"; status.textContent = err.message || String(err); }
    function done(res) {
      ctx.result = res;
      ctx.eob = res.eob;
      ctx.onResult(res);
    }
    var pdf = box.querySelector("#eob-pdf"), photos = box.querySelector("#eob-photos"), remove = box.querySelector(".eob-remove");
    if (pdf) pdf.addEventListener("change", function () {
      var f = pdf.files && pdf.files[0];
      pdf.value = "";
      if (!f) return;
      if (!/pdf$/i.test(f.type) && !/\.pdf$/i.test(f.name)) { fail(new Error("Choose a PDF, or take photos of your EOB.")); return; }
      busy("Reading your EOB…");
      API.uploadEob(ctx.billId(), f).then(done, fail);
    });
    if (photos) photos.addEventListener("change", function () {
      var files = Array.prototype.slice.call(photos.files || []).slice(0, 5);
      photos.value = "";
      if (!files.length) return;
      if (!window.CandorifyPhoto || !window.CandorifyPhoto.readFiles) { fail(new Error("Photo reading isn't available on this page.")); return; }
      window.CandorifyPhoto.readFiles(files, busy)
        .then(function (pages) { busy("Comparing with your bill…"); return API.uploadEobText(ctx.billId(), pages); })
        .then(done, fail);
    });
    if (remove) remove.addEventListener("click", function () {
      busy("Removing…");
      API.removeEob(ctx.billId()).then(function (res) { ctx.result = null; done(res); }, fail);
    });
  }

  function introHTML() {
    return '<p class="xsub">After a visit, your insurance sends an Explanation of Benefits (EOB). It shows what your plan paid and ' +
      "what you may owe. Add it and we'll check that the bill doesn't ask for more.</p>" +
      '<div class="xrow">' +
      '<label class="btn btn-secondary btn-sm">Upload EOB (PDF)<input type="file" id="eob-pdf" accept="application/pdf" class="sr-only"></label>' +
      '<label class="btn btn-secondary btn-sm">Take photos of it<input type="file" id="eob-photos" accept="image/*" multiple class="sr-only"></label>' +
      "</div>" +
      '<p class="xstatus" role="status"></p>' +
      '<p class="xfine">Your EOB file is never stored. We keep only its totals and dates with this bill.</p>';
  }

  function summaryHTML(e, r) {
    var cells = [["billed", "Billed to insurance"], ["allowed", "Plan's approved amount"], ["plan_paid", "Plan paid"], ["you_owe", "You may owe"]]
      .filter(function (c) { return e[c[0]] != null; })
      .map(function (c) { return "<div><span>" + c[1] + "</span><strong>" + money(e[c[0]]) + "</strong></div>"; }).join("");
    var visit = r && r.same_visit === true && e.service_dates && e.service_dates.length
      ? '<p class="xok">Same visit: ' + esc(date(e.service_dates[0])) + "</p>" : "";
    var note = r && r.note ? '<p class="xnote">' + esc(r.note) + "</p>" : "";
    return '<p class="xsub">From your EOB. Anything that doesn\'t match the bill shows up in the list above.</p>' +
      '<div class="xgrid">' + cells + "</div>" + visit + note +
      '<div class="xrow"><button type="button" class="btn btn-quiet btn-sm eob-remove">Remove this EOB</button></div>' +
      '<p class="xstatus" role="status"></p>' +
      '<p class="xfine">Your EOB file is never stored. We keep only its totals and dates with this bill.</p>';
  }

  window.CandorifyEob = { render: render };
})();