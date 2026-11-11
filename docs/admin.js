/* ============================================================================
   TradeGuard — admin.js  (v1.0)
   «اپ ادمین» جدا از اپ کاربر:
     • تشخیص نقش فقط از روی initDataUnsafe.user.id + هش موجود در TG_CONFIG
       (نه ?admin=1 — آن قابل جعل بود)
     • برای کاربر عادی هیچ عنصری از پنل ساخته نمی‌شود (نه مخفی، نه غیرفعال: وجود ندارد)
     • تب اختصاصی 👑 با ظاهر متفاوت + وضعیت زنده اجراهای GitHub Actions
   ============================================================================ */
(function () {
  "use strict";

  var CFG = window.TG_CONFIG || {};
  var HASHES = (CFG.adminHashes || []).map(String).filter(Boolean);
  var REPO = CFG.repo || "rmanm19/tradeguard-bot";
  var BOT = String(CFG.botUsername || "TradeGuard1_bot").replace(/^@/, "");

  var T = {
    fa: {
      tab: "مدیر",
      title: "پنل مؤسس",
      sub: "این تب فقط برای حساب شما ساخته می‌شود — کاربر عادی حتی المانش را ندارد",
      runs: "وضعیت اجرای ربات (GitHub Actions)",
      loading: "در حال خواندن وضعیت…",
      runsErr: "خواندن وضعیت ناموفق بود (احتمالاً محدودیت نرخ گیت‌هاب)",
      openActions: "باز کردن GitHub Actions",
      cmds: "دستورهای مدیریتی — روی هرکدام بزنید تا کپی شود",
      shortcuts: "میان‌برها",
      openBot: "باز کردن چت ربات",
      exit: "خروج از حالت مدیر",
      copied: "کپی شد",
      success: "موفق",
      failure: "ناموفق",
      inProgress: "در حال اجرا",
      cancelled: "لغو‌شده",
      pending: "در صف",
      none: "داده‌ای نیست",
      lang: "زبان"
    },
    en: {
      tab: "Admin",
      title: "Founder Panel",
      sub: "This tab is built only for your account — normal users don't even have the element",
      runs: "Bot runs (GitHub Actions)",
      loading: "Loading status…",
      runsErr: "Could not load status (GitHub rate limit?)",
      openActions: "Open GitHub Actions",
      cmds: "Admin commands — tap to copy",
      shortcuts: "Shortcuts",
      openBot: "Open bot chat",
      exit: "Exit admin mode",
      copied: "Copied",
      success: "success",
      failure: "failed",
      inProgress: "running",
      cancelled: "cancelled",
      pending: "pending",
      none: "no data",
      lang: "Language"
    }
  };

  function lang() {
    var l = String(document.documentElement.getAttribute("lang") || "fa").slice(0, 2);
    return T[l] ? l : "en";
  }
  function t() { return T[lang()]; }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function tgApp() {
    try { return (window.Telegram && window.Telegram.WebApp) || null; } catch (e) { return null; }
  }

  function tgUser() {
    var tg = tgApp();
    try {
      if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) return tg.initDataUnsafe.user;
    } catch (e) {}
    return window.TG_USER || null;
  }

  function sha16(str) {
    if (!(window.crypto && window.crypto.subtle && window.crypto.subtle.digest)) {
      return Promise.resolve("");
    }
    try {
      var data = new TextEncoder().encode(str);
      return window.crypto.subtle.digest("SHA-256", data).then(function (buf) {
        var out = "";
        var bytes = new Uint8Array(buf);
        for (var i = 0; i < bytes.length; i++) out += ("0" + bytes[i].toString(16)).slice(-2);
        return out.slice(0, 16);
      }).catch(function () { return ""; });
    } catch (e) {
      return Promise.resolve("");
    }
  }

  function openBot(payload) {
    var url = "https://t.me/" + BOT + (payload ? "?start=" + encodeURIComponent(payload) : "");
    var tg = tgApp();
    try {
      if (tg && tg.openTelegramLink) { tg.openTelegramLink(url); return; }
    } catch (e) {}
    window.open(url, "_blank", "noopener");
  }

  function copyText(txt) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).catch(function () {});
        return;
      }
    } catch (e) {}
    try {
      var ta = document.createElement("textarea");
      ta.value = txt;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    } catch (e) {}
  }

  var flashEl = null;
  function flash(msg) {
    if (!flashEl) {
      flashEl = document.createElement("div");
      flashEl.className = "adm-flash";
      document.body.appendChild(flashEl);
    }
    flashEl.textContent = msg;
    flashEl.classList.add("show");
    clearTimeout(flashEl._t);
    flashEl._t = setTimeout(function () { flashEl.classList.remove("show"); }, 1600);
  }

  function haptic() {
    var tg = tgApp();
    try {
      if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred("light");
    } catch (e) {}
  }

  /* ---------------- تب و پنل ---------------- */
  function buildTab() {
    var nav = document.querySelector(".tabbar");
    if (!nav) return null;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tab-btn admin-tab";
    btn.dataset.tab = "admin";
    btn.innerHTML = '<span class="adm-tab-ico">👑</span><span>' + esc(t().tab) + "</span>";
    btn.addEventListener("click", function () {
      haptic();
      var all = document.querySelectorAll(".tab-btn");
      for (var i = 0; i < all.length; i++) all[i].classList.remove("is-on");
      btn.classList.add("is-on");
      var panes = document.querySelectorAll(".tab-pane");
      for (var j = 0; j < panes.length; j++) {
        panes[j].classList.toggle("is-active", panes[j].dataset.pane === "admin");
      }
      var sb = document.querySelector(".screen-body");
      if (sb) sb.scrollTop = 0;
      loadRuns();
    });
    nav.appendChild(btn);
    return btn;
  }

  var CMDS = ["/admin", "/id", "/check", "/price 300", "/seturl https://", "/setchannel @", "/broadcast ", "/grantpro "];

  function buildPane(user) {
    var body = document.querySelector(".screen-body");
    if (!body) return null;

    var sec = document.createElement("section");
    sec.className = "tab-pane admin-pane";
    sec.dataset.pane = "admin";

    var uname = user && user.username ? "@" + user.username : (user ? [user.first_name, user.last_name].filter(Boolean).join(" ") : "—");
    var cmdHtml = CMDS.map(function (c) {
      return '<button class="adm-cmd" type="button" data-cmd="' + esc(c) + '"><code>' + esc(c.trim()) + "</code></button>";
    }).join("");

    sec.innerHTML =
      '<div class="adm-banner">' +
        '<div class="adm-badge">ADMIN</div>' +
        '<div class="adm-who">👑 <b>' + esc(uname) + "</b> · <code>" + esc(user ? user.id : "—") + "</code></div>" +
        '<div class="adm-sub">' + esc(t().sub) + "</div>" +
      "</div>" +

      '<div class="card adm-card">' +
        '<div class="adm-card-h">🛰 ' + esc(t().runs) + "</div>" +
        '<div id="admRuns" class="adm-runs"><div class="adm-muted">' + esc(t().loading) + "</div></div>" +
        '<a class="adm-link" href="https://github.com/' + esc(REPO) + '/actions" target="_blank" rel="noopener">' +
          esc(t().openActions) + " ↗</a>" +
      "</div>" +

      '<div class="card adm-card">' +
        '<div class="adm-card-h">⌨️ ' + esc(t().cmds) + "</div>" +
        '<div class="adm-cmds">' + cmdHtml + "</div>" +
      "</div>" +

      '<div class="card adm-card">' +
        '<div class="adm-card-h">⚡ ' + esc(t().shortcuts) + "</div>" +
        '<div class="adm-actions">' +
          '<button class="adm-btn adm-btn-primary" type="button" id="admOpenBot">🤖 ' + esc(t().openBot) + "</button>" +
          '<button class="adm-btn" type="button" id="admExit">👤 ' + esc(t().exit) + "</button>" +
        "</div>" +
      "</div>";

    body.appendChild(sec);

    sec.querySelectorAll(".adm-cmd").forEach(function (b) {
      b.addEventListener("click", function () {
        haptic();
        copyText(b.dataset.cmd);
        flash(t().copied + ": " + b.dataset.cmd.trim());
      });
    });

    var openBtn = sec.querySelector("#admOpenBot");
    if (openBtn) openBtn.addEventListener("click", function () { haptic(); openBot("admin"); });

    var exitBtn = sec.querySelector("#admExit");
    if (exitBtn) {
      exitBtn.addEventListener("click", function () {
        haptic();
        try { sessionStorage.setItem("tg_admin_off", "1"); } catch (e) {}
        try { window.location.reload(); } catch (e) { window.location.href = window.location.href; }
      });
    }

    return sec;
  }

  /* ---------------- وضعیت زنده اجراها ---------------- */
  var cache = { ts: 0, data: null };

  function statusIcon(run) {
    if (run.status === "in_progress") return { cls: "st-run", label: t().inProgress };
    if (run.status === "queued" || run.status === "pending") return { cls: "st-wait", label: t().pending };
    if (run.conclusion === "success") return { cls: "st-ok", label: t().success };
    if (run.conclusion === "cancelled") return { cls: "st-muted", label: t().cancelled };
    if (run.conclusion) return { cls: "st-bad", label: t().failure };
    return { cls: "st-muted", label: run.status || "—" };
  }

  function ago(iso) {
    var then = Date.parse(iso || "");
    if (!then) return "";
    var mins = Math.max(0, Math.round((Date.now() - then) / 60000));
    if (mins < 1) return lang() === "fa" ? "همین حالا" : "just now";
    if (mins < 60) return (lang() === "fa" ? mins + " دقیقه پیش" : mins + "m ago");
    var h = Math.round(mins / 60);
    if (h < 24) return (lang() === "fa" ? h + " ساعت پیش" : h + "h ago");
    var d = Math.round(h / 24);
    return (lang() === "fa" ? d + " روز پیش" : d + "d ago");
  }

  function renderRuns(data) {
    var box = document.getElementById("admRuns");
    if (!box) return;
    var runs = (data && data.workflow_runs) || [];
    if (!runs.length) {
      box.innerHTML = '<div class="adm-muted">' + esc(t().none) + "</div>";
      return;
    }
    box.innerHTML = runs.map(function (r) {
      var s = statusIcon(r);
      return (
        '<div class="adm-run">' +
          '<span class="adm-dot ' + s.cls + '"></span>' +
          '<div class="adm-run-t">' + esc(r.name || "workflow") + "</div>" +
          '<div class="adm-run-m">' + esc(s.label) + " · " + esc(ago(r.created_at)) + "</div>" +
          '<a class="adm-run-a" href="' + esc(r.html_url) + '" target="_blank" rel="noopener">↗</a>' +
        "</div>"
      );
    }).join("");
  }

  function loadRuns() {
    var box = document.getElementById("admRuns");
    if (!box) return;
    if (cache.data && Date.now() - cache.ts < 60000) { renderRuns(cache.data); return; }
    if (typeof fetch !== "function") {
      box.innerHTML = '<div class="adm-err">' + esc(t().runsErr) + "</div>";
      return;
    }
    fetch("https://api.github.com/repos/" + REPO + "/actions/runs?per_page=5", {
      headers: { Accept: "application/vnd.github+json" },
      cache: "no-store"
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (d) {
        cache = { ts: Date.now(), data: d };
        renderRuns(d);
      })
      .catch(function () {
        box.innerHTML = '<div class="adm-err">' + esc(t().runsErr) + "</div>";
      });
  }

  /* ---------------- boot ---------------- */
  function init() {
    if (!HASHES.length) {
      // پنل تنظیم نشده: هیچ چیزی ساخته نمی‌شود (کاربر عادی هم همین را می‌بیند)
      return;
    }
    try {
      if (sessionStorage.getItem("tg_admin_off") === "1") return;
    } catch (e) {}

    var user = tgUser();
    if (!user || !user.id) return; // بیرون از تلگرام: نقش ادمین معنا ندارد

    sha16("tg-admin:" + user.id).then(function (h) {
      if (!h || HASHES.indexOf(h) === -1) return; // کاربر عادی → خروج، بدون هیچ DOM
      document.body.setAttribute("data-role", "admin");
      buildTab();
      buildPane(user);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
