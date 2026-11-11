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

  function renderRadar() {
    const radarList = $("#radarList");
    if (!radarList) return;
    const d = t();
    const xrayBox = $("#whaleXrayBox");
    if (xrayBox) xrayBox.classList.toggle("hidden", radarMode !== "whales");

    if (radarMode === "whales") {
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

    const list = radarMode === "extremes" ? marketState.top_extremes : marketState.majors;
    radarList.innerHTML = "";

    list.forEach((c, i) => {
      const locked = !isPro && i >= PRO_UNLOCK_INDEX;
      const row = document.createElement("div");
      row.className = "row" + (locked ? " locked" : "");
      const sign = c.rate_8h > 0 ? "+" : "";
      const rateClass = Math.abs(c.rate_8h) >= 0.02 ? "up" : "";
      const subInfo = c.oi_m ? `OI $${fmt(c.oi_m, 1, 1)}M` : `$${c.price}`;

      row.innerHTML = `
        <div class="row-sym"><b>$${c.sym}</b><small>${subInfo}</small></div>
        <div class="row-rate ${rateClass}">
          <b>${sign}${fmt(c.rate_8h, 2, 3)}%</b><small>${fmt(c.apr, 0, 0)}% ${d.aprLabel}</small>
        </div>
        <div>${sparkFromSeed(c.sym, c.rate_8h, c.chg_24h || 0)}</div>
        <div class="row-tag">${tagFor(c)}</div>`;
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

    renderOppCard();
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
      }
    } catch (_) {}
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

  $$("#radarModeSeg .rm-btn").forEach((btn) => {
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

    $("#subIdle")?.classList.toggle("hidden", isPro);
    $("#subActive")?.classList.toggle("hidden", !isPro);

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

  /* ---------- وضعیت واقعی اشتراک (منبع: pro_users.json که ربات می‌نویسد) ---------- */
  let proExpiryDate = "";

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
      const entry = (data && data.users && data.users[key]) || null;
      if (!entry) return;
      const now = Math.floor(Date.now() / 1000);
      inviteCount = Math.max(0, Number(entry.ref) || 0);
      const exp = Number(entry.exp) || 0;
      if (exp > now) {
        proExpiryDate = new Date(exp * 1000).toLocaleDateString();
        setPro(true);
      }
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

  // راه‌اندازی اولیه
  setLanguage(currentLang);
  fetchLiveMarket();
  fetchLiveWhales();
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
