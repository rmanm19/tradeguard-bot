/* ============================================================================
   TradeGuard — landing.js  (v1.0)
   ----------------------------------------------------------------------------
   فقط سه کار، سبک و بی‌خطر:
     ۱) ورود پله‌ای بخش‌ها با اسکرول (اگر مرورگر IntersectionObserver نداشت،
        هیچ کلاسی اضافه نمی‌شود و صفحه همان‌طور که هست دیده می‌شود)
     ۲) پارالاکس ملایم هالهٔ گوشی
     ۳) تیلت گوشیِ دمو با ماوس (فقط دسکتاپ با اشاره‌گر دقیق)
   هیچ وابستگی بیرونی و هیچ درخواست شبکه‌ای ندارد.
   ============================================================================ */
(function () {
  "use strict";

  var doc = typeof document !== "undefined" ? document : null;
  if (!doc) return;
  var win = typeof window !== "undefined" ? window : null;

  function mq(q) {
    try {
      return !!(win && typeof win.matchMedia === "function" && win.matchMedia(q).matches);
    } catch (e) {
      return false;
    }
  }
  var reduced = mq("(prefers-reduced-motion: reduce)");

  /* ---------------------------------------------------------------- reveal */
  function initReveal() {
    if (reduced || !win || !("IntersectionObserver" in win)) return;

    var groups = [
      [".hero-copy > *", 0.06],
      [".hero-demo", 0],
      [".sec-head > *", 0.06],
      [".feat-card", 0.08],
      [".m-card", 0.07],
      [".road", 0],
      [".founder-sim", 0],
      [".site-footer .foot-row", 0.06]
    ];

    var io = new win.IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        var e = entries[i];
        if (!e.isIntersecting) continue;
        e.target.classList.add("lp-in");
        io.unobserve(e.target);
      }
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

    groups.forEach(function (pair) {
      var nodes = doc.querySelectorAll(pair[0]);
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.classList.contains("lp-reveal")) continue;
        n.classList.add("lp-reveal");
        if (pair[1]) n.style.setProperty("--lp-delay", (i * pair[1]).toFixed(2) + "s");
        io.observe(n);
      }
    });
  }

  /* -------------------------------------------------------------- parallax */
  function initParallax() {
    var glow = doc.querySelector(".phone-glow");
    if (!glow || reduced) return;

    var pending = false;
    function apply() {
      pending = false;
      var y = (win.pageYOffset || doc.documentElement.scrollTop || 0);
      if (y > 1200) y = 1200;
      glow.style.transform = "translate3d(0," + (y * 0.08).toFixed(1) + "px,0)";
    }
    win.addEventListener("scroll", function () {
      if (pending) return;
      pending = true;
      if (win.requestAnimationFrame) win.requestAnimationFrame(apply);
      else setTimeout(apply, 40);
    }, { passive: true });
  }

  /* ----------------------------------------------------------------- tilt */
  function initTilt() {
    var phone = doc.querySelector(".hero-demo .phone");
    if (!phone || reduced) return;
    if (!mq("(hover: hover) and (pointer: fine)")) return;
    if (!mq("(min-width: 1021px)")) return;  /* روی موبایل گوشی تخت می‌مانَد */

    var MAX = 6;
    var demo = doc.querySelector(".hero-demo");
    (demo || phone).addEventListener("pointermove", function (ev) {
      var r = phone.getBoundingClientRect();
      if (!r.width || !r.height) return;
      var px = (ev.clientX - r.left) / r.width - 0.5;
      var py = (ev.clientY - r.top) / r.height - 0.5;
      phone.style.transform =
        "rotateY(" + (-9 + px * 2 * MAX).toFixed(2) + "deg) rotateX(" +
        (4 - py * 2 * MAX).toFixed(2) + "deg) scale(1.012)";
    }, { passive: true });

    (demo || phone).addEventListener("pointerleave", function () {
      phone.style.transform = "";
    }, { passive: true });
  }

  function boot() {
    try { initReveal(); } catch (e) {}
    try { initParallax(); } catch (e) {}
    try { initTilt(); } catch (e) {}
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
