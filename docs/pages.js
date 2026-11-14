/* ============================================================================
   TradeGuard — pages.js  (v1.0)
   ----------------------------------------------------------------------------
   یک کار، سبک و بی‌خطر: ورود پله‌ای بخش‌های صفحه با اسکرول.
   اگر مرورگر IntersectionObserver نداشت یا کاربر «کاهش حرکت» را روشن کرده بود،
   هیچ کلاسی اضافه نمی‌شود و صفحه همان‌طور که هست دیده می‌شود.
   بدون وابستگی بیرونی و بدون هیچ درخواست شبکه.
   ============================================================================ */
(function () {
  "use strict";

  var doc = typeof document !== "undefined" ? document : null;
  if (!doc) return;
  var win = typeof window !== "undefined" ? window : null;

  function reduced() {
    try {
      return !!(win && typeof win.matchMedia === "function" &&
        win.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (e) {
      return false;
    }
  }

  function initReveal() {
    if (!win || reduced() || !("IntersectionObserver" in win)) return;

    /* [selector, stagger-seconds] */
    var groups = [
      [".wrap > *", 0.05],
      [".rows > *", 0.05],
      [".plans > *", 0.05],
      [".live > div", 0.05],
      [".items > *", 0.05],
      [".stats > *", 0.05],
      [".why > *", 0.04],
      [".perks > li", 0.03]
    ];

    var io = new win.IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        var e = entries[i];
        if (!e.isIntersecting) continue;
        e.target.classList.add("pg-in");
        io.unobserve(e.target);
      }
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.06 });

    for (var g = 0; g < groups.length; g++) {
      var nodes = doc.querySelectorAll(groups[g][0]);
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.classList.contains("pg-reveal")) continue;
        n.classList.add("pg-reveal");
        if (groups[g][1]) {
          /* سقف تأخیر: عناصر پایین صفحه پشت صف طولانی نمانند */
          var delay = Math.min(i * groups[g][1], 0.3);
          n.style.setProperty("--pg-delay", delay.toFixed(2) + "s");
        }
        io.observe(n);
      }
    }
  }

  function boot() {
    try { initReveal(); } catch (e) {}
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
