# Outreach — بروکرها، صرافی‌ها، پراپ‌فرم‌ها و کانال‌های دنیا

> این فایل «کاری است که امشب آماده شده تا فقط Send بزنی». هر لینک یا آدرسی که اینجا آمده،
> صفحهٔ رسمی خودشان است. هر عددی که در پیام‌ها می‌آید، همان چیزی است که در
> `docs/api/stats.json` و `docs/api/radar.json` قابل بررسی است.
>
> **قاعدهٔ سخت:** هیچ پیامی به لیست خریداری‌شده، هیچ DM انبوه، هیچ «ممبر تضمینی» و هیچ
> عددی که خودمان نمی‌توانیم اثبات کنیم. اگر شریک خواست «سود تضمینی» بنویسیم، معامله را رد می‌کنیم.

---

## ۰) در یک نگاه: چه چیزی داریم که برای طرف مقابل ارزش دارد

| دارایی | برای صرافی/بروکر | برای کانال‌های دنیا |
|---|---|---|
| مینی‌اپ ۶ زبانه (fa/en/ru/ar/tr/es) | مخاطب جهانی، بدون هزینهٔ نصب | محتوای قابل اشتراک با لینک |
| رادار فاندینگ/OI روی دادهٔ عمومی | ترافیک معامله‌گران فیوچرز | پست‌های آماده و فورواردشدنی |
| ابزار ریسک/پراپ (لات، R/R، دراودان) | مخاطب پراپ (بالا-CPA) | محتوای آموزشی واقعی |
| صفحهٔ SEO هر نماد (`/s/<symbol>.html`) | ورودی ارگانیک | منبع قابل ارجاع |
| فید دادهٔ باز (`/api/radar.json`) | داده بدون کلید API | محتوای خودکار برای ربات‌ها |
| رهگیری واقعی قیف (کلیک → استارت → عضویت تأییدشده → پرو) | گزارش ماهانه با دلتا | — |

**چیزی که نمی‌فروشیم:** فالوور فیک، ترافیک تضمینی، رتبهٔ ساختگی، سیگنال با دقت اثبات‌نشده، دادهٔ شخصی.

---

## ۱) دسته‌بندی اهداف (به ترتیب اولویت)

### الف) صرافی‌ها — برنامهٔ Affiliate / Partner (رسمی)
| هدف | صفحهٔ رسمی | چه بخواهی |
|---|---|---|
| OKX | `https://www.okx.com/affiliates` | لینک/کد اختصاصی + پنل؛ درخواست «Broker/Partner» برای جایگاه در مینی‌اپ |
| Bybit | `https://affiliates.bybit.com` (و `https://www.bybit.com/en/affiliates`) | rev-share + account manager برای کمپین فارسی/عربی |
| Binance | `https://www.binance.com/en/affiliate` | توجه: حداقل‌ها سخت‌گیرند (۵۰۰ عضو کامیونیتی / ۵٬۰۰۰ دنبال‌کننده) — با اعداد واقعی اقدام کن، نه بزرگ‌نمایی |
| سایر (BingX، WhiteBIT، BYDFi، KuCoin، Gate، MEXC) | از فوتر سایت خودشان → Affiliate/Partners | همان قالب، بدون تغییر |

**چه چیزی در فرم بنویسیم (اعداد واقعی، امروز):**
- محصول: مینی‌اپ تلگرام، ۶ زبان، بدون نصب؛ رادار زنده + ابزار ریسک + هشدار.
- مخاطب: فارسی‌زبان فعلی، کانال انگلیسی برای بازار جهانی.
- کانال و آمار: از `docs/api/stats.json` (همان اعداد عمومی؛ هیچ ادعای اضافه).
- رهگیری: `?start=p_<id>` + postback آماده (`PARTNER_KIT_FA.md`).
- چیزی که پیشنهاد می‌دهیم: کارت/پروفایل شریک داخل اپ + صفحهٔ فرود اختصاصی + پست کانال با برچسب همکاری.

### ب) پراپ‌فرم‌ها — Partner/Affiliate
- FTMO · FundedNext · The 5%ers · FunderPro: از صفحهٔ اصلی → `Affiliates` / `Partners` / `Contact`.
- پیام کوتاه، چون تیم‌های کوچک‌ترند و سریع‌تر جواب می‌دهند.
- قلاب ما: **مخاطب پراپ** + ابزارهای دقیق (دراودان روزانه، consistency، حجم از ریسک) + ژورنال.
- قابل ارائه: `docs/business.html` + `PARTNER_KIT_FA.md` + گزارش ماهانه با دلتا (`/biz report`).

### ج) کانال‌های دنیا — Cross-promo (نه تبلیغ پولی)
- هدف: کانال‌های آموزشی/دادهٔ تریدری (فارسی، عربی، روسی، ترکی، اسپانیایی، انگلیسی)، نه کانال‌های «سیگنال VIP».
- پیشنهاد منصفانه: یک پست معرفی از ما در کانال شما، یک پست معرفی از شما در کانال ما؛ هر دو با برچسب.
- اگر پولی شد: فقط CPM/پست ثابت با تسویهٔ ساده — نه «تضمین عضو».
- پیدا کردن: جست‌وجوی تلگرام با کلیدواژه‌های هر زبان + کاتالوگ‌های عمومی (TGStat / Telemetr) با فیلتر موضوع «Crypto/Forex» و بررسی نسبت ویو به ممبر (نسبت غیرواقعی = رد).

### د) رسانه/دایرکتوری و جست‌وجو
- `sitemap.xml` را در Google Search Console ثبت کن (یک‌بار).
- برای ایندکس شدن `t.me/s/tradeguard1` کاری لازم نیست، ولی صفحه‌های `docs/s/*.html` ورودی اصلی‌اند.
- دایرکتوری‌های ربات/کانال تلگرام بیشترشان کیفیت پایین دارند؛ فقط آن‌هایی که رتبهٔ واقعی می‌دهند ارزش وقت دارند — قبل از ثبت، ترافیک خروجی‌شان را ببین.

---

## ۲) متن‌های آماده (کپی/پیست)

### ۲٫۱ ایمیل به صرافی (Affiliate/Partner) — انگلیسی
> **Subject:** Partner placement: a 6-language Telegram mini-app with live funding/OI data
>
> Hi team,
>
> I run TradeGuard, a Telegram mini-app for traders (FA/EN/RU/AR/TR/ES) with a live funding-rate
> and open-interest radar, a prop risk calculator, personal alerts and a trading journal. All market
> data comes from public exchange APIs; nothing is signaled or promised.
>
> Where a partnership could fit:
> - a partner card inside the app (labelled, commission disclosed, tracked link);
> - a dedicated landing page (`/p.html?id=<id>`) with a tracked CTA;
> - one sponsored post per day maximum in our channels, marked as a partnership.
>
> Everything is measurable on your side: click → bot start (`?start=p_<id>`) → verified channel join
> → active subscription. We can consume your S2S postback for KYC/FTD too.
>
> Public, no-login data to evaluate us: `https://rmanm19.github.io/tradeguard-bot/api/stats.json` and
> `…/api/radar.json`. Partner terms and tracking spec: `PARTNER_KIT_FA.md` (English sections inside).
>
> If this fits, tell me which program to apply to and I will complete it today.
>
> Best,
> — TradeGuard

### ۲٫۲ پیام به پراپ‌فرم — انگلیسی (کوتاه‌تر)
> Hi — I run TradeGuard, a free 6-language Telegram mini-app for prop traders: position size from
> risk, daily drawdown guard, consistency check, trade journal, plus a live funding radar.
> Your audience fits ours (people already paying for challenges), and we can measure a real funnel:
> click → bot start → channel join → active user.
>
> Would you be open to (a) an affiliate/partner application, or (b) a reciprocal content swap
> (one educational post each, both labelled)? I can send the media kit in one message.

### ۲٫۳ پیام به ادمین کانال — Cross-promo (فارسی)
> سلام 👋 من TradeGuard رو می‌سازم — یک مینی‌اپ تلگرام برای تریدرها: رادار فاندینگ/OI زنده،
> ماشین‌حساب ریسک و حجم پراپ، هشدار شخصی و ژورنال. ۶ زبانه، بدون نصب، دادهٔ واقعی و بدون وعدهٔ سود.
>
> پیشنهاد ساده و منصفانه: یک پست معرفی از ما در کانال شما، یک پست معرفی از شما در کانال ما
> (هر دو با برچسب «همکاری»). اگر ترجیح می‌دی پولی باشه، تعرفهٔ پست ثابت رو بفرست — ولی
> «تضمین عضو» نمی‌خرم و نمی‌فروشم.
>
> برای بررسی: `tradeguard1` (کانال) · `TradeGuard1_bot` (ربات) · صفحهٔ داده: `…/api/radar.json`

### ۲٫۴ پیام به ادمین کانال — Cross-promo (انگلیسی)
> Hi — I build TradeGuard, a 6-language Telegram mini-app for traders: live funding/OI radar,
> prop risk calculator, personal alerts and a journal. Real market data, no profit promises.
>
> Fair swap: one intro post in your channel, one in mine, both clearly labelled. If you prefer a
> paid slot, send your flat rate — I don't buy or sell "guaranteed members".
>
> Evaluate us: `/api/stats.json` + `/api/radar.json` (public, no key).

### ۲٫۵ پیام پیگیری (۴ روز بعد، کوتاه)
> Following up once: is a partner placement or a reciprocal post something you'd consider this
> quarter? If the answer is no, a one-line "not now" is genuinely useful — I'll close the loop.

> **چرا یک پیگیری، نه پنج:** اسپم نکردن بخشی از برند است؛ کسی که از ما اسپم می‌گیرد،
> به کانال ما هم اعتماد نمی‌کند.

---

## ۳) آهنگ اجرا (Cadence) — امشب و ۱۰ روز آینده

| روز | کار | خروجی |
|---|---|---|
| شب ۱ | ۱۰ درخواست Affiliate (۳ صرافی بزرگ + ۳ پراپ + ۴ کانال) | فرم‌ها پر شده، draft ایمیل‌ها آماده |
| روز ۲ | پیام‌های Cross-promo (فارسی + انگلیسی) | ۱۰ DM ارسال‌شده |
| روز ۵ | پیگیری اول (تک‌پیام) | ۱۰ پیگیری |
| روز ۷ | بررسی اعداد: `/biz` + `/top` + `stats.json` | یک صفحه گزارش |
| روز ۱۰ | تصمیم: چه چیزی کار کرد؟ جایگاه اول را به کی می‌دهیم؟ | یک تصمیم، نه ده حدس |

**KPI واقعی (نه «تعداد ممبر»):**
1. نرخ پاسخ (پاسخ ÷ ارسال) — هدف سالم: ۱۵–۲۵٪ برای پراپ، ۵–۱۰٪ برای صرافی بزرگ.
2. کلیک → استارت (`p_<id>`) — از `/biz`.
3. استارت → عضویت تأییدشده — از `/biz`.
4. ۹۰ روز ماندگاری کاربر — این همان عددی است که بروکرها بر اساسش منابع را رتبه می‌دهند.

---

## ۴) چیزهایی که باید همراه پیام باشد

- صفحهٔ رسانه‌ای: `docs/press.html` (اعداد زنده + boilerplate ۶ زبانه + بنرها).
- B2B: `docs/business.html` · کیت شریک: `PARTNER_KIT_FA.md` · فید: `docs/api/index.html`.
- اگر خواستند نمونهٔ ترافیک: فقط `stats.json` و `/biz`؛ هیچ اسکرین‌شات ساختگی.

---

## ۵) قالب ردیابی (در Notion/Linear هم ساخته شد)

| هدف | دسته | لینک/آدرس | تاریخ تماس | وضعیت | پاسخ | مرحلهٔ بعد |
|---|---|---|---|---|---|---|
| OKX | صرافی | okx.com/affiliates | | draft | | فرم را پر کن |
| Bybit | صرافی | affiliates.bybit.com | | draft | | فرم را پر کن |
| Binance | صرافی | binance.com/en/affiliate | | draft | | شرایط را چک کن |
| FTMO | پراپ | ftmo.com → Affiliates | | draft | | ایمیل |
| FundedNext | پراپ | fundednext.com → Partners | | draft | | ایمیل |
| The 5%ers | پراپ | the5ers.com → Affiliates | | draft | | ایمیل |
| کانال FA #۱ | کانال | (از جست‌وجوی تلگرام) | | draft | | DM |
| کانال EN #۱ | کانال | (از جست‌وجوی تلگرام) | | draft | | DM |
| کانال AR #۱ | کانال | (از جست‌وجوی تلگرام) | | draft | | DM |
| کانال RU #۱ | کانال | (از جست‌وجوی تلگرام) | | draft | | DM |

> نام کانال‌ها را با جست‌وجوی تلگرام خودت پر کن؛ من عمداً اسم کانال حدس نمی‌زنم
> (اسم اشتباه = پیام به آدم اشتباه).

---

## ۶) پاسخ‌های آماده به سؤال‌های رایج

**«چند ممبر دارید؟»** → عدد واقعی `stats.json` + کانال؛ اگر کم است، همین را می‌گوییم و روی
کیفیت ترافیک و ابزار تمرکز می‌کنیم.

**«CPA چند می‌دهید؟»** → ما طرف تقاضا هستیم؛ CPA را شما تعیین می‌کنید. ما قیف واقعی می‌دهیم و
postback شما را مصرف می‌کنیم.

**«می‌شود بنویسید سود تضمینی / بدون ریسک؟»** → نه. این جمله هم غیرقانونی است در بسیاری از
حوزه‌ها، هم اعتماد مخاطب را می‌سوزاند. جایگزین: «ابزار تصمیم» + آموزش.

**«می‌شود جایگاه انحصاری بگیرم؟»** → بله، با قرارداد: انحصار = نبود رقیب هم‌دسته در آن جایگاه
برای مدت مشخص، و افشای کمیسیون همان‌جا می‌ماند.
