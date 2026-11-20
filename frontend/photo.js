/* Bill photos: read ON THE USER'S DEVICE with Tesseract.js. The photos never leave the phone;
   only the text lines are sent to the backend (/api/upload/photo-text).
   Used on bill.html (add after main.js):  <script src="photo.js" defer></script>
   main.js asks window.CandorifyPhoto: has(), clear(), readPages(onStatus). */
(function () {
  "use strict";
  var MAX_PHOTOS = 5, MAX_MB = 20;
  var V = "5.1.1";
  var TESSERACT_JS = "https://cdn.jsdelivr.net/npm/tesseract.js@" + V + "/dist/tesseract.min.js";
  var WORKER_OPTIONS = {
    workerPath: "https://cdn.jsdelivr.net/npm/tesseract.js@" + V + "/dist/worker.min.js",
    corePath: "https://cdn.jsdelivr.net/npm/tesseract.js-core@" + V,
    langPath: "https://cdn.jsdelivr.net/npm/@tesseract.js-data/eng@1.0.0/4.0.0_best_int",
  };
  var photos = [];          // [{ file, url }]
  var loading = null;       // the Tesseract script, loaded once on first use

  function $(s, r) { return (r || document).querySelector(s); }
  function toast(msg, bad) {
    var t = $("#toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.toggle("err", !!bad);
    t.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { t.classList.remove("show"); }, bad ? 5000 : 3500);
  }

  // ---------- picking photos ----------
  var box;
  function build() {
    var main = $(".upload-main");
    if (!main || $("#photo-pick")) return false;
    var style = document.createElement("style");
    style.textContent =
      ".photo-pick{margin:18px 0 6px}" +
      ".photo-or{display:flex;align-items:center;gap:12px;margin:0 0 12px;color:var(--muted,#595D51);font-size:.92rem}" +
      ".photo-or::before,.photo-or::after{content:'';flex:1;height:1px;background:currentColor;opacity:.25}" +
      ".photo-btns{display:flex;flex-wrap:wrap;gap:10px}" +
      ".photo-btns label{cursor:pointer;display:inline-flex;align-items:center;gap:8px}" +
      ".photo-btns svg{width:18px;height:18px}" +
      ".photo-list{list-style:none;display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 0;padding:0}" +
      ".photo-list li{position:relative;width:76px;animation:photoIn .3s cubic-bezier(.2,.8,.2,1) both}" +
      ".photo-list img{display:block;width:76px;height:96px;object-fit:cover;border-radius:8px;border:1px solid rgba(31,59,45,.25)}" +
      ".photo-list span{display:block;margin-top:4px;font-size:.78rem;text-align:center}" +
      ".photo-list button{position:absolute;top:-8px;right:-8px;width:26px;height:26px;border-radius:50%;border:0;" +
      "background:#18211B;color:#EFE8D9;font-size:15px;line-height:1;cursor:pointer}" +
      ".photo-tip{margin:10px 0 0;font-size:.86rem;color:var(--muted,#595D51)}" +
      "@keyframes photoIn{from{opacity:0;transform:scale(.9)}to{opacity:1;transform:none}}" +
      "@media (prefers-reduced-motion:reduce){.photo-list li{animation:none}}";
    document.head.appendChild(style);

    var cam = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>';
    var pics = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/></svg>';
    box = document.createElement("div");
    box.id = "photo-pick"; box.className = "photo-pick";
    box.innerHTML =
      '<p class="photo-or">or use photos of a paper bill</p>' +
      '<div class="photo-btns">' +
        '<label class="btn btn-secondary btn-sm">' + cam + 'Take a photo' +
          '<input type="file" accept="image/*" capture="environment" class="sr-only" id="photo-camera"></label>' +
        '<label class="btn btn-secondary btn-sm">' + pics + 'Choose photos' +
          '<input type="file" accept="image/*" multiple class="sr-only" id="photo-files"></label>' +
      '</div>' +
      '<ol class="photo-list" aria-label="Your bill photos"></ol>' +
      '<p class="photo-tip">One photo per page, up to 5. Lay the bill flat in good light and fill the photo with the charges. ' +
      'Photos are read on your device and never uploaded.</p>';
    var row = $("#file-row");
    (row && row.parentNode === main ? row : $("#dropzone")).insertAdjacentElement("afterend", box);
    $("#photo-camera").addEventListener("change", onPick);
    $("#photo-files").addEventListener("change", onPick);
    return true;
  }

  function onPick(e) {
    var files = Array.prototype.slice.call(e.target.files || []);
    e.target.value = "";
    if (!files.length) return;
    var room = MAX_PHOTOS - photos.length;
    if (room <= 0) { toast("You can add up to " + MAX_PHOTOS + " photos.", true); return; }
    if (files.length > room) toast("Only the first " + room + " more photo" + (room === 1 ? "" : "s") + " were added (up to " + MAX_PHOTOS + ").", true);
    files.slice(0, room).forEach(function (f) {
      if (!/^image\//.test(f.type) && !/\.(jpe?g|png|heic|heif|webp)$/i.test(f.name)) { toast("That isn't a photo. Choose a JPG or PNG.", true); return; }
      if (f.size > MAX_MB * 1024 * 1024) { toast("That photo is over " + MAX_MB + " MB.", true); return; }
      photos.push({ file: f, url: URL.createObjectURL(f) });
    });
    // photos replace a chosen PDF
    var row = $("#file-row"), clear = $("#btn-clear-file");
    if (photos.length && row && !row.hidden && clear) clear.click();
    render();
  }

  function render() {
    var list = $(".photo-list", box);
    list.innerHTML = "";
    photos.forEach(function (p, i) {
      var li = document.createElement("li");
      var img = document.createElement("img"); img.src = p.url; img.alt = "Page " + (i + 1);
      var label = document.createElement("span"); label.textContent = "Page " + (i + 1);
      var rm = document.createElement("button");
      rm.type = "button"; rm.textContent = "\u00d7"; rm.setAttribute("aria-label", "Remove page " + (i + 1));
      rm.addEventListener("click", function () { URL.revokeObjectURL(p.url); photos.splice(i, 1); render(); });
      li.appendChild(img); li.appendChild(label); li.appendChild(rm); list.appendChild(li);
    });
    var upload = $("#btn-upload"), row = $("#file-row");
    var hasPdf = row && !row.hidden;
    if (upload) {
      upload.disabled = !photos.length && !hasPdf;
      if (photos.length) upload.textContent = "Read my " + (photos.length === 1 ? "photo" : photos.length + " photos");
      else if (/photo/.test(upload.textContent)) upload.textContent = "Read my bill";
    }
    var status = $("#upload-status");
    if (status && photos.length) status.textContent = "";
  }

  function clear() {
    photos.forEach(function (p) { URL.revokeObjectURL(p.url); });
    photos = [];
    if (box) render();
  }

  // ---------- reading the photos on the device ----------
  function loadTesseract() {
    if (window.Tesseract) return Promise.resolve();
    if (!loading) {
      loading = new Promise(function (ok, fail) {
        var s = document.createElement("script");
        s.src = TESSERACT_JS; s.async = true;
        s.onload = ok;
        s.onerror = function () { loading = null; fail(new Error("Couldn't load the photo reader. Check your connection and try again.")); };
        document.head.appendChild(s);
      });
    }
    return loading;
  }

  // Straightens orientation (EXIF), scales to a good reading size, and boosts contrast (grayscale + levels).
  function prepare(file) {
    var source = window.createImageBitmap
      ? createImageBitmap(file, { imageOrientation: "from-image" }).catch(function () { return imgFallback(file); })
      : imgFallback(file);
    return source.then(function (img) {
      var w = img.width, h = img.height;
      var scale = Math.min(2400 / Math.max(w, h), 2.5);
      if (Math.min(w, h) * scale < 1000) scale = 1000 / Math.min(w, h);
      var c = document.createElement("canvas");
      c.width = Math.round(w * scale); c.height = Math.round(h * scale);
      var ctx = c.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(img, 0, 0, c.width, c.height);
      var data = ctx.getImageData(0, 0, c.width, c.height), px = data.data, hist = new Uint32Array(256);
      for (var i = 0; i < px.length; i += 4) {
        var g = (px[i] * 299 + px[i + 1] * 587 + px[i + 2] * 114) / 1000 | 0;
        px[i] = g; hist[g]++;
      }
      var total = px.length / 4, lo = 0, hi = 255, acc = 0;
      while (lo < 255 && (acc += hist[lo]) < total * 0.02) lo++;
      acc = 0;
      while (hi > 0 && (acc += hist[hi]) < total * 0.02) hi--;
      // Stretch contrast only for washed-out photos; clean scans/screenshots (mostly white) stay as they are.
      var stretch = hi - lo >= 60;
      for (var j = 0; j < px.length; j += 4) {
        var v = stretch ? Math.max(0, Math.min(255, (px[j] - lo) * 255 / (hi - lo))) : px[j];
        px[j] = px[j + 1] = px[j + 2] = v;
      }      
      ctx.putImageData(data, 0, 0);
      return c;
    });
  }
  function imgFallback(file) {
    return new Promise(function (ok, fail) {
      var img = new Image(), url = URL.createObjectURL(file);
      img.onload = function () { URL.revokeObjectURL(url); ok(img); };
      img.onerror = function () { URL.revokeObjectURL(url); fail(new Error("We can't open this photo. Take a new one, or save it as JPG.")); };
      img.src = url;
    });
  }

  // Returns [[lines of page 1], [lines of page 2], ...]. onStatus(text) shows progress.
  // Returns [[lines of page 1], [lines of page 2], ...]. onStatus(text) shows progress.
  function readPages(onStatus) {
    return readFiles(photos.map(function (p) { return p.file; }), onStatus);
  }

  // Same, for any list of image files (also used for insurance EOB photos, see eob.js).
  function readFiles(files, onStatus) {
    var say = onStatus || function () {};
    var n = files.length, current = 0, worker;
    say("Getting the photo reader ready…");
    return loadTesseract().then(function () {
      return window.Tesseract.createWorker("eng", 1, Object.assign({
        logger: function (m) {
          if (m.status === "recognizing text") {
            var pct = Math.round(((current + (m.progress || 0)) / n) * 100);
            say("Reading " + (n > 1 ? "page " + (current + 1) + " of " + n : "your photo") + "… " + pct + "%");
          }
        },
      }, WORKER_OPTIONS));
    }).then(function (w) {
      worker = w;
      return worker.setParameters({ tessedit_pageseg_mode: "6", preserve_interword_spaces: "1" });
    }).then(function () {
      var pages = [];
      return files.reduce(function (chain, file, i) {
        return chain.then(function () {
          current = i;
          return prepare(file).then(function (canvas) { return worker.recognize(canvas); }).then(function (r) {
            pages.push((r.data.text || "").split("\n").map(function (l) { return l.trim(); })
              .filter(Boolean).map(function (l) { return l.slice(0, 300); }).slice(0, 400));
          });
        });
      }, Promise.resolve()).then(function () { return pages; });
    }).finally(function () {
      if (worker) worker.terminate();
    });
  }

  window.CandorifyPhoto = {
    has: function () { return photos.length > 0; },
    clear: clear,
    readPages: readPages,
    readFiles: readFiles,
  };
  
  function init() { build(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();