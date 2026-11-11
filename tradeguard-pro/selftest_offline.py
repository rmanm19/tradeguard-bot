#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سلف‌تست آفلاین TradeGuard
=========================
بدون اینترنت، بدون توکن واقعی، بدون پکیج خارجی.

    python selftest_offline.py

تمام تماس‌های تلگرام و صرافی‌ها با نسخه تقلبی جایگزین می‌شوند تا فقط
«سلامت منطق ربات» بررسی شود: ساخت دیتابیس، ثبت کاربر، منوها، اشتراک پرو،
دعوت دوستان، پرداخت Stars، دستورات /radar /scan /consistency /admin.

اگر این تست سبز شد، یعنی هر خطایی در GitHub Actions به توکن/شبکه مربوط است،
نه به کد.
"""

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# توکن تقلبی — هیچ تماس واقعی زده نمی‌شود
os.environ["BOT_TOKEN"] = "123456789:AAtest-token-not-real-000000000000"
os.environ.pop("TG_DB_KEY", None)
os.environ.pop("ADMIN_USER_ID", None)
os.environ.pop("AI_API_KEY", None)
os.environ.pop("PRO_STATUS_PUSH", None)   # تست هرگز به ریپو پوش نمی‌کند
_STATUS_TMP = Path(tempfile.mkdtemp()) / "pro_users.json"
os.environ["PRO_STATUS_PATH"] = str(_STATUS_TMP)

import bot  # noqa: E402  (بعد از تنظیم متغیرها import می‌شود)

FAILS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} {detail}")
        FAILS.append(name)


# ── جایگزینی شبکه ────────────────────────────────────────────────
SENT = []          # (api_method, payload)
DOWNLOADS = []     # (chat_id, filename)


def fake_http_json(url, method="GET", payload=None, headers=None, timeout=12.0):
    api = url.rsplit("/", 1)[-1] if "api.telegram.org" in url else ""
    if api:
        SENT.append((api, payload or {}))
        if api == "getMe":
            return {"ok": True, "result": {"id": 987654321, "username": "TradeGuardTestBot", "is_bot": True}}
        if api == "getUpdates":
            return {"ok": True, "result": []}
        if api == "getChat":
            return {"ok": True, "result": {"id": -100123, "type": "channel", "title": "Test"}}
        return {"ok": True, "result": {"message_id": len(SENT)}}
    # صرافی‌ها / AI — داده‌ی نمونه برمی‌گردانیم
    if "hyperliquid" in url:
        return [{"universe": [{"name": "BTC"}, {"name": "ETH"}]},
                [{"funding": "0.000125", "openInterest": "1000", "markPx": "60000"},
                 {"funding": "0.0008", "openInterest": "5000", "markPx": "3000"}]]
    if "okx.com" in url:
        return {"data": [{"fundingRate": "0.0005"}]}
    if "dexscreener" in url:
        return {"pairs": [{"chainId": "ethereum", "priceUsd": "0.000012",
                           "liquidity": {"usd": 250000},
                           "baseToken": {"symbol": "PEPE", "address": "0x6982508145454ce325ddbe47a25d4ec3d2311933"}}]}
    if "gopluslabs" in url:
        return {"result": {"0x6982": {"is_honeypot": "0", "buy_tax": "0", "sell_tax": "0.05"}}}
    if "alternative.me" in url:
        return {"data": [{"value": "63", "value_classification": "Greed"}]}
    return {}


def fake_send_document(chat_id, file_path, filename, caption=""):
    DOWNLOADS.append((chat_id, filename))
    return {"ok": True}


bot.http_json = fake_http_json
bot.tg_send_document = fake_send_document

# دیتابیس و .env موقت تا فایل‌های واقعی ربات دست نخورند
tmpdir = tempfile.mkdtemp(prefix="tgtest-")
bot.DB_PATH = Path(tmpdir) / "tradeguard.db"
bot.ENV_PATH = Path(tmpdir) / ".env"

ADMIN = 555000111
USER = 777000222
FRIEND = 888000333


def msg(text: str, uid: int = USER, lang: str = "fa") -> dict:
    return {
        "message_id": 1,
        "date": 0,
        "chat": {"id": uid, "type": "private"},
        "from": {"id": uid, "is_bot": False, "first_name": "Test", "language_code": lang},
        "text": text,
    }


def last_text() -> str:
    for api, payload in reversed(SENT):
        if api in ("sendMessage", "sendDocument", "editMessageText"):
            return str(payload.get("text") or payload.get("caption") or "")
    return ""


def count(api: str) -> int:
    return sum(1 for a, _ in SENT if a == api)


print("\n🧪 TradeGuard — سلف‌تست آفلاین\n")

print("۱) دیتابیس")
bot.init_db()
check("init_db بدون خطا", bot.DB_PATH.exists(), str(bot.DB_PATH))

print("\n۲) /start و ثبت کاربر")
bot.handle_message(msg("/start"))
check("پیام خوش‌آمد ارسال شد", count("sendMessage") >= 1)
check("متن خوش‌آمد فارسی است", "تریدگارد" in last_text().upper() or "TradeGuard" in last_text() or "خوش" in last_text())
with bot._db_lock:
    import sqlite3
    with sqlite3.connect(bot.DB_PATH) as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
check("کاربر در دیتابیس ثبت شد", users == 1, f"users={users}")

print("\n۳) زبان‌ها")
for code in ("en", "ru", "ar", "tr", "es"):
    n = len(SENT)
    bot.handle_message(msg("/start", uid=900000 + hash(code) % 1000, lang=code))
    check(f"زبان {code}", len(SENT) > n)

bot.handle_message(msg("/lang"))
check("منوی زبان با دکمه‌ها", "inline_keyboard" in str(SENT[-1][1].get("reply_markup")))
bot.handle_callback({"id": "cb1", "from": {"id": USER}, "data": "setlang_en",
                     "message": {"message_id": 5, "chat": {"id": USER}}})
check("تغییر زبان به en", bot.get_user_lang(USER) == "en")

print("\n۴) دستورات تحلیلی")
bot.handle_message(msg("/radar"))
check("/radar پاسخ داد", "sendMessage" in [a for a, _ in SENT])
bot.handle_message(msg("/scan PEPE"))
check("/scan پاسخ داد", count("sendMessage") > 0)
bot.handle_message(msg("/consistency 1200 600 40"))
check("/consistency محاسبه کرد", "Consistency" in last_text())
bot.handle_message(msg("/lot 10000 1 20"))
check("/lot محاسبه کرد", "Lot" in last_text() or "lot" in last_text())
bot.handle_message(msg("/guard"))
check("/guard پاسخ داد", count("sendMessage") > 0)
bot.handle_message(msg("/ai"))
check("/ai پاسخ داد (حالت بدون کلید AI)", count("sendMessage") > 0)

print("\n۵) پرو، فایل‌ها و پرداخت Stars")
bot.handle_message(msg("/pro"))
check("اینویس Stars ساخته شد", count("sendInvoice") >= 1, f"sendInvoice={count('sendInvoice')}")

payment = {
    "message_id": 9,
    "date": 0,
    "chat": {"id": USER, "type": "private"},
    "from": {"id": USER, "is_bot": False, "first_name": "Test", "language_code": "en"},
    "successful_payment": {"currency": "XTR", "total_amount": bot.SUBSCRIPTION_STARS,
                           "telegram_payment_charge_id": "test-charge-123"},
}
bot.handle_message(payment)
pro, exp = bot.is_user_pro(USER)
check("اشتراک PRO فعال شد", pro, f"pro={pro}")

# همان پرداخت باید وضعیت را برای مینی‌اپ هم منتشر کند
_status = __import__("json").loads(_STATUS_TMP.read_text(encoding="utf-8")) if _STATUS_TMP.exists() else {}
_key = bot.pro_status_key(USER)
check("بعد از پرداخت، فایل وضعیت مینی‌اپ به‌روز شد",
      int((_status.get("users", {}).get(_key) or {}).get("exp", 0)) > 0,
      str(list(_status.get("users", {}).keys())))

n_dl = len(DOWNLOADS)
for data in ("download_ea", "download_pine"):
    bot.handle_callback({"id": f"cb-{data}", "from": {"id": USER}, "data": data,
                         "message": {"message_id": 6, "chat": {"id": USER}}})
check("ارسال فایل .mq5 و .pine از دکمه‌های شیشه‌ای", len(DOWNLOADS) - n_dl == 2,
      f"downloads={DOWNLOADS[n_dl:]}")
check("نام فایل‌ها درست است",
      sorted(n for _, n in DOWNLOADS[n_dl:]) == ["TradeGuard_PropProtector.mq5", "TradeGuard_SmartRadar.pine"],
      str(DOWNLOADS[n_dl:]))

bot.handle_message(payment)  # پرداخت تکراری
with bot._db_lock:
    with sqlite3.connect(bot.DB_PATH) as conn:
        pays = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
check("پرداخت تکراری دوبار ثبت نشد", pays == 1, f"payments={pays}")

print("\n۶) موتور دعوت (۳ دوست = پرو رایگان)")
for i, friend in enumerate((FRIEND, FRIEND + 1, FRIEND + 2), start=1):
    bot.handle_message(msg(f"/start ref_{USER}", uid=friend))
cnt, unlocked = bot.get_user_referral_stats(USER)
check("شمارش دعوت‌ها", cnt == 3, f"count={cnt}")
check("پرو رایگان فعال شد", unlocked)

print("\n۷) امنیت پنل مدیر")
# بدون ADMIN_USER_ID: هیچ‌کس (جز اولین کاربر) نباید به پنل و دستورات مدیریتی دسترسی داشته باشد
before = count("sendMessage")
bot.handle_message(msg("/admin", uid=ADMIN))
check("کاربر عادی از پنل منع شد", count("sendMessage") > before and bot.ADMIN_USER_ID == "", f"admin={bot.ADMIN_USER_ID!r}")
before = count("sendMessage")
bot.handle_message(msg("/broadcast سلام به همه", uid=ADMIN))
check("ارسال همگانی برای غیرادمین قفل است", "✅" not in last_text())

bot.handle_message(msg("/admin"))  # USER اولین کاربر ربات است
check("اولین کاربر پنل را می‌بیند", "پنل" in last_text() or count("sendMessage") > before)
bot.handle_callback({"id": "cb-claim", "from": {"id": USER}, "data": "claim_admin",
                     "message": {"message_id": 7, "chat": {"id": USER}}})
check("ادعای ادمینی اولین کاربر ثبت شد", bot.ADMIN_USER_ID == str(USER), f"admin={bot.ADMIN_USER_ID!r}")

before = count("sendMessage")
bot.handle_callback({"id": "cb-claim2", "from": {"id": 424242}, "data": "claim_admin",
                     "message": {"message_id": 8, "chat": {"id": 424242}}})
check("ادمین دوم نمی‌تواند ربات را تصاحب کند", bot.ADMIN_USER_ID == str(USER))

before = count("sendMessage")
bot.handle_message(msg("/price 500", uid=424242))
check("/price برای غیرادمین قفل است", bot.SUBSCRIPTION_STARS != 500)
bot.handle_message(msg("/price 500"))
check("/price برای ادمین کار می‌کند", bot.SUBSCRIPTION_STARS == 500, f"price={bot.SUBSCRIPTION_STARS}")
bot.handle_message(msg("/seturl https://tg.mydomain.ir/app"))
check("/seturl توسط ادمین ذخیره شد", bot.get_setting("MINI_APP_URL") == "https://tg.mydomain.ir/app")

print("\n۷ب) پایداری تنظیمات بعد از ری‌استارت (سناریوی GitHub Actions)")
bot.ADMIN_USER_ID = ""
bot.MINI_APP_URL = "https://example.com"
bot.SUBSCRIPTION_STARS = 300
bot.apply_persisted_settings()
check("ادمین از دیتابیس بازیابی شد", bot.ADMIN_USER_ID == str(USER), f"admin={bot.ADMIN_USER_ID!r}")
check("قیمت از دیتابیس بازیابی شد", bot.SUBSCRIPTION_STARS == 500, f"price={bot.SUBSCRIPTION_STARS}")
check("لینک مینی‌اپ از دیتابیس بازیابی شد", bot.MINI_APP_URL == "https://tg.mydomain.ir/app")

print("\n۷ج) تفکیک واقعی منوی ادمین از منوی کاربر")

def kb_buttons(payload):
    kb = (payload or {}).get("reply_markup") or {}
    return [b for row in (kb.get("inline_keyboard") or []) for b in row]

def cb(data, uid):
    bot.handle_callback({"id": f"cb-{data}", "from": {"id": uid}, "data": data,
                         "message": {"message_id": 11, "chat": {"id": uid}}})

# --- منوی کاربر عادی ---
SENT.clear()
bot.handle_message(msg("/start", uid=424242))
user_btns = kb_buttons(SENT[-1][1] if SENT else {})
check("منوی کاربر عادی هیچ دکمه‌ی مدیریتی ندارد",
      not any(b.get("callback_data") == "admin_panel" for b in user_btns),
      str([b.get("callback_data") for b in user_btns]))
check("منوی کاربر عادی دکمه خرید دارد",
      any(b.get("callback_data") == "buy_pro" for b in user_btns))

# --- منوی ادمین ---
SENT.clear()
bot.handle_message(msg("/start"))
admin_btns = kb_buttons(SENT[-1][1] if SENT else {})
check("منوی ادمین دکمه «پنل مدیریت مؤسس» دارد",
      any(b.get("callback_data") == "admin_panel" for b in admin_btns))

# --- /admin برای غیرادمین ---
SENT.clear()
bot.handle_message(msg("/admin", uid=424242))
check("/admin برای غیرادمین باز نمی‌شود", "پنل مدیریت مؤسس" not in last_text())
check("به غیرادمین پیام رد دسترسی داده شد", "دسترسی" in last_text() or "مؤسس" in last_text())

# --- کال‌بک‌های ادمین برای غیرادمین ---
SENT.clear()
cb("adm_stats", 424242)
check("کال‌بک adm_stats برای غیرادمین اجرا نمی‌شود", "آمار کاربران" not in last_text())
check("به غیرادمین هشدار کال‌بک داده شد", any(a == "answerCallbackQuery" for a, _ in SENT))

# --- پنل ادمین و همه زیرصفحه‌ها ---
SENT.clear()
bot.handle_message(msg("/admin"))
check("پنل مؤسس باز شد", "پنل مدیریت مؤسس" in last_text())
sections = [("adm_stats", "آمار کاربران"), ("adm_revenue", "درآمد و فروش"),
            ("adm_users", "۱۰ کاربر آخر"), ("adm_health", "سلامت سیستم"),
            ("adm_channel", "کانال ویترین"), ("adm_url", "لینک مینی‌اپ"),
            ("adm_help_grant", "گرنت پرو"), ("adm_help_broadcast", "پیام همگانی")]
for data_key, marker in sections:
    SENT.clear()
    cb(data_key, USER)
    check(f"بخش {data_key} → «{marker}»", marker in last_text(), last_text()[:60])

# --- بازگشت به نمای کاربر ---
SENT.clear()
cb("user_view", USER)
back_btns = kb_buttons(SENT[-1][1] if SENT else {})
check("نمای کاربر از پنل، منوی کاربر را برمی‌گرداند",
      any(b.get("callback_data") == "radar" for b in back_btns))

# --- /id ---
SENT.clear()
bot.handle_message(msg("/id"))
check("/id شناسه عددی را نشان می‌دهد", str(USER) in last_text())

print("\n۷د) خرید Stars و دعوت واقعی (مسیر مینی‌اپ)")
import hashlib as _hashlib

# --- deep-link خرید: /start pro باید فاکتور بفرستد ---
BUYER = USER + 9000          # کاربر تازه (کاربر قبلی در تست پرداخت، پرو شده است)
SENT.clear()
bot.handle_message(msg("/start pro", uid=BUYER))
invoices = [pl for api, pl in SENT if api == "sendInvoice"]
check("/start pro فاکتور Stars می‌فرستد", len(invoices) == 1, f"sendInvoice×{len(invoices)}")
if invoices:
    inv = invoices[0]
    check("فاکتور با ارز XTR است", inv.get("currency") == "XTR", str(inv.get("currency")))
    check("قیمت فاکتور با SUBSCRIPTION_STARS یکی است",
          (inv.get("prices") or [{}])[0].get("amount") == bot.SUBSCRIPTION_STARS)
    check("payload فاکتور قابل تشخیص است", str(inv.get("payload", "")).startswith("tradeguard_pro"))
    check("provider_token برای Stars خالی است", inv.get("provider_token") == "")

# --- alias های دیگر ---
for alias in ("/start buy", "/buy", "/pro"):
    SENT.clear()
    bot.handle_message(msg(alias, uid=BUYER))
    check(f"«{alias}» هم فاکتور می‌فرستد", any(api == "sendInvoice" for api, _ in SENT))

# کاربری که از قبل پرو است به‌جای فاکتور تکراری، وضعیتش را می‌بیند
SENT.clear()
bot.handle_message(msg("/start pro", uid=USER))
check("کاربر پرو فاکتور تکراری نمی‌گیرد، وضعیتش را می‌بیند",
      not any(api == "sendInvoice" for api, _ in SENT) and "PRO" in last_text().upper())

# --- deep-link دعوت: لینک واقعی با آیدی خودِ کاربر ---
SENT.clear()
bot.handle_message(msg("/start invite", uid=USER))
txt = last_text()
ref_link = bot.invite_link(USER)
check("لینک دعوت با آیدی کاربر ساخته می‌شود", ref_link.endswith(f"?start=ref_{USER}"), ref_link)
check("/start invite لینک اختصاصی را می‌فرستد", ref_link in txt or f"start=ref_{USER}" in txt, txt[:80])
check("پیام دعوت پیشرفت واقعی را نشان می‌دهد",
      ("0" in txt) and ("3" in txt) and any(
          w in txt.lower() for w in ("دعوت", "invite", "referral", "davet", "приглаш", "دعو", "invit")),
      txt[:80])
SENT.clear()
bot.handle_message(msg("/invite", uid=USER))
check("دستور /invite هم لینک می‌دهد", f"start=ref_{USER}" in last_text())

# --- /status وضعیت واقعی را می‌گوید ---
SENT.clear()
bot.handle_message(msg("/status", uid=USER))
_st = last_text()
check("/status وضعیت اشتراک را نشان می‌دهد",
      ("PRO" in _st.upper()) and any(ch.isdigit() for ch in _st), _st[:80])

# --- pre_checkout: فقط فاکتور خود ربات تأیید می‌شود ---
SENT.clear()
bot.process_update({"update_id": 1, "pre_checkout_query": {
    "id": "pcq-ok", "invoice_payload": f"tradeguard_pro_30d_{bot.SUBSCRIPTION_STARS}",
    "currency": "XTR", "total_amount": bot.SUBSCRIPTION_STARS}})
answers = [pl for api, pl in SENT if api == "answerPreCheckoutQuery"]
check("pre_checkout معتبر تأیید می‌شود", answers and answers[-1].get("ok") is True, str(answers[-1:]))
SENT.clear()
bot.process_update({"update_id": 2, "pre_checkout_query": {
    "id": "pcq-bad", "invoice_payload": "hacker_payload", "currency": "XTR", "total_amount": 1}})
answers = [pl for api, pl in SENT if api == "answerPreCheckoutQuery"]
check("pre_checkout جعلی رد می‌شود", answers and answers[-1].get("ok") is False, str(answers[-1:]))

# --- وضعیت پرو برای مینی‌اپ (فایل عمومی، بدون آیدی خام) ---
tmp_status = Path(tempfile.mkdtemp()) / "pro_users.json"
old_status_file = bot.PRO_STATUS_FILE
bot.PRO_STATUS_FILE = tmp_status
bot.publish_pro_status([USER])
raw = tmp_status.read_text(encoding="utf-8")
data = __import__("json").loads(raw)
key = _hashlib.sha256(("tg-pro:" + str(USER)).encode()).hexdigest()[:16]
check("فایل وضعیت پرو ساخته می‌شود", isinstance(data.get("users"), dict), raw[:60])
check("کلید کاربر هش است، نه آیدی خام", key in data["users"] and str(USER) not in raw)
check("کاربر پرو در فایل exp دارد", int((data["users"].get(key) or {}).get("exp", 0)) > 0)
check("کلید pro_status_key با الگوریتم مینی‌اپ یکی است", bot.pro_status_key(USER) == key)
# بعد از انقضا باید حذف شود
with bot._db_lock, __import__("sqlite3").connect(bot.DB_PATH) as _c:
    _c.execute("UPDATE users SET pro_until = 0, referrals_count = 0 WHERE user_id = ?", (USER,))
bot.publish_pro_status([USER])
data2 = __import__("json").loads(tmp_status.read_text(encoding="utf-8"))
check("کاربر بدون پرو و بدون دعوت از فایل حذف می‌شود", key not in data2.get("users", {}), str(data2)[:60])
bot.PRO_STATUS_FILE = old_status_file

print("\n۸) امنیت پیکربندی")
check("MINI_APP_URL تقلبی رد می‌شود", not bot.is_real_app_url("https://example.com"))
check("MINI_APP_URL واقعی قبول می‌شود", bot.is_real_app_url("https://tg.mydomain.ir/app"))
check("کیبورد زبان ۶ گزینه دارد",
      sum(len(r) for r in bot.language_keyboard()["inline_keyboard"]) == 6)
for lang in bot.SUPPORTED_LANGS:
    missing = [k for k in bot.BOT_STRINGS["en"] if k not in bot.BOT_STRINGS[lang]]
    check(f"ترجمه {lang} کامل است", not missing, str(missing[:5]))

print("\n" + "─" * 46)
if FAILS:
    print(f"❌ {len(FAILS)} تست شکست خورد: {', '.join(FAILS)}")
    sys.exit(1)
print(f"✅ همه تست‌ها سبز — {len(SENT)} تماس تلگرام، {len(DOWNLOADS)} فایل")
sys.exit(0)
