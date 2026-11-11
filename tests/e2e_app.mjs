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

let PRO_USERS = {};   // نقشهٔ هش → { exp, ref } که ربات در docs/pro_users.json می‌نویسد

function stubFetch(url) {
  const u = String(url);
  const json = (obj) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(obj), text: () => Promise.resolve(JSON.stringify(obj)) });
  if (u.includes("metaAndAssetCtxs")) return json([{ universe: HL.universe }, HL.ctxs]);
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
  if (u.includes("dexscreener")) return json({ pairs: [{ chainId: "ethereum", priceUsd: "0.0000123", liquidity: { usd: 320000 }, baseToken: { symbol: "PEPE", address: "0x6982508145454ce325ddbe47a25d4ec3d2311933" } }] });
  if (u.includes("gopluslabs")) return json({ result: { "0x6982508145454ce325ddbe47a25d4ec3d2311933": { is_honeypot: "0", buy_tax: "0", sell_tax: "0.05" } } });
  if (u.includes("pro_users.json")) return json({ updated: 0, users: PRO_USERS });
  if (u.includes("api.github.com")) return json({ workflow_runs: [{ name: "TradeGuard Bot", status: "in_progress", conclusion: null, created_at: new Date().toISOString(), html_url: "https://github.com/x" }] });
  return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}), text: () => Promise.resolve("") });
}

const ADMIN_ID = 777123456;
const hash = crypto.createHash("sha256").update("tg-admin:" + ADMIN_ID).digest("hex").slice(0, 16);

function boot({ userId = null, adminHashes = [hash], htmlFile = "app.html", proUsers = {} } = {}) {
  PRO_USERS = proUsers;
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push("jsdomError: " + (e && e.message)));
  vc.on("error", (...a) => errors.push("console.error: " + a.join(" ")));

  const html = read(htmlFile).replace(/<script[^>]*src="[^"]*"[^>]*><\/script>/g, "");
  const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc, url: "https://example.com/" + htmlFile });
  const w = dom.window;

  Object.defineProperty(w, "crypto", { value: crypto.webcrypto, configurable: true });
  w.fetch = (u, i) => stubFetch(u, i);
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

  w.eval(`window.TG_CONFIG = { generatedAt: "t", repo: "rmanm19/tradeguard-bot", botUsername: "TradeGuard1_bot", adminHashes: ${JSON.stringify(adminHashes)} };`);
  for (const f of ["i18n.js", "static_api.js", "app.js", "app_tg.js", "admin.js"]) {
    try { w.eval(read(f)); } catch (e) { errors.push(`eval ${f}: ${e.stack}`); }
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

console.log("\n" + "─".repeat(50));
if (fails) { console.log(`❌ ${fails} سنجه شکست خورد`); process.exit(1); }
console.log("✅ کل مینی‌اپ و صفحه معرفی بدون خطا اجرا شد");
process.exit(0);
