/* ============================================================================
   TradeGuard — space.js  (v1.0)
   ----------------------------------------------------------------------------
   لایهٔ حرکت و عمق مینی‌اپ:
     ۱) صحنهٔ پس‌زمینه (سحابی + شبکهٔ پرسپکتیو + ستاره + شهاب)
     ۲) تزئین کارت‌ها با هستهٔ هولوگرافیک سه‌بعدی و بازتاب نور
     ۳) تیلت سه‌بعدی کارت‌ها با ماوس (فقط دستگاه‌های دقیق)
     ۴) اندیکاتور لغزندهٔ نوار تب
     ۵) پالس اعداد هنگام به‌روزرسانی دادهٔ زنده
     ۶) پارالاکس ملایم صحنه با اسکرول
   هیچ وابستگی بیرونی ندارد، بدون canvas کار می‌کند، و در محیط‌های بدون DOM
   واقعی (jsdom) هم بی‌خطا اجرا می‌شود. اگر prefers-reduced-motion روشن باشد،
   حرکت‌ها خاموش می‌شوند ولی ساختار و خوانایی دست‌نخورده می‌ماند.
   ============================================================================ */
(function () {
  "use strict";

  var DONE = false;
  var doc = typeof document !== "undefined" ? document : null;
  if (!doc) return;

  var win = typeof window !== "undefined" ? window : null;

  /* ---------- ابزارها ---------- */
  function el(tag, cls, parent) {
    var n = doc.createElement(tag);
    if (cls) n.className = cls;
    if (parent) parent.appendChild(n);
    return n;
  }
  function mq(query) {
    try {
      if (!win || typeof win.matchMedia !== "function") return false;
      return !!win.matchMedia(query).matches;
    } catch (e) {
      return false;
    }
  }
  function reduced() { return mq("(prefers-reduced-motion: reduce)"); }
  function finePointer() {
    return mq("(hover: hover) and (pointer: fine)") && !mq("(max-width: 719px)");
  }
  function app() { return doc.getElementById("tgApp"); }

  /* =========================================================================
     ۱) صحنهٔ پس‌زمینه
     ========================================================================= */
  function buildScene(host) {
    var scene = doc.getElementById("spaceScene");
    if (!scene) {
      scene = el("div", "", host);
      scene.id = "spaceScene";
      scene.setAttribute("aria-hidden", "true");

      el("div", "sp-neb sp-neb-a", scene);
      el("div", "sp-neb sp-neb-b", scene);
      el("div", "sp-neb sp-neb-c", scene);

      var grid = el("div", "sp-grid", scene);
      el("i", "", grid);

      var stars = el("div", "sp-stars", scene);
      layStars(stars);

      // سه شهاب‌سنگ با زمان‌بندی نامنظم
      var shots = [
        { top: "9%", left: "6%", dur: "13s", delay: "4s" },
        { top: "26%", left: "-4%", dur: "17s", delay: "11s" },
        { top: "4%", left: "44%", dur: "21s", delay: "18s" }
      ];
      shots.forEach(function (s) {
        var n = el("i", "sp-shoot", scene);
        n.style.setProperty("--sp-top", s.top);
        n.style.setProperty("--sp-left", s.left);
        n.style.setProperty("--sp-dur", s.dur);
        n.style.setProperty("--sp-delay", s.delay);
      });

      el("div", "sp-veil", scene);
    }
    // صحنه همیشه باید اولین فرزند باشد تا زیر همه‌چیز بماند
    if (host.firstChild && host.firstChild !== scene) {
      host.insertBefore(scene, host.firstChild);
    }
    return scene;
  }

  /** آیا کارت قهرمان قبلاً تزئین شده؟ (جلوگیری از تکرار) */
  function hasDecor(card) {
    var kids = card.children || [];
    for (var i = 0; i < kids.length; i++) {
      var cl = kids[i].classList;
      if (cl && cl.contains("sp-aurora")) return true;
    }
    return false;
  }

  /** ستاره‌ها را با پراکندگی طبیعی می‌چیند (بدون rAF، فقط CSS) */
  function layStars(box) {
    var count = mq("(max-width: 400px)") ? 34 : 52;
    for (var i = 0; i < count; i++) {
      var s = el("i", "sp-star", box);
      var big = Math.random() > 0.86;
      if (big) s.className = "sp-star is-big";
      s.style.top = (Math.random() * 88).toFixed(2) + "%";
      s.style.left = (Math.random() * 100).toFixed(2) + "%";
      s.style.setProperty("--sp-dur", (4.5 + Math.random() * 7).toFixed(2) + "s");
      s.style.setProperty("--sp-delay", (-Math.random() * 9).toFixed(2) + "s");
      s.style.opacity = (0.28 + Math.random() * 0.5).toFixed(2);
    }
  }

  /* =========================================================================
     ۲) تزئین کارت‌ها
     ========================================================================= */
  function decorateCards() {
    var root = app();
    if (!root) return;

    // کارت قهرمان: هالهٔ چرخان + حلقهٔ HUD + هستهٔ سه‌بعدی
    var heroes = root.querySelectorAll(".opp-card");
    for (var i = 0; i < heroes.length; i++) {
      var card = heroes[i];
      if (hasDecor(card)) continue;
      card.insertBefore(el("i", "sp-aurora"), card.firstChild);
      card.insertBefore(el("i", "sp-hud"), card.firstChild);
      var core = el("div", "sp-core", null);
      el("i", "", core);
      el("i", "", core);
      el("i", "", core);
      card.insertBefore(core, card.firstChild);
    }

  }

  /* =========================================================================
     ۳) تیلت سه‌بعدی + بازتاب نور
     ========================================================================= */
  function initTilt() {
    if (reduced() || !finePointer()) return;
    var active = null;
    var MAX = 6;

    function reset(node) {
      if (!node) return;
      node.classList.remove("is-tilting");
      node.style.removeProperty("--sp-rx");
      node.style.removeProperty("--sp-ry");
      node.style.removeProperty("--sp-mx");
      node.style.removeProperty("--sp-my");
    }

    function onMove(ev) {
      var target = ev.target && ev.target.closest ? ev.target.closest("#tgApp .card") : null;
      if (target !== active) {
        reset(active);
        active = target;
      }
      if (!target) return;
      var r = target.getBoundingClientRect();
      if (!r.width || !r.height) return;
      var px = (ev.clientX - r.left) / r.width;
      var py = (ev.clientY - r.top) / r.height;
      target.classList.add("is-tilting");
      target.style.setProperty("--sp-ry", ((px - 0.5) * 2 * MAX).toFixed(2) + "deg");
      target.style.setProperty("--sp-rx", ((0.5 - py) * 2 * MAX).toFixed(2) + "deg");
      target.style.setProperty("--sp-mx", (px * 100).toFixed(1) + "%");
      target.style.setProperty("--sp-my", (py * 100).toFixed(1) + "%");
    }

    doc.addEventListener("pointermove", onMove, { passive: true });
    doc.addEventListener("pointerdown", onMove, { passive: true });
    doc.addEventListener("pointerleave", function () { reset(active); active = null; }, { passive: true });
    if (win && win.addEventListener) {
      win.addEventListener("blur", function () { reset(active); active = null; });
    }
  }

  /* =========================================================================
     ۴) اندیکاتور لغزندهٔ نوار تب
     ========================================================================= */
  function initTabGlow() {
    var bar = doc.querySelector("#tgApp .tabbar");
    if (!bar) return;

    var glow = bar.querySelector(".tab-glow");
    if (!glow) {
      glow = el("i", "tab-glow");
      glow.setAttribute("aria-hidden", "true");
      bar.insertBefore(glow, bar.firstChild);
    }

    var raf = null;
    function place() {
      var on = bar.querySelector(".tab-btn.is-on") || bar.querySelector(".tab-btn");
      if (!on) return;
      var w = on.offsetWidth || 0;
      if (!w) return;                       // jsdom: هنوز چیدمانی وجود ندارد
      glow.style.setProperty("--sp-tab-x", on.offsetLeft + "px");
      glow.style.setProperty("--sp-tab-w", w + "px");
      glow.classList.add("is-ready");
    }
    function schedule() {
      if (raf) return;
      var r = win && win.requestAnimationFrame ? win.requestAnimationFrame : function (f) { return setTimeout(f, 16); };
      raf = r(function () { raf = null; place(); });
    }

    bar.addEventListener("click", function () { setTimeout(place, 0); }, true);
    if (win && win.ResizeObserver) {
      try { new win.ResizeObserver(schedule).observe(bar); } catch (e) {}
    }
    if (win && win.addEventListener) win.addEventListener("resize", schedule);
    if (win && win.MutationObserver) {
      var mo = new win.MutationObserver(function (list) {
        for (var i = 0; i < list.length; i++) {
          if (list[i].attributeName === "class") return schedule();
        }
      });
      mo.observe(bar, { attributes: true, subtree: true, attributeFilter: ["class"] });
    }
    // تب فعال ممکن است بعد از رندر اولیه عوض شود
    setTimeout(place, 60);
    setTimeout(place, 400);
    schedule();
  }

  /* =========================================================================
     ۵) پالس اعداد زنده
     ========================================================================= */
  function initNumPulse() {
    if (!win || !win.MutationObserver) return;
    var ids = ["oppEarn", "oppApr", "oppRate", "fngLiveBadge", "btcLiveBadge", "usageFill", "wdFill"];
    var timers = {};

    function pulse(node) {
      if (!node || reduced()) return;
      var key = node.id || "x";
      node.classList.remove("sp-pop");
      // ری‌فلو برای اجرای دوبارهٔ انیمیشن
      void node.offsetWidth;
      node.classList.add("sp-pop");
      if (timers[key]) clearTimeout(timers[key]);
      timers[key] = setTimeout(function () { node.classList.remove("sp-pop"); }, 700);
    }

    var mo = new win.MutationObserver(function (list) {
      for (var i = 0; i < list.length; i++) {
        var t = list[i].target;
        if (t && t.nodeType === 1) pulse(t);
        else if (t && t.parentNode) pulse(t.parentNode);
      }
    });

    ids.forEach(function (id) {
      var n = doc.getElementById(id);
      if (n) {
        try { mo.observe(n, { childList: true, characterData: true, subtree: true }); } catch (e) {}
      }
    });
  }

  /* =========================================================================
     ۶) پارالاکس ملایم
     ========================================================================= */
  function initParallax() {
    var scene = doc.getElementById("spaceScene");
    var body = doc.querySelector("#tgApp .screen-body");
    if (!scene || !body || reduced()) return;

    var pending = false;
    var last = 0;
    function apply() {
      pending = false;
      scene.style.transform = "translate3d(0," + (last * -0.06).toFixed(2) + "px,0)";
    }
    body.addEventListener("scroll", function () {
      last = body.scrollTop || 0;
      if (last > 900) last = 900;           // سقف جابه‌جایی
      if (!pending) {
        pending = true;
        if (win && win.requestAnimationFrame) win.requestAnimationFrame(apply);
        else setTimeout(apply, 32);
      }
    }, { passive: true });
  }

  /* =========================================================================
     راه‌اندازی
     ========================================================================= */
  function boot() {
    if (DONE) return;
    DONE = true;
    var root = app();
    if (!root) return;

    try { buildScene(root); } catch (e) {}
    try { decorateCards(); } catch (e) {}
    try { initTabGlow(); } catch (e) {}
    try { initTilt(); } catch (e) {}
    try { initNumPulse(); } catch (e) {}
    try { initParallax(); } catch (e) {}

    // تب‌ها ممکن است محتوایشان دوباره ساخته شود ⇒ تزئین مجدد
    root.addEventListener("click", function (ev) {
      var b = ev.target && ev.target.closest ? ev.target.closest(".tab-btn") : null;
      if (b) setTimeout(decorateCards, 30);
    }, true);
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  // برای تست‌های سرتاسری
  if (win) win.__spaceBoot = boot;
})();
