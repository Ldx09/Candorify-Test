// homepage only!! sliding cards, spinning glass box, the clock, fade ins, count ups
// purely the looks. the actual app (upload, letters, all that) is in main.js
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  // reduce motion setting on = nothing moves for them. respect it
  const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const pad = (n) => String(n).padStart(2, "0");
  const onHome = () => { const h = $("#view-home"); return h && !h.hidden; };

  // anything that moves on scroll goes in here so it all runs once per frame. keeps it smooth
  const scrollers = [];
  let ticking = false;
  function frame() { ticking = false; scrollers.forEach((fn) => fn()); }
  function requestFrame() { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }
  addEventListener("scroll", requestFrame, { passive: true });
  addEventListener("resize", () => { layouts.forEach((fn) => fn()); requestFrame(); });
  const layouts = [];

  // --- small helpers ---
  function initClock() {
    const els = $$("[data-clock]");
    if (!els.length) return;
    const tick = () => {
      const t = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
      els.forEach((el) => { el.textContent = t; });
    };
    tick();
    setInterval(tick, 15000);
  }

  function initTicks() {
    $$("[data-ticks]").forEach((el) => {
      const n = parseInt(el.dataset.ticks, 10) || 20;
      el.innerHTML = Array.from({ length: n }, (_, i) => `<i style="--i:${i}"></i>`).join("");
    });
  }
  function lightTicks(el, fraction) {
    if (!el) return;
    const ticks = el.children, lit = Math.round(fraction * ticks.length);
    for (let i = 0; i < ticks.length; i++) ticks[i].classList.toggle("on", i < lit);
  }

  // ========== WHAT WE LOOK FOR (sideways cards) ==========
  // scroll down -> cards slide sideways (studio noun vibes). the 6 cards are written right below, edit them here
  // want a photo on a card? add img: "assets/img/look/double.jpg" (any path) and it fills the card behind the number + title. Matt if u find good photos lmk
  const SLIDES = [
    { title: "Double charges",
      text: "The same test, scan, or supply can show up twice. We compare every line and point out repeats on the same day.",
      example: "Two identical blood tests, same day, same price." },
    { title: "Bad math",
      text: "Quantity times price should equal the line total. We redo the math on every single line.",
      example: "1 × $260.00, billed as $620.00." },
    { title: "Wrong totals",
      text: "We add up every charge and compare it to the amount you're asked to pay.",
      example: "Charges add up to $355.00. Amount due says $455.00." },
    { title: "Odd quantities",
      text: "Some numbers don't fit your visit. We point them out so you can ask.",
      example: "30 blood draws during a 3-day stay." },
    { title: "Extra days",
      text: "We ask how many nights you stayed, then compare it to the room charges.",
      example: "7 room days billed. You stayed 6 nights." },
    { title: "Confusing codes",
      text: "Every billing code on your bill, explained in plain words and in your language.",
      example: "J1100 means a steroid shot, billed per 1 mg." },
  ];

  let galleryJump = null;

  function initGallery() {
    const section = $("#what-we-look-for"), track = $("#gal-track"), cap = $("#gal-cap"), ticks = $("#gal-ticks");
    if (!section || !track) return;
    const n = SLIDES.length;

    track.innerHTML = SLIDES.map((s, i) => `
      <li class="ngal-card">
        <figure class="frame-card">
          <div class="ngal-img">
            ${s.img ? `<img class="ngal-photo" src="${esc(s.img)}" alt="" loading="lazy">` : ""}
            <span class="ngal-num" aria-hidden="true">${pad(i + 1)}</span>
            <span class="ngal-card-title">${esc(s.title)}</span>
          </div>
          <figcaption>
            <span class="ngal-card-text"><span>${esc(s.text)}</span> <span class="ngal-card-ex">For example: ${esc(s.example)}</span></span>
          </figcaption>
        </figure>
      </li>`).join("");

    const pinned = !reduceMotion;
    section.classList.toggle("is-static", !pinned);
    let dist = 0, active = -1, lastX = 0, blur = 0, skew = 0, settling = false;
    function settle() {
      if (settling) return;
      settling = true;
      const step = () => {
        blur *= 0.82; skew *= 0.8;
        if (blur < 0.12 && Math.abs(skew) < 0.05) { blur = 0; skew = 0; }
        track.style.filter = blur ? `blur(${blur.toFixed(2)}px)` : "none";
        track.style.transform = `translate3d(${lastX.toFixed(1)}px,0,0) skewX(${skew.toFixed(2)}deg)`;
        if (blur || skew) requestAnimationFrame(step); else settling = false;
      };
      requestAnimationFrame(step);
    }

    function setActive(i) {
      if (i === active) return;
      active = i;
      const s = SLIDES[i];
      cap.innerHTML = `<p class="cap dim">${pad(i + 1)} / ${pad(n)}</p>
        <p class="ngal-name">${esc(s.title)}</p>
        <p class="ngal-text">${esc(s.text)}</p>
        <p class="ngal-ex"><span class="cap">For example</span> ${esc(s.example)}</p>`;
      cap.classList.remove("swap"); void cap.offsetWidth; cap.classList.add("swap");
      $$(".ngal-card", track).forEach((c, k) => c.classList.toggle("is-active", k === i));
    }

    // each card stops dead center before the next one slides in, so the caption always matches
    // whatever card is in the middle. PER_CARD = how much scrolling each card gets (in screen heights)
    // bump it up if u want each card to hang around longer
    const PER_CARD = 0.9;
    let scrollLen = 0;
    function layout() {
      if (!pinned) { section.style.height = ""; track.style.paddingLeft = track.style.paddingRight = ""; return; }
      track.style.transform = "none";
      const cards = $$(".ngal-card", track);
      const w = track.parentElement.clientWidth, cw = cards[0].offsetWidth;
      const side = Math.max(0, (w - cw) / 2) + "px";        // so the 1st + last card can both reach the middle
      track.style.paddingLeft = side;
      track.style.paddingRight = side;
      // exact gap between card centers. offsetLeft rounds and over 6 cards it drifted like 5px
      const mid = (c) => { const r = c.getBoundingClientRect(); return r.left + r.width / 2; };
      const stepPx = cards.length > 1 ? (mid(cards[cards.length - 1]) - mid(cards[0])) / (cards.length - 1) : 0;
      dist = stepPx * (n - 1);                               // card 1 centered -> card 6 centered
      scrollLen = Math.round(innerHeight * PER_CARD * (n - 1));
      section.style.height = (innerHeight + scrollLen) + "px";
    }

    function onScroll() {
      if (!onHome()) return;
      if (!pinned) return;
      const r = section.getBoundingClientRect();
      if (r.bottom < -50 || r.top > innerHeight + 50) return;
      const p = scrollLen ? clamp(-r.top / scrollLen, 0, 1) : 0;
      // chill on each card for a sec then glide to the next (same trick as the glass box)
      const raw = p * (n - 1), i = Math.floor(raw), f = raw - i;
      const k = clamp((f - 0.3) / 0.4, 0, 1), eased = k * k * (3 - 2 * k);
      const pos = Math.min(n - 1, i + eased);
      const x = -(pos / (n - 1)) * dist;
      const v = x - lastX; lastX = x;
      // lil motion blur + lean while it's moving, settles when u stop scrolling
      blur = Math.max(blur, Math.min(3, Math.abs(v) * 0.06));
      skew = clamp(v * 0.04, -3, 3);
      track.style.transform = `translate3d(${x.toFixed(1)}px,0,0) skewX(${skew.toFixed(2)}deg)`;
      settle();
      lightTicks(ticks, pos / (n - 1));
      setActive(clamp(Math.round(pos), 0, n - 1));   // whichever card is closest to the middle
    }

    if (!pinned) {
      // no-motion version: cards just scroll sideways normally and the caption follows whatever's most visible
      track.parentElement.addEventListener("scroll", () => {
        const w = track.parentElement;
        const p = w.scrollWidth > w.clientWidth ? w.scrollLeft / (w.scrollWidth - w.clientWidth) : 0;
        setActive(clamp(Math.round(p * (n - 1)), 0, n - 1));
        lightTicks(ticks, p);
      }, { passive: true });
    }

    galleryJump = (i) => {
      if (pinned) {
        const top = section.getBoundingClientRect().top + scrollY;
        scrollTo({ top: top + (scrollLen * i) / (n - 1) + 2, behavior: "smooth" });
      } else {
        section.scrollIntoView();
        const card = $$(".ngal-card", track)[i];
        if (card) track.parentElement.scrollLeft = card.offsetLeft - 16;
      }
    };

    layouts.push(layout);
    scrollers.push(onScroll);
    layout();
    setActive(0);
    // images + fonts loading in change the track width so re-measure when they do
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { layout(); requestFrame(); });
    addEventListener("load", () => { layout(); requestFrame(); });
  }

  function initLookButtons() {
    $$("[data-look]").forEach((b) => b.addEventListener("click", () => {
      if (galleryJump) galleryJump(parseInt(b.dataset.look, 10) || 0);
    }));
  }

  // ---- how it works: the glass box ----
  // box turns 1 side per step as u scroll. the 4 sides are written in home.html
  function initBox() {
    const section = $("#how-it-works"), cube = $("#box-cube");
    if (!section || !cube) return;
    const faces = $$(".nbox-face", cube), steps = faces.length;
    const count = $("#box-count"), index = $$("#box-index button"), vticks = $("#box-ticks");
    vticks.innerHTML = Array.from({ length: 24 }, () => "<i></i>").join("");
    const bars = Array.from(vticks.children);
    const pinned = !reduceMotion;
    section.classList.toggle("is-static", !pinned);
    let active = -1;

    function setActive(i) {
      if (i === active) return;
      active = i;
      count.textContent = pad(i + 1);
      faces.forEach((f, k) => f.classList.toggle("is-front", k === i));
      index.forEach((b, k) => b.toggleAttribute("aria-current", k === i));
    }

    function onScroll() {
      if (!onHome() || !pinned) return;
      const r = section.getBoundingClientRect();
      if (r.bottom < -50 || r.top > innerHeight + 50) return;
      const total = section.offsetHeight - innerHeight;
      const p = clamp(-r.top / total, 0, 1) * (steps - 1);
      const i = Math.floor(p), f = p - i;
      // pauses on each side for a sec before turning so ppl can actually read it
      const k = clamp((f - 0.22) / 0.56, 0, 1), e = k * k * (3 - 2 * k);
      const pos = Math.min(steps - 1, i + e);
      cube.style.transform = `rotateX(${(pos * 90).toFixed(2)}deg)`;
      setActive(Math.round(pos));
      const centre = (pos / (steps - 1)) * (bars.length - 1);
      bars.forEach((b, n) => { b.style.setProperty("--w", (1 - Math.min(1, Math.abs(n - centre) / 5)).toFixed(2)); });
    }

    index.forEach((b) => b.addEventListener("click", () => {
      const step = parseInt(b.dataset.step, 10);
      if (!pinned) { faces[step].scrollIntoView({ block: "center" }); return; }
      const top = section.getBoundingClientRect().top + scrollY;
      const total = section.offsetHeight - innerHeight;
      scrollTo({ top: top + (total * step) / (steps - 1) + 2, behavior: "smooth" });
    }));

    scrollers.push(onScroll);
    setActive(0);
    bars.forEach((b, n) => b.style.setProperty("--w", (1 - Math.min(1, n / 5)).toFixed(2)));
  }

  // code + language card
  const CODES = {
    "85025": { en: "Complete blood count, a common blood test", es: "Hemograma completo, un análisis de sangre común", zh: "全血细胞计数，一种常见的血液检查" },
    "71046": { en: "Chest X-ray, 2 views", es: "Radiografía de tórax, 2 vistas", zh: "胸部X光检查，2个角度" },
    "J1100": { en: "Steroid shot (dexamethasone), per 1 mg", es: "Inyección de esteroide (dexametasona), por 1 mg", zh: "类固醇注射（地塞米松），每1毫克" },
  };
  function initLangCard() {
    const outEl = $("#lang-out");
    if (!outEl) return;
    let code = "85025", lang = "en";
    function render() {
      outEl.textContent = CODES[code][lang];
      outEl.lang = lang;
      $$(".code-pick").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.code === code)));
      $$(".lang-tabs [data-lang]").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.lang === lang)));
    }
    $$(".code-pick").forEach((b) => b.addEventListener("click", () => { code = b.dataset.code; render(); }));
    $$(".lang-tabs [data-lang]").forEach((b) => b.addEventListener("click", () => { lang = b.dataset.lang; render(); }));
    render();
  }

  // letter demo: tick a charge and it pops into the letter
  function initAskDemo() {
    const boxes = $$("[data-ask]");
    if (!boxes.length) return;
    function render() {
      const picked = boxes.filter((b) => b.checked).map((b) => b.dataset.ask);
      $("#ask-list").innerHTML = picked.length
        ? picked.map((p) => `<li>${esc(p)}</li>`).join("")
        : '<li class="muted">Tick a charge to add it.</li>';
    }
    boxes.forEach((b) => b.addEventListener("change", render));
    render();
  }

  // MENU - the photo preview follows whatever item ur pointing at
  function initMenuPreview() {
    const menu = $("#site-menu"), img = $("#menu-img");
    if (!menu || !img) return;
    const show = (btn) => {
      const items = $$(".menu-list li:not([hidden]) button", menu);
      const n = items.indexOf(btn);
      if (n < 0) return;
      $("#menu-pnum").textContent = pad(n + 1) + " / " + pad(items.length);
      $("#menu-plabel").textContent = btn.textContent.trim();
      img.innerHTML = `<span>${esc(btn.textContent.trim())}</span>`;
      img.classList.remove("swap"); void img.offsetWidth; img.classList.add("swap");
    };
    menu.addEventListener("pointerover", (e) => { const b = e.target.closest(".menu-list button"); if (b) show(b); });
    menu.addEventListener("focusin", (e) => { const b = e.target.closest(".menu-list button"); if (b) show(b); });
  }

  // ------- reveal on scroll, count ups, progress bar, header, floating sign up pill -------
  function initScrollEffects() {
    const reveal = $$("[data-reveal], [data-reveal-group] > *");
    $$("[data-reveal-group]").forEach((g) => $$(":scope > *", g).forEach((el, i) => el.style.setProperty("--delay", (i * 0.1) + "s")));
    if (reduceMotion || !("IntersectionObserver" in window)) {
      reveal.forEach((el) => el.classList.add("is-in"));
    } else {
      document.documentElement.classList.add("js-reveal");
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } });
      }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
      reveal.forEach((el) => io.observe(el));
    }

    // number count-ups!!
    // every stat sits at 0 and shoots up fast once u can actually see it. way more fun than just showing the number
    //   data-count="31.7"        the final number (decimals ok)
    //   data-decimals="1"        how many decimals to show (default 0)
    //   data-prefix / data-suffix text before/after, e.g. "$" and " billion"
    //   data-count-delay="600"   wait (ms) so the fade-in finishes first (default 350)
    //   data-count-dur="900"     how long the count takes (ms, default 900)
    const counters = $$("[data-count]");
    const show = (el, n) => {
      const dec = Number(el.dataset.decimals) || 0;
      el.textContent = (el.dataset.prefix || "") +
        n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + (el.dataset.suffix || "");
    };
    const run = (el) => {
      const end = Number(el.dataset.count);
      if (reduceMotion) { show(el, end); return; }
      const delay = el.dataset.countDelay != null ? Number(el.dataset.countDelay) : 350;
      const dur = Number(el.dataset.countDur) || 900;
      show(el, 0);
      setTimeout(() => {
        const t0 = performance.now();
        const step = (now) => {
          const k = Math.min(1, Math.max(0, (now - t0) / dur)), eased = 1 - Math.pow(1 - k, 3);
          show(el, k < 1 ? end * eased : end);
          if (k < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }, delay);
    };
    if (!reduceMotion && "IntersectionObserver" in window) {
      counters.forEach((el) => show(el, 0));   // sit at 0 until it scrolls into view
      const co = new IntersectionObserver((entries) => {
        entries.forEach((e) => { if (e.isIntersecting) { run(e.target); co.unobserve(e.target); } });
      }, { threshold: 0.4 });
      counters.forEach((el) => co.observe(el));
    }

    const bar = $("#scroll-bar"), header = $(".site-header"), bg = $(".nh-bg"), cta = $("#float-cta");
    let dismissed = false;
    scrollers.push(() => {
      const y = scrollY, max = document.documentElement.scrollHeight - innerHeight;
      if (bar) bar.style.transform = `scaleX(${max > 0 ? y / max : 0})`;
      const home = onHome();
      const hero = $(".nh");
      const heroH = hero ? hero.offsetHeight : 600;
      header.classList.toggle("is-scrolled", y > 8);
      header.classList.toggle("is-over-hero", home && y < heroH - 70);
      if (bg && home && !reduceMotion) bg.style.transform = `translate3d(0,${(Math.min(y, 900) * 0.3).toFixed(1)}px,0) scale(1.15)`;
      const end = $(".ncta");
      const nearEnd = end && end.getBoundingClientRect().top < innerHeight;
      // hide the floating pill while a pinned section (gallery / glass box) is taking up the screen
      const pinnedOnScreen = $$(".ngal:not(.is-static), .nbox:not(.is-static)").some((el) => {
        const r = el.getBoundingClientRect();
        return r.top < innerHeight * 0.5 && r.bottom > innerHeight * 0.5;
      });
      const show = home && !document.body.classList.contains("logged-in") && !dismissed && y > heroH * 0.8 && !nearEnd && !pinnedOnScreen;
      if (cta) { if (show) cta.hidden = false; cta.classList.toggle("is-on", show); }
    });
    if (cta) cta.addEventListener("click", () => { dismissed = true; cta.classList.remove("is-on"); });

    // switching views doesnt fire a scroll event so re-measure when it happens
    if ("MutationObserver" in window) {
      const mo = new MutationObserver(() => { layouts.forEach((fn) => fn()); requestFrame(); });
      $$("main > .view").forEach((v) => mo.observe(v, { attributes: true, attributeFilter: ["hidden"] }));
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTicks();
    initClock();
    initGallery();
    initLookButtons();
    initBox();
    initLangCard();
    initAskDemo();
    initMenuPreview();
    initScrollEffects();
    requestFrame();
  });
})();

// ok small disclaimer, some AI was used to help assist writing a few of these features
