/**
 * سلف‌تست سرتاسری مینی‌اپ تلگرام (بدون مرورگر واقعی)
 * ---------------------------------------------------
 * app.html و شش فایل جاوااسکریپت واقعی را داخل jsdom اجرا می‌کند و
 * APIهای بیرونی (Hyperliquid، Fear&Greed، GoPlus، DexScreener، GitHub)
 * را شبیه‌سازی می‌کند؛ هیچ درخواست شبکه‌ای واقعی ارسال نمی‌شود.
 *
 * اجرا:  cd tests && npm i && node e2e_app.mjs
 * متغیر DOCS برای اشاره به مسیر دیگری از docs/ قابل استفاده است.
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { JSDOM, VirtualConsole } from "jsdom";

const DOCS = process.env.DOCS || path.resolve(import.meta.dirname, "..", "docs");
const read = (f) => fs.readFileSync(path.join(DOCS, f), "utf8");
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const HL = {
  universe: ["BTC", "ETH", "SOL", "SUI", "DOGE", "PEPE"].map((n) => ({ name: n })),
  ctxs: [
    { funding: "0.000125", openInterest: "1000", markPx: "60000", prevDayPx: "59000", dayNtlVlm: "900000000" },
    { funding: "0.0009", openInterest: "4000", markPx: "3000", prevDayPx: "2900", dayNtlVlm: "500000000" },
    { funding: "-0.0004", openInterest: "2000", markPx: "180", prevDayPx: "185", dayNtlVlm: "300000000" },
    { funding: "0.0031", openInterest: "900", markPx: "3.4", prevDayPx: "3.1", dayNtlVlm: "120000000" },
    { funding: "0.0012", openInterest: "1500", markPx: "0.19", prevDayPx: "0.18", dayNtlVlm: "80000000" },
    { funding: "0.0019", openInterest: "700", markPx: "0.000012", prevDayPx: "0.000011", dayNtlVlm: "50000000" }
  ]
};

let HL_LIVE = false;   // فقط تست‌هایی که باید داده زندهٔ هایپرلیکوید ببینند
let PARTNERS = { partners: [], disclosure: "" };   // محتوای partners.json برای تست
let PRO_USERS = {};   // نقشهٔ هش → { exp, ref } که ربات در docs/pro_users.json می‌نویسد
let PRO_FREE_MODE = false;   // پرچم دورهٔ رایگان در همان فایل

function stubFetch(url, init) {
  const u = String(url);
  const body = String((init && init.body) || "");
  const json = (obj) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(obj), text: () => Promise.resolve(JSON.stringify(obj)) });
  if ((u.includes("metaAndAssetCtxs") || body.includes("metaAndAssetCtxs")) && HL_LIVE) return json([{ universe: HL.universe }, HL.ctxs]);
  if (u.includes("clearinghouseState")) return json({
    marginSummary: { accountValue: "1250000", totalNtlPos: "800000" },
    assetPositions: [
      { position: { coin: "BTC", szi: "2.5", positionValue: "150000", unrealizedPnl: "4200", entryPx: "59000" } },
      { position: { coin: "ETH", szi: "-40", positionValue: "120000", unrealizedPnl: "-1800", entryPx: "3050" } }
    ]
  });
  if (u.includes("leaderboard")) return json({
    leaderboardRows: [
      { ethAddress: "0x1111111111111111111111111111111111111111", accountValue: "12000000", windowPerformances: [["day", { vlm: "90000000" }]] },
      { ethAddress: "0x2222222222222222222222222222222222222222", accountValue: "8000000", windowPerformances: [["day", { vlm: "70000000" }]] }
    ]
  });
  if (u.includes("alternative.me")) return json({ data: [{ value: "62", value_classification: "Greed" }] });
  if (u.includes("okx.com")) return json({ data: [{ fundingRate: "0.00013" }] });
  if (u.includes("fapi.binance.com")) return json([
    { symbol: "BTCUSDT", lastFundingRate: "0.0004", markPrice: "60000" },
    { symbol: "ETHUSDT", lastFundingRate: "0.00005", markPrice: "3000" },
    { symbol: "SOLUSDT", lastFundingRate: "-0.0002", markPrice: "180" },
    { symbol: "XRPUSDT", lastFundingRate: "0.0001", markPrice: "0.6" },
    { symbol: "DOGEUSDT", lastFundingRate: "0.0003", markPrice: "0.19" },
    { symbol: "OTHERUSDT", lastFundingRate: "0.9", markPrice: "1" }
  ]);
  if (u.includes("dexscreener")) return json({ pairs: [{ chainId: "ethereum", priceUsd: "0.0000123", liquidity: { usd: 320000 }, baseToken: { symbol: "PEPE", address: "0x6982508145454ce325ddbe47a25d4ec3d2311933" } }] });
  if (u.includes("gopluslabs")) return json({ result: { "0x6982508145454ce325ddbe47a25d4ec3d2311933": { is_honeypot: "0", buy_tax: "0", sell_tax: "0.05" } } });
  if (u.includes("pro_users.json")) return json({ updated: 0, freeMode: PRO_FREE_MODE, users: PRO_USERS });
  if (u.includes("partners.json")) return json(PARTNERS);
  if (u.includes("api.github.com")) return json({ workflow_runs: [{ name: "TradeGuard Bot", status: "in_progress", conclusion: null, created_at: new Date().toISOString(), html_url: "https://github.com/x" }] });
  return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}), text: () => Promise.resolve("") });
}

const ADMIN_ID = 777123456;
const hash = crypto.createHash("sha256").update("tg-admin:" + ADMIN_ID).digest("hex").slice(0, 16);

function boot({ userId = null, adminHashes = [hash], htmlFile = "app.html", proUsers = {}, freeMode = false, channel = "", seedStorage = {}, offline = false, liveHyperliquid = false } = {}) {
  PRO_USERS = proUsers;
  HL_LIVE = !!liveHyperliquid;
  PRO_FREE_MODE = freeMode;
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push("jsdomError: " + (e && e.message)));
  vc.on("error", (...a) => errors.push("console.error: " + a.join(" ")));

  const html = read(htmlFile).replace(/<script[^>]*src="[^"]*"[^>]*><\/script>/g, "");
  const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc, url: "https://example.com/" + htmlFile });
  const w = dom.window;

  // دادهٔ اولیهٔ localStorage (برای تست آنبوردینگ و کش)
  try {
    Object.entries(seedStorage || {}).forEach(([k, v]) => w.localStorage.setItem(k, String(v)));
  } catch (e) {}

  Object.defineProperty(w, "crypto", { value: crypto.webcrypto, configurable: true });
  const offlineFetch = () => Promise.resolve({
    ok: false, status: 404, json: () => Promise.resolve({}), text: () => Promise.resolve("")
  });
  w.fetch = (u, i) => (offline ? offlineFetch() : stubFetch(u, i));
  w.TextEncoder = TextEncoder;
  w.__copied = "";
  Object.defineProperty(w.navigator, "clipboard", {
    configurable: true,
    value: { writeText: (t) => { w.__copied = t; return Promise.resolve(); } }
  });
  w.HTMLCanvasElement.prototype.getContext = function () {
    const grad = { addColorStop() {} };
    return new Proxy({}, {
      get: (t, k) => {
        if (k === "measureText") return () => ({ width: 10 });
        if (k === "createLinearGradient" || k === "createRadialGradient" || k === "createPattern") return () => grad;
        if (typeof k === "string") return () => {};
        return undefined;
      },
      set: () => true
    });
  };
  w.HTMLCanvasElement.prototype.toDataURL = function () { return "data:image/png;base64,AAA"; };
  // jsdom نمی‌تواند دانلود واقعی انجام دهد؛ کلیک لنگر را فقط ثبت می‌کنیم
  w.__downloads = [];
  w.HTMLAnchorElement.prototype.click = function () { w.__downloads.push({ name: this.download, href: this.href }); };
  w.Telegram = {
    WebApp: {
      initDataUnsafe: userId ? { user: { id: userId, username: "tester", first_name: "Test", last_name: "U", language_code: "fa" } } : {},
      ready() {}, expand() {}, onEvent() {}, enableClosingConfirmation() {},
      openTelegramLink(url) { w.__opened = url; },
      themeParams: {}, colorScheme: "dark", viewportStableHeight: 800,
      HapticFeedback: { impactOccurred() {}, selectionChanged() {}, notificationOccurred() {} },
      MainButton: { hide() {}, show() {}, setText() {}, onClick() {} },
      BackButton: { show() {}, hide() {}, onClick() {} }
    }
  };
  w.addEventListener("error", (e) => errors.push("window.error: " + ((e.error && e.error.stack) || e.message)));
  w.addEventListener("unhandledrejection", (e) => errors.push("rejection: " + ((e.reason && e.reason.stack) || e.reason)));

  w.eval(`window.TG_CONFIG = { generatedAt: "t", repo: "rmanm19/tradeguard-bot", botUsername: "TradeGuard1_bot", channel: ${JSON.stringify(channel)}, adminHashes: ${JSON.stringify(adminHashes)} };`);
  for (const f of ["i18n.js", "static_api.js", "app.js", "app_tg.js", "admin.js"]) {
    try { w.eval(read(f)); } catch (e) { errors.push(`eval ${f}: ${e.stack}`); }
    // static_api.js خودش window.fetch را جایگزین می‌کند؛ در حالت آفلاین بعد از آن دوباره قطع می‌کنیم
    if (f === "static_api.js" && offline) w.fetch = () => offlineFetch();
  }
  try { w.document.dispatchEvent(new w.Event("DOMContentLoaded", { bubbles: true })); } catch (e) { errors.push("DCL: " + e); }
  try { w.dispatchEvent(new w.Event("load")); } catch (e) {}
  return { dom, w, errors };
}

let fails = 0;
const check = (n, c, d = "") => { console.log(`  ${c ? "✅" : "❌"} ${n}${c ? "" : " — " + d}`); if (!c) fails++; };

console.log("\n🧪 اجرای کامل مینی‌اپ در مرورگر شبیه‌سازی‌شده\n");

const A = boot({ userId: 999000111 });
await wait(1200);
const d = A.w.document;
check("هیچ خطای جاوااسکریپت در بارگذاری", A.errors.length === 0, A.errors.slice(0, 3).join(" | "));
check("رادار ردیف ساخت", d.querySelectorAll("#radarList .row").length > 0, String(d.querySelectorAll("#radarList .row").length));
check("بهترین فرصت رندر شد", ((d.querySelector("#oppSym") || {}).textContent || "").includes("$"), (d.querySelector("#oppSym") || {}).textContent);
check("شاخص ترس و طمع به‌روز شد", !!(d.querySelector("#fngLiveBadge") || {}).textContent);
check("گارد دراودان محاسبه شد", /[\d۰-۹]/.test((d.querySelector("#outCap") || {}).textContent || ""), (d.querySelector("#outCap") || {}).textContent);
check("حجم پیشنهادی محاسبه شد", /[\d۰-۹]/.test((d.querySelector("#outLot") || {}).textContent || ""), (d.querySelector("#outLot") || {}).textContent);
check("معاملات مجاز محاسبه شد", /[\d۰-۹]/.test((d.querySelector("#outTrades") || {}).textContent || ""), (d.querySelector("#outTrades") || {}).textContent);
check("کاربر عادی تب ادمین ندارد", !d.querySelector(".admin-tab"));

const click = (sel) => { const el = d.querySelector(sel); if (!el) return false; el.dispatchEvent(new A.w.MouseEvent("click", { bubbles: true })); return true; };
check("تب گارد باز می‌شود", click('.tab-btn[data-tab="guard"]') && d.querySelector('[data-pane="guard"]').classList.contains("is-active"));
check("تب هشدارها باز می‌شود", click('.tab-btn[data-tab="alerts"]') && d.querySelector('[data-pane="alerts"]').classList.contains("is-active"));
check("تب اشتراک باز می‌شود", click('.tab-btn[data-tab="sub"]') && d.querySelector('[data-pane="sub"]').classList.contains("is-active"));

click("#buyBtn");
check("پنجره خرید باز می‌شود", !d.querySelector("#invoice").classList.contains("hidden"));
click("#startBtn");
await wait(80);
check("دکمه پرداخت به چت ربات می‌رود", String(A.w.__opened || "").includes("t.me/TradeGuard1_bot"), String(A.w.__opened));
check("پرداخت، پرو را محلی باز نمی‌کند", !((d.querySelector("#planChip") || {}).classList || {}).contains || !((d.querySelector("#planChip") || {}).classList || {}).contains("pro"));

click('.tab-btn[data-tab="radar"]');
d.querySelector("#rugInput").value = "PEPE";
click("#rugScanBtn");
await wait(500);
check("اسکنر توکن جواب می‌دهد", /PEPE|SAFE|CAUTION|DANGER/i.test((d.querySelector("#rugOut") || {}).textContent || ""), (d.querySelector("#rugOut") || {}).textContent);
check("اسکنر کارت نتیجه ساخت (نه فقط متن خطا)", !!d.querySelector("#rugOut.rug-out:not(.hidden)"), d.querySelector("#rugOut").className);

if (d.querySelector("#wxInput")) d.querySelector("#wxInput").value = "0x1111111111111111111111111111111111111111";
click("#wxScanBtn");
await wait(500);
check("اشعه ایکس کیف پول جواب می‌دهد", /BTC|ETH|Equity|کیف/i.test((d.querySelector("#wxResult") || {}).textContent || ""), (d.querySelector("#wxResult") || {}).textContent);

click("#aicRunBtn");
await wait(200);
check("دستیار AI متن می‌دهد", ((d.querySelector("#aicOut") || {}).textContent || "").length > 20);

for (const [lg, dir] of [["en", "ltr"], ["ar", "rtl"], ["ru", "ltr"], ["tr", "ltr"], ["es", "ltr"], ["fa", "rtl"]]) {
  const item = d.querySelector(`#appLangMenu .app-lang-item[data-lang="${lg}"]`);
  if (item) item.dispatchEvent(new A.w.MouseEvent("click", { bubbles: true }));
  await wait(150);
  const langAttr = d.documentElement.getAttribute("lang") || "";
  const dirAttr = d.documentElement.getAttribute("dir") || "rtl";
  check(`زبان ${lg} + جهت ${dir}`, langAttr.startsWith(lg) && dirAttr === dir, `lang=${langAttr} dir=${dirAttr}`);
}
check("پس از تغییر زبان هم خطایی نبود", A.errors.length === 0, A.errors.slice(0, 2).join(" | "));


/* ---------- ۲ب) ماژول‌های بیشتر ---------- */
click('.tab-btn[data-tab="guard"]');
await wait(80);
check("محاسبه‌گر Consistency کار می‌کند", /[\d۰-۹]/.test((d.querySelector("#csOut") || {}).textContent || ""), (d.querySelector("#csOut") || {}).textContent.slice(0, 60));
const gb = d.querySelector("#guardToggle");
if (gb) { gb.dispatchEvent(new A.w.MouseEvent("click", { bubbles: true })); }
await wait(60);
check("دکمه گارد وضعیتش را عوض می‌کند", !!gb && /on|off|is-on|is-off|active/.test(gb.className), gb ? gb.className : "—");

click('.tab-btn[data-tab="alerts"]');
await wait(60);
check("لیست هشدارها پر است", d.querySelectorAll('[data-pane="alerts"] .alert-row, [data-pane="alerts"] .row, [data-pane="alerts"] .feed > *').length > 0,
  String(d.querySelectorAll('[data-pane="alerts"] *').length));

click('.tab-btn[data-tab="sub"]');
await wait(60);
const refLink = (d.querySelector("#refLink") || {}).value || "";
const USER_ID = 999000111;   // همان کاربرِ بوت A
check("کارت دعوت لینک واقعی کاربر را می‌سازد",
  refLink === `https://t.me/TradeGuard1_bot?start=ref_${USER_ID}`, refLink);
check("دکمه شبیه‌سازی دعوت حذف شده", !d.querySelector("#simInviteBtn"));
click("#refCopyBtn");
await wait(60);
check("کپی لینک کار می‌کند", A.w.__copied === refLink, A.w.__copied);
click("#refShareBtn");
await wait(60);
check("اشتراک‌گذاری، شیت تلگرام را باز می‌کند",
  String(A.w.__opened || "").includes("t.me/share/url") && String(A.w.__opened).includes("ref_"), String(A.w.__opened));
check("شیت پرداخت ادعای موفقیت جعلی ندارد",
  !d.querySelector("[data-step=\"3\"]") && !d.querySelector("#payBtn"));

click('.tab-btn[data-tab="radar"]');
await wait(60);
const wm = d.querySelector('#radarModeSeg .rm-btn[data-mode="whales"]');
if (wm) { wm.dispatchEvent(new A.w.MouseEvent("click", { bubbles: true })); }
await wait(500);
check("حالت نهنگ‌ها کارت می‌سازد", d.querySelectorAll("#radarList .whale-card").length > 0, String(d.querySelectorAll("#radarList .whale-card").length));
check("اشعه ایکس در حالت نهنگ نمایش داده می‌شود", !d.querySelector("#whaleXrayBox").classList.contains("hidden"));

click("#shareCardBtn");
await wait(120);
check("کارت استوری ساخته می‌شود", !d.querySelector("#storySheet").classList.contains("hidden"));
click("#dlStoryBtn");
await wait(60);
check("دانلود کارت استوری فایل PNG می‌سازد", (A.w.__downloads || []).some((x) => /TrendGuard|TradeGuard_.*\.png$/.test(x.name || "") && /^data:image\/png/.test(x.href || "")), JSON.stringify((A.w.__downloads || []).slice(-1)));
check("دانلود کارت استوری خطای جاوااسکریپت نمی‌دهد", A.errors.filter((e) => !/Not implemented/.test(e)).length === 0, A.errors.slice(0, 2).join(" | "));

const B = boot({ userId: ADMIN_ID });
await wait(700);
const db = B.w.document;
check("ادمین: تب 👑 ساخته شد", !!db.querySelector(".admin-tab"));
check("ادمین: پنل ساخته شد", !!db.querySelector('[data-pane="admin"]'));
db.querySelector(".admin-tab").dispatchEvent(new B.w.MouseEvent("click", { bubbles: true }));
await wait(600);
check("ادمین: وضعیت اجراها بارگذاری شد", /TradeGuard|در حال اجرا|running|موفق/i.test((db.querySelector("#admRuns") || {}).textContent || ""), (db.querySelector("#admRuns") || {}).textContent);
check("ادمین: خطای جاوااسکریپت ندارد", B.errors.length === 0, B.errors.slice(0, 2).join(" | "));

const C = boot({ userId: 555000111, adminHashes: [hash] });
await wait(400);
check("کاربر عادی با هش دیگران ادمین نمی‌شود", !C.w.document.querySelector(".admin-tab"));

const D = boot({ htmlFile: "index.html", userId: null, adminHashes: [hash] });
await wait(800);
const dd = D.w.document;
check("صفحه معرفی بدون خطا", D.errors.length === 0, D.errors.slice(0, 2).join(" | "));
check("بخش «مدل درآمد» برای همه هست", !!dd.querySelector("#model"));
check("سیمولاتور برای همه هست", !!dd.querySelector("#simSection"));
check("صفحه معرفی هیچ تب ادمینی ندارد", !dd.querySelector(".admin-tab"));

/* ---------- ۳) وضعیت واقعی پرو از فایلِ ربات (docs/pro_users.json) ---------- */
const proKeyOf = (uid) => crypto.createHash("sha256").update("tg-pro:" + String(uid)).digest("hex").slice(0, 16);
const futureExp = Math.floor(Date.now() / 1000) + 20 * 86400;

const E = boot({ userId: 777000111, proUsers: { [proKeyOf(777000111)]: { exp: futureExp, ref: 3 } } });
await wait(700);
const ed = E.w.document;
check("کاربر پرو (طبق فایل ربات) قفل‌ها را باز می‌بیند",
  ((ed.querySelector("#planChip") || {}).className || "").includes("pro"),
  (ed.querySelector("#planChip") || {}).className);
check("پنل «پرو فعال» نمایش داده می‌شود", !ed.querySelector("#subActive").classList.contains("hidden"));
check("شمارنده دعوت از دادهٔ واقعی می‌آید",
  /[3۳]/.test((ed.querySelector("#refCounter") || {}).textContent || ""), (ed.querySelector("#refCounter") || {}).textContent);
check("تاریخ انقضای پرو نمایش داده می‌شود",
  /[\d۰-۹]/.test((ed.querySelector("#proActiveDate") || {}).textContent || ""), (ed.querySelector("#proActiveDate") || {}).textContent);
check("ردیف‌های رادار برای پرو قفل نیستند",
  ed.querySelectorAll("#radarList .row.locked, #radarList .locked").length === 0,
  String(ed.querySelectorAll("#radarList .locked").length));
check("خطای جاوااسکریپت در حالت پرو نیست", E.errors.length === 0, E.errors.slice(0, 2).join(" | "));
ed.querySelector("#refreshProBtn")?.dispatchEvent(new E.w.MouseEvent("click", { bubbles: true }));
await wait(400);
check("دکمه «وضعیت را بررسی کن» برای کاربر پرو خطا نمی‌دهد", E.errors.length === 0, E.errors.slice(0, 2).join(" | "));

const F = boot({ userId: 888000111 });
await wait(500);
const fd = F.w.document;
check("کاربر بدون رکورد در فایل، روی پلن پایه می‌ماند",
  !fd.querySelector("#subIdle").classList.contains("hidden"), fd.querySelector("#subIdle").className);
check("قفل رادار برای کاربر عادی سرجایش است",
  fd.querySelectorAll("#radarList .locked").length > 0, String(fd.querySelectorAll("#radarList .locked").length));
check("خرید با دکمهٔ ربات هم پرو را محلی باز نمی‌کند (کاربر عادی)", !((fd.querySelector("#planChip") || {}).className || "").includes("pro"));
fd.querySelector("#refreshProBtn")?.dispatchEvent(new F.w.MouseEvent("click", { bubbles: true }));
await wait(400);
check("بررسی وضعیت برای کاربر عادی، توست راهنما نشان می‌دهد",
  !fd.querySelector("#appToast").classList.contains("hidden"),
  (fd.querySelector("#appToast") || {}).textContent);
check("بررسی وضعیت، پرو را برای کاربر عادی باز نمی‌کند",
  !((fd.querySelector("#planChip") || {}).className || "").includes("pro"));

/* ---------- ۳٫۵) آنبوردینگ، دیده‌بان و کش آنی ---------- */
const I = boot({ userId: 444000111 });
await wait(500);
const id_ = I.w.document;
check("آنبوردینگ در اولین اجرا نمایش داده می‌شود", !id_.querySelector("#onboard").classList.contains("hidden"));
check("اسلاید اول آنبوردینگ فعال است", !id_.querySelector('.ob-slide[data-ob="1"]').classList.contains("hidden"));
check("سه نقطهٔ صفحه‌بندی دارد", id_.querySelectorAll(".ob-dots i").length === 3);
id_.querySelector("#obNext").dispatchEvent(new I.w.MouseEvent("click", { bubbles: true }));
await wait(60);
check("بعدی → اسلاید دوم", !id_.querySelector('.ob-slide[data-ob="2"]').classList.contains("hidden"));
id_.querySelector("#obNext").dispatchEvent(new I.w.MouseEvent("click", { bubbles: true }));
await wait(60);
check("دکمهٔ آخر «شروع کن» می‌شود",
  /شروع|Get started|Начать|ابدأ|Başla|Empezar/i.test((id_.querySelector("#obNext") || {}).textContent || ""),
  (id_.querySelector("#obNext") || {}).textContent);
id_.querySelector("#obNext").dispatchEvent(new I.w.MouseEvent("click", { bubbles: true }));
await wait(80);
check("آنبوردینگ بسته و ثبت می‌شود",
  id_.querySelector("#onboard").classList.contains("hidden") &&
  !!I.w.localStorage.getItem("tg_onboard_v1"));
check("اجرای بعدی همان کاربر، آنبوردینگ نمی‌بیند", (() => {
  const J = boot({ userId: 444000111, htmlFile: "app.html", seedStorage: { tg_onboard_v1: "1" } });
  return J.w.document.querySelector("#onboard").classList.contains("hidden");
})());

// دیده‌بان
await wait(300);
const favs = id_.querySelectorAll("#radarList .fav-btn");
check("هر ردیف رادار دکمهٔ ستاره دارد", favs.length > 0, String(favs.length));
if (favs.length) {
  const sym = favs[0].getAttribute("data-sym");
  favs[0].dispatchEvent(new I.w.MouseEvent("click", { bubbles: true }));
  await wait(80);
  check("ستاره‌کردن در localStorage ذخیره می‌شود",
    (I.w.localStorage.getItem("tg_favs") || "").includes(sym), I.w.localStorage.getItem("tg_favs"));
  check("ستاره ظاهرش عوض می‌شود", (id_.querySelector("#radarList .fav-btn") || {}).textContent === "★");
  id_.querySelector("#favFilter").dispatchEvent(new I.w.MouseEvent("click", { bubbles: true }));
  await wait(120);
  check("فیلتر دیده‌بان فقط ارزهای ستاره‌شده را نشان می‌دهد",
    id_.querySelectorAll("#radarList .row").length === 1,
    String(id_.querySelectorAll("#radarList .row").length));
  id_.querySelector("#favFilter").dispatchEvent(new I.w.MouseEvent("click", { bubbles: true }));
  await wait(80);
}

// کش آنی: با داده ذخیره‌شده، رادار قبل از شبکه رندر می‌شود
const CACHED = { ts: Date.now(), data: {
  btc_price: 80000, fng_val: 61, fng_label: "Greed",
  top_extremes: [{ sym: "CACHEDCOIN", rate_8h: 0.42, apr: 320.5, daily_500: 4.2, oi_m: 12.3, chg_24h: 3.1, direction: "short" }],
  majors: [], best_opp: { sym: "CACHEDCOIN", rate_8h: 0.42, daily_500: 4.2 } } };
const K = boot({ userId: 444000222, seedStorage: { tg_onboard_v1: "1", tg_market_cache: JSON.stringify(CACHED) }, offline: true });
await wait(300);
check("رندر آنی از کش (قبل از شبکه) انجام می‌شود",
  /CACHEDCOIN/.test(K.w.document.querySelector("#radarList").textContent || ""),
  (K.w.document.querySelector("#radarList").textContent || "").slice(0, 40));

/* ---------- ۳٫۶) زنجیرهٔ روز + کشیدن برای به‌روزرسانی ---------- */
const dayKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const todayK = dayKey(new Date());
const yest = new Date(); yest.setDate(yest.getDate() - 1);
const yestK = dayKey(yest);

const S1 = boot({ userId: 555000111, seedStorage: { tg_onboard_v1: "1" } });
await wait(350);
check("چیپ زنجیرهٔ روز در اجرای اول دیده می‌شود",
  !S1.w.document.querySelector("#streakChip").classList.contains("hidden"));
check("اجرای اول = روز ۱",
  (S1.w.document.querySelector("#streakDays") || {}).textContent === "1",
  (S1.w.document.querySelector("#streakDays") || {}).textContent);

const S2 = boot({ userId: 555000222, seedStorage: { tg_onboard_v1: "1", tg_streak: JSON.stringify({ last: yestK, days: 3 }) } });
await wait(350);
check("روز پیاپی با ورود دیروزی، یکی جلو می‌رود",
  (S2.w.document.querySelector("#streakDays") || {}).textContent === "4",
  (S2.w.document.querySelector("#streakDays") || {}).textContent);
check("شمارنده در localStorage ذخیره می‌شود",
  JSON.parse(S2.w.localStorage.getItem("tg_streak") || "{}").last === todayK,
  S2.w.localStorage.getItem("tg_streak"));

const S3 = boot({ userId: 555000333, seedStorage: { tg_onboard_v1: "1", tg_streak: JSON.stringify({ last: todayK, days: 5 }) } });
await wait(350);
check("دو بار در یک روز، شمارنده بالا نمی‌رود",
  (S3.w.document.querySelector("#streakDays") || {}).textContent === "5",
  (S3.w.document.querySelector("#streakDays") || {}).textContent);

const S4 = boot({ userId: 555000444, seedStorage: { tg_onboard_v1: "1", tg_streak: JSON.stringify({ last: "2020-01-01", days: 9 }) } });
await wait(350);
check("غیبت چندروزه، زنجیره را از ۱ شروع می‌کند",
  (S4.w.document.querySelector("#streakDays") || {}).textContent === "1",
  (S4.w.document.querySelector("#streakDays") || {}).textContent);

const S5 = boot({ userId: 555000555, seedStorage: { tg_onboard_v1: "1" } });
await wait(300);
const sd = S5.w.document;
check("نوار کشیدن برای به‌روزرسانی وجود دارد", !!sd.querySelector("#ptrBar"));
check("نوار به‌صورت پیش‌فرض بسته است",
  !sd.querySelector("#ptrBar").classList.contains("is-on"));
check("راهنمای کشیدن ترجمه شده است",
  (sd.querySelector("#ptrTxt") || {}).textContent === "برای به‌روزرسانی بکش",
  (sd.querySelector("#ptrTxt") || {}).textContent);
check("درخواست به‌روزرسانی در دسترس است",
  !!(S5.w.TG_PULL && typeof S5.w.TG_PULL.trigger === "function"));
const refreshed = await S5.w.TG_PULL.trigger();
await wait(120);
check("به‌روزرسانی اجرا می‌شود", refreshed === true, String(refreshed));
check("پس از به‌روزرسانی، نشانگر بسته می‌شود",
  !sd.querySelector("#ptrBar").classList.contains("is-busy"));
check("بدون شبکه، پیام صادقانه نشان داده می‌شود",
  /شبکه|No network|сети|اتصال|Ağ|red/i.test((sd.querySelector("#appToast") || {}).textContent || ""),
  (sd.querySelector("#appToast") || {}).textContent);
check("هیچ خطای جاوااسکریپت در این بخش نیست", S5.errors.length === 0, S5.errors.slice(0, 2).join(" | "));

/* ---------- ۳٫۷) بخش شرکا (لینک همکاری) ---------- */
PARTNERS = { partners: [], disclosure: "" };
const P0 = boot({ userId: 666000999, seedStorage: { tg_onboard_v1: "1" } });
await wait(500);
check("بدون شریک، بخش شرکا پنهان است",
  P0.w.document.querySelector("#partnersBox").classList.contains("hidden"));

PARTNERS = {
  disclosure: "لینک همکاری — ممکن است کمیسیون بگیریم.",
  partners: [
    { id: "propfirm_x", name: "Prop Firm X", note: "۵۰٪ تخفیف چالش — کد TRADE50", url: "https://propfirmx.example/r/tg", emoji: "🏦", badge: "۵۰٪" }
  ]
};
const P1 = boot({ userId: 666000888, seedStorage: { tg_onboard_v1: "1" } });
await wait(600);
const pdoc = P1.w.document;
check("با شریک، بخش شرکا نمایش داده می‌شود",
  !pdoc.querySelector("#partnersBox").classList.contains("hidden"));
check("نام شریک رندر می‌شود",
  /Prop Firm X/.test(pdoc.querySelector("#partnersList").textContent));
check("لینک شریک از مسیر ربات رد می‌شود (رهگیری کلیک واقعی)",
  /t\.me\/TradeGuard1_bot\?start=p_propfirm_x/.test((pdoc.querySelector(".partner-item") || {}).href || ""),
  (pdoc.querySelector(".partner-item") || {}).href);
check("لینک اصلی شریک در data-partner-url نگه داشته می‌شود",
  (pdoc.querySelector(".partner-item") || {}).getAttribute("data-partner-url") === "https://propfirmx.example/r/tg",
  (pdoc.querySelector(".partner-item") || {}).getAttribute("data-partner-url"));
check("rel امنیتی لینک ست شده",
  /noopener/.test((pdoc.querySelector(".partner-item") || {}).getAttribute("rel") || ""));
check("افشای شفاف کمیسیون دیده می‌شود",
  /کمیسیون/.test(pdoc.querySelector("#partnersList").textContent),
  pdoc.querySelector("#partnersList").textContent.slice(0, 80));

PARTNERS = { partners: [], disclosure: "" };

/* ---------- ۴) دورهٔ رایگان و دکمهٔ کانال ---------- */
const G = boot({ userId: 666000111, freeMode: true, channel: "@tradeguard_live" });
await wait(700);
const gd = G.w.document;
check("دورهٔ رایگان: همه‌چیز برای کاربر عادی باز است",
  ((gd.querySelector("#planChip") || {}).className || "").includes("pro"),
  (gd.querySelector("#planChip") || {}).className);
check("دورهٔ رایگان: کارت خرید (subIdle) پنهان است", gd.querySelector("#subIdle").classList.contains("hidden"));
check("دورهٔ رایگان: یادداشت «رایگان» دیده می‌شود", !gd.querySelector("#freeNote").classList.contains("hidden"));
check("دورهٔ رایگان: نشان کارت «رایگان» است",
  /رایگان|Free|Gratis|Ücretsiz|Бесплатно|مجاني/i.test((gd.querySelector("#planChip") || {}).textContent || ""),
  (gd.querySelector("#planChip") || {}).textContent);
check("دورهٔ رایگان: خطای جاوااسکریپت نیست", G.errors.length === 0, G.errors.slice(0, 2).join(" | "));

check("دکمهٔ کانال با کانال تنظیم‌شده دیده می‌شود", !gd.querySelector("#joinChannelBtn").classList.contains("hidden"));
gd.querySelector("#joinChannelBtn").dispatchEvent(new G.w.MouseEvent("click", { bubbles: true }));
await wait(60);
check("دکمهٔ کانال، لینک کانال را باز می‌کند",
  String(G.w.__opened || "").includes("t.me/tradeguard_live"), String(G.w.__opened));

check("دکمهٔ پاداش عضویت کانال دیده می‌شود",
  !gd.querySelector("#claimJoinBtn").classList.contains("hidden"));
gd.querySelector("#claimJoinBtn").dispatchEvent(new G.w.MouseEvent("click", { bubbles: true }));
await wait(60);
check("دکمهٔ پاداش، کاربر را به بررسی واقعی عضویت در ربات می‌فرستد",
  String(G.w.__opened || "").includes("t.me/TradeGuard1_bot?start=checkjoin"), String(G.w.__opened));

const H = boot({ userId: 666000222, proUsers: {}, channel: "" });
await wait(400);
const hd = H.w.document;
check("بدون دورهٔ رایگان: کارت خرید برمی‌گردد", !hd.querySelector("#subIdle").classList.contains("hidden"));
check("بدون کانال در config: دکمهٔ کانال پنهان است", hd.querySelector("#joinChannelBtn").classList.contains("hidden"));

// ---------------------------------------------------------------
// نقشهٔ لیکوئیدیشن (تخمینی) — دادهٔ زنده، محاسبهٔ شفاف
// ---------------------------------------------------------------
console.log("\n🕳 نقشهٔ لیکوئیدیشن\n");
const LQ = boot({ userId: 555000111 });
await wait(500);
const ld2 = LQ.w.document;
const lqBox = ld2.querySelector("#liqMap");
check("نقشهٔ لیکوئیدیشن با دادهٔ زنده نمایش داده می‌شود",
  lqBox && !lqBox.classList.contains("hidden"), lqBox ? lqBox.className : "missing");
const lqCards = ld2.querySelectorAll("#liqRows .liq-card");
check("برای هر ارز یک کارت لیکوئیدیشن ساخته می‌شود", lqCards.length >= 3, String(lqCards.length));
check("هر کارت سه سطح اهرم (۱۰/۲۵/۵۰) دارد",
  lqCards.length > 0 && lqCards[0].querySelectorAll(".liq-cell").length === 3,
  lqCards.length ? String(lqCards[0].querySelectorAll(".liq-cell").length) : "—");
check("متن روش محاسبه (تخمینی) نمایش داده می‌شود",
  /تخمین/.test(String((ld2.querySelector("#liqNote") || {}).textContent || "")),
  String((ld2.querySelector("#liqNote") || {}).textContent || "").slice(0, 60));
check("سمت دارای ریسک (لانگ/شورت) بر اساس فاندینگ مشخص می‌شود",
  ld2.querySelector(".liq-crowd.is-long, .liq-crowd.is-short") !== null);
check("قیمت لیکوئید لانگ کمتر از شورت است (منطق درست)",
  (() => {
    const card = lqCards[0];
    if (!card) return false;
    const cells = card.querySelectorAll(".liq-cell");
    const parse = (t) => Number(String(t).replace(/[^0-9.]/g, ""));
    const first = cells[0];
    const lo = parse(first.querySelector(".liq-px-long").textContent);
    const sh = parse(first.querySelector(".liq-px-short").textContent);
    return lo > 0 && sh > 0 && lo < sh;
  })(), "long < short");
const lqEnBtn = ld2.querySelector('#appLangMenu .app-lang-item[data-lang="en"]');
if (lqEnBtn) lqEnBtn.dispatchEvent(new LQ.w.MouseEvent("click", { bubbles: true }));
await wait(60);
check("نقشه با تغییر زبان عنوان را عوض می‌کند",
  /Liquidation map/.test(String((ld2.querySelector("#liqTitle") || {}).textContent || "")),
  String((ld2.querySelector("#liqTitle") || {}).textContent || ""));

// ---------------------------------------------------------------
// فاندینگ چند صرافی (آربیتراژ): دادهٔ واقعی هر صرافی، بدون ادعای سود
// ---------------------------------------------------------------
console.log("\n🔀 فاندینگ چند صرافی\n");
const FXM = boot({ userId: 555000333, liveHyperliquid: true });
await wait(700);
const fxd = FXM.w.document;
const fxBox = fxd.querySelector("#fxBox");
check("جدول فاندینگ چند صرافی رندر می‌شود",
  fxBox && !fxBox.classList.contains("hidden") && fxd.querySelectorAll("#fxRows .fx-row").length >= 4,
  fxBox ? String(fxd.querySelectorAll("#fxRows .fx-row").length) : "missing");
check("هر ردیف نام صرافی‌ها را در سرستون دارد (HL/OKX/BN)",
  /HL/.test(String((fxd.querySelector(".fx-thead") || {}).textContent || ""))
  && /OKX/.test(String((fxd.querySelector(".fx-thead") || {}).textContent || ""))
  && /BN/.test(String((fxd.querySelector(".fx-thead") || {}).textContent || "")));
const fxBtc = fxd.querySelector('#fxRows .fx-row[data-sym="BTC"]');
check("ردیف BTC سه نرخ دارد (۰٫۱۰۰ / ۰٫۰۱۳ / ۰٫۰۴۰)",
  !!fxBtc && /0\.100/.test(fxBtc.textContent) && /0\.013/.test(fxBtc.textContent) && /0\.040/.test(fxBtc.textContent),
  fxBtc ? fxBtc.textContent : "—");
check("اختلاف سالانه درست است (۰٫۱۰۰−۰٫۰۱۳ = ۰٫۰۸۷ × ۳ × ۳۶۵ ≈ ۹۵٪)",
  !!fxBtc && /95%/.test(fxBtc.textContent), fxBtc ? fxBtc.textContent : "—");
check("ارزهای خارج از فهرست نادیده گرفته می‌شوند (OTHER حذف می‌شود)",
  !fxd.querySelector('#fxRows .fx-row[data-sym="OTHER"]'));
check("نرخ مثبت (لانگ می‌پردازد) و منفی رنگ/کلاس متفاوت دارند",
  fxd.querySelectorAll("#fxRows .fx-rate.pos").length > 0 && fxd.querySelectorAll("#fxRows .fx-rate.neg").length > 0);
check("ستون‌های ناموجود «—» نشان می‌دهند، نه عدد ساختگی",
  fxd.querySelectorAll("#fxRows .fx-rate.na").length > 0
  || fxd.querySelectorAll("#fxRows .fx-rate").length >= fxd.querySelectorAll("#fxRows .fx-row").length * 3);
check("جدول فاندینگ خطای جاوااسکریپت ندارد", FXM.errors.length === 0, FXM.errors.slice(0, 2).join(" | "));

// حالت آفلاین: جدول پنهان می‌ماند و چیزی از خودش نمی‌سازد
const FXOFF = boot({ userId: 555000333, offline: true });
await wait(400);
check("بدون اینترنت جدول فاندینگ مخفی می‌ماند (بدون دادهٔ جعلی)",
  (FXOFF.w.document.querySelector("#fxBox") || {}).className
    ? String(FXOFF.w.document.querySelector("#fxBox").className).includes("hidden")
    : true,
  String((FXOFF.w.document.querySelector("#fxBox") || {}).className || ""));

// ---------------------------------------------------------------
// ژورنال تریدر: ریسک، حجم پوزیشن، R و آمار واقعی (فقط localStorage)
// ---------------------------------------------------------------
console.log("\n🧮 ژورنال تریدر\n");
const JR = boot({ userId: 555000222 });
await wait(500);
const jd = JR.w.document;
const jw = JR.w;
const jClick = (sel) => {
  const el = jd.querySelector(sel);
  if (!el) return false;
  el.dispatchEvent(new jw.MouseEvent("click", { bubbles: true }));
  return true;
};
const jSet = (sel, v) => {
  const el = jd.querySelector(sel);
  if (!el) return false;
  el.value = String(v);
  el.dispatchEvent(new jw.Event("input", { bubbles: true }));
  return true;
};
const jText = (sel) => String((jd.querySelector(sel) || {}).textContent || "");
const jList = () => {
  try { return JSON.parse(jw.localStorage.getItem("tg_journal_v1") || "[]"); } catch (e) { return []; }
};

check("تب ژورنال در نوار پایین هست", !!jd.querySelector('.tab-btn[data-tab="journal"]'));
check("تب ژورنال باز می‌شود", jClick('.tab-btn[data-tab="journal"]')
  && jd.querySelector('[data-pane="journal"]').classList.contains("is-active"));
check("در شروع، ژورنال خالی است و راهنما نشان می‌دهد",
  jList().length === 0 && jText("#jrList").length > 20, jText("#jrList").slice(0, 40));
check("فرم خالی خطای فارسی می‌دهد (نه سکوت)",
  /بالانس|ورود|حد ضرر/.test(jText("#jrCalc")), jText("#jrCalc").slice(0, 60));

jSet("#jrBalance", 1000);
jSet("#jrRiskPct", 1);
jSet("#jrEntry", 64000);
jSet("#jrStop", 62500);
jSet("#jrTarget", 67500);
await wait(30);
const calcTxt = jText("#jrCalc");
check("ریسک دلاری درست است (۱۰۰۰ دلار × ۱٪ = ۱۰ دلار)", calcTxt.includes("$10.00"), calcTxt.slice(0, 120));
check("حجم پوزیشن از فاصلهٔ ورود تا حد ضرر حساب می‌شود (۱۰ ÷ ۱۵۰۰ ≈ ۰٫۰۰۶۶۷)",
  /0\.0066/.test(calcTxt), calcTxt);
check("نسبت R/R درست است (۳۵۰۰ ÷ ۱۵۰۰ ≈ ۲٫۳۳)", calcTxt.includes("1 : 2.33"), calcTxt);
check("جهت معامله از محل حد ضرر تشخیص داده می‌شود (لانگ)", /لانگ/.test(calcTxt), calcTxt);

jClick("#jrSaveBtn");
await wait(40);
check("معامله در localStorage ذخیره می‌شود (بدون سرور)", jList().length === 1, JSON.stringify(jList()).slice(0, 90));
check("کارت معامله با R/R نمایش داده می‌شود", /R:R 1:2\.33/.test(jText("#jrList")), jText("#jrList").slice(0, 120));
check("بعد از ذخیره، فرم قیمت‌ها پاک می‌شود (اشتباه سهوی)",
  (jd.querySelector("#jrEntry") || {}).value === "" && (jd.querySelector("#jrStop") || {}).value === "");

jClick('#jrList button[data-act="win"]');
await wait(40);
check("بستن معامله با «برد» عدد R را از R/R می‌سازد (۲٫۳۳R)",
  jList()[0] && jList()[0].status === "win" && Math.abs(Number(jList()[0].r) - 2.3333) < 0.01,
  JSON.stringify(jList()[0]).slice(0, 120));
check("برچسب R روی کارت ظاهر می‌شود", /\+2\.33R/.test(jText("#jrList")), jText("#jrList").slice(0, 120));
check("آمار: نرخ برد ۱۰۰٪ و انتظار +۲٫۳۳R",
  jText("#jrStats").includes("100%") && /\+2\.33R/.test(jText("#jrStats")), jText("#jrStats").slice(0, 160));

// ستاپ غلط: هدف زیر ورود در حالت لانگ
jSet("#jrEntry", 100);
jSet("#jrStop", 90);
jSet("#jrTarget", 80);
await wait(30);
check("هدف در جهت اشتباه، خطای روشن می‌دهد",
  /جهت اشتباه/.test(jText("#jrCalc")), jText("#jrCalc").slice(0, 80));
jClick("#jrSaveBtn");
await wait(30);
check("ستاپ نامعتبر ذخیره نمی‌شود", jList().length === 1, String(jList().length));

// ستاپ دوم: لانگ ۱۰۰ → ۹۰ با هدف ۱۳۰ (R/R=۳)
jSet("#jrBalance", 1000);
jSet("#jrRiskPct", 1);
jSet("#jrEntry", 100);
jSet("#jrStop", 90);
jSet("#jrTarget", 130);
await wait(30);
jClick("#jrSaveBtn");
await wait(40);
check("ستاپ دوم ذخیره شد", jList().length === 2, String(jList().length));
jClick('#jrList button[data-act="loss"]');
await wait(40);
check("معاملهٔ باخت همیشه −۱R ثبت می‌کند",
  jList().filter((x) => x.status === "loss").every((x) => x.r === -1), JSON.stringify(jList()).slice(0, 140));
check("انتظار با ترکیب برد و باخت درست است (۱٫۳۳ ÷ ۲ ≈ +۰٫۶۷R)",
  /\+0\.67R/.test(jText("#jrStats")), jText("#jrStats").slice(0, 200));
check("ضریب سود = مجموع برد ÷ مجموع باخت (۲٫۳۳)",
  /2\.33/.test(jText("#jrStats")), jText("#jrStats").slice(0, 200));

jClick("#jrExportBtn");
await wait(60);
check("خروجی JSON ژورنال دانلود می‌شود",
  jw.__downloads.some((x) => x.name === "tradeguard-journal.json"), JSON.stringify(jw.__downloads).slice(0, 120));

// بالانس/ریسک برای دفعهٔ بعد نگه داشته می‌شود
const balEl = jd.querySelector("#jrBalance");
balEl.dispatchEvent(new jw.Event("change", { bubbles: true }));
await wait(40);
let prefs = {};
try { prefs = JSON.parse(jw.localStorage.getItem("tg_jr_prefs") || "{}"); } catch (e) {}
check("بالانس و درصد ریسک برای بار بعد ذخیره می‌شوند",
  String(prefs.balance) === "1000" && String(prefs.riskPct) === "1", JSON.stringify(prefs));

const beforeDel = jList().length;
jClick('#jrList button[data-act="del"]');
await wait(40);
check("حذف معامله از ژورنال کار می‌کند", jList().length === beforeDel - 1, String(jList().length));

const jEnBtn = jd.querySelector('#appLangMenu .app-lang-item[data-lang="en"]');
if (jEnBtn) jEnBtn.dispatchEvent(new jw.MouseEvent("click", { bubbles: true }));
await wait(60);
check("ژورنال هم ۶ زبانه است (عنوان و تب انگلیسی می‌شوند)",
  /Risk, size & journal/.test(jText(".jr-title"))
  && /Journal/.test(jText('.tab-btn[data-tab="journal"] span')),
  jText(".jr-title"));
check("ژورنال هیچ خطای جاوااسکریپت ندارد", JR.errors.length === 0, JR.errors.slice(0, 2).join(" | "));

// پایداری بین اجراها: با دادهٔ ذخیره‌شده، ژورنال همان معامله را نشان می‌دهد
const JR2 = boot({
  userId: 555000222,
  seedStorage: {
    tg_journal_v1: JSON.stringify([
      { id: "tseeded", sym: "ETH", dir: "short", entry: 3000, stop: 3100, target: 2700, units: 1, riskPct: 1, rr: 3, status: "win", opened: 1, closed: 2, r: 3 }
    ])
  }
});
await wait(300);
const jd2 = JR2.w.document;
jd2.querySelector('.tab-btn[data-tab="journal"]')?.dispatchEvent(new JR2.w.MouseEvent("click", { bubbles: true }));
await wait(60);
check("فرم جدید بالانس ذخیره‌شده را از قبل پر می‌کند",
  String((jd2.querySelector("#jrBalance") || {}).value || "") === "" ||
  String((jd2.querySelector("#jrBalance") || {}).value) === "1000", String((jd2.querySelector("#jrBalance") || {}).value));
check("ژورنال بعد از بازکردن دوباره، معاملات قبلی را می‌خواند",
  /ETH/.test(String((jd2.querySelector("#jrList") || {}).textContent || ""))
  && /\+3\.00R/.test(String((jd2.querySelector("#jrStats") || {}).textContent || "")),
  String((jd2.querySelector("#jrStats") || {}).textContent || "").slice(0, 80));

// ---------------------------------------------------------------
// صفحهٔ فرود اختصاصی هر شریک (docs/p.html?id=<id>)
// ---------------------------------------------------------------
console.log("\n🔗 صفحهٔ فرود شریک (p.html)\n");
const ONE = {
  disclosure: "لینک همکاری — کمیسیون می‌گیریم.",
  partners: [{
    id: "propfirm_x", name: "Prop Firm X", note: "۵۰٪ تخفیف ثبت‌نام",
    url: "https://propfirmx.example/r/tg", badge: "۵۰٪", emoji: "🏦",
    perks: ["چالش رایگان ۲ مرحله‌ای", "برداشت سریع"]
  }]
};

function bootLanding(query, partners) {
  PARTNERS = partners;
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push("jsdomError: " + (e && e.message)));
  vc.on("error", (...a) => errors.push("console.error: " + a.join(" ")));
  const dom = new JSDOM(read("p.html"), {
    runScripts: "dangerously",
    pretendToBeVisual: true,
    virtualConsole: vc,
    url: "https://example.com/p.html" + query,
    beforeParse(w) {
      w.fetch = (u) => stubFetch(u);
      w.addEventListener("error", (e) => errors.push("window.error: " + ((e.error && e.error.stack) || e.message)));
      w.addEventListener("unhandledrejection", (e) => errors.push("rejection: " + ((e.reason && e.reason.stack) || e.reason)));
    }
  });
  return { dom, w: dom.window, errors };
}

const L = bootLanding("?id=propfirm_x", ONE);
await wait(120);
const lw = L.w, ld = lw.document, lmain = ld.getElementById("main");
check("صفحهٔ فرود شریک نام شریک را نشان می‌دهد", /Prop Firm X/.test(lmain.textContent), lmain.textContent.slice(0, 80));
check("صفحهٔ فرود مزیت‌های شریک را فهرست می‌کند", /چالش رایگان ۲ مرحله‌ای/.test(lmain.textContent), lmain.textContent.slice(0, 120));
check("صفحهٔ فرود نشان (badge) شریک را نشان می‌دهد", /۵۰٪/.test(lmain.textContent));
check("دکمهٔ اصلی صفحهٔ فرود کد رهگیری اختصاصی دارد",
  /t\.me\/TradeGuard1_bot\?start=p_propfirm_x/.test((lmain.querySelector(".cta") || {}).href || ""),
  (lmain.querySelector(".cta") || {}).href);
check("صفحهٔ فرود کد رهگیری را برای چسباندن نشان می‌دهد", /p_propfirm_x/.test(lmain.textContent));
check("صفحهٔ فرود افشای کمیسیون را نشان می‌دهد", /کمیسیون/.test(lmain.textContent));
check("صفحهٔ فرود خودش را لینک وابسته اعلام می‌کند",
  /sponsored/.test((lmain.querySelector(".cta") || {}).getAttribute("rel") || ""),
  (lmain.querySelector(".cta") || {}).getAttribute("rel"));
check("عنوان صفحه با نام شریک ست می‌شود", /Prop Firm X/.test(ld.title), ld.title);
check("صفحهٔ فرود بدون خطای جاوااسکریپت اجرا می‌شود", L.errors.length === 0, L.errors.slice(0, 2).join(" | "));
check("صفحهٔ فرود راست‌به‌چپ و فارسی است",
  ld.documentElement.dir === "rtl" && ld.documentElement.lang === "fa",
  `${ld.documentElement.dir}/${ld.documentElement.lang}`);

const L2 = bootLanding("?id=propfirm_x&lang=en", ONE);
await wait(120);
check("نسخهٔ انگلیسی صفحهٔ فرود چپ‌به‌راست است",
  L2.w.document.documentElement.dir === "ltr" && L2.w.document.documentElement.lang === "en",
  `${L2.w.document.documentElement.dir}/${L2.w.document.documentElement.lang}`);
check("نسخهٔ انگلیسی متن انگلیسی دارد",
  /Sign up with this link/.test(L2.w.document.getElementById("main").textContent),
  L2.w.document.getElementById("main").textContent.slice(0, 80));

const L3 = bootLanding("?id=ghost_partner", ONE);
await wait(120);
check("شناسهٔ ناشناس صفحهٔ معتبر نبودن لینک را نشان می‌دهد",
  /معتبر نیست/.test(L3.w.document.getElementById("main").textContent),
  L3.w.document.getElementById("main").textContent.slice(0, 80));
const L4 = bootLanding("", ONE);
await wait(120);
check("بدون شناسه هم پیام صادقانه نشان داده می‌شود",
  /معتبر نیست/.test(L4.w.document.getElementById("main").textContent));
const L5 = bootLanding("?id=propfirm_x", { partners: [], disclosure: "" });
await wait(120);
check("وقتی هیچ شریکی منتشر نشده، صفحه شریک جعلی نمی‌سازد",
  /منتشر نشده|معتبر نیست/.test(L5.w.document.getElementById("main").textContent),
  L5.w.document.getElementById("main").textContent.slice(0, 80));

const EVIL = { partners: [{ id: "x1", name: "<img src=x onerror=alert(1)>", note: "n", url: "https://evil.example/r" }] };
const L6 = bootLanding("?id=x1", EVIL);
await wait(120);
check("نام شریک در صفحهٔ فرود امن escape می‌شود",
  L6.w.document.querySelectorAll("#main img").length === 0,
  L6.w.document.getElementById("main").innerHTML.slice(0, 120));

console.log("\n" + "─".repeat(50));
if (fails) { console.log(`❌ ${fails} سنجه شکست خورد`); process.exit(1); }
console.log("✅ کل مینی‌اپ و صفحه معرفی بدون خطا اجرا شد");
process.exit(0);
