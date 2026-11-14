/* ============ TradeGuard v4.0 Global — Multilingual Live Mini-App Engine ============ */
(function () {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const DICTS = window.TG_I18N || {};
  const SUPPORTED_LANGS = ["fa", "en", "ru", "ar", "tr", "es"];

  // اتصال خودکار به Telegram WebApp SDK
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try {
      tg.ready();
      tg.expand();
    } catch (_) {}
  }
  function haptic(type = "light") {
    try {
      if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(type);
    } catch (_) {}
  }

  /* ---------- Language Detection & Helper ---------- */
  function detectInitialLang() {
    try {
      const q = new URLSearchParams(window.location.search).get("lang");
      if (q && SUPPORTED_LANGS.includes(q.toLowerCase())) return q.toLowerCase();
      const saved = localStorage.getItem("tg_lang");
      if (saved && SUPPORTED_LANGS.includes(saved)) return saved;
      const tgCode = tg?.initDataUnsafe?.user?.language_code?.slice(0, 2)?.toLowerCase();
      if (tgCode && SUPPORTED_LANGS.includes(tgCode)) return tgCode;
    } catch (_) {}
    return "fa";
  }

  let currentLang = detectInitialLang();
  const t = () => DICTS[currentLang] || DICTS.fa;

  const fmt = (v, min = 0, max = min) =>
    Number(v).toLocaleString(t().digits || "en-US", {
      minimumFractionDigits: min,
      maximumFractionDigits: max,
    });

  const tpl = (str, vars) =>
    String(str || "").replace(/\{(\w+)\}/g, (_, k) => (vars[k] !== undefined ? vars[k] : ""));

  /* ---------- Toasts ---------- */
  const pageToast = $("#pageToast");
  let pageToastT;
  function toast(msg) {
    if (!pageToast) return;
    pageToast.textContent = msg;
    pageToast.classList.remove("hidden");
    clearTimeout(pageToastT);
    pageToastT = setTimeout(() => pageToast.classList.add("hidden"), 2800);
  }

  const appToastEl = $("#appToast");
  let appToastT;
  /* باز کردن چت ربات — تنها مسیر واقعی پرداخت/فعال‌سازی اشتراک */
  function openBotChat(startParam) {
    var bot = String((window.TG_CONFIG || {}).botUsername || "TradeGuard1_bot").replace(/^@/, "");
    var url = "https://t.me/" + bot + (startParam ? "?start=" + encodeURIComponent(startParam) : "");
    try {
      var tg = window.Telegram && window.Telegram.WebApp;
      if (tg && tg.openTelegramLink) { tg.openTelegramLink(url); return; }
    } catch (e) {}
    window.open(url, "_blank", "noopener");
  }

  function appToast(msg) {
    if (!appToastEl) return;
    appToastEl.textContent = msg;
    appToastEl.classList.remove("hidden");
    clearTimeout(appToastT);
    appToastT = setTimeout(() => appToastEl.classList.add("hidden"), 3100);
  }

  /* ---------- State ---------- */
  let radarMode = "extremes";
  let arbCapital = 500;
  let isPro = false;
  let guardOn = false;
  let balance = 10000;
  let inviteCount = 0;
  let liveBtcPrice = 80330;
  let lastCalc = { cap: 500, perTrade: 50, lots: 0.1, maxTrades: 10, dd: 5, risk: 0.5 };
  const PRO_UNLOCK_INDEX = 4;
  const TODAY_USED = 0.33;

  let whalesList = [
    { address: "0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00", short_addr: "0xecb6…2b00", equity_m: 114.3, coin: "BTC", side: "SHORT", val_m: 21.87, entry: 77637.9, upnl: -114913, liq: 235712.0, lev: 5 },
    { address: "0xf5d81a1383c5968a51f079b80d1aa8b1462bc019", short_addr: "0xf5d8…c019", equity_m: 87.5, coin: "ETH", side: "LONG", val_m: 8.42, entry: 2790.5, upnl: 142600, liq: 1820.0, lev: 6 },
    { address: "0x393d0b87ed38fc779fd9611144ae649ba6082109", short_addr: "0x393d…2109", equity_m: 42.1, coin: "SOL", side: "LONG", val_m: 5.18, entry: 172.4, upnl: 89400, liq: 118.5, lev: 10 },
    { address: "0xe6111266afdcdf0b1fe8505028cc1f7419d798a7", short_addr: "0xe611…98a7", equity_m: 29.8, coin: "HYPE", side: "SHORT", val_m: 3.64, entry: 24.8, upnl: 41200, liq: 48.2, lev: 4 },
  ];

  let marketState = {
    live: false,
    total_markets: 235,
    btc_price: 80330,
    session_key: "ny",
    top_whale: { sym: "BTC", oi_m: 3420.0, price: 80330 },
    top_mover: { sym: "SUI", chg_24h: 6.4, vol_m: 412.0 },
    best_opp: {
      sym: "SUI",
      rate_8h: 0.245,
      apr: 268.3,
      daily_500: 3.68,
      oi_m: 184.2,
      direction: "short",
    },
    top_extremes: [
      { sym: "SUI", price: 3.42, rate_8h: 0.245, apr: 268.3, daily_500: 3.68, oi_m: 184.2, chg_24h: 6.4, direction: "short" },
      { sym: "BLUR", price: 0.18, rate_8h: -0.32, apr: 350.4, daily_500: 4.8, oi_m: 14.5, chg_24h: -3.4, direction: "squeeze" },
      { sym: "PEPE", price: 0.000012, rate_8h: 0.168, apr: 183.9, daily_500: 2.52, oi_m: 135.8, chg_24h: 8.1, direction: "short" },
      { sym: "DOGE", price: 0.19, rate_8h: 0.085, apr: 93.1, daily_500: 1.28, oi_m: 420.0, chg_24h: 2.3, direction: "short" },
      { sym: "SOL", price: 178.4, rate_8h: 0.042, apr: 46.0, daily_500: 0.63, oi_m: 890.0, chg_24h: 1.9, direction: "short" },
      { sym: "XMR", price: 599.9, rate_8h: 0.035, apr: 38.3, daily_500: 0.52, oi_m: 124.1, chg_24h: 0.4, direction: "short" },
    ],
    majors: [
      { sym: "BTC", price: 80330, rate_8h: 0.012, apr: 13.1, daily_500: 0.18, oi_m: 3420, chg_24h: 0.5, direction: "neutral" },
      { sym: "ETH", price: 2840, rate_8h: 0.018, apr: 19.7, daily_500: 0.27, oi_m: 1950, chg_24h: 0.8, direction: "neutral" },
      { sym: "SOL", price: 178.4, rate_8h: 0.042, apr: 46.0, daily_500: 0.63, oi_m: 890, chg_24h: 1.9, direction: "short" },
      { sym: "DOGE", price: 0.19, rate_8h: 0.085, apr: 93.1, daily_500: 1.28, oi_m: 420, chg_24h: 2.3, direction: "short" },
      { sym: "SUI", price: 3.42, rate_8h: 0.245, apr: 268.3, daily_500: 3.68, oi_m: 184, chg_24h: 6.4, direction: "short" },
      { sym: "XRP", price: 2.18, rate_8h: 0.022, apr: 24.1, daily_500: 0.33, oi_m: 510, chg_24h: 1.1, direction: "neutral" },
    ],
  };

  /* =======================================================
     1) RADAR & ALERTS (Multilingual + Live On-Chain)
  ======================================================= */
  function strategyLabel(dir) {
    const d = t();
    if (dir === "short") return d.stratShort;
    if (dir === "squeeze") return d.stratSqueeze;
    return d.stratNeutral;
  }

  function magnetLabel(dir) {
    const d = t();
    if (dir === "short") return d.magShort;
    if (dir === "squeeze") return d.magSqueeze;
    return d.magNeutral;
  }

  function tagFor(item) {
    const d = t();
    if (item.direction === "short") return `<span class="tag tag-short">${d.tagShort}</span>`;
    if (item.direction === "squeeze") return `<span class="tag tag-squeeze">${d.tagSqueeze}</span>`;
    return `<span class="tag tag-neutral">${d.tagNeutral}</span>`;
  }

  function sparkFromSeed(sym, rate, chg) {
    const w = 58, h = 22;
    let seed = 0;
    for (let i = 0; i < sym.length; i++) seed += sym.charCodeAt(i) * (i + 3);
    const pts = [];
    for (let i = 0; i < 10; i++) {
      pts.push(Math.sin(seed + i * 0.85) * 4 + (chg >= 0 ? i * 0.7 : -i * 0.7));
    }
    const max = Math.max(...pts), min = Math.min(...pts), span = max - min || 1;
    const coords = pts.map((v, i) => {
      const x = (i / (pts.length - 1)) * w;
      const y = h - 3 - ((v - min) / span) * (h - 6);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const color = Math.abs(rate) >= 0.025 ? (rate > 0 ? "#25D69A" : "#FFC94D") : "#5E7397";
    return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">
      <polyline points="${coords.join(" ")}" fill="none" stroke="${color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
  }

  /* ── نقشهٔ لیکوئیدیشن (تخمینی) ───────────────────────────────────────
     فاصله تا لیکوئید هر پوزیشن ≈ ۱ ÷ اهرم (منهای کارمزد نگهداری).
     این یک «تخمین از روی OI و اهرم رایج» است، نه دفتر سفارش صرافی —
     هیچ ادعای دقیق‌بودن میلی‌متری دربارهٔ دادهٔ خصوصی صرافی نمی‌کنیم. */
  const LIQ_LEVS = [10, 25, 50];
  const LIQ_MMR = 0.005;

  function liqPrice(price, lev, side) {
    const p = Number(price) || 0;
    if (!(p > 0) || !(lev > 0)) return 0;
    const keep = 1 / lev - LIQ_MMR;
    return side === "long" ? Math.max(0, p * (1 - keep)) : p * (1 + keep);
  }

  function liqShortNum(v) {
    const n = Number(v) || 0;
    if (n >= 1000) return "$" + (n / 1000).toFixed(1) + "k";
    if (n >= 100) return "$" + n.toFixed(0);
    if (n >= 1) return "$" + n.toFixed(2);
    return "$" + n.toFixed(6);
  }

  function liqCandidates() {
    const src = (marketState.top_extremes || []).concat(marketState.majors || []);
    const seen = Object.create(null);
    const out = [];
    src.forEach((c) => {
      if (!c || !c.sym || seen[c.sym]) return;
      if (!(Number(c.price) > 0)) return;
      if (!(Number(c.oi_m) > 0)) return;
      seen[c.sym] = 1;
      out.push(c);
    });
    out.sort((a, b) => b.oi_m - a.oi_m);
    return out.slice(0, 5);
  }

  /* ── فاندینگ چند صرافی: یک نگاه به آربیتراژ فاندینگ ────────────────
     هر عدد از API عمومی همان صرافی می‌آید؛ اگر صرافی جواب ندهد
     «—» می‌ماند. اختلاف = بالاترین منهای پایین‌ترین فاندینگ. */
  let fxMatrix = null;
  let fxFetchedAt = 0;

  function fxRateCell(v) {
    if (v === null || v === undefined || !isFinite(Number(v))) return '<span class="fx-rate na">—</span>';
    const n = Number(v);
    const cls = n > 0 ? "pos" : n < 0 ? "neg" : "";
    const sign = n > 0 ? "+" : "";
    return '<span class="fx-rate ' + cls + '">' + sign + n.toFixed(3) + "</span>";
  }

  function renderFundingMatrix() {
    const box = $("#fxBox");
    const rows = $("#fxRows");
    if (!box || !rows) return;
    const d = t();
    const data = fxMatrix;
    const list = (data && data.rows) || [];
    if (!list.length) {
      box.classList.add("hidden");
      rows.innerHTML = "";
      return;
    }
    box.classList.remove("hidden");
    rows.innerHTML = list
      .map((r) => {
        const hot = Number(r.carry_apr) >= 20;
        return (
          '<div class="fx-row" data-sym="' + r.sym + '">' +
          "<b>$" + r.sym + "</b>" +
          fxRateCell(r.rates.hyperliquid) +
          fxRateCell(r.rates.okx) +
          fxRateCell(r.rates.binance) +
          '<span class="fx-spread ' + (hot ? "hot" : "cold") + '" title="' + (d.fxApr || "") + '">' +
          (Number(r.carry_apr) >= 0 ? "+" : "") + Number(r.carry_apr).toFixed(0) + "%</span>" +
          "</div>"
        );
      })
      .join("");
  }

  function loadFundingMatrix(force) {
    const fresh = fxMatrix && Date.now() - fxFetchedAt < 60000;
    if (fresh && !force) {
      renderFundingMatrix();
      return Promise.resolve(fxMatrix);
    }
    return fetch("/api/funding-matrix")
      .then((r) => (r && r.ok ? r.json() : null))
      .then((data) => {
        fxMatrix = data && data.rows && data.rows.length ? data : null;
        fxFetchedAt = Date.now();
        renderFundingMatrix();
        return fxMatrix;
      })
      .catch(() => {
        renderFundingMatrix();
        return null;
      });
  }

  function renderLiquidationMap() {
    const box = $("#liqMap");
    const rows = $("#liqRows");
    if (!box || !rows) return;
    const d = t();
    const title = $("#liqTitle");
    const note = $("#liqNote");
    if (title && d.liqTitle) title.textContent = d.liqTitle;
    if (note && d.liqNote) note.textContent = d.liqNote;

    const coins = liqCandidates();
    if (!coins.length) {
      box.classList.add("hidden");
      rows.innerHTML = "";
      return;
    }
    box.classList.remove("hidden");

    rows.innerHTML = coins
      .map((c) => {
        const price = Number(c.price) || 0;
        const longSide = (c.rate_8h || 0) >= 0;
        const crowded = longSide ? d.liqCrowdedLong || "" : d.liqCrowdedShort || "";
        const sideClass = longSide ? "is-long" : "is-short";
        const levels = LIQ_LEVS.map((lev) => {
          const lp = liqPrice(price, lev, "long");
          const sp = liqPrice(price, lev, "short");
          return (
            `<span class="liq-cell"><b>${lev}×</b>` +
            `<span class="liq-px liq-px-long">${liqShortNum(lp)}</span>` +
            `<span class="liq-px liq-px-short">${liqShortNum(sp)}</span></span>`
          );
        }).join("");
        return (
          `<div class="liq-card" data-sym="${c.sym}">` +
          `<div class="liq-top"><b>$${c.sym}</b>` +
          `<span class="liq-spot">$${Number(price).toLocaleString("en-US")}</span>` +
          `<span class="liq-oi">OI $${fmt(c.oi_m, 1, 1)}M</span>` +
          `<span class="liq-crowd ${sideClass}">${crowded}</span></div>` +
          `<div class="liq-grid"><span class="liq-grid-head">${d.liqLong || ""}</span>` +
          `<span class="liq-grid-head liq-grid-head-short">${d.liqShort || ""}</span></div>` +
          `<div class="liq-cells">${levels}</div></div>`
        );
      })
      .join("");
  }

  function renderRadar() {
    const radarList = $("#radarList");
    if (!radarList) return;
    const d = t();
    const xrayBox = $("#whaleXrayBox");
    if (xrayBox) xrayBox.classList.toggle("hidden", radarMode !== "whales");

    if (radarMode === "whales") {
      const liqBox = $("#liqMap");
      if (liqBox) liqBox.classList.add("hidden");
      radarList.innerHTML = "";
      whalesList.forEach((w) => {
        const card = document.createElement("div");
        card.className = "whale-card";
        const sideTag =
          w.side === "LONG"
            ? `<span class="tag tag-long">LONG ${w.lev}x</span>`
            : `<span class="tag tag-short">SHORT ${w.lev}x</span>`;
        const pnlCls = w.upnl >= 0 ? "pnl-pos" : "pnl-neg";
        const pnlSign = w.upnl >= 0 ? "+$" : "-$";
        const liqTxt = w.liq ? `$${Number(w.liq).toLocaleString("en-US")}` : "Cross";
        card.innerHTML = `
          <div class="wc-top">
            <div class="wc-coin">🐋 <b>$${w.coin}</b> · $${fmt(w.val_m, 2, 2)}M ${sideTag}</div>
            <span class="wc-addr">${w.short_addr}</span>
          </div>
          <div class="wc-bot">
            <span>${d.wcEntry}: <b>$${Number(w.entry).toLocaleString("en-US")}</b></span>
            <span>${d.wcLiq}: <b>${liqTxt}</b></span>
            <span class="${pnlCls}">${pnlSign}${Math.abs(Math.round(w.upnl)).toLocaleString("en-US")}</span>
          </div>`;
        card.addEventListener("click", () => {
          haptic("light");
          const inp = $("#wxInput");
          if (inp) {
            inp.value = w.address;
            inspectWallet(w.address);
          }
        });
        radarList.appendChild(card);
      });
      renderOppCard();
      return;
    }

    const fullList = radarMode === "extremes" ? marketState.top_extremes : marketState.majors;
    const favs = loadFavs();
    let list = fullList;
    if (favOnly) {
      list = fullList.filter((c) => favs.includes(c.sym));
      if (!list.length) {
        radarList.innerHTML = `<div class="fav-empty">${d.favEmpty}</div>`;
        renderOppCard();
        return;
      }
    }
    radarList.innerHTML = "";

    list.forEach((c, i) => {
      const locked = !isPro && i >= PRO_UNLOCK_INDEX;
      const row = document.createElement("div");
      row.className = "row" + (locked ? " locked" : "");
      const sign = c.rate_8h > 0 ? "+" : "";
      const rateClass = Math.abs(c.rate_8h) >= 0.02 ? "up" : "";
      const subInfo = c.oi_m ? `OI $${fmt(c.oi_m, 1, 1)}M` : `$${c.price}`;

      const faved = favs.includes(c.sym);
      row.innerHTML = `
        <div class="row-sym"><b>$${c.sym}</b><small>${subInfo}</small></div>
        <div class="row-rate ${rateClass}">
          <b>${sign}${fmt(c.rate_8h, 2, 3)}%</b><small>${fmt(c.apr, 0, 0)}% ${d.aprLabel}</small>
        </div>
        <div>${sparkFromSeed(c.sym, c.rate_8h, c.chg_24h || 0)}</div>
        <div class="row-tag">${tagFor(c)}</div>
        <button class="fav-btn${faved ? " is-on" : ""}" data-sym="${c.sym}" aria-label="watchlist">${faved ? "★" : "☆"}</button>`;
      const favBtn = row.querySelector(".fav-btn");
      if (favBtn) {
        favBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          haptic("light");
          const added = toggleFav(c.sym);
          favBtn.textContent = added ? "★" : "☆";
          favBtn.classList.toggle("is-on", added);
          appToast(added ? tpl(d.toastFavAdded, { s: c.sym }) : tpl(d.toastFavRemoved, { s: c.sym }));
          if (favOnly) renderRadar();
        });
      }
      radarList.appendChild(row);
    });

    if (!isPro && list.length > PRO_UNLOCK_INDEX) {
      const ov = document.createElement("div");
      ov.className = "lock-overlay";
      ov.innerHTML = `<span>${tpl(d.lockMoreTpl, { n: fmt(list.length - PRO_UNLOCK_INDEX) })}</span>`;
      radarList.style.position = "relative";
      ov.addEventListener("click", () => goToTab("sub"));
      radarList.appendChild(ov);
      requestAnimationFrame(() => {
        const rows = $$(".row", radarList);
        const lockedRows = rows.filter((r) => r.classList.contains("locked"));
        if (lockedRows.length) {
          const first = lockedRows[0];
          const top = first.offsetTop;
          const bottom = rows[rows.length - 1].offsetTop + rows[rows.length - 1].offsetHeight;
          ov.style.top = top + "px";
          ov.style.height = bottom - top + "px";
        }
      });
    }

    renderLiquidationMap();
    renderOppCard();
    loadFundingMatrix();
  }

  function renderOppCard() {
    const b = marketState.best_opp;
    if (!b) return;
    const d = t();
    liveBtcPrice = marketState.btc_price || liveBtcPrice;
    const btcBadge = $("#btcLiveBadge");
    if (btcBadge) btcBadge.textContent = `BTC $${Number(liveBtcPrice).toLocaleString("en-US")}`;
    const fngBadge = $("#fngLiveBadge");
    if (fngBadge && marketState.fng_val) {
      fngBadge.textContent = `F&G: ${marketState.fng_val}`;
    }

    $("#oppSym").textContent = "$" + b.sym;
    const tagEl = $("#oppTag");
    if (tagEl) {
      tagEl.textContent = b.direction === "squeeze" ? d.tagSqueeze : d.tagShort;
      tagEl.className = "tag " + (b.direction === "squeeze" ? "tag-squeeze" : "tag-short");
    }

    const sign = b.rate_8h > 0 ? "+" : "";
    const rateEl = $("#oppRate");
    if (rateEl) rateEl.textContent = sign + fmt(b.rate_8h, 2, 3) + "%";
    const aprEl = $("#oppApr");
    if (aprEl) aprEl.textContent = fmt(b.apr || Math.abs(b.rate_8h) * 1095, 0, 0) + "%";

    const dailyOnCap = (Math.abs(b.rate_8h) / 100) * 3 * arbCapital;
    const monthlyOnCap = Math.round(dailyOnCap * 30);
    $("#oppEarn").textContent = fmt(dailyOnCap, 1, 2);
    const unitEl = $("#oppUnitEl");
    if (unitEl && d.oppUnitCap) {
      unitEl.textContent = tpl(d.oppUnitCap, { mo: fmt(monthlyOnCap) });
    }

    const foot = $("#oppFoot");
    if (foot) {
      const baseFoot = tpl(d.oppFootTpl, {
        strat: strategyLabel(b.direction),
        mag: magnetLabel(b.direction),
      });
      const spreadTxt =
        b.spread_vs_okx !== undefined
          ? tpl(d.oppSpreadTpl, { sp: fmt(b.spread_vs_okx, 2, 3) })
          : "";
      foot.innerHTML = baseFoot + spreadTxt;
    }

    const st = $("#liveStatusTxt");
    if (st) {
      st.textContent = marketState.live
        ? tpl(d.liveMarketsCount, { n: fmt(marketState.total_markets) })
        : d.liveConnecting;
    }
    const cap = $("#demoLiveCaption");
    if (cap) {
      cap.textContent = tpl(d.demoCaptionTpl, {
        n: fmt(marketState.total_markets),
        btc: Number(liveBtcPrice).toLocaleString("en-US"),
      });
    }
  }

  function renderLocalizedAlerts() {
    const feed = $("#alertsFeed");
    if (!feed) return;
    const d = t();
    const w = marketState.top_whale || { sym: "BTC", oi_m: 3420, price: liveBtcPrice };
    const ex = (marketState.top_extremes && marketState.top_extremes[0]) || marketState.best_opp;
    const mv = marketState.top_mover || { sym: "SUI", chg_24h: 6.4, vol_m: 412 };
    const sessMap = { london: d.alSessLondon, ny: d.alSessNy, quiet: d.alSessQuiet };

    const items = [
      {
        icon: "🐋",
        type: "whale",
        locked: false,
        title: tpl(d.alWhaleTitle, {
          sym: w.sym,
          oi: Number(w.oi_m).toFixed(1),
          px: Number(w.price).toLocaleString("en-US"),
        }),
        meta: d.alWhaleMeta,
      },
      {
        icon: "🧲",
        type: "fund",
        locked: false,
        title: tpl(d.alFundTitle, {
          sym: ex.sym,
          rate: (ex.rate_8h > 0 ? "+" : "") + Number(ex.rate_8h).toFixed(3),
          mag: magnetLabel(ex.direction),
          apr: Math.round(ex.apr || 120),
        }),
        meta: d.alFundMeta,
      },
      {
        icon: "⚡",
        type: "news",
        locked: false,
        title: tpl(d.alMoveTitle, {
          sym: mv.sym,
          chg: (mv.chg_24h > 0 ? "+" : "") + Number(mv.chg_24h).toFixed(1),
          vol: Number(mv.vol_m).toFixed(1),
        }),
        meta: sessMap[marketState.session_key] || d.alSessQuiet,
      },
      {
        icon: "🛡️",
        type: "guard",
        locked: false,
        title: d.alGuardTitle,
        meta: d.alGuardMeta,
      },
      {
        icon: "💸",
        type: "payout",
        locked: true,
        title: d.alPayoutTitle,
        meta: d.alPayoutMeta,
      },
    ];

    feed.innerHTML = "";
    items.forEach((a) => {
      const locked = a.locked && !isPro;
      const div = document.createElement("div");
      div.className = "feed-item" + (locked ? " locked-item" : "");
      if (a.locked) div.id = "lockedAlert";
      div.innerHTML = `
        <span class="fi-icon ${a.type}">${a.icon}</span>
        <div class="fi-body">
          <div class="fi-title">${a.title}</div>
          <div class="fi-meta">${a.meta}</div>
        </div>
        ${locked ? '<span class="lock-badge">🔒</span>' : ""}`;
      feed.appendChild(div);
    });
  }

  async function fetchLiveMarket() {
    try {
      const resp = await fetch("/api/live-radar", { cache: "no-store" });
      if (!resp.ok) return;
      const data = await resp.json();
      if (data && Array.isArray(data.top_extremes) && data.top_extremes.length) {
        marketState = data;
        renderRadar();
        renderLocalizedAlerts();
        // کش برای رندر آنی در اجرای بعدی (اپ باید فوری باز شود، حتی قبل از شبکه)
        try {
          localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data }));
        } catch (e) {}
      }
    } catch (_) {}
  }

  /* رندر فوری از آخرین دادهٔ ذخیره‌شده (حداکثر ۶ ساعت عمر) */
  function hydrateMarketCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (!parsed || !parsed.data || Date.now() - Number(parsed.ts || 0) > 6 * 3600 * 1000) return;
      if (!Array.isArray(parsed.data.top_extremes) || !parsed.data.top_extremes.length) return;
      marketState = parsed.data;
      const live = $("#liveStatusTxt");
      if (live) live.textContent = t().cachedData;
      renderRadar();
      renderLocalizedAlerts();
    } catch (e) {}
  }

  let whaleLongPct = 38;
  let whaleShortPct = 62;

  async function fetchLiveWhales() {
    try {
      const resp = await fetch("/api/live-whales", { cache: "no-store" });
      if (!resp.ok) return;
      const data = await resp.json();
      if (data && Array.isArray(data.whales) && data.whales.length) {
        whalesList = data.whales;
        if (typeof data.long_pct === "number") {
          whaleLongPct = data.long_pct;
          whaleShortPct = data.short_pct;
        }
        const lEl = $("#wdLongPct"), sEl = $("#wdShortPct"), fEl = $("#wdFill");
        if (lEl) lEl.textContent = `${whaleLongPct}%`;
        if (sEl) sEl.textContent = `${whaleShortPct}%`;
        if (fEl) fEl.style.width = `${whaleLongPct}%`;
        if (radarMode === "whales") renderRadar();
      }
    } catch (_) {}
  }

  /* ---------- Live In-App AI Market Copilot ---------- */
  function renderAiBrief() {
    const out = $("#aicOut");
    if (!out) return;
    const d = t();
    const b = marketState.best_opp || { sym: "SUI", rate_8h: 0.245, daily_500: 3.68 };
    out.classList.remove("hidden");
    out.innerHTML = tpl(d.aicBriefTpl, {
      sym: b.sym,
      rate: (b.rate_8h > 0 ? "+" : "") + Number(b.rate_8h).toFixed(3),
      d500: Number(b.daily_500 || 3.5).toFixed(2),
      lPct: whaleLongPct,
      sPct: whaleShortPct,
    });
  }

  $("#aicRunBtn")?.addEventListener("click", () => {
    haptic("medium");
    fetchLiveWhales();
    renderAiBrief();
  });

  /* ---------- GMGN-Style Token Anti-Rug & Honeypot Scanner ---------- */
  async function scanToken(rawQ) {
    const out = $("#rugOut");
    if (!out) return;
    const d = t();
    const q = (rawQ || "").trim() || "PEPE";
    out.classList.remove("hidden");
    out.textContent = `⏳ Scanning ${q.toUpperCase()} on DEX + GoPlus Security…`;
    try {
      const r = await fetch(`/api/token-scan?q=${encodeURIComponent(q)}`, { cache: "no-store" });
      const data = await r.json();
      if (!data || !data.ok) {
        out.textContent = d.rugErr;
        return;
      }
      const cls =
        data.verdict === "SAFE" ? "safe" : data.verdict === "CAUTION" ? "caution" : "danger";
      const verdTxt =
        data.verdict === "SAFE" ? d.rugSafe : data.verdict === "CAUTION" ? d.rugCaution : d.rugDanger;
      out.innerHTML = tpl(d.rugResTpl, {
        sym: data.symbol,
        chain: data.chain,
        cls,
        score: data.score,
        verd: verdTxt,
        liq: Number(data.liq_usd).toLocaleString("en-US"),
        hp: data.is_honeypot ? d.rugHpYes : d.rugHpNo,
        bt: data.buy_tax,
        st: data.sell_tax,
      });
    } catch (_) {
      out.textContent = d.rugErr;
    }
  }

  $("#rugScanBtn")?.addEventListener("click", () => {
    haptic("medium");
    scanToken($("#rugInput")?.value || "PEPE");
  });
  $("#rugInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") scanToken($("#rugInput")?.value || "PEPE");
  });

  async function inspectWallet(addr) {
    const out = $("#wxResult");
    if (!out) return;
    const d = t();
    const clean = (addr || "").trim();
    if (!clean.startsWith("0x") || clean.length !== 42) {
      out.classList.remove("hidden");
      out.textContent = d.wxErr;
      return;
    }
    out.classList.remove("hidden");
    out.textContent = "⏳ Scanning Hyperliquid L1…";
    try {
      const r = await fetch(`/api/wallet?addr=${encodeURIComponent(clean)}`, { cache: "no-store" });
      const data = await r.json();
      if (!data || !data.ok) {
        out.textContent = d.wxErr;
        return;
      }
      const head = tpl(d.wxSummaryTpl, {
        eq: Number(data.account_value).toLocaleString("en-US"),
        ntl: Number(data.total_notional).toLocaleString("en-US"),
      });
      if (!data.positions || !data.positions.length) {
        out.innerHTML = `${head}<br/><span>${d.wxNoPos}</span>`;
        return;
      }
      const lines = data.positions.slice(0, 4).map((p) => {
        const cls = p.upnl >= 0 ? "pnl-pos" : "pnl-neg";
        const s = p.upnl >= 0 ? "+$" : "-$";
        return `• <b>$${p.coin}</b> ${p.side} (${p.lev}x) · $${Number(p.val_usd).toLocaleString("en-US")} · <span class="${cls}">${s}${Math.abs(p.upnl).toLocaleString("en-US")}</span>`;
      });
      out.innerHTML = `${head}<br/>${lines.join("<br/>")}`;
    } catch (_) {
      out.textContent = d.wxErr;
    }
  }

  $("#wxScanBtn")?.addEventListener("click", () => {
    haptic("medium");
    inspectWallet($("#wxInput")?.value || "");
  });

  $$("#arbCapSeg .cap-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      $$("#arbCapSeg .cap-btn").forEach((b) => b.classList.remove("is-on"));
      btn.classList.add("is-on");
      arbCapital = parseInt(btn.dataset.cap, 10) || 500;
      renderOppCard();
    });
  });

  $("#favFilter")?.addEventListener("click", () => {
    haptic("light");
    favOnly = !favOnly;
    const chip = $("#favFilter");
    if (chip) chip.classList.toggle("is-on", favOnly);
    if (favOnly && !loadFavs().length) appToast(t().toastFavEmpty);
    renderRadar();
  });

  $$("#radarModeSeg .rm-btn[data-mode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      $$("#radarModeSeg .rm-btn").forEach((b) => b.classList.remove("is-on"));
      btn.classList.add("is-on");
      radarMode = btn.dataset.mode;
      if (radarMode === "whales") fetchLiveWhales();
      renderRadar();
    });
  });

  /* =======================================================
     2) PROP DEALS (Localized per language/region)
  ======================================================= */
  function renderPropDeals() {
    const box = $("#propDealsList");
    if (!box) return;
    const d = t();
    const deals = d.deals || [];
    box.innerHTML = "";
    deals.forEach((item) => {
      const card = document.createElement("div");
      card.className = "deal-card";
      card.innerHTML = `
        <div class="deal-top">
          <div>
            <div class="deal-name">${item.name}</div>
            <div class="deal-sub">${item.badge}</div>
          </div>
          <span class="deal-cb">+${fmt(item.cashback_usdt)} ${d.dealCbSuffix}</span>
        </div>
        <div class="deal-meta">
          <span>${d.dealChallenge}: $${fmt(item.plan_10k_usd)}</span>
          <span>${d.dealDd}: ${item.daily_dd}</span>
          <span>${d.dealDisc}: ${fmt(item.discount_pct)}%</span>
        </div>
        <div class="deal-foot">
          <span class="deal-ver">✓ ${item.verified_payouts}</span>
          <button class="deal-code-btn" data-code="${item.code}">${d.dealCopy}: ${item.code}</button>
        </div>`;
      box.appendChild(card);
    });

    $$(".deal-code-btn", box).forEach((btn) => {
      btn.addEventListener("click", () => {
        haptic("medium");
        const code = btn.dataset.code;
        if (navigator.clipboard) navigator.clipboard.writeText(code).catch(() => {});
        appToast(tpl(t().toastCopyCode, { code }));
      });
    });
  }

  /* =======================================================
     3) GUARD CALCULATOR + REAL DOWNLOADS + STORY CANVAS
  ======================================================= */
  const ddRange = $("#ddRange");
  const riskRange = $("#riskRange");
  const slRange = $("#slRange");

  function setRangeFill(el) {
    if (!el) return;
    const pct = ((el.value - el.min) / (el.max - el.min)) * 100;
    el.style.setProperty("--fill", pct + "%");
  }

  const INST_CONFIG = {
    XAUUSD: { min: 2, max: 25, step: 1, def: 5, mult: 100, prefix: "$" },
    EURUSD: { min: 10, max: 100, step: 5, def: 50, mult: 10, prefix: "", suffix: " pip" },
    NAS100: { min: 15, max: 150, step: 5, def: 50, mult: 10, prefix: "", suffix: " pt" },
    BTCUSD: { min: 100, max: 1500, step: 50, def: 500, mult: 1, prefix: "$" },
  };
  let currentInst = "XAUUSD";

  function calcGuard() {
    const d = t();
    const cfg = INST_CONFIG[currentInst] || INST_CONFIG.XAUUSD;
    const dd = parseFloat(ddRange.value);
    const risk = parseFloat(riskRange.value);
    const sl = parseFloat(slRange.value);

    const cap = balance * (dd / 100);
    const perTrade = balance * (risk / 100);
    const lots = Math.max(0.01, perTrade / (sl * cfg.mult));
    const maxTrades = Math.max(1, Math.floor(cap / perTrade));

    lastCalc = { cap, perTrade, lots, maxTrades, dd, risk };

    $("#ddVal").textContent = fmt(dd, dd % 1 ? 1 : 0) + "%";
    $("#riskVal").textContent = fmt(risk, 1) + "%";
    $("#slVal").textContent = `${cfg.prefix || ""}${fmt(sl)}${cfg.suffix || ""}`;

    $("#outCap").textContent = "$" + fmt(cap);
    $("#outRisk").textContent = "$" + fmt(perTrade);
    $("#outLot").textContent = `${fmt(lots, 2)} ${d.lotUnit}`;
    $("#outTrades").textContent = `${fmt(maxTrades)} ${d.tradesUnit}`;

    $("#usagePct").textContent = tpl(d.usageOfCapTpl, { n: fmt(Math.round(TODAY_USED * 100)) });
    $("#usageFill").style.width = TODAY_USED * 100 + "%";

    $$("#balSeg .seg-btn").forEach((b) => {
      const val = parseInt(b.dataset.bal, 10);
      b.textContent = "$" + fmt(val);
    });

    const recEl = $("#recovNote");
    if (recEl && d.recovTpl) {
      const recPct = (dd / (100 - dd)) * 100;
      recEl.innerHTML = tpl(d.recovTpl, {
        dd: fmt(dd, dd % 1 ? 1 : 0),
        rec: fmt(recPct, 2, 2),
      });
    }

    [ddRange, riskRange, slRange].forEach(setRangeFill);
  }

  $$("#instSeg .inst-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      $$("#instSeg .inst-btn").forEach((b) => b.classList.remove("is-on"));
      btn.classList.add("is-on");
      currentInst = btn.dataset.inst || "XAUUSD";
      const cfg = INST_CONFIG[currentInst] || INST_CONFIG.XAUUSD;
      slRange.min = cfg.min;
      slRange.max = cfg.max;
      slRange.step = cfg.step;
      slRange.value = cfg.def;
      calcGuard();
    });
  });

  function calcConsistency() {
    const out = $("#csOut");
    const totEl = $("#csTotal");
    const bestEl = $("#csBest");
    const capEl = $("#csCap");
    if (!out || !totEl || !bestEl || !capEl) return;
    const d = t();
    const total = Math.max(1, parseFloat(totEl.value) || 0);
    const best = Math.max(0, parseFloat(bestEl.value) || 0);
    const cap = parseFloat(capEl.value) || 40;
    const score = (best / total) * 100;
    const capDec = cap / 100;

    if (score <= cap + 0.01) {
      const maxToday = Math.round((capDec * total) / (1 - capDec));
      out.classList.remove("warn");
      out.innerHTML = tpl(d.csSafeTpl, {
        score: fmt(score, 1, 1),
        cap: fmt(cap),
        maxDay: fmt(maxToday),
      });
    } else {
      const reqTotal = best / capDec;
      const needMore = Math.max(1, Math.ceil(reqTotal - total));
      out.classList.add("warn");
      out.innerHTML = tpl(d.csWarnTpl, {
        score: fmt(score, 1, 1),
        cap: fmt(cap),
        need: fmt(needMore),
      });
    }
  }

  ["#csTotal", "#csBest", "#csCap"].forEach((sel) => {
    $(sel)?.addEventListener("input", calcConsistency);
    $(sel)?.addEventListener("change", calcConsistency);
  });

  $$("#firmPresets .fp-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      $$("#firmPresets .fp-btn").forEach((b) => b.classList.remove("is-on"));
      btn.classList.add("is-on");
      ddRange.value = btn.dataset.dd;
      riskRange.value = btn.dataset.risk;
      const capEl = $("#csCap");
      if (capEl && btn.dataset.cap) capEl.value = btn.dataset.cap;
      calcGuard();
      calcConsistency();
    });
  });

  /* ---------- Custom Alert Builder ---------- */
  let customAlerts = [];
  try {
    customAlerts = JSON.parse(localStorage.getItem("tg_custom_alerts") || "[]");
  } catch (_) {
    customAlerts = [];
  }

  function renderCustomAlerts() {
    const box = $("#caList");
    if (!box) return;
    box.innerHTML = "";
    customAlerts.forEach((al, idx) => {
      const chip = document.createElement("div");
      chip.className = "ca-chip";
      chip.innerHTML = `<span>🔔 <b>$${al.sym}</b> ➜ ${al.val}</span><button class="ca-del" type="button">✕</button>`;
      $(".ca-del", chip).addEventListener("click", () => {
        customAlerts.splice(idx, 1);
        try {
          localStorage.setItem("tg_custom_alerts", JSON.stringify(customAlerts));
        } catch (_) {}
        renderCustomAlerts();
      });
      box.appendChild(chip);
    });
  }

  $("#caAddBtn")?.addEventListener("click", () => {
    const sym = $("#caSym")?.value || "BTC";
    const valEl = $("#caVal");
    const val = (valEl?.value || "").trim() || (sym === "BTC" ? "$82,000" : "+0.15%");
    haptic("medium");
    customAlerts.unshift({ sym, val });
    customAlerts = customAlerts.slice(0, 4);
    if (valEl) valEl.value = "";
    try {
      localStorage.setItem("tg_custom_alerts", JSON.stringify(customAlerts));
    } catch (_) {}
    renderCustomAlerts();
    appToast(tpl(t().caAddedToast, { sym, val }));
  });

  [ddRange, riskRange, slRange].forEach((el) => el.addEventListener("input", calcGuard));

  $$("#balSeg .seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      $$("#balSeg .seg-btn").forEach((b) => b.classList.remove("is-on"));
      btn.classList.add("is-on");
      balance = parseInt(btn.dataset.bal, 10);
      calcGuard();
    });
  });

  function syncGuardUi() {
    const d = t();
    const guardToggle = $("#guardToggle");
    const pill = $("#guardState");
    if (!guardToggle || !pill) return;
    if (guardOn) {
      guardToggle.textContent = d.guardBtnOn;
      guardToggle.classList.remove("btn-guard-off");
      guardToggle.classList.add("btn-guard-on");
      pill.textContent = d.stateOn;
      pill.classList.remove("off");
      pill.classList.add("on");
    } else {
      guardToggle.textContent = d.guardBtnOff;
      guardToggle.classList.add("btn-guard-off");
      guardToggle.classList.remove("btn-guard-on");
      pill.textContent = d.stateOff;
      pill.classList.add("off");
      pill.classList.remove("on");
    }
  }

  $("#guardToggle")?.addEventListener("click", () => {
    haptic("medium");
    guardOn = !guardOn;
    syncGuardUi();
    if (guardOn) appToast(t().toastGuardOn);
  });

  $("#eaRow")?.addEventListener("click", () => {
    if (!isPro) {
      appToast(t().toastNeedProMt5);
      goToTab("sub");
      return;
    }
    window.location.href = "TradeGuard_PropProtector.mq5";
    appToast(t().toastDlMt5);
  });

  $("#pineRow")?.addEventListener("click", () => {
    if (!isPro) {
      appToast(t().toastNeedProPine);
      goToTab("sub");
      return;
    }
    window.location.href = "TradeGuard_SmartRadar.pine";
    appToast(t().toastDlPine);
  });

  /* ---------- Viral Story PNG Card (Supports RTL & LTR!) ---------- */
  const storySheet = $("#storySheet");
  const storyCanvas = $("#storyCanvas");

  function drawStoryCard() {
    if (!storyCanvas || typeof storyCanvas.getContext !== "function") return;
    if (!storyCanvas.getContext("2d")) return;
    const d = t();
    const isRtl = d.dir === "rtl";
    const ctx = storyCanvas.getContext("2d");
    const W = storyCanvas.width;
    const H = storyCanvas.height;

    const grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0, "#070D1B");
    grad.addColorStop(0.55, "#101E36");
    grad.addColorStop(1, "#081221");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    const glow1 = ctx.createRadialGradient(W * 0.8, H * 0.16, 10, W * 0.8, H * 0.16, 320);
    glow1.addColorStop(0, "rgba(37, 214, 154, 0.25)");
    glow1.addColorStop(1, "rgba(37, 214, 154, 0)");
    ctx.fillStyle = glow1;
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = "rgba(42, 171, 238, 0.45)";
    ctx.lineWidth = 3;
    ctx.strokeRect(36, 36, W - 72, H - 72);

    ctx.textAlign = "center";
    ctx.fillStyle = "#2AABEE";
    ctx.font = "bold 26px Tahoma, Segoe UI, sans-serif";
    ctx.fillText(d.storyTop, W / 2, 118);

    ctx.fillStyle = "#FFFFFF";
    ctx.font = "bold 38px Tahoma, Segoe UI, sans-serif";
    ctx.fillText(d.storyHeadline, W / 2, 185);

    ctx.fillStyle = "rgba(20, 34, 58, 0.92)";
    ctx.fillRect(76, 245, W - 152, 170);
    ctx.strokeStyle = "rgba(37, 214, 154, 0.5)";
    ctx.strokeRect(76, 245, W - 152, 170);

    ctx.fillStyle = "#8FA2C0";
    ctx.font = "22px Tahoma, Segoe UI, sans-serif";
    ctx.fillText(d.storySubBox, W / 2, 300);

    ctx.fillStyle = "#25D69A";
    ctx.font = "bold 62px Tahoma, Segoe UI, sans-serif";
    ctx.fillText(`$${balance.toLocaleString("en-US")}`, W / 2, 382);

    const rows = [
      [d.storyRow1, `-3.8% ($${Math.round(balance * 0.038)})`],
      [d.storyRow2, `${lastCalc.lots.toFixed(2)} Lot`],
      [d.storyRow3, `+$${(balance * 0.001).toFixed(0)} / Day`],
      [d.storyRow4, `$${Number(liveBtcPrice).toLocaleString("en-US")}`],
    ];

    let y = 485;
    rows.forEach(([label, val]) => {
      ctx.fillStyle = "rgba(16, 26, 44, 0.9)";
      ctx.fillRect(76, y, W - 152, 92);
      ctx.strokeStyle = "rgba(30, 44, 69, 0.9)";
      ctx.strokeRect(76, y, W - 152, 92);

      if (isRtl) {
        ctx.textAlign = "right";
        ctx.fillStyle = "#B9C6DE";
        ctx.font = "23px Tahoma, Segoe UI, sans-serif";
        ctx.fillText(label, W - 104, y + 55);
        ctx.textAlign = "left";
        ctx.fillStyle = "#FFC94D";
        ctx.font = "bold 26px Tahoma, Segoe UI, sans-serif";
        ctx.fillText(val, 104, y + 55);
      } else {
        ctx.textAlign = "left";
        ctx.fillStyle = "#B9C6DE";
        ctx.font = "22px Segoe UI, Tahoma, sans-serif";
        ctx.fillText(label, 104, y + 55);
        ctx.textAlign = "right";
        ctx.fillStyle = "#FFC94D";
        ctx.font = "bold 26px Segoe UI, Tahoma, sans-serif";
        ctx.fillText(val, W - 104, y + 55);
      }
      y += 112;
    });

    ctx.textAlign = "center";
    ctx.fillStyle = "#25D69A";
    ctx.font = "bold 26px Tahoma, Segoe UI, sans-serif";
    ctx.fillText(d.storyFoot, W / 2, 995);

    ctx.fillStyle = "#FFFFFF";
    ctx.font = "bold 25px Segoe UI, Tahoma, sans-serif";
    ctx.fillText("Telegram Mini-App: @TradeGuard_bot", W / 2, 1045);
  }

  $("#shareCardBtn")?.addEventListener("click", () => {
    haptic("medium");
    // مرورگرهای بدون پشتیبانی canvas نباید کل اپ را با خطای بدون کنترل بترکانند
    try {
      drawStoryCard();
    } catch (err) {
      console.warn("[TradeGuard] story card failed:", err);
      appToast(t().toastStorySaved || "—");
    }
    storySheet.classList.remove("hidden");
  });

  $("#storyBack")?.addEventListener("click", () => storySheet.classList.add("hidden"));

  $("#dlStoryBtn")?.addEventListener("click", () => {
    if (!storyCanvas) return;
    try {
      const link = document.createElement("a");
      link.download = `TradeGuard_${currentLang.toUpperCase()}_${balance}.png`;
      link.href = storyCanvas.toDataURL("image/png");
      link.click();
      appToast(t().toastStorySaved);
    } catch (err) {
      console.warn("[TradeGuard] story download failed:", err);
      appToast(t().toastStorySaved || "—");
    }
  });

  /* =======================================================
     3.5) ژورنال تریدر: ریسک، حجم پوزیشن و R
     -------------------------------------------------------
     فلسفه: هیچ عددی از سرور نمی‌آید و هیچ «سود ادعایی» ثبت
     نمی‌شود. هرچه می‌بینی از قیمت‌هایی است که خودِ کاربر
     وارد کرده (ورود/حد ضرر/هدف) و فقط روی همین دستگاه
     ذخیره می‌شود.
  ======================================================= */
  const JRN_KEY = "tg_journal_v1";
  const JRN_MAX = 200;

  function jrnRead() {
    try {
      const raw = localStorage.getItem(JRN_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr.filter((t) => t && typeof t === "object" && t.id) : [];
    } catch (_) {
      return [];
    }
  }

  function jrnWrite(list) {
    try {
      localStorage.setItem(JRN_KEY, JSON.stringify(list.slice(0, JRN_MAX)));
    } catch (_) {}
  }

  function jrnVal(id) {
    const el = $("#" + id);
    if (!el) return 0;
    const n = parseFloat(String(el.value).replace(",", "."));
    return isFinite(n) ? n : 0;
  }

  function jrnMoney(v) {
    if (!isFinite(v)) return "—";
    const a = Math.abs(v);
    if (a >= 10000) return "$" + Math.round(v).toLocaleString("en-US");
    if (a >= 1) return "$" + v.toFixed(2);
    return "$" + v.toFixed(4);
  }

  function jrnSize(v) {
    if (!isFinite(v) || v === 0) return "—";
    const a = Math.abs(v);
    if (a >= 1000) return v.toFixed(0);
    if (a >= 1) return v.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
    return v.toPrecision(4);
  }

  /* محاسبهٔ کامل یک ستاپ: ریسک، حجم، نسبت R */
  function jrnCalc(v) {
    const entry = Number(v.entry) || 0;
    const stop = Number(v.stop) || 0;
    const target = Number(v.target) || 0;
    const balance = Number(v.balance) || 0;
    const riskPct = Number(v.riskPct) || 0;
    const errs = [];
    if (!(entry > 0) || !(stop > 0)) errs.push("fill");
    if (!(balance > 0)) errs.push("balance");
    if (!(riskPct > 0)) errs.push("risk");
    if (entry > 0 && stop > 0 && entry === stop) errs.push("sameStop");
    const dir = stop > 0 && entry > 0 && stop < entry ? "long" : "short";
    if (target > 0 && entry > 0) {
      if (dir === "long" && target <= entry) errs.push("targetSide");
      if (dir === "short" && target >= entry) errs.push("targetSide");
    }
    const perUnit = Math.abs(entry - stop);
    const riskAmt = (balance * riskPct) / 100;
    const units = perUnit > 0 ? riskAmt / perUnit : 0;
    const notional = units * entry;
    const rr = perUnit > 0 && target > 0 ? Math.abs(target - entry) / perUnit : 0;
    const reward = units > 0 && target > 0 ? Math.abs(target - entry) * units : 0;
    return { dir, perUnit, riskAmt, units, notional, rr, reward, errs, entry, stop, target, balance, riskPct };
  }

  function jrnCell(label, value, cls) {
    return (
      '<div class="jr-cell' + (cls ? " " + cls : "") + '"><span>' + label + "</span><b>" + value + "</b></div>"
    );
  }

  function renderJournalCalc() {
    const box = $("#jrCalc");
    if (!box) return;
    const d = t();
    const c = jrnCalc({
      balance: jrnVal("jrBalance"),
      riskPct: jrnVal("jrRiskPct"),
      entry: jrnVal("jrEntry"),
      stop: jrnVal("jrStop"),
      target: jrnVal("jrTarget"),
    });
    const errMap = {
      fill: d.jrErrFill,
      balance: d.jrErrBalance,
      risk: d.jrErrRisk,
      sameStop: d.jrErrSameStop,
      targetSide: d.jrErrTarget,
    };
    let html = "";
    html += jrnCell(d.jrRiskAmount || "Risk", jrnMoney(c.riskAmt), c.riskAmt > 0 ? "is-good" : "");
    html += jrnCell(d.jrUnits || "Size", jrnSize(c.units));
    html += jrnCell(d.jrNotional || "Notional", jrnMoney(c.notional));
    html += jrnCell(
      d.jrRR || "R:R",
      c.rr > 0 ? "1 : " + c.rr.toFixed(2) : "—",
      c.rr >= 1.5 ? "is-good" : c.rr > 0 && c.rr < 1 ? "is-bad" : ""
    );
    if (c.reward > 0) html += jrnCell(d.jrReward || "Reward", jrnMoney(c.reward), "is-good");
    if (c.entry > 0 && c.stop > 0 && !c.errs.includes("sameStop")) {
      html += jrnCell(d.jrDir || "Side", c.dir === "long" ? d.jrLong || "Long" : d.jrShort || "Short");
    }
    const errs = c.errs.filter((e) => errMap[e]);
    if (errs.length) {
      html += '<div class="jr-hint">' + errs.map((e) => errMap[e]).join("<br>") + "</div>";
    }
    box.innerHTML = html;
  }

  function jrnStats(list) {
    const closed = list.filter((x) => x.status && x.status !== "open");
    const wins = closed.filter((x) => x.status === "win");
    const losses = closed.filter((x) => x.status === "loss");
    const withR = closed.filter((x) => typeof x.r === "number" && isFinite(x.r));
    const sumR = withR.reduce((a, x) => a + x.r, 0);
    const posR = withR.filter((x) => x.r > 0).reduce((a, x) => a + x.r, 0);
    const negR = withR.filter((x) => x.r < 0).reduce((a, x) => a + x.r, 0);
    const good = list.filter(
      (x) => Number(x.stop) > 0 && Number(x.riskPct) > 0 && Number(x.riskPct) <= 1 && Number(x.rr) >= 1.5
    );
    return {
      total: list.length,
      closed: closed.length,
      open: list.length - closed.length,
      wins: wins.length,
      losses: losses.length,
      winRate: closed.length ? (wins.length / closed.length) * 100 : 0,
      expectancy: withR.length ? sumR / withR.length : null,
      pf: negR < 0 ? posR / Math.abs(negR) : posR > 0 ? Infinity : null,
      best: withR.length ? Math.max.apply(null, withR.map((x) => x.r)) : null,
      worst: withR.length ? Math.min.apply(null, withR.map((x) => x.r)) : null,
      discipline: list.length ? (good.length / list.length) * 100 : 0,
    };
  }

  function renderJournalStats(list) {
    const box = $("#jrStats");
    if (!box) return;
    const d = t();
    const s = jrnStats(list);
    if (!s.total) {
      box.classList.add("hidden");
      box.innerHTML = "";
      return;
    }
    box.classList.remove("hidden");
    const rTxt = (v) => (v === null ? "—" : (v > 0 ? "+" : "") + v.toFixed(2) + "R");
    const pfTxt = s.pf === null ? "—" : s.pf === Infinity ? "∞" : s.pf.toFixed(2);
    box.innerHTML = [
      '<div class="jr-stat"><b>' + s.closed + "</b><span>" + (d.jrStatClosed || "Closed") + "</span></div>",
      '<div class="jr-stat"><b>' + (s.closed ? s.winRate.toFixed(0) + "%" : "—") + "</b><span>" + (d.jrStatWinRate || "Win rate") + "</span></div>",
      '<div class="jr-stat"><b>' + rTxt(s.expectancy) + "</b><span>" + (d.jrStatExp || "Expectancy") + "</span></div>",
      '<div class="jr-stat"><b>' + pfTxt + "</b><span>" + (d.jrStatPF || "Profit factor") + "</span></div>",
      '<div class="jr-stat"><b>' + rTxt(s.best) + "</b><span>" + (d.jrStatBest || "Best") + "</span></div>",
      '<div class="jr-stat"><b>' + rTxt(s.worst) + "</b><span>" + (d.jrStatWorst || "Worst") + "</span></div>",
      '<div class="jr-stat" style="grid-column:1/-1"><b>' + s.discipline.toFixed(0) + '%</b><span>' +
        (d.jrStatDisc || "Discipline") + " · " + (d.jrStatDiscHint || "") + "</span></div>",
    ].join("");
  }

  function renderJournalList(list) {
    const box = $("#jrList");
    if (!box) return;
    const d = t();
    if (!list.length) {
      box.innerHTML = '<div class="jr-empty">' + (d.jrEmpty || "") + "</div>";
      return;
    }
    box.innerHTML = list
      .map((x) => {
        const status = x.status || "open";
        let pill = '<span class="jr-pill r-open">' + (d.jrOpen || "Open") + "</span>";
        if (status === "win") pill = '<span class="jr-pill r-pos">+' + (Number(x.r) || 0).toFixed(2) + "R</span>";
        if (status === "loss") pill = '<span class="jr-pill r-neg">' + (Number(x.r) || -1).toFixed(2) + "R</span>";
        if (status === "be") pill = '<span class="jr-pill r-open">0.00R</span>';
        const dirPill =
          '<span class="jr-pill ' + (x.dir === "short" ? "short" : "long") + '">' +
          (x.dir === "short" ? d.jrShort || "Short" : d.jrLong || "Long") + "</span>";
        const meta =
          "E " + jrnSize(x.entry) + " · SL " + jrnSize(x.stop) +
          (Number(x.target) > 0 ? " · TP " + jrnSize(x.target) : "") +
          " · " + jrnSize(x.units) + " × " + jrnMoney(x.entry) + " · R:R " +
          (Number(x.rr) > 0 ? "1:" + Number(x.rr).toFixed(2) : "—");
        const acts =
          status === "open"
            ? '<button class="is-win" data-act="win" data-id="' + x.id + '">' + (d.jrWin || "Win") + "</button>" +
              '<button class="is-loss" data-act="loss" data-id="' + x.id + '">' + (d.jrLoss || "Loss") + "</button>" +
              '<button data-act="be" data-id="' + x.id + '">' + (d.jrBE || "Break-even") + "</button>"
            : "";
        return (
          '<div class="jr-item">' +
          '<div class="jr-item-top"><b>' + (x.sym ? "$" + String(x.sym).toUpperCase() : "—") + "</b>" +
          dirPill + pill + "</div>" +
          '<div class="jr-item-meta">' + meta + "</div>" +
          '<div class="jr-item-actions">' + acts +
          '<button data-act="del" data-id="' + x.id + '">' + (d.jrDelete || "Delete") + "</button></div>" +
          "</div>"
        );
      })
      .join("");
  }

  function renderJournal() {
    const list = jrnRead();
    renderJournalCalc();
    renderJournalStats(list);
    renderJournalList(list);
  }

  function jrnUpdate(id, patch) {
    const list = jrnRead().map((x) => (x.id === id ? Object.assign({}, x, patch) : x));
    jrnWrite(list);
    renderJournal();
  }

  function jrnRemove(id) {
    jrnWrite(jrnRead().filter((x) => x.id !== id));
    renderJournal();
  }

  function jrnAddFromForm() {
    const d = t();
    const c = jrnCalc({
      balance: jrnVal("jrBalance"),
      riskPct: jrnVal("jrRiskPct"),
      entry: jrnVal("jrEntry"),
      stop: jrnVal("jrStop"),
      target: jrnVal("jrTarget"),
    });
    if (c.errs.length) {
      appToast(d.jrErrFill || "Fill the form");
      renderJournalCalc();
      return;
    }
    const symEl = $("#jrSym");
    const trade = {
      id: "t" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      sym: symEl ? String(symEl.value || "").trim().toUpperCase().slice(0, 12) : "",
      dir: c.dir,
      entry: c.entry,
      stop: c.stop,
      target: c.target,
      units: Number(c.units.toFixed(8)),
      riskPct: c.riskPct,
      rr: Number(c.rr.toFixed(4)),
      status: "open",
      opened: Date.now(),
      closed: null,
      r: null,
    };
    const list = [trade].concat(jrnRead()).slice(0, JRN_MAX);
    jrnWrite(list);
    if (symEl) symEl.value = "";
    ["jrEntry", "jrStop", "jrTarget"].forEach((id) => {
      const el = $("#" + id);
      if (el) el.value = "";
    });
    renderJournal();
    appToast(d.jrSaved || "Saved");
    haptic("medium");
  }

  function jrnBind() {
    /* بالانس و درصد ریسک را نگه می‌داریم تا هر بار تایپ نشوند (فقط روی دستگاه) */
    const JRN_PREFS = "tg_jr_prefs";
    try {
      const prefs = JSON.parse(localStorage.getItem(JRN_PREFS) || "{}");
      if (prefs.balance) $("#jrBalance").value = prefs.balance;
      if (prefs.riskPct) $("#jrRiskPct").value = prefs.riskPct;
    } catch (_) {}
    ["jrBalance", "jrRiskPct"].forEach((id) => {
      const el = $("#" + id);
      if (!el) return;
      el.addEventListener("change", () => {
        try {
          localStorage.setItem(
            JRN_PREFS,
            JSON.stringify({ balance: jrnVal("jrBalance") || "", riskPct: jrnVal("jrRiskPct") || "" })
          );
        } catch (_) {}
      });
    });
    ["jrBalance", "jrRiskPct", "jrEntry", "jrStop", "jrTarget"].forEach((id) => {
      const el = $("#" + id);
      if (el) el.addEventListener("input", renderJournalCalc);
    });
    $("#jrSaveBtn")?.addEventListener("click", jrnAddFromForm);
    $("#jrResetBtn")?.addEventListener("click", () => {
      ["jrSym", "jrEntry", "jrStop", "jrTarget"].forEach((id) => {
        const el = $("#" + id);
        if (el) el.value = "";
      });
      renderJournalCalc();
    });
    $("#jrList")?.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-act]");
      if (!btn) return;
      const id = btn.dataset.id;
      const act = btn.dataset.act;
      if (act === "del") {
        jrnRemove(id);
        return;
      }
      const item = jrnRead().find((x) => x.id === id);
      if (!item) return;
      const rr = Number(item.rr) || 0;
      if (act === "win") jrnUpdate(id, { status: "win", closed: Date.now(), r: rr > 0 ? Number(rr.toFixed(4)) : null });
      if (act === "loss") jrnUpdate(id, { status: "loss", closed: Date.now(), r: -1 });
      if (act === "be") jrnUpdate(id, { status: "be", closed: Date.now(), r: 0 });
      haptic("light");
    });
    $("#jrExportBtn")?.addEventListener("click", () => {
      const d = t();
      try {
        const payload = {
          app: "TradeGuard journal",
          exported_at: new Date().toISOString(),
          note: "R multiples are derived from the prices you entered, not from claimed PnL.",
          trades: jrnRead(),
        };
        const json = JSON.stringify(payload, null, 2);
        let url = "";
        try {
          if (typeof URL !== "undefined" && URL.createObjectURL) {
            url = URL.createObjectURL(new Blob([json], { type: "application/json" }));
          }
        } catch (_) {}
        if (!url) {
          // بازگشتی برای WebViewهای قدیمی/محیط‌های بدون Blob URL
          url = "data:application/json;charset=utf-8," + encodeURIComponent(json);
        }
        const a = document.createElement("a");
        a.href = url;
        a.download = "tradeguard-journal.json";
        a.rel = "noopener";
        document.body.appendChild(a);
        a.click();
        a.remove();
        if (url.indexOf("blob:") === 0) setTimeout(() => URL.revokeObjectURL(url), 4000);
        appToast(d.jrExported || "Exported");
      } catch (_) {
        appToast(d.jrExportFail || "Export failed");
      }
    });
    renderJournal();
  }

  jrnBind();

  /* =======================================================
     4) TABS, STARS BILLING & VIRAL REFERRAL
  ======================================================= */
  $$(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      $$(".tab-btn").forEach((b) => b.classList.remove("is-on"));
      btn.classList.add("is-on");
      $$(".tab-pane").forEach((p) =>
        p.classList.toggle("is-active", p.dataset.pane === btn.dataset.tab)
      );
      $(".screen-body").scrollTop = 0;
      if (btn.dataset.tab === "radar") renderRadar();
      if (btn.dataset.tab === "journal") renderJournal();
    });
  });

  function goToTab(name) {
    const btn = $(`.tab-btn[data-tab="${name}"]`);
    if (btn) btn.click();
  }

  const invoice = $("#invoice");
  function showStep(n) {
    $$(".sheet-step", invoice).forEach((s) =>
      s.classList.toggle("hidden", s.dataset.step !== String(n))
    );
  }

  $("#buyBtn")?.addEventListener("click", () => {
    haptic("medium");
    showStep(1);
    invoice.classList.remove("hidden");
  });
  $("#invBack")?.addEventListener("click", () => invoice.classList.add("hidden"));

  /* نام واقعی ربات در شیت پرداخت — از config تولیدشده (قبلاً هاردکد و اشتباه بود) */
  const TG_CONFIG = window.TG_CONFIG || {};
  const BOT_USERNAME = String(TG_CONFIG.botUsername || "TradeGuard1_bot").replace(/^@/, "");
  const invBotName = $("#invBotName");
  if (invBotName) invBotName.textContent = "@" + BOT_USERNAME;

  /* ربات صاحب پرداخت است (Telegram Stars).
     قبلاً این دکمه فقط `setPro(true)` می‌کرد؛ یعنی هر کسی با یک کلیک
     اشتراک پولی را باز می‌کرد — بدون این‌که یک استارز پرداخت شود. */
  $("#startBtn")?.addEventListener("click", () => {
    invoice.classList.add("hidden");
    openBotChat("pro");
    appToast(t().toastPayInBot || t().toastProOn);
  });

  function syncProUi() {
    const d = t();
    const chip = $("#planChip");
    if (chip) {
      chip.textContent = isPro ? d.planPro : d.planBasic;
      chip.classList.toggle("pro", isPro);
      chip.classList.toggle("off", !isPro);
    }

    $("#subIdle")?.classList.toggle("hidden", isPro || isFreeMode);
    $("#subActive")?.classList.toggle("hidden", !(isPro || isFreeMode));

    // 🎁 نشان دورهٔ رایگان
    if (chip && isFreeMode) {
      chip.textContent = d.planFree;
      chip.classList.add("pro");
      chip.classList.remove("off");
    }
    const freeNote = $("#freeNote");
    if (freeNote) freeNote.classList.toggle("hidden", !isFreeMode);
    if (isFreeMode) {
      const dateEl = $("#proActiveDate");
      if (dateEl) dateEl.textContent = d.freeBadge;
    }

    // 📣 دکمهٔ کانال (فقط اگر کانال عمومی در config باشد)
    const chBtn = $("#joinChannelBtn");
    if (chBtn) {
      const cfgChannel = String(TG_CONFIG.channel || "").replace(/^@/, "");
      channelUrl = cfgChannel ? "https://t.me/" + cfgChannel : "";
      chBtn.classList.toggle("hidden", !channelUrl);
      const claimBtn = $("#claimJoinBtn");
      if (claimBtn) claimBtn.classList.toggle("hidden", !channelUrl);
    }

    const ea = $("#eaRow");
    if (ea) {
      ea.classList.toggle("locked", !isPro);
      ea.classList.toggle("open", isPro);
      $(".ea-lock", ea).textContent = isPro ? d.dlMt5Txt : d.lockTxt;
    }

    const pine = $("#pineRow");
    if (pine) {
      pine.classList.toggle("locked", !isPro);
      pine.classList.toggle("open", isPro);
      $(".ea-lock", pine).textContent = isPro ? d.dlPineTxt : d.lockTxt;
    }

    renderInviteCard();
    const expEl = $("#proActiveDate");
    if (expEl) expEl.textContent = proExpiryDate ? tpl(d.proExpiryTpl, { d: proExpiryDate }) : d.proActiveDate;
    $("#planStarsNum") && ($("#planStarsNum").textContent = fmt(300));
    $("#invPriceNum") && ($("#invPriceNum").textContent = fmt(300));
    $("#alertTabBadge") && ($("#alertTabBadge").textContent = fmt(3));
  }

  function setPro(v) {
    isPro = v;
    syncProUi();
    renderRadar();
    renderLocalizedAlerts();
  }

  let newsSec = 14 * 60 + 38;
  const newsEl = $("#newsCountdown");
  if (newsEl) {
    setInterval(() => {
      newsSec = newsSec > 0 ? newsSec - 1 : 15 * 60;
      const m = Math.floor(newsSec / 60);
      const s = newsSec % 60;
      newsEl.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }, 1000);
  }

  /* ---------- کارت دعوت واقعی (بدون شبیه‌سازی) ----------
     لینک از آیدی خودِ کاربر ساخته می‌شود و همان پارامتری است که ربات در
     /start می‌خواند: https://t.me/<bot>?start=ref_<uid>
     شمارنده و وضعیت پرو از فایل عمومی pro_users.json می‌آید که فقط ربات
     آن را می‌نویسد؛ کاربر نمی‌تواند خودش را پرو کند. */
  function tgUser() {
    try {
      return (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe &&
        window.Telegram.WebApp.initDataUnsafe.user) || null;
    } catch (e) { return null; }
  }

  function inviteLinkFor(uid) {
    if (!uid) return "";
    return "https://t.me/" + BOT_USERNAME + "?start=ref_" + uid;
  }

  function renderInviteCard() {
    const d = t();
    const u = tgUser();
    const link = inviteLinkFor(u && u.id);
    const box = $("#refLink");
    if (box && link) box.value = link;
    const goal = 3;
    const shown = Math.max(0, Math.min(goal, Number(inviteCount) || 0));
    const cnt = $("#refCounter");
    if (cnt) cnt.textContent = tpl(d.vcCountTpl, { n: fmt(shown) });
    const fill = $("#refFill");
    if (fill) fill.style.width = Math.min(100, Math.round((shown / goal) * 100)) + "%";
    [$("#refCopyBtn"), $("#refShareBtn")].forEach((b) => {
      if (b) b.disabled = !link;
    });
    const hint = $(".vc-hint");
    if (hint) hint.textContent = proExpiryDate ? tpl(d.proExpiryTpl, { d: proExpiryDate }) : d.refHint;
  }

  $("#refCopyBtn")?.addEventListener("click", async () => {
    haptic("medium");
    const link = ($("#refLink") || {}).value || "";
    if (!link) {
      openBotChat("invite");
      appToast(t().toastInviteViaBot);
      return;
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(link);
      } else {
        const el = $("#refLink");
        el.select();
        document.execCommand("copy");
      }
      appToast(t().refCopied);
    } catch (e) {
      appToast(t().refCopyFail);
    }
  });

  $("#claimJoinBtn")?.addEventListener("click", () => {
    haptic("medium");
    // پاداش فقط بعد از تأیید واقعی عضویت در ربات داده می‌شود
    openBotChat("checkjoin");
  });

  $("#joinChannelBtn")?.addEventListener("click", () => {
    haptic("medium");
    if (!channelUrl) return;
    try {
      if (window.Telegram && Telegram.WebApp && Telegram.WebApp.openTelegramLink) {
        Telegram.WebApp.openTelegramLink(channelUrl);
        return;
      }
    } catch (e) {}
    window.open(channelUrl, "_blank", "noopener");
  });

  $("#refreshProBtn")?.addEventListener("click", async () => {
    haptic("medium");
    appToast(t().toastChecking);
    await loadEntitlements();
    if (!isPro) appToast(t().toastProStillFree);
  });

  $("#refShareBtn")?.addEventListener("click", () => {
    haptic("medium");
    const link = ($("#refLink") || {}).value || "";
    if (!link) {
      openBotChat("invite");
      appToast(t().toastInviteViaBot);
      return;
    }
    const share = "https://t.me/share/url?url=" + encodeURIComponent(link) +
      "&text=" + encodeURIComponent(t().refShareText || "");
    try {
      if (window.Telegram && Telegram.WebApp && Telegram.WebApp.openTelegramLink) {
        Telegram.WebApp.openTelegramLink(share);
        return;
      }
    } catch (e) {}
    window.open(share, "_blank", "noopener");
  });

  /* ---------- خوش‌آمدگویی اولین اجرا ----------
     فقط یک‌بار نشان داده می‌شود؛ بعد از آن در localStorage ثبت می‌شود. */
  const OB_KEY = "tg_onboard_v1";
  let obStep = 1;

  function renderOnboard() {
    $$(".ob-slide").forEach((el) => el.classList.toggle("hidden", el.dataset.ob !== String(obStep)));
    const dots = $$(".ob-dots i");
    dots.forEach((dot, i) => dot.classList.toggle("is-on", i === obStep - 1));
    const next = $("#obNext");
    if (next) next.textContent = obStep >= 3 ? t().obStart : t().obNext;
  }

  function closeOnboard() {
    const el = $("#onboard");
    if (el) {
      el.classList.add("hidden");
      el.setAttribute("aria-hidden", "true");
    }
    try {
      localStorage.setItem(OB_KEY, "1");
    } catch (e) {}
  }

  function maybeShowOnboard() {
    let done = "1";
    try {
      done = localStorage.getItem(OB_KEY) || "";
    } catch (e) {
      return;   // اگر localStorage نیست، مزاحم نشو
    }
    if (done) return;
    const el = $("#onboard");
    if (!el) return;
    obStep = 1;
    renderOnboard();
    el.classList.remove("hidden");
    el.setAttribute("aria-hidden", "false");
  }

  $("#obNext")?.addEventListener("click", () => {
    haptic("medium");
    if (obStep >= 3) {
      closeOnboard();
      return;
    }
    obStep += 1;
    renderOnboard();
  });
  $("#obSkip")?.addEventListener("click", () => {
    haptic("light");
    closeOnboard();
  });

  /* ---------- وضعیت واقعی اشتراک (منبع: pro_users.json که ربات می‌نویسد) ---------- */
  let proExpiryDate = "";
  let isFreeMode = false;
  let channelUrl = "";

  /* ---------- دیده‌بان (Watchlist) + کش برای رندر آنی ---------- */
  const FAV_KEY = "tg_favs";
  const CACHE_KEY = "tg_market_cache";
  let favOnly = false;

  function loadFavs() {
    try {
      const raw = localStorage.getItem(FAV_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr.filter((x) => typeof x === "string") : [];
    } catch (e) {
      return [];
    }
  }

  function saveFavs(list) {
    try {
      localStorage.setItem(FAV_KEY, JSON.stringify(list));
    } catch (e) {}
  }

  function toggleFav(sym) {
    const list = loadFavs();
    const i = list.indexOf(sym);
    if (i >= 0) list.splice(i, 1);
    else list.push(sym);
    saveFavs(list);
    return i < 0;   // true = اضافه شد
  }

  async function proStatusKey(uid) {
    const enc = new TextEncoder().encode("tg-pro:" + uid);
    const dig = await crypto.subtle.digest("SHA-256", enc);
    return Array.from(new Uint8Array(dig))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
      .slice(0, 16);
  }

  async function loadEntitlements() {
    const u = tgUser();
    if (!u || !u.id || !(window.crypto && crypto.subtle)) return;
    try {
      const key = await proStatusKey(u.id);
      const res = await fetch("pro_users.json?v=" + Date.now(), { cache: "no-store" });
      if (!res || !res.ok) return;
      const data = await res.json();
      // 🎁 دورهٔ رشد: پرچم سراسری از ربات — همه‌چیز رایگان
      isFreeMode = !!(data && data.freeMode);
      const entry = (data && data.users && data.users[key]) || null;
      const now = Math.floor(Date.now() / 1000);
      if (entry) {
        inviteCount = Math.max(0, Number(entry.ref) || 0);
        const exp = Number(entry.exp) || 0;
        if (exp > now) {
          proExpiryDate = new Date(exp * 1000).toLocaleDateString();
          setPro(true);
        }
      }
      if (isFreeMode) setPro(true);
      syncProUi();
    } catch (e) {
      /* آفلاین یا فایل موجود نیست ⇒ حالت پایه */
    }
  }

  /* =======================================================
  /* =======================================================
     5) FOUNDER PROFIT SIMULATOR
  ======================================================= */
  const fsDirect = $("#fsDirect");
  const fsAff = $("#fsAff");
  const fsProp = $("#fsProp");

  function calcFounderProfit() {
    if (!fsDirect || !fsAff || !fsProp) return;
    const d = t();
    const directUsers = parseInt(fsDirect.value, 10);
    const affUsers = parseInt(fsAff.value, 10);
    const propSales = parseInt(fsProp.value, 10);

    const netStars = directUsers * 300 + affUsers * 150;
    const starsUsd = netStars * 0.013;
    const propUsd = propSales * 8;
    const monthlyUsd = starsUsd + propUsd;
    const dailyUsd = monthlyUsd / 30;
    const yearlyUsd = monthlyUsd * 12;

    $("#fsDirectVal").textContent = `${fmt(directUsers)} ${d.fsUsersUnit}`;
    $("#fsAffVal").textContent = `${fmt(affUsers)} ${d.fsUsersUnit}`;
    $("#fsPropVal").textContent = `${fmt(propSales)} ${d.fsSalesUnit}`;

    $("#fsOutDaily").textContent = `$${fmt(dailyUsd, 1, 1)} ${d.fsPerDay}`;
    $("#fsOutMonthly").textContent = `$${fmt(Math.round(monthlyUsd))}`;
    $("#fsOutYearly").textContent = `$${fmt(Math.round(yearlyUsd))}`;
    $("#fsOutStars").textContent = tpl(d.fsStarsBreakTpl, {
      stars: fmt(netStars),
      sUsd: fmt(Math.round(starsUsd)),
      pUsd: fmt(propUsd),
    });

    [fsDirect, fsAff, fsProp].forEach(setRangeFill);
  }

  [fsDirect, fsAff, fsProp].forEach((el) => el?.addEventListener("input", calcFounderProfit));

  /* =======================================================
     6) GLOBAL LANGUAGE ENGINE (6 Languages + RTL/LTR Flip)
  ======================================================= */
  function setLanguage(lang) {
    if (!SUPPORTED_LANGS.includes(lang)) lang = "fa";
    currentLang = lang;
    try {
      localStorage.setItem("tg_lang", lang);
    } catch (_) {}

    const d = t();
    document.documentElement.lang = lang;
    document.documentElement.dir = d.dir;
    if (d.metaTitle) document.title = d.metaTitle;

    // ترجمه تمام عناصر متنی و HTML
    $$("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n");
      if (d[k] !== undefined) el.textContent = d[k];
    });
    $$("[data-i18n-html]").forEach((el) => {
      const k = el.getAttribute("data-i18n-html");
      if (d[k] !== undefined) el.innerHTML = d[k];
    });

    // آپدیت وضعیت دکمه‌های تغییر زبان در هدر سایت و داخل مینی‌اپ
    $$("#topLangBar .lang-btn").forEach((b) =>
      b.classList.toggle("is-on", b.dataset.lang === lang)
    );
    $$("#appLangMenu .app-lang-item").forEach((b) =>
      b.classList.toggle("is-on", b.dataset.lang === lang)
    );
    const appLbl = $("#appLangLabel");
    if (appLbl) appLbl.textContent = `${d.flag} ${d.short}`;

    const wxInp = $("#wxInput");
    if (wxInp && d.wxPlaceholder) wxInp.placeholder = d.wxPlaceholder;
    const caInp = $("#caVal");
    if (caInp && d.caPlaceholder) caInp.placeholder = d.caPlaceholder;
    const rugInp = $("#rugInput");
    if (rugInp && d.rugPlaceholder) rugInp.placeholder = d.rugPlaceholder;
    const aicOut = $("#aicOut");
    if (aicOut && !aicOut.classList.contains("hidden")) renderAiBrief();

    // رندر مجدد تمام ماژول‌های زنده با زبان و جهت جدید
    syncGuardUi();
    syncProUi();
    calcGuard();
    calcConsistency();
    renderCustomAlerts();
    renderRadar();
    renderPropDeals();
    renderLocalizedAlerts();
    calcFounderProfit();
    if (storySheet && !storySheet.classList.contains("hidden")) {
      drawStoryCard();
    }
  }

  // کلیک روی نوار زبان بالای سایت
  $$("#topLangBar .lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      setLanguage(btn.dataset.lang);
    });
  });

  // منوی زبان داخل خود مینی‌اپ (گوشی)
  const appLangBtn = $("#appLangBtn");
  const appLangMenu = $("#appLangMenu");
  appLangBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    haptic("light");
    appLangMenu.classList.toggle("hidden");
  });

  $$("#appLangMenu .app-lang-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.stopPropagation();
      haptic("medium");
      appLangMenu.classList.add("hidden");
      setLanguage(item.dataset.lang);
    });
  });

  document.addEventListener("click", () => {
    appLangMenu?.classList.add("hidden");
  });

  $$(".nav .btn-tg").forEach((el) =>
    el.addEventListener("click", () => toast(t().toastDemoReady))
  );

  /* ---------- v10: زنجیرهٔ روز (streak) + کشیدن برای به‌روزرسانی ---------- */
  const STREAK_KEY = "tg_streak";

  function dayKey(d) {
    const x = d || new Date();
    return (
      x.getFullYear() +
      "-" +
      String(x.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(x.getDate()).padStart(2, "0")
    );
  }

  function readStreak() {
    try {
      const o = JSON.parse(localStorage.getItem(STREAK_KEY) || "{}");
      return { last: String(o.last || ""), days: Math.max(0, Number(o.days) || 0) };
    } catch (e) {
      return { last: "", days: 0 };
    }
  }

  /* یک بار در روز شمارنده را جلو می‌برد؛ اگر یک روز کامل غایب بوده، از ۱ شروع می‌شود */
  function bumpStreak() {
    const s = readStreak();
    const today = dayKey();
    if (s.last === today) return { days: s.days, isNew: false };
    const y = new Date();
    y.setDate(y.getDate() - 1);
    const days = s.last === dayKey(y) ? s.days + 1 : 1;
    try {
      localStorage.setItem(STREAK_KEY, JSON.stringify({ last: today, days }));
    } catch (e) {}
    return { days, isNew: true };
  }

  function renderStreak(info) {
    const chip = $("#streakChip");
    const num = $("#streakDays");
    if (!chip || !num) return;
    if (!info || !info.days) {
      chip.classList.add("hidden");
      return;
    }
    num.textContent = String(info.days);
    chip.classList.remove("hidden");
    if (info.isNew && info.days >= 2) {
      const d = t();
      const msg = info.days % 7 === 0 ? d.streakMilestone : d.streakToast;
      appToast(String(msg || "").replace("{n}", String(info.days)));
    }
  }

  let refreshInFlight = false;

  /* به‌روزرسانی واقعی: هردو منبع زنده + نشانگر و محو شدن ردیف‌های قدیمی */
  async function refreshAll(showToast) {
    if (refreshInFlight) return false;
    refreshInFlight = true;
    const rows = $("#radarList");
    const bar = $("#ptrBar");
    const txt = $("#ptrTxt");
    if (rows) rows.classList.add("is-refreshing");
    if (bar) {
      bar.classList.add("is-busy");
      if (txt) txt.textContent = t().ptrRefreshing;
    }
    haptic("light");
    try {
      await Promise.all([fetchLiveMarket(), fetchLiveWhales()]);
    } catch (e) {}
    refreshInFlight = false;
    if (rows) rows.classList.remove("is-refreshing");
    if (bar) {
      bar.classList.remove("is-busy", "is-on", "is-ready");
      if (txt) txt.textContent = t().ptrPull;
    }
    if (showToast) {
      const live = marketState && marketState.live;
      appToast(live ? t().ptrDone : t().ptrOffline);
    }
    return true;
  }

  function initPullToRefresh() {
    const scroller = $(".screen-body");
    const bar = $("#ptrBar");
    const txt = $("#ptrTxt");
    if (!scroller || !bar) return;
    const THRESHOLD = 68;
    let startY = 0;
    let pulling = false;
    let dist = 0;

    const reset = () => {
      pulling = false;
      dist = 0;
      bar.classList.remove("is-on", "is-ready");
      if (txt) txt.textContent = t().ptrPull;
    };

    scroller.addEventListener(
      "touchstart",
      (e) => {
        if (refreshInFlight) return;
        if (scroller.scrollTop > 0) return;
        const ts = e.touches && e.touches[0];
        if (!ts) return;
        startY = ts.clientY;
        pulling = true;
        dist = 0;
      },
      { passive: true }
    );

    scroller.addEventListener(
      "touchmove",
      (e) => {
        if (!pulling || refreshInFlight) return;
        const ts = e.touches && e.touches[0];
        if (!ts) return;
        dist = ts.clientY - startY;
        if (dist <= 0) {
          reset();
          return;
        }
        if (scroller.scrollTop > 0) return;
        const ready = dist >= THRESHOLD;
        bar.classList.add("is-on");
        bar.classList.toggle("is-ready", ready);
        if (txt) txt.textContent = ready ? t().ptrRelease : t().ptrPull;
        if (dist > 8 && e.cancelable) e.preventDefault();
      },
      { passive: false }
    );

    const finish = () => {
      if (!pulling) return;
      const ready = dist >= THRESHOLD;
      if (ready) {
        refreshAll(true);
      }
      reset();
    };
    scroller.addEventListener("touchend", finish, { passive: true });
    scroller.addEventListener("touchcancel", reset, { passive: true });

    // برای تست و دسترسی برنامه‌ای (بدون ژست لمسی)
    window.TG_PULL = {
      trigger: () => refreshAll(true),
      state: () => ({ busy: refreshInFlight, dist, pulling })
    };
  }

  /* ---------- شرکا / لینک‌های همکاری (v11) ---------- */
  let partnersItems = [];
  let partnersDisclosure = "";

  function renderPartners() {
    const box = $("#partnersBox");
    const list = $("#partnersList");
    if (!box || !list) return;
    if (!partnersItems.length) {
      box.classList.add("hidden");
      list.innerHTML = "";
      return;
    }
    const d = t();
    list.innerHTML = "";
    partnersItems.forEach((pt) => {
      const url = String(pt.url || "");
      if (!/^https?:\/\//.test(url)) return;
      // لینک رهگیری واقعی: کلیک اول به ربات می‌رود، شمرده می‌شود، بعد به شریک
      const pid = String(pt.id || pt.slug || "").trim();
      const botUser = String((window.TG_CONFIG || {}).botUsername || "").replace(/^@/, "");
      const tracked = pid && botUser ? `https://t.me/${botUser}?start=p_${encodeURIComponent(pid)}` : url;
      const a = document.createElement("a");
      a.className = "partner-item";
      a.href = tracked;
      a.setAttribute("data-partner-url", url);
      a.target = "_blank";
      a.rel = "noopener noreferrer nofollow sponsored";
      const logo = document.createElement("span");
      logo.className = "partner-logo";
      logo.textContent = pt.emoji || "🤝";
      const meta = document.createElement("span");
      meta.className = "partner-meta";
      const name = document.createElement("b");
      name.textContent = String(pt.name || "");
      const note = document.createElement("small");
      note.textContent = String(pt.note || "");
      meta.append(name, note);
      a.append(logo, meta);
      if (pt.badge) {
        const badge = document.createElement("span");
        badge.className = "partner-badge";
        badge.textContent = String(pt.badge);
        a.append(badge);
      }
      a.addEventListener("click", () => {
        haptic("light");
        // داخل تلگرام، لینک در مرورگر داخلی باز شود (نه iframe اپ)
        try {
          const tg = window.Telegram && window.Telegram.WebApp;
          if (tg && tg.openLink) {
            tg.openLink(tracked);
            a.preventDefault && a.preventDefault();
          }
        } catch (e) {}
      });
      list.appendChild(a);
    });
    if (!list.children.length) {
      box.classList.add("hidden");
      return;
    }
    const note = document.createElement("p");
    note.className = "partners-note";
    note.textContent = String(partnersDisclosure || d.partnersNote || "");
    list.appendChild(note);
    box.classList.remove("hidden");
  }

  async function loadPartners() {
    try {
      const resp = await fetch("partners.json", { cache: "no-store" });
      if (!resp.ok) return;
      const data = await resp.json();
      const arr = (data && Array.isArray(data.partners)) ? data.partners : [];
      partnersItems = arr.filter((x) => x && x.name && x.url).slice(0, 6);
      partnersDisclosure = String((data && data.disclosure) || "");
      renderPartners();
    } catch (e) {}
  }

  // راه‌اندازی اولیه
  setLanguage(currentLang);
  hydrateMarketCache();
  fetchLiveMarket();
  renderStreak(bumpStreak());
  initPullToRefresh();
  maybeShowOnboard();
  fetchLiveWhales();
  loadPartners();
  setInterval(fetchLiveMarket, 22000);

  // وضعیت واقعی اشتراک/دعوت از فایلی که ربات می‌نویسد
  loadEntitlements();
  // بعد از برگشت از چت ربات (پرداخت/دعوت) دوباره چک می‌شود
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") loadEntitlements();
  });
  $$(".tab-btn").forEach((b) => {
    if (b.dataset.tab === "sub") b.addEventListener("click", loadEntitlements);
  });
})();
