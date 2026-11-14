/* ============================================================================
   TradeGuard — selftest_docs.mjs
   سلف‌تست مینی‌اپ/اپ ادمین، بدون مرورگر و بدون پکیج خارجی:

       node docs/selftest_docs.mjs

   چه چیزی را تضمین می‌کند؟
     ۱) هر ۶ زبان کامل‌اند و همه‌ی کلیدهای مصرف‌شده در HTML/JS ترجمه دارند
     ۲) نقش ادمین فقط از روی initDataUnsafe + هش کانفیگ تعیین می‌شود
        (دروازه‌ی قابل جعل ?admin=1 کاملاً حذف شده باشد)
     ۳) خرید/دعوت دیگر به‌صورت محلی «پرو» باز نمی‌کند (پرداخت باید در ربات باشد)
     ۴) الگوریتم هش ادمین در JS و Python (workflow) یکی است
     ۵) ترتیب بارگذاری اسکریپت‌ها درست است (config → i18n → … → admin)
   ============================================================================ */

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const read = (f) => fs.readFileSync(path.join(ROOT, f), "utf8");

let fails = 0;
function check(name, cond, detail = "") {
  if (cond) {
    console.log(`  ✅ ${name}`);
  } else {
    console.log(`  ❌ ${name}${detail ? " — " + detail : ""}`);
    fails++;
  }
}

/** حذف کامنت‌ها برای این‌که توضیحات فارسی، تستِ «کدِ حذف‌شده» را قرمز نکنند */
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:\"'\\])\/\/[^\n]*/g, "$1");
}

function loadScript(file) {
  const win = {};
  const fn = new Function("window", "document", read(file) + "\n;return window;");
  fn(win, { documentElement: { setAttribute() {} }, body: { setAttribute() {} } });
  return win;
}

console.log("\n🧪 TradeGuard — سلف‌تست مینی‌اپ / اپ ادمین\n");

/* ── ۱) دیکشنری ───────────────────────────────────────────────── */
const win = loadScript("i18n.js");
const I18N = win.TG_I18N || {};
const LANGS = ["fa", "en", "ru", "ar", "tr", "es"];
check("چندزبانه بودن (۶ زبان)", LANGS.every((l) => I18N[l] && Object.keys(I18N[l]).length > 50),
  Object.keys(I18N).join(","));

const html = read("app.html");
const appJs = read("app.js");
const used = new Set();
for (const m of html.matchAll(/data-i18n(?:-html|-ph|-title|-aria)?="([^"]+)"/g)) used.add(m[1]);
for (const m of appJs.matchAll(/\bt\(\s*["']([a-zA-Z0-9_]+)["']/g)) used.add(m[1]);
const missing = [];
for (const l of LANGS) for (const k of used) if (!(k in I18N[l])) missing.push(`${l}:${k}`);
check(`ترجمه‌ی همه‌ی ${used.size} کلید در ۶ زبان`, missing.length === 0, missing.slice(0, 8).join(", "));
check("کلیدهای مسیر پرداخت/دعوت جدید", LANGS.every((l) => I18N[l].toastPayInBot && I18N[l].toastInviteViaBot));

/* ── ۲) دروازه‌ی ادمین ─────────────────────────────────────────── */
const appTg = read("app_tg.js");
const indexHtml = read("index.html");
const adminJs = read("admin.js");
const configJs = read("config.js");

const appTgCode = stripComments(appTg);
check("app_tg.js دیگر از ?admin=1 استفاده نمی‌کند",
  !/get\(\s*["']admin["']\s*\)/.test(appTgCode) && !/admin\s*===\s*["']1["']/.test(appTgCode));
check("index.html دیگر با ?admin=1 نقش نمی‌دهد",
  !/get\(\s*["']admin["']\s*\)/.test(indexHtml) && !/data-role"?\s*,\s*"admin"/.test(indexHtml));
check("admin.js از هش کانفیگ استفاده می‌کند",
  /TG_CONFIG/.test(adminJs) && /adminHashes/.test(adminJs) && /tg-admin:/.test(adminJs));
check("admin.js نقش را از initDataUnsafe می‌خواند", /initDataUnsafe/.test(adminJs));
check("admin.js هیچ المانی برای کاربر عادی نمی‌سازد (return پیش از buildTab)",
  /HASHES\.indexOf\(h\) === -1\) return/.test(adminJs));

const cfg = loadScript("config.js").TG_CONFIG || {};
check("config.js ساختار درست دارد",
  typeof cfg.repo === "string" && typeof cfg.botUsername === "string" && Array.isArray(cfg.adminHashes),
  JSON.stringify(cfg).slice(0, 80));

/* ── ۳) پرداخت واقعی، نه کلید جادویی ───────────────────────────── */
const appJsClean = stripComments(appJs);
/* setPro(true) فقط باید داخل loadEntitlements باشد؛ یعنی فقط از روی فایل
   وضعیتی که خودِ ربات می‌نویسد — نه از روی کلیک یا پارامتر URL. */
const entStart = appJsClean.indexOf("async function loadEntitlements");
const entEnd = entStart >= 0 ? appJsClean.indexOf("\n  }", entStart) : -1;
const entBody = entStart >= 0 && entEnd > entStart ? appJsClean.slice(entStart, entEnd) : "";
const setProTrue = appJsClean.match(/setPro\(\s*true\s*\)/g) || [];
const inEnt = (entBody.match(/setPro\(\s*true\s*\)/g) || []).length;
check("PRO فقط از فایل وضعیت ربات فعال می‌شود (نه با کلیک/پارامتر)",
  setProTrue.length === inEnt && inEnt >= 1 && inEnt <= 2 && /pro_users\.json/.test(entBody),
  `setPro(true)×${setProTrue.length} (داخل loadEntitlements: ${inEnt})`);
check("دورهٔ رایگان هم از همان فایل می‌آید (نه از URL)",
  /freeMode/.test(entBody) && /isFreeMode\s*=\s*!!\(data\s*&&\s*data\.freeMode\)/.test(appJsClean));
check("پارامتر URL هیچ‌وقت PRO را باز نمی‌کند",
  !/[?&](pro|pro_until|vip)=/i.test(appJsClean) && !/URLSearchParams[^;]*pro/i.test(appJsClean));
check("دکمه پرداخت به چت ربات وصل است", /openBotChat\("pro"\)/.test(appJsClean));
check("شبیه‌سازی دعوت حذف شد و لینک واقعی ref_ ساخته می‌شود",
  !/simInviteBtn/.test(html) && !/simInviteBtn/.test(appJsClean) && /start=ref_/.test(appJsClean));
check("کارت دعوت فقط پیام ربات را باز نمی‌کند (کپی/اشتراک واقعی دارد)",
  /refCopyBtn/.test(html) && /refShareBtn/.test(html) && /t\.me\/share\/url/.test(appJsClean));
check("شیت پرداخت ادعای موفقیت جعلی ندارد",
  !/payBtn/.test(html) && !/invSuccessTitle/.test(html) && !/setTimeout\(\s*\(\)\s*=>\s*showStep\(3\)/.test(appJsClean));

/* ── ۴) هم‌خوانی الگوریتم هش JS و Python ───────────────────────── */
const sampleId = "123456789";
const jsHash = crypto.createHash("sha256").update("tg-admin:" + sampleId).digest("hex").slice(0, 16);
let pyHash = "";
try {
  pyHash = execFileSync("python3", ["-c",
    `import hashlib;print(hashlib.sha256(("tg-admin:" + "${sampleId}").encode()).hexdigest()[:16])`
  ]).toString().trim();
} catch {
  pyHash = "(python3 در دسترس نیست)";
}
check("هش ادمین در JS و Python یکسان است", jsHash === pyHash, `js=${jsHash} py=${pyHash}`);
check("طول هش ۱۶ کاراکتر (مانند workflow)", jsHash.length === 16);

/* ── ۵) ترتیب بارگذاری و لینک‌ها ───────────────────────────────── */
const order = ["config.js", "i18n.js", "static_api.js", "app.js", "app_tg.js", "admin.js"]
  .map((f) => html.indexOf(`<script src="${f}"></script>`));
check("همه‌ی اسکریپت‌ها در app.html هستند", order.every((i) => i >= 0), order.join(","));
check("ترتیب اسکریپت‌ها درست است", order.every((v, i) => i === 0 || v > order[i - 1]), order.join(","));
check("admin.css لینک شده", /href="admin\.css"/.test(html));
check("admin.js پیش از بسته‌شدن body بارگذاری می‌شود",
  html.indexOf('<script src="admin.js"></script>') < html.lastIndexOf("</body>"));

/* ── ۶) کارت‌های ادمin در صفحه کاربر وجود ندارد ────────────────── */
check("HTML خام هیچ بخش ادمینی ندارد (کاملاً داینامیک)",
  !/data-pane="admin"/.test(html) && !/adm-banner/.test(html));

/* ── ۷) صفحهٔ فرود اختصاصی هر شریک (p.html) ──────────────────── */
const landing = read("p.html");
check("صفحهٔ فرود شریک وجود دارد و خودبسنده است",
  landing.includes("TradeGuard") && !/<script[^>]+src=/.test(landing));
check("صفحهٔ فرود لینک رهگیری p_<id> می‌سازد", landing.includes('"?start=p_"'));
check("صفحهٔ فرود از partners.json می‌خواند", /fetch\("partners\.json"/.test(landing));
check("صفحهٔ فرود با شناسهٔ ناشناس شریک جعلی نمی‌سازد",
  /showFallback/.test(landing) && /notReady/.test(landing));
check("صفحهٔ فرود ایندکس نمی‌شود و افشای کمیسیون دارد",
  /name="robots" content="noindex/.test(landing) && /کمیسیون/.test(landing));
/* ── ۸) صفحهٔ B2B و مستندات فید داده ──────────────────────────── */
const biz = read("business.html");
const apiDoc = read("api/index.html");
check("صفحهٔ B2B برای بروکرها وجود دارد و خودبسنده است",
  biz.includes("TradeGuard") && !/<script[^>]+src=/.test(biz));
check("B2B اعداد را از فید واقعی می‌خواند (نه عدد هاردکد)",
  /fetch\("api\/stats\.json"/.test(biz) && /data-k="users_total"/.test(biz));
check("B2B نسخهٔ انگلیسی هم دارد",
  biz.includes("For brokers & exchanges") && /dir = "ltr"/.test(biz));
check("B2B افشای همکاری و خطوط سرخ را می‌گوید",
  /افشای همکاری|Partnership disclosure/.test(biz) && /سود تضمینی|guaranteed profit/.test(biz));
check("B2B به کد رهگیری اختصاصی و تأیید واقعی عضویت اشاره می‌کند",
  /p_&lt;id&gt;/.test(biz) && /getChatMember/.test(biz));
check("B2B لینک استارت با کد قابل‌شمارش دارد",
  /start=biz_inquiry/.test(biz));
check("مستندات فید داده مسیرها و شکل JSON را می‌دهد",
  apiDoc.includes("api/radar.json") && apiDoc.includes("api/stats.json")
  && apiDoc.includes("funding_pct_8h") && apiDoc.includes("fear_greed"));
check("مستندات فید، بدون‌کلید بودن و سقف نرخ را شفاف می‌گوید",
  /No API key|no API key/.test(apiDoc) && /generated_at/.test(apiDoc) && /۳۰ ثانیه|30 seconds/.test(apiDoc));
check("مستندات فید ادعای سیگنال/سود نمی‌کند",
  /not a signal|نه سیگنال/.test(apiDoc) && !/guaranteed profit/i.test(apiDoc));
check("هر دو صفحه به هم لینک می‌دهند",
  /business\.html/.test(apiDoc) && /api\/index\.html/.test(biz));
const siteHtml = read("index.html");
check("فوتر صفحهٔ اصلی به B2B و API لینک می‌دهد",
  /href="business\.html"/.test(siteHtml) && /href="api\/index\.html"/.test(siteHtml));
check("بنرهای تبلیغاتی ساخته شده‌اند",
  ["ad_radar", "ad_risk", "ad_reward"].every((n) => fs.existsSync(path.join(ROOT, "assets", "ads", n + ".png"))));

console.log("\n" + "─".repeat(48));
if (fails) {
  console.log(`❌ ${fails} تست شکست خورد`);
  process.exit(1);
}
console.log("✅ همه تست‌های مینی‌اپ سبز");
