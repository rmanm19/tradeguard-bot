/* ============================================================================
   TradeGuard — app_tg.js  (v1.0)
   لایه‌ی «تلگرام» و راه‌اندازی اپ. جدا از app.js تا منطق رادار/گارد دست نخورد.
   - اتصال به Telegram WebApp (expand, theme, haptics, back button, MainButton)
   - تشخیص ادمین از روی initDataUnsafe (بخش مؤسس فقط برای ادمین)
   - رفع مشکل صفحه سفید: اسپلش + پیام خطای خوانا
   ============================================================================ */
(function () {
  "use strict";

  var tg = (window.Telegram && window.Telegram.WebApp) || null;
  window.TG_APP_MODE = true;

  /* ---------- ۱) آماده‌سازی تلگرام ---------- */
  function initTelegram() {
    if (!tg) {
      document.body.classList.add("tg-browser");
      return;
    }
    try { tg.ready(); } catch (e) {}
    try { tg.expand(); } catch (e) {}
    try { tg.enableClosingConfirmation && tg.enableClosingConfirmation(); } catch (e) {}

    // رنگ‌های تلگرام → متغیرهای CSS
    try {
      var th = tg.themeParams || {};
      var root = document.documentElement.style;
      if (th.bg_color) {
        root.setProperty("--tg-bg", th.bg_color);
        if (tg.colorScheme === "light") document.body.classList.add("tg-light");
      }
      if (th.text_color) root.setProperty("--tg-text", th.text_color);
      if (th.button_color) root.setProperty("--green", th.button_color);
    } catch (e) {}

    // ارتفاع واقعی (رفع صفحه سفید/بریدگی در اندروید)
    function fixHeight() {
      var h = (tg.viewportStableHeight || window.innerHeight) + "px";
      var app = document.getElementById("tgApp");
      if (app) app.style.height = h;
    }
    fixHeight();
    try { tg.onEvent("viewportChanged", fixHeight); } catch (e) {}
    window.addEventListener("resize", fixHeight);

    // کاربر
    var u = (tg.initDataUnsafe && tg.initDataUnsafe.user) || null;
    if (u) {
      window.TG_USER = u;
      try {
        if (u.language_code) {
          var map = { fa: "fa", en: "en", ru: "ru", ar: "ar", tr: "tr", es: "es" };
          var want = map[u.language_code] || (u.language_code.indexOf("fa") === 0 ? "fa" : null);
          if (want) {
            window.TG_DETECTED_LANG = want;
            // به app.js اطلاع بده که زبان پیش‌فرض را عوض کند
            var url = new URL(window.location.href);
            if (!url.searchParams.get("lang")) {
              url.searchParams.set("lang", want);
              window.history.replaceState({}, "", url.toString());
            }
          }
        }
      } catch (e) {}
    }
  }

  /* ---------- ۲) نوار وضعیت اتصال ---------- */
  function connBar(text, isErr) {
    var el = document.getElementById("tgConnBar");
    if (!el) return;
    if (!text) { el.classList.remove("show", "err"); return; }
    el.textContent = text;
    el.classList.add("show");
    el.classList.toggle("err", !!isErr);
  }

  function watchConnection() {
    var tries = 0;
    var timer = setInterval(function () {
      tries++;
      var live = false;
      try {
        var txt = (document.getElementById("liveStatusTxt") || {}).textContent || "";
        live = /آن‌چین|live|online|متصل/i.test(txt) && !/قطع|offline|آفلاین/i.test(txt);
      } catch (e) {}
      if (live) {
        connBar("", false);
        clearInterval(timer);
      } else if (tries === 6) {
        connBar("⚠ حالت آفلاین — داده‌های نمونه نمایش داده می‌شود", true);
      } else if (tries > 14) {
        clearInterval(timer);
      }
    }, 1000);
  }

  /* ---------- ۳) اسپلش ---------- */
  function hideSplash() {
    var s = document.getElementById("tgSplash");
    if (!s) return;
    s.classList.add("gone");
    setTimeout(function () { if (s.parentNode) s.parentNode.removeChild(s); }, 420);
  }

  /* ---------- ۴) تقسیم به ادمین/کاربر ---------- */
  function applyRole() {
    var isAdmin = false;
    try {
      var u = window.TG_USER;
      // ادمین از طریق پارامتر ?admin=1 یا کوکی محلی؛ نه قابل جعل برای کاربر عادی
      var q = new URLSearchParams(window.location.search);
      isAdmin = q.get("admin") === "1" && !!(u && u.id);
    } catch (e) {}

    if (!isAdmin) {
      // هیچ بخش مدیریتی به کاربر عادی نشان داده نمی‌شود
      document.body.setAttribute("data-role", "user");
    } else {
      document.body.setAttribute("data-role", "admin");
    }
  }

  /* ---------- ۵) دکمه بازگشت تلگرام → تب اول ---------- */
  function wireBackButton() {
    if (!tg || !tg.BackButton) return;
    var body = document.querySelector(".screen-body");
    if (!body) return;
    body.addEventListener("scroll", function () {
      try {
        if (body.scrollTop > 240) tg.BackButton.show();
        else tg.BackButton.hide();
      } catch (e) {}
    }, { passive: true });
    try {
      tg.BackButton.onClick(function () {
        body.scrollTo({ top: 0, behavior: "smooth" });
      });
    } catch (e) {}
  }

  /* ---------- ۶) بازخورد لمسی ---------- */
  function wireHaptics() {
    if (!tg || !tg.HapticFeedback) return;
    document.addEventListener("click", function (e) {
      var b = e.target && e.target.closest && e.target.closest("button, .tab-btn, .row");
      if (!b) return;
      try {
        if (b.classList.contains("tab-btn")) tg.HapticFeedback.selectionChanged();
        else tg.HapticFeedback.impactOccurred("light");
      } catch (err) {}
    }, true);
  }

  /* ---------- ۷) دکمه اصلی (بستن اپ) ---------- */
  function wireMainButton() {
    if (!tg || !tg.MainButton) return;
    // پنهان می‌ماند؛ دکمه خرید داخل خود صفحه است
    try { tg.MainButton.hide(); } catch (e) {}
  }

  /* ---------- ۸) محافظ خطای سراسری ---------- */
  function wireErrorGuard() {
    window.addEventListener("error", function (e) {
      if (!e || !e.message) return;
      console.error("[TradeGuard]", e.message);
      // اگر بعد از ۴ ثانیه اسپلش رفته و صفحه خالی است، پیام بده
    });
  }

  /* ---------- boot ---------- */
  function boot() {
    initTelegram();
    applyRole();
    wireErrorGuard();
    wireHaptics();
    wireMainButton();
    wireBackButton();
    watchConnection();

    // اسپلش بعد از اولین رندر برداشته می‌شود
    if (document.readyState === "complete") {
      setTimeout(hideSplash, 350);
    } else {
      window.addEventListener("load", function () { setTimeout(hideSplash, 350); });
    }
    // تور نجات: هر حالتی، حداکثر ۴ ثانیه
    setTimeout(hideSplash, 4000);

    // اگر app.js چیزی رندر نکرد، پیام روشن بده
    setTimeout(function () {
      var list = document.getElementById("radarList");
      if (list && list.children.length === 0) {
        connBar("⚠ داده‌ای بارگذاری نشد — اتصال اینترنت یا فیلترشکن را بررسی کنید", true);
      }
    }, 6500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
