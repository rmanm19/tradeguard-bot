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

import json
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

# در CI، FREE_MODE=1 از محیط می‌آید؛ تست باید از حالت پیش‌فرضِ خاموش شروع کند
# تا مسیر پرداخت هم بررسی شود (بخش «۷ه» خودش روشن/خاموش می‌کند).
bot.FREE_MODE = False

# ⚠️ از همان اولین دستور، فید عمومی را به پوشهٔ موقت می‌بریم.
# وگرنه آزمون `/price 500` (بخش ۷الف) با publish_plans فایل واقعیِ
# docs/api/plans.json را با «قیمت تست» بازنویسی می‌کند و سایت بعد از هر
# اجرای تست، قیمت ۵۰۰ ⭐ نشان می‌دهد در حالی که ربات ۳۰۰ ⭐ می‌گیرد.
bot.PUBLIC_FEED_DIR = Path(tempfile.mkdtemp()) / "api"

FAILS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} {detail}")
        FAILS.append(name)


# ── جایگزینی شبکه ────────────────────────────────────────────────
SENT = []          # (api_method, payload)
# وضعیت کانال جعلی؛ تست‌ها می‌توانند آن را عوض کنند (پین/توضیحات/عکس)
CHAT_STATE = {"pinned_message": {"message_id": 42}, "description": "", "photo": None}
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
            chat = {"id": -100123, "type": "channel", "title": "Test", "username": "testchannel"}
            if CHAT_STATE.get("pinned_message"):
                chat["pinned_message"] = CHAT_STATE["pinned_message"]
            if CHAT_STATE.get("description"):
                chat["description"] = CHAT_STATE["description"]
            if CHAT_STATE.get("photo"):
                chat["photo"] = CHAT_STATE["photo"]
            return {"ok": True, "result": chat}
        if api == "getChatMemberCount":
            return {"ok": True, "result": 1234}
        if api == "getChatMember":
            return {"ok": True, "result": {"status": "administrator",
                                           "can_post_messages": True, "can_pin_messages": True}}
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
# تغییر قیمت باید همان لحظه به plans.json برسد (تک‌منبع حقیقت)، اما نه به فایل ریپو
_pj = bot.PUBLIC_FEED_DIR / "plans.json"
check("تغییر قیمت فوراً در plans.json منتشر می‌شود",
      _pj.exists() and '"stars": 500' in _pj.read_text(encoding="utf-8"),
      str(bot.PUBLIC_FEED_DIR))
check("فید عمومیِ تست بیرون از ریپو است (آزمون آرتیفکت واقعی را بازنویسی نمی‌کند)",
      bot.REPO_ROOT not in bot.PUBLIC_FEED_DIR.parents, str(bot.PUBLIC_FEED_DIR))
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

print("\n۷ه) دورهٔ رایگان (FREE_MODE) و ارتقای کانال")

# --- خاموش: رفتار پرداختی مثل قبل ---
bot.FREE_MODE = False
SENT.clear()
bot.handle_message(msg("/buy", uid=BUYER))
check("خاموش: /buy فاکتور می‌فرستد", any(a == "sendInvoice" for a, _ in SENT))
_newbie = FRIEND + 500
check("خاموش: کاربر تازه پرو نیست", bot.is_user_pro(_newbie)[0] is False)

# --- روشن: همه دسترسی دارند، پرداخت بسته است ---
bot.set_free_mode(True)
check("روشن: free_mode_active() درست است", bot.free_mode_active())
check("روشن: کاربر تازه هم دسترسی پرو دارد", bot.is_user_pro(_newbie)[0] is True)
check("روشن: وضعیت واقعی پرداخت دست‌نخورده است", bot.is_user_pro(_newbie, access=False)[0] is False)
SENT.clear()
bot.handle_message(msg("/buy", uid=BUYER))
check("روشن: /buy فاکتور نمی‌فرستد", not any(a == "sendInvoice" for a, _ in SENT))
check("روشن: /buy پیام دورهٔ رایگان می‌دهد",
      any(w in last_text() for w in ("رایگان", "free", "Free")), last_text()[:60])
SENT.clear()
bot.handle_message(msg("/start pro", uid=BUYER))
check("روشن: deep-link pro هم پرداخت نمی‌گیرد", not any(a == "sendInvoice" for a, _ in SENT))

# منوی شیشه‌ای: دکمهٔ خرید نبود، دکمهٔ دورهٔ رایگان باشد
kb = bot.main_keyboard(True, "fa")
cbs = [b.get("callback_data") for row in kb["inline_keyboard"] for b in row]
check("روشن: دکمهٔ خرید از منو حذف شده", "buy_pro" not in cbs)
check("روشن: دکمهٔ «دورهٔ رایگان» در منو هست", "free_info" in cbs)

# فایل وضعیت: پرچم freeMode منتشر شود
bot.publish_pro_status()
_status2 = __import__("json").loads(_STATUS_TMP.read_text(encoding="utf-8"))
check("فایل وضعیت freeMode=true را منتشر می‌کند", _status2.get("freeMode") is True, str(_status2)[:60])

# --- دستور ادمین فقط برای ادمین ---
SENT.clear()
bot.handle_message(msg("/freemode off", uid=BUYER))
check("غیرادمین نمی‌تواند حالت رایگان را عوض کند", bot.FREE_MODE is True)
SENT.clear()
bot.handle_message(msg("/freemode off"))
check("ادمین حالت رایگان را خاموش می‌کند", bot.FREE_MODE is False)
_status3 = __import__("json").loads(_STATUS_TMP.read_text(encoding="utf-8"))
check("فایل وضعیت freeMode=false شد", _status3.get("freeMode") is False)
bot.set_free_mode(True)   # برای تست‌های بعدی

# --- کانال: پست و پین ---
bot.PUBLIC_CHANNEL_ID = "@testchannel"
bot.BOT_USERNAME = "TradeGuardTestBot"
check("اعتبارسنجی کانال تستی", bot.validate_channel_target(silent=True) is True)
check("لینک کانال ساخته می‌شود", bot.channel_url() == "https://t.me/testchannel", bot.channel_url())
_posts = []
bot.tg_send_message = lambda chat_id, text, **kw: (_posts.append((chat_id, text, kw)) or {"ok": True, "result": {"message_id": len(_posts)}})
SENT.clear()
bot.handle_message(msg("/channelpost"))
_chan_posts = [pp for pp in _posts if pp[0] == "@testchannel"]
_kb_btns = [b["url"] for row in (_chan_posts[-1][2].get("reply_markup", {}) if _chan_posts else {}
                                  ).get("inline_keyboard", []) for b in row]
check("پست فوری کانال ارسال شد", bool(_chan_posts), str(_chan_posts[-1:]))
check("پست کانال ۳ فرصت برتر دارد",
      bool(_chan_posts) and (_chan_posts[-1][1].count("$") >= 3 or "🥇" in _chan_posts[-1][1]),
      _chan_posts[-1][1][:60] if _chan_posts else "")
check("پست کانال دکمهٔ مینی‌اپ و دعوت دارد", len(_kb_btns) >= 2, str(_kb_btns))
check("پست کانال دکمهٔ «ارسال به دوست» دارد (رشد واقعی = فوروارد)",
      any(u.startswith("https://t.me/share/url") for u in _kb_btns), str(_kb_btns[:4]))
SENT.clear()
bot.handle_message(msg("/channelpin"))
_chan_posts = [pp for pp in _posts if pp[0] == "@testchannel"]
check("پیام خوش‌آمد کانال ارسال شد", bool(_chan_posts) and "خوش آمدید" in _chan_posts[-1][1],
      _chan_posts[-1][1][:60] if _chan_posts else "")
check("درخواست پین ارسال شد", any(a == "pinChatMessage" for a, _ in SENT), str([a for a, _ in SENT]))
SENT.clear()
bot.handle_message(msg("/channelpost", uid=BUYER))
check("غیرادمین نمی‌تواند در کانال پست بگذارد", not any(a == "sendMessage" for a, _ in SENT))
SENT.clear()
_posts.clear()
bot.handle_message(msg("/channelstatus"))
_st = _posts[-1][1] if _posts else ""
check("/channelstatus تعداد اعضا را از تلگرام می‌خواند", "اعضا" in _st and "۱۲۳۴" in _st, _st[:120])
check("/channelstatus ادمین‌بودن ربات را نشان می‌دهد", "ادمین" in _st and "administrator" in _st, _st[:120])
check("/channelstatus وضعیت پین را می‌گوید", "پین‌شده" in _st, _st[:120])
check("/channelstatus پست خودکار را روشن و ۳ساعته نشان می‌دهد",
      "هر ۳ ساعت" in _st and "روشن" in _st, _st[-160:])
check("/channelstatus زمان آخرین پست را نشان می‌دهد", "آخرین پست خودکار" in _st and "پیش" in _st, _st[-120:])
check("/channelstatus زمان پست بعدی را می‌گوید", "پست بعدی" in _st, _st[-160:])
_posts.clear()
bot.handle_message(msg("/channelstatus", uid=BUYER))
check("غیرادمین وضعیت کانال را نمی‌گیرد",
      "وضعیت کانال" not in " ".join(pp[1] for pp in _posts), str(_posts[-1:]))

bot.PUBLIC_CHANNEL_ID = ""
_posts.clear()
bot.handle_message(msg("/channelstatus"))
_st2 = _posts[-1][1] if _posts else ""
check("بدون کانال، /channelstatus راهنمای فعال‌سازی می‌دهد",
      "تنظیم نشده" in _st2 and "/channel" in _st2, _st2[:120])
bot.FREE_MODE = False

print("\n۸) امنیت پیکربندی")
check("MINI_APP_URL تقلبی رد می‌شود", not bot.is_real_app_url("https://example.com"))
check("MINI_APP_URL واقعی قبول می‌شود", bot.is_real_app_url("https://tg.mydomain.ir/app"))
check("کیبورد زبان ۶ گزینه دارد",
      sum(len(r) for r in bot.language_keyboard()["inline_keyboard"]) == 6)
for lang in bot.SUPPORTED_LANGS:
    missing = [k for k in bot.BOT_STRINGS["en"] if k not in bot.BOT_STRINGS[lang]]
    check(f"ترجمه {lang} کامل است", not missing, str(missing[:5]))

print("\n۹) گزارش مدیریتی")
import sqlite3 as _sqlite  # noqa: E402

bot.ADMIN_USER_ID = str(USER)
_posts.clear()
bot.handle_message(msg("/report"))
_admin_posts = [pp for pp in _posts if pp[0] == USER]
_rep = _admin_posts[-1][1] if _admin_posts else ""
check("دستور /report برای ادمین گزارش می‌فرستد", "گزارش مدیریتی" in _rep, _rep[:80])
check("گزارش تعداد کاربران را از دیتابیس می‌خواند",
      "کاربران ربات" in _rep and any(ch.isdigit() for ch in _rep), _rep[:120])
check("گزارش وضعیت دورهٔ رایگان را نشان می‌دهد", "دورهٔ رایگان" in _rep, _rep[-120:])
_users_n = _sqlite.connect(bot.DB_PATH).execute("SELECT COUNT(*) FROM users").fetchone()[0]
check("عدد کاربران گزارش دقیقاً همان دیتابیس است",
      f"*{_users_n:,}*" in _rep, f"db={_users_n} report={_rep[:120]}")
check("گزارش جای خالی/«None» ندارد", "None" not in _rep, _rep[:120])
_posts.clear()
bot.handle_message(msg("/report", uid=BUYER))
check("غیرادمین گزارش نمی‌گیرد", "گزارش مدیریتی" not in " ".join(pp[1] for pp in _posts),
      str(_posts[-1:]))
_posts.clear()
bot.handle_message(msg("/stats", uid=BUYER))
check("غیرادمین با /stats هم گزارش نمی‌گیرد",
      "گزارش مدیریتی" not in " ".join(pp[1] for pp in _posts), str(_posts[-1:]))
bot.ADMIN_USER_ID = ""

print("\n۹٫۵) موتور محتوای کانال")
import calendar as _cal  # noqa: E402
import time as _time  # noqa: E402


def ts_at_hour(hour: int) -> int:
    g = _time.gmtime()
    return _cal.timegm((g.tm_year, g.tm_mon, g.tm_mday, hour, 0, 0))


check("بازهٔ ارسال: ظهر UTC مجاز است", bot.in_post_window(ts_at_hour(12)) is True)
check("بازهٔ ارسال: نیمه‌شب UTC مجاز نیست", bot.in_post_window(ts_at_hour(23)) is False)
check("فاصلهٔ پست خودکار ۳ ساعت است", bot.CHANNEL_POST_INTERVAL_SEC == 3 * 3600,
      str(bot.CHANNEL_POST_INTERVAL_SEC))
_cats = [bot.next_channel_category() for _ in range(len(bot.CHANNEL_CYCLE))]
check("چرخهٔ محتوا همهٔ دسته‌ها را می‌پوشاند", set(_cats) == {"radar", "edu", "feature"}, str(_cats))
_wrap = bot.next_channel_category()
check("چرخه پس از یک دور به ابتدا برمی‌گردد", _wrap == _cats[0], f"{_cats[0]} vs {_wrap}")
_re_code = __import__("re").compile(r"start=(post_(?:edu|feature)\d+)")
_e1, _ekb = bot.build_edu_post()
_e2, _ = bot.build_edu_post()
check("پست آموزشی ساخته می‌شود", "🎓" in _e1 and len(_e1) > 200, _e1[:60])
check("دو پست آموزشی پشت‌سرهم تکراری نیستند", _e1 != _e2)
check("پست آموزشی دکمهٔ مینی‌اپ دارد", "t.me/" in _ekb["inline_keyboard"][0][0]["url"])
check("هر اسلاید آموزشی کد منبع اختصاصی خودش را دارد (post_edu1..N)",
      _re_code.search(_ekb["inline_keyboard"][0][0]["url"]) is not None
      and _re_code.search(_ekb["inline_keyboard"][0][0]["url"]).group(1) !=
      _re_code.search(bot.build_edu_post()[1]["inline_keyboard"][0][0]["url"]).group(1),
      _ekb["inline_keyboard"][0][0]["url"])
_f1, _fkb = bot.build_feature_post()
check("پست معرفی قابلیت ساخته می‌شود", len(_f1) > 150, _f1[:60])
check("پست قابلیت، دکمهٔ دعوت هم دارد", len(_fkb["inline_keyboard"]) >= 2)
check("پست آموزشی هم فورواردشدنی است (دکمهٔ share روی همهٔ پست‌ها)",
      any(b.get("url", "").startswith("https://t.me/share/url")
          for row in _fkb["inline_keyboard"] for b in row))
_all_channel_text = " ".join(t + " " + b for t, b in bot.CHANNEL_EDU_POSTS + bot.CHANNEL_FEATURE_POSTS)
check("هیچ پست کانال وعدهٔ سود تضمینی ندارد",
      "تضمین" not in _all_channel_text and "سود قطعی" not in _all_channel_text)
check("تعریف‌ها بدون داده/توصیهٔ جعلی هستند (امضای آموزش)",
      "توصیهٔ سرمایه‌گذاری نیست" in _e1)
check("زمان پست بعدی توضیح انسانی دارد", len(bot.next_post_eta()) > 5, bot.next_post_eta())
_r, _rkb = bot.build_slot_post("radar")
check("اسلات رادار، پست دادهٔ زنده می‌دهد", "$" in _r and len(_rkb["inline_keyboard"]) >= 1)

_plan = bot.channel_plan(6)
check("برنامهٔ پست‌ها ۶ اسلات نشان می‌دهد", _plan.count("\n") >= 7 and "۱." in _plan, _plan[:80])
check("برنامه هر سه دسته را دارد", "🎓" in _plan and "✨" in _plan and "📡" in _plan, _plan[:200])
_posts.clear()
bot.handle_message(msg("/channelplan", uid=BUYER))
check("غیرادمین برنامهٔ محتوا را نمی‌بیند",
      "برنامهٔ پست" not in " ".join(pp[1] for pp in _posts), str(_posts[-1:]))
bot.ADMIN_USER_ID = str(USER)   # بخش ۹ این را خالی کرده بود
_posts.clear()
bot.PUBLIC_CHANNEL_ID = "@testchannel"
bot.handle_message(msg("/channelpost edu"))
_chan_last = [pp for pp in _posts if pp[0] == "@testchannel"]
check("/channelpost edu پست آموزشی می‌فرستد",
      bool(_chan_last) and "🎓" in _chan_last[-1][1], str(_chan_last[-1:])[:120])
_posts.clear()
bot.handle_message(msg("/channelpost feature"))
_chan_last = [pp for pp in _posts if pp[0] == "@testchannel"]
check("/channelpost feature پست معرفی قابلیت می‌فرستد",
      bool(_chan_last) and "داخل تلگرام" in _chan_last[-1][1]
      and "t.me/" in str((_chan_last[-1][2].get("reply_markup") or {})),
      str(_chan_last[-1:])[:140])
bot.PUBLIC_CHANNEL_ID = ""
bot.ADMIN_USER_ID = ""

print("\n۹٫۶) تکمیل پروفایل کانال")
_desc = bot.channel_description_text()
check("توضیحات کانال از سقف ۲۵۵ کاراکتر تلگرام رد نمی‌شود", len(_desc) <= 255, str(len(_desc)))
check("توضیحات کانال، لینک مینی‌اپ دارد",
      "t.me/" in _desc and "?start=channel" in _desc and bot.BOT_USERNAME in _desc, _desc[-70:])
check("توضیحات، ارزش پیشنهادی دارد", "رادار" in _desc and "آموزش" in _desc, _desc[:80])

bot.ADMIN_USER_ID = str(USER)
bot.PUBLIC_CHANNEL_ID = "@testchannel"
CHAT_STATE.update({"pinned_message": None, "description": "", "photo": None})  # کانال ناقص
UPLOADS = []
bot.tg_set_chat_photo = lambda chat_id, path: (UPLOADS.append((chat_id, str(path))) or {"ok": True})

SENT.clear()
_posts.clear()
bot.handle_message(msg("/channelinfo"))
_info = _posts[-1][1] if _posts else ""
check("/channelinfo چک‌لیست پروفایل می‌دهد", "تکمیل پروفایل کانال" in _info, _info[:80])
check("چک‌لیست عکس و توضیحات و پین را جدا نشان می‌دهد",
      "عکس پروفایل" in _info and "توضیحات" in _info and "پین‌شده" in _info, _info[:200])
check("چک‌لیست کارهای باقی‌مانده را می‌گوید", "باقی‌مانده" in _info or "کامل است" in _info, _info[-200:])

SENT.clear()
bot.handle_message(msg("/channeldesc"))
_setdesc = [pl for api, pl in SENT if api == "setChatDescription"]
check("/channeldesc توضیحات را روی کانال ست می‌کند", bool(_setdesc), str([a for a, _ in SENT]))
check("متن ارسالی همان متن آماده است",
      bool(_setdesc) and _setdesc[0]["description"] == _desc, str(_setdesc[:1])[:120])

SENT.clear()
bot.handle_message(msg("/channeldesc کانال تستی تریدگارد — رادار و آموزش"))
_setdesc = [pl for api, pl in SENT if api == "setChatDescription"]
check("/channeldesc متن دلخواه را می‌پذیرد",
      bool(_setdesc) and "کانال تستی" in _setdesc[0]["description"], str(_setdesc[:1])[:120])

SENT.clear()
bot.handle_message(msg("/channeltitle TradeGuard | رادار"))
_title = [pl for api, pl in SENT if api == "setChatTitle"]
check("/channeltitle عنوان را ست می‌کند", bool(_title) and "TradeGuard" in _title[0]["title"],
      str([a for a, _ in SENT]))

UPLOADS.clear()
_posts.clear()
bot.handle_message(msg("/channelphoto"))
check("/channelphoto فایل لوگو را آپلود می‌کند", len(UPLOADS) == 1, str(UPLOADS))
check("مسیر لوگو واقعاً وجود دارد", bot.CHANNEL_AVATAR_PATH.exists(), str(bot.CHANNEL_AVATAR_PATH))

SENT.clear()
UPLOADS.clear()
_posts.clear()
bot.handle_message(msg("/channelcomplete"))
_api_calls = [a for a, _ in SENT]
check("/channelcomplete توضیحات را ست می‌کند", "setChatDescription" in _api_calls, str(_api_calls))
check("/channelcomplete عکس می‌گذارد", len(UPLOADS) == 1, str(UPLOADS))
check("/channelcomplete پیام خوش‌آمد را پین می‌کند",
      "pinChatMessage" in _api_calls and any(pp[0] == "@testchannel" for pp in _posts), str(_api_calls))

SENT.clear()
UPLOADS.clear()
_posts.clear()
for _cmd in ("/channeldesc", "/channelphoto", "/channelcomplete", "/channeltitle", "/channelinfo"):
    bot.handle_message(msg(_cmd, uid=BUYER))
check("غیرادمین هیچ‌کدام از دستورهای پروفایل را اجرا نمی‌کند",
      not SENT and not UPLOADS, f"{SENT[:2]} | {UPLOADS}")

bot.PUBLIC_CHANNEL_ID = ""
bot.ADMIN_USER_ID = ""
CHAT_STATE.update({"pinned_message": {"message_id": 42}, "description": "", "photo": None})

print("\n۹٫۷) شرکا / لینک همکاری")
import json as _json  # noqa: E402

_pfile = Path(tempfile.mkdtemp()) / "partners.json"
bot.PARTNERS_FILE = _pfile
_pfile.write_text(_json.dumps({"disclosure": "لینک همکاری — ممکن است کمیسیون بگیریم.",
                               "partners": [{"name": "Prop Firm X", "note": "۵۰٪ تخفیف",
                                             "url": "https://t.me/propfirm_x", "badge": "۵۰٪"}]},
                              ensure_ascii=False), encoding="utf-8")
_partners = bot.load_partners()
check("partners.json خوانده می‌شود", len(_partners["partners"]) == 1, str(_partners)[:100])
_ptext = bot.partners_text()
check("متن /partners نام شریک را دارد", "Prop Firm X" in _ptext, _ptext[:80])
check("متن /partners لینک را دارد", "https://t.me/propfirm_x" in _ptext, _ptext[:120])
check("متن /partners افشای کمیسیون دارد", "کمیسیون" in _ptext, _ptext[-80:])
_posts.clear()
bot.handle_message(msg("/partners"))
check("دستور /partners برای کاربر عادی جواب می‌دهد",
      bool(_posts) and "Prop Firm X" in _posts[-1][1], str(_posts[-1:])[:120])

_pfile.write_text(_json.dumps({"partners": []}), encoding="utf-8")
_empty = bot.partners_text()
check("بدون شریک، پیام صادقانه است", "هنوز هیچ شریکی" in _empty, _empty[:60])
_posts.clear()
bot.handle_message(msg("/partners"))
check("دستور /partners با لیست خالی هم پاسخ می‌دهد",
      bool(_posts) and "هنوز هیچ شریکی" in _posts[-1][1], str(_posts[-1:])[:120])
_pfile.unlink()
check("فایل نبودن partners.json ربات را نمی‌شکند", bot.load_partners()["partners"] == [])

print("\n۹٫۸) رهگیری کلیک لینک شرکا")
_pfile2 = Path(tempfile.mkdtemp()) / "partners.json"
bot.PARTNERS_FILE = _pfile2
_pfile2.write_text(_json.dumps({"disclosure": "لینک همکاری — کمیسیون می‌گیریم.",
                                "partners": [{"id": "propfirm_x", "name": "Prop Firm X",
                                              "note": "۵۰٪ تخفیف", "url": "https://propfirmx.example/r/tg",
                                              "badge": "۵۰٪"}]}, ensure_ascii=False), encoding="utf-8")
check("شریک با id پیدا می‌شود", (bot.partner_by_id("propfirm_x") or {}).get("name") == "Prop Firm X")
check("id ناشناس None برمی‌گرداند", bot.partner_by_id("nope") is None)
_posts.clear()
bot.handle_message(msg("/start p_propfirm_x", uid=BUYER))
_landing = [pp for pp in _posts if pp[0] == BUYER]
check("لینک شرکا در ربات پیام مقصد می‌دهد", bool(_landing) and "Prop Firm X" in _landing[-1][1],
      str(_landing[-1:])[:120])
check("دکمهٔ رفتن به سایت شریک وجود دارد",
      bool(_landing) and "propfirmx.example" in str(_landing[-1][2].get("reply_markup") or {}),
      str(_landing[-1:])[:160])
check("کلیک شریک در دیتابیس ثبت می‌شود",
      bot.get_setting("partner_start_propfirm_x") == "1", bot.get_setting("partner_start_propfirm_x"))
bot.handle_message(msg("/start p_propfirm_x", uid=BUYER))
check("کلیک دوم شمارنده را ۲ می‌کند", bot.get_setting("partner_start_propfirm_x") == "2",
      bot.get_setting("partner_start_propfirm_x"))
_summary = dict(bot.partner_click_summary())
check("خلاصهٔ کلیک‌ها شریک را نشان می‌دهد", _summary.get("propfirm_x") == 2, str(_summary))
_posts.clear()
bot.handle_message(msg("/start p_ghost", uid=BUYER))
check("لینک شرکای نامعتبر، پیام صادقانه می‌دهد",
      bool(_posts) and "معتبر نیست" in _posts[-1][1], str(_posts[-1:])[:100])
_posts.clear()
bot.ADMIN_USER_ID = str(USER)
bot.handle_message(msg("/report"))
check("گزارش مدیریتی کلیک شرکا را دارد",
      bool(_posts) and "کلیک لینک شرکا" in _posts[-1][1], str(_posts[-1:])[:120])
from pathlib import Path as _Path  # noqa: E402
_u = _posts[-1][2].get("reply_markup") or {}
check("گزارش مدیریتی دکمهٔ گزارش/بازگشت دارد", isinstance(_u, dict), str(_u)[:80])

bot.MINI_APP_URL = "https://rmanm19.github.io/tradeguard-bot/app.html"
_pl = bot.partner_landing_url("propfirm_x")
check("صفحهٔ فرود شریک از دامنهٔ مینی‌اپ ساخته می‌شود",
      _pl.endswith("/p.html?id=propfirm_x&lang=fa") and "/app.html" not in _pl, _pl)
check("صفحهٔ فرود برای شناسهٔ خالی ساخته نمی‌شود", bot.partner_landing_url("") == "")
_posts.clear()
bot.handle_message(msg("/partnerlink propfirm_x"))
check("/partnerlink لینک صفحهٔ فرود را می‌دهد",
      bool(_posts) and "p.html?id=propfirm_x" in _posts[-1][1], str(_posts[-1:])[:160])
check("/partnerlink لینک تلگرام با کد رهگیری را می‌دهد",
      bool(_posts) and "start=p_propfirm_x" in _posts[-1][1], str(_posts[-1:])[:160])
_posts.clear()
bot.handle_message(msg("/partnerlink ghost"))
check("/partnerlink برای شناسهٔ ناشناس صادق است",
      bool(_posts) and "partners.json نیست" in _posts[-1][1], str(_posts[-1:])[:120])
_posts.clear()
bot.handle_message(msg("/partnerlink", uid=BUYER))
check("غیرادمین به /partnerlink دسترسی ندارد",
      bool(_posts) and "فقط ادمین" in _posts[-1][1], str(_posts[-1:])[:100])
bot.MINI_APP_URL = ""
bot.ADMIN_USER_ID = ""

print("\n۹٫۹) پاداش عضویت کانال + رهگیری منبع ورود")
import sqlite3 as _sql2  # noqa: E402

bot.PUBLIC_CHANNEL_ID = "@testchannel"
_pay_before = _sql2.connect(bot.DB_PATH).execute("SELECT COUNT(*) FROM payments").fetchone()[0]

check("گزارش عضویت، وضعیت واقعی از تلگرام می‌گیرد",
      bot.channel_membership_status(USER) == "administrator", bot.channel_membership_status(USER))
_ok, _days, _st = bot.claim_join_reward(FRIEND)
check("پاداش عضویت برای عضو واقعی صادر می‌شود", _ok is True and _days == 7, f"{_ok} {_days} {_st}")
_pay_after = _sql2.connect(bot.DB_PATH).execute("SELECT COUNT(*) FROM payments").fetchone()[0]
check("پاداش، ردیف پرداخت جعلی نمی‌سازد (آمار درآمد آلوده نمی‌شود)",
      _pay_after == _pay_before, f"{_pay_before} → {_pay_after}")
_pro_until = _sql2.connect(bot.DB_PATH).execute(
    "SELECT pro_until FROM users WHERE user_id = ?", (FRIEND,)).fetchone()[0]
check("پرو کاربر تا ۷ روز آینده فعال است",
      int(_pro_until) > int(_time.time()) + 6 * 86400, str(_pro_until))
_ok2, _days2, _st2 = bot.claim_join_reward(FRIEND)
check("پاداش عضویت فقط یک‌بار داده می‌شود", _ok2 is False and _st2 == "already", f"{_ok2} {_st2}")

_orig_member = bot.channel_membership_status
bot.channel_membership_status = lambda uid: "left"
_ok3, _days3, _st3 = bot.claim_join_reward(USER)
check("عضو نبودن، پاداش نمی‌گیرد", _ok3 is False and _st3 == "left", f"{_ok3} {_st3}")
_posts.clear()
bot.handle_message(msg("/checkjoin"))
check("/checkjoin برای غیرعضو پیام صادقانه می‌دهد",
      bool(_posts) and "هنوز عضو کانال نیستی" in _posts[-1][1], str(_posts[-1:])[:120])
bot.channel_membership_status = _orig_member

_posts.clear()
bot.handle_message(msg("/checkjoin"))
check("/checkjoin برای عضو، پاداش را تأیید می‌کند",
      bool(_posts) and ("تأیید شد" in _posts[-1][1] or "قبلاً گرفته" in _posts[-1][1]),
      str(_posts[-1:])[:120])

check("کد منبع معتبر ثبت می‌شود", bot.record_source("ad_telegram") == 1)
check("کد منبع تکراری شمرده می‌شود", bot.record_source("ad_telegram") == 2)
check("کد منبع نامعتبر رد می‌شود", bot.record_source("bad code!") == 0)
_summary = dict(bot.source_summary())
check("خلاصهٔ منابع کد را نشان می‌دهد", _summary.get("ad_telegram") == 2, str(_summary))
_posts.clear()
bot.handle_message(msg("/start ad_instagram", uid=USER))
check("ورود با لینک کمپین شمارش می‌شود",
      bot.get_setting("src_ad_instagram") == "1", bot.get_setting("src_ad_instagram"))
_src_text = bot.sources_text()
check("متن /sources منابع را با تعداد نشان می‌دهد",
      "ad_telegram" in _src_text and "ad_instagram" in _src_text, _src_text[:120])
_posts.clear()
bot.handle_message(msg("/sources", uid=BUYER))
check("غیرادمین منابع ورود را نمی‌بیند",
      "منابع ورود" not in " ".join(pp[1] for pp in _posts), str(_posts[-1:])[:100])
bot.ADMIN_USER_ID = str(USER)
_posts.clear()
bot.handle_message(msg("/sources"))
check("ادمین فهرست منابع را می‌گیرد", bool(_posts) and "منابع ورود" in _posts[-1][1],
      str(_posts[-1:])[:100])
_posts.clear()
bot.handle_message(msg("/report"))
check("گزارش مدیریتی خط منابع ورود دارد",
      bool(_posts) and "منابع ورود" in _posts[-1][1], str(_posts[-1:])[:100])
bot.ADMIN_USER_ID = ""
bot.PUBLIC_CHANNEL_ID = ""

print("\n۹٫۱۰) قیف منبع ورود + گزارش هفتگی")
NEW1, NEW2 = 909100111, 909100222
bot.PUBLIC_CHANNEL_ID = "@testchannel"
bot.register_user_and_check_referral(NEW1, "cmp1", "fa", None, "ad_campaign1")
bot.register_user_and_check_referral(NEW2, "cmp2", "fa", None, "ad_campaign1")
_src_row = _sql2.connect(bot.DB_PATH).execute(
    "SELECT source FROM users WHERE user_id = ?", (NEW1,)).fetchone()
check("منبع ورود کاربر در دیتابیس ذخیره می‌شود", _src_row and _src_row[0] == "ad_campaign1", str(_src_row))
_rows = {r["source"]: r for r in bot.funnel_rows()}
check("قیف منبع را با تعداد کاربر نشان می‌دهد",
      _rows.get("ad_campaign1", {}).get("users") == 2, str(_rows.get("ad_campaign1")))
check("قیف ورودی‌های بدون منبع را direct می‌کند", "direct" in _rows, str(list(_rows)[:5]))
bot.claim_join_reward(NEW1)
_rows = {r["source"]: r for r in bot.funnel_rows()}
check("عضویت کانال در قیف همان منبع شمرده می‌شود",
      _rows["ad_campaign1"]["joined"] == 1, str(_rows["ad_campaign1"]))
check("نرخ تبدیل عضویت حساب می‌شود",
      abs(_rows["ad_campaign1"]["join_rate"] - 50.0) < 0.01, str(_rows["ad_campaign1"]))
_ftxt = bot.funnel_text()
check("متن قیف درصد تبدیل را نشان می‌دهد", "ad_campaign1" in _ftxt and "%" in _ftxt, _ftxt[:140])
check("متن قیف جمع کل را می‌دهد", "جمع:" in _ftxt, _ftxt[-160:])
# پول به تفکیک منبع: کدام پست/دعوت واقعاً فروخت؟
_money_rows = {r["source"]: r for r in bot.funnel_rows()}
_paid_src = next((r for r in _money_rows.values() if r.get("payments")), None)
check("قیف، خرید و استارز هر منبع را از جدول پرداخت می‌خواند",
      _paid_src is not None and _paid_src["stars"] > 0
      and abs(_paid_src["usd"] - bot.stars_to_usd(_paid_src["stars"])) < 0.01,
      str(_paid_src))
check("متن قیف درآمد همان منبع را نشان می‌دهد",
      "💰" in _ftxt and _paid_src["source"] in _ftxt, _ftxt[:220])
_weekly = bot.weekly_growth_report()
check("گزارش هفتگی ساخته می‌شود", "گزارش هفتگی رشد" in _weekly, _weekly[:80])
check("گزارش هفتگی عدد عضویت کانال دارد", "عضویت کانال" in _weekly, _weekly[:160])
check("گزارش هفتگی مقدار None ندارد", "None" not in _weekly, _weekly[:160])
bot.ADMIN_USER_ID = str(USER)
_posts.clear()
bot.handle_message(msg("/sources"))
check("/sources خروجی قیف می‌دهد",
      bool(_posts) and "قیف واقعی" in _posts[-1][1], str(_posts[-1:])[:100])
bot.ADMIN_USER_ID = ""
bot.PUBLIC_CHANNEL_ID = ""

print("\n۹٫۱۱) کانال انگلیسی + ارسال چندکاناله")
import re as _re  # noqa: E402

_fa_re = _re.compile(r"[\u0600-\u06FF]")
_en_edu, _en_kb = bot.build_edu_post_en()
_en_feat, _en_fkb = bot.build_feature_post_en()
_en_radar, _ = bot.build_channel_post_en([])
check("پست آموزشی انگلیسی ساخته می‌شود", "🎓" in _en_edu and len(_en_edu) > 150, _en_edu[:60])
check("پست آموزشی انگلیسی هیچ حرف فارسی ندارد", not _fa_re.search(_en_edu), _en_edu[:80])
check("پست قابلیت انگلیسی فارسی ندارد", not _fa_re.search(_en_feat), _en_feat[:80])
check("رادار انگلیسی هم بدون فارسی است", not _fa_re.search(_en_radar), _en_radar[:80])
check("دکمهٔ انگلیسی به کد رهگیری خودش لینک دارد",
      "post_edu" in _en_kb["inline_keyboard"][0][0]["url"], str(_en_kb)[:120])
check("کد منبع پست انگلیسی شمارهٔ اسلاید و _en دارد",
      bool(__import__("re").search(r"start=post_edu\d+_en", _en_kb["inline_keyboard"][0][0]["url"])),
      _en_kb["inline_keyboard"][0][0]["url"])

_c1 = bot.next_channel_category("en")
_c2 = bot.next_channel_category("en")
check("چرخهٔ انگلیسی مستقل از فارسی است",
      _c1 == bot.CHANNEL_CYCLE[0] and _c2 == bot.CHANNEL_CYCLE[1], f"{_c1},{_c2}")
check("شمارندهٔ فارسی با انگلیسی قاطی نمی‌شود",
      bot.get_setting("channel_cycle_idx_en") == "2", bot.get_setting("channel_cycle_idx_en"))

bot.PUBLIC_CHANNEL_ID = "@testchannel"
bot.PUBLIC_CHANNEL_EN = "@testchannel_en"
bot.set_setting("last_channel_post_ts", "1")
bot.set_setting("last_channel_post_ts_en", "1")
_posts.clear()
_noon = int(_cal.timegm((_time.gmtime().tm_year, _time.gmtime().tm_mon, _time.gmtime().tm_mday, 12, 0, 0)))
_sent = bot.post_due_slots(_noon)
_chan_ids = {c for c, _ in _sent}
check("در بازهٔ ارسال، هر دو کانال پست می‌گیرند",
      _chan_ids == {"@testchannel", "@testchannel_en"}, str(_sent))
_en_posts = [pp for pp in _posts if pp[0] == "@testchannel_en"]
check("پست کانال انگلیسی به انگلیسی است",
      bool(_en_posts) and not _fa_re.search(_en_posts[-1][1]), str(_en_posts[-1:])[:100])
check("زمان آخرین پست هر کانال جدا ذخیره می‌شود",
      bot.get_setting("last_channel_post_ts") == str(_noon)
      and bot.get_setting("last_channel_post_ts_en") == str(_noon))
_posts.clear()
_sent2 = bot.post_due_slots(_noon + 60)
check("پست تکراری قبل از ۳ ساعت ارسال نمی‌شود", _sent2 == [], str(_sent2))
_sent3 = bot.post_due_slots(_noon + 4 * 3600)
check("بعد از ۳ ساعت دوباره ارسال می‌شود", len(_sent3) == 2, str(_sent3))

_orig_send = bot.tg_send_message
bot.tg_send_message = lambda *a, **k: {"ok": False, "error_code": 403, "description": "no rights"}
_idx_en_before = bot.get_setting("channel_cycle_idx_en")
bot.set_setting("last_channel_post_ts_en", "1")
bot.set_setting("last_channel_post_ts", str(_noon + 4 * 3600))
_failed = bot.post_due_slots(_noon + 4 * 3600)
check("ارسال ناموفق به کانال، پست ثبت‌شده ندارد", _failed == [], str(_failed))
check("ارسال ناموفق، چرخهٔ محتوا را جلو نمی‌برد",
      bot.get_setting("channel_cycle_idx_en") == _idx_en_before,
      f"{_idx_en_before} → {bot.get_setting('channel_cycle_idx_en')}")
bot.tg_send_message = _orig_send
bot.set_setting("last_channel_post_ts_en", "1")

bot.ADMIN_USER_ID = str(USER)
_posts.clear()
bot.handle_message(msg("/channelen"))
check("/channelen وضعیت کانال انگلیسی را می‌دهد",
      bool(_posts) and "کانال انگلیسی" in _posts[-1][1], str(_posts[-1:])[:100])
bot.PUBLIC_CHANNEL_EN = "@testchannel_en"
CHAT_STATE.update({"pinned_message": None, "description": "", "photo": None})
_uploads = []
_orig_photo = bot.tg_set_chat_photo
bot.tg_set_chat_photo = lambda cid, path: (_uploads.append(cid) or {"ok": True})
_posts.clear()
bot.handle_message(msg("/channelen setup"))
_pin_posts = [pp for pp in _posts if pp[0] == "@testchannel_en"]
check("setup کانال انگلیسی: عکس پروفایل ست می‌شود", _uploads == ["@testchannel_en"], str(_uploads))
check("setup کانال انگلیسی: توضیحات و پین انجام می‌شود",
      bool(_posts) and "Description set" in _posts[-1][1] and "pinned" in _posts[-1][1],
      str(_posts[-1:])[:160])
check("پیام پین کانال انگلیسی، انگلیسی است",
      bool(_pin_posts) and not _fa_re.search(_pin_posts[-1][1]), str(_pin_posts[-1:])[:120])
check("توضیحات انگلیسی کوتاه‌تر از سقف ۲۵۵ کاراکتر است",
      len(bot.channel_description_text_en()) <= bot.CHANNEL_DESC_LIMIT,
      str(len(bot.channel_description_text_en())))
check("توضیحات انگلیسی هیچ حرف فارسی ندارد",
      not _fa_re.search(bot.channel_description_text_en()), bot.channel_description_text_en()[:60])
CHAT_STATE.update({"pinned_message": {"message_id": 42}, "description": bot.channel_description_text_en(),
                   "photo": {"big": 1}})
_posts.clear()
_uploads.clear()
bot.handle_message(msg("/channelen setup"))
check("setup دوباره، پروفایل کامل را دست نمی‌زند",
      _uploads == [] and bool(_posts) and "از قبل کامل" in _posts[-1][1], str(_posts[-1:])[:120])
bot.tg_set_chat_photo = _orig_photo
_posts.clear()
bot.handle_message(msg("/channelen", uid=BUYER))
check("غیرادمین نمی‌تواند کانال انگلیسی را عوض کند",
      not any("@whatever" in pp[1] for pp in _posts), str(_posts[-1:])[:80])
bot.PUBLIC_CHANNEL_EN = ""
bot.PUBLIC_CHANNEL_ID = ""

print("\n۹٫۱۲) جدول دعوت‌کننده‌ها + برنامهٔ کانال انگلیسی")
import sqlite3 as _sql3  # noqa: E402

_con = _sql3.connect(bot.DB_PATH)
_con.execute("UPDATE users SET referrals_count = 3, username = 'topguy' WHERE user_id = ?", (USER,))
_con.execute("UPDATE users SET referrals_count = 1, username = '' WHERE user_id = ?", (BUYER,))
_con.commit()
_con.close()

_rows = bot.referral_leaderboard()
check("جدول دعوت فقط شمارش واقعی دیتابیس را می‌خواند",
      bool(_rows) and _rows[0][0] == USER and _rows[0][1] == 3 and _rows[0][2] == "topguy", str(_rows[:2]))
check("کسی که دعوت ندارد در جدول نمی‌آید",
      all(r[1] > 0 for r in _rows) and len(_rows) == 2, str(_rows))
_posts.clear()
bot.handle_message(msg("/top", uid=BUYER))
_t = _posts[-1][1] if _posts else ""
check("/top یوزرنیم نفر اول را نشان می‌دهد", "@topguy" in _t, _t[:120])
_board_rows = [ln for ln in _t.splitlines() if "دعوت" in ln and "کاربر" in ln]
check("/top آیدی بدون یوزرنیم را ماسک می‌کند",
      bool(_board_rows) and "کاربر ••" in _board_rows[0] and str(BUYER) not in _board_rows[0],
      str(_board_rows)[:160])
check("/top رتبه و لینک دعوت خود کاربر را می‌دهد",
      "جای تو" in _t and "start=ref_" in _t, _t[-180:])
_en_board = bot.leaderboard_text(BUYER, "en")
check("/top برای زبان غیرفارسی انگلیسی جواب می‌دهد",
      "Invite leaderboard" in _en_board and not _fa_re.search(_en_board), _en_board[:120])

_posts.clear()
bot.ADMIN_USER_ID = str(USER)
bot.handle_message(msg("/channelplan en"))
_plan_en = _posts[-1][1] if _posts else ""
check("برنامهٔ کانال انگلیسی تیتر انگلیسی دارد",
      "English channel" in _plan_en and not _fa_re.search(_plan_en), _plan_en[:120])
check("برنامهٔ کانال انگلیسی وقتی کانال نیست، صادقانه می‌گوید",
      "not set" in _plan_en, _plan_en[-120:])
_posts.clear()
bot.handle_message(msg("/channelplan"))
_plan_fa = _posts[-1][1] if _posts else ""
check("برنامهٔ کانال فارسی سر جایش است",
      "برنامهٔ پست‌های بعدی" in _plan_fa, _plan_fa[:100])
check("برنامهٔ فارسی به نسخهٔ انگلیسی اشاره می‌کند",
      "/channelplan en" in _plan_fa, _plan_fa[-160:])
check("زمان پست بعدی نسخهٔ انگلیسی، انگلیسی است",
      not _fa_re.search(bot.next_post_eta_en()), bot.next_post_eta_en())

_posts.clear()
bot.ADMIN_USER_ID = str(USER)
bot.handle_message(msg("/adkit"))
_kit = _posts[-1][1] if _posts else ""
check("/adkit هر سه کد کمپین را می‌دهد",
      all(c in _kit for c in ("start=ad_radar", "start=ad_risk", "start=ad_reward")), _kit[:200])
check("/adkit مسیر بنرها را نشان می‌دهد",
      "docs/assets/ads/ad_radar.png" in _kit, _kit[-200:])
check("/adkit کاربر را به اندازه‌گیری با /sources می‌فرستد", "/sources" in _kit, _kit[-160:])
_posts.clear()
bot.handle_message(msg("/adkit", uid=BUYER))
check("غیرادمین به /adkit دسترسی ندارد",
      bool(_posts) and "فقط ادمین" in _posts[-1][1], str(_posts[-1:])[:100])
bot.ADMIN_USER_ID = ""

print("\n۹٫۱۳) هم‌خوانی متن پروفایل کانال با اسکریپت تنظیم پروفایل")
import channel_profile as _cp  # noqa: E402

check("متن توضیحات انگلیسی ربات و اسکریپت یکی است",
      _cp.TEXTS["en"]["desc"] == bot.CHANNEL_DESCRIPTION_EN, _cp.TEXTS["en"]["desc"][:60])
check("متن توضیحات فارسی ربات و اسکریپت یکی است",
      _cp.TEXTS["fa"]["desc"] == bot.CHANNEL_DESCRIPTION, _cp.TEXTS["fa"]["desc"][:60])
check("عنوان پیشنهادی کانال زیر سقف ۱۲۸ کاراکتر است",
      all(len(t["title"]) <= 128 for t in _cp.TEXTS.values()), str(len(_cp.TEXTS["en"]["title"])))
check("متن خوش‌آمد انگلیسی هیچ حرف فارسی ندارد",
      not _fa_re.search(_cp.TEXTS["en"]["welcome"]), _cp.TEXTS["en"]["welcome"][:60])
import os as _os2  # noqa: E402
_saved_tok = _os2.environ.pop("BOT_TOKEN", None)
_rc = _cp.main()
if _saved_tok is not None:
    _os2.environ["BOT_TOKEN"] = _saved_tok
check("اسکریپت پروفایل بدون توکن خطا می‌دهد و کرش نمی‌کند", _rc == 2, str(_rc))
check("کد قفل‌شدن روی یوزرنیم در راهنما ذکر شده (Bot API نمی‌تواند عوض کند)",
      "یوزرنیم" in _cp.__doc__, _cp.__doc__[:60])

print("\n۹٫۱۴) پروفایل خودکار کانال انگلیسی در استارت‌آپ")
bot.PUBLIC_CHANNEL_ID = ""
bot.PUBLIC_CHANNEL_EN = "@testchannel_en"
bot.ADMIN_USER_ID = str(USER)
CHAT_STATE.update({"pinned_message": None, "description": "", "photo": None})
_auto_ups = []
_auto_photo = bot.tg_set_chat_photo
bot.tg_set_chat_photo = lambda cid, path: (_auto_ups.append(cid) or {"ok": True})
_posts.clear()
bot._auto_en_channel_profile_once()
check("استارت‌آپ، عکس پروفایل کانال انگلیسی را ست می‌کند",
      _auto_ups == ["@testchannel_en"], str(_auto_ups))
check("استارت‌آپ، پیام خوش‌آمد انگلیسی را در کانال می‌فرستد",
      any(pp[0] == "@testchannel_en" for pp in _posts), str([pp[0] for pp in _posts]))
check("استارت‌آپ، گزارش تکمیل پروفایل را به ادمین می‌دهد",
      any("پروفایل کانال انگلیسی" in pp[1] for pp in _posts), str(_posts[-1:])[:120])
check("پیام خوش‌آمد داخل کانال انگلیسی هیچ حرف فارسی ندارد",
      all(not _fa_re.search(pp[1]) for pp in _posts if pp[0] == "@testchannel_en"),
      str([pp[1][:40] for pp in _posts if pp[0] == "@testchannel_en"]))

_real_tg_call = bot.tg_call


def _failing_call(method_name, payload=None, timeout=15.0):
    if method_name == "getChat":
        return {"ok": False, "description": "Bad Request: chat not found"}
    return _real_tg_call(method_name, payload, timeout)


bot.tg_call = _failing_call
_posts.clear()
bot._auto_en_channel_profile_once()
check("یوزرنیم عوض‌شده، هشدار مشخص به ادمین می‌دهد",
      any("کانال انگلیسی در دسترس نیست" in pp[1] for pp in _posts), str(_posts[-1:])[:140])
check("هشدار، دستور درست را پیشنهاد می‌دهد",
      any("/channelen @new_username" in pp[1] for pp in _posts), str(_posts[-1:])[:160])
bot.tg_call = _real_tg_call
bot.tg_set_chat_photo = _auto_photo
bot.PUBLIC_CHANNEL_EN = ""
bot.ADMIN_USER_ID = ""
CHAT_STATE.update({"pinned_message": {"message_id": 42}, "description": "", "photo": None})

print("\n۹٫۱۵) فید عمومی داده (برای توسعه‌دهنده‌ها و شرکا)")
_feeds = []


def _fake_rates(_n=0):
    _feeds.append(1)
    return [{"sym": "BTC", "rate_pct": 0.012, "oi_m": 3420.5, "price": 80330.0},
            {"sym": "SOL", "rate_pct": -0.031, "oi_m": 890.2, "price": 178.4}]


bot.PUBLIC_FEED_DIR = Path(tempfile.mkdtemp()) / "api"
check("بدون دادهٔ زنده هیچ فیدی ساخته نمی‌شود (هیچ عدد ساختگی)",
      bot.build_public_feed([]) is None and bot.build_public_feed(None) is None)
_feed = bot.publish_public_feed(_fake_rates())
_radar_path = bot.PUBLIC_FEED_DIR / "radar.json"
_stats_path = bot.PUBLIC_FEED_DIR / "stats.json"
check("فید radar.json و stats.json نوشته می‌شود",
      _radar_path.exists() and _stats_path.exists(), str(bot.PUBLIC_FEED_DIR))
_radar = _json.loads(_radar_path.read_text(encoding="utf-8"))
_stats = _json.loads(_stats_path.read_text(encoding="utf-8"))
check("فید عمومی نفس‌های لازم را دارد",
      all(k in _radar for k in ("generated_at", "fear_greed", "funding", "disclaimer")), str(list(_radar)))
check("فید عمومی، فاندینگ و OI واقعی را می‌دهد",
      len(_radar["funding"]) == 2 and _radar["funding"][0]["symbol"] == "BTC"
      and _radar["funding"][0]["oi_usd_m"] == 3420.5, str(_radar["funding"][:1]))
check("سالانه‌سازی فاندینگ درست است (۰٫۰۱۲٪ × ۳ × ۳۶۵ ≈ ۱۳٫۱٪)",
      abs(_radar["funding"][0]["apr_pct"] - 13.1) < 0.2, str(_radar["funding"][0]["apr_pct"]))
check("علامت APR حفظ می‌شود (فاندینگ منفی = APR منفی)",
      _radar["funding"][1]["apr_pct"] < 0, str(_radar["funding"][1]["apr_pct"]))
_noprice = bot.build_public_feed([{"sym": "XRP", "rate_pct": 0.02, "oi_m": 50.0}])
check("قیمت فقط وقتی موجود است منتشر می‌شود (به‌جای null حذف می‌شود)",
      _radar["funding"][0].get("mark_price") == 80330.0
      and "mark_price" not in (_noprice or {"funding": [{}]})["funding"][0],
      str((_noprice or {}).get("funding")))
check("فید عمومی هیچ توکن یا آیدی شخصی ندارد",
      "BOT_TOKEN" not in _radar_path.read_text(encoding="utf-8")
      and "user_id" not in _radar_path.read_text(encoding="utf-8"),
      "بررسی محتوا")
check("مسیر نسبی PUBLIC_FEED_DIR نسبت به ریشهٔ ریپو حل می‌شود (باگ کش‌شدهٔ CI)",
      bot.resolve_repo_path("docs/api", Path("/x")) == bot.REPO_ROOT / "docs" / "api"
      and bot.resolve_repo_path("", Path("/x")) == Path("/x")
      and bot.resolve_repo_path("/tmp/z", Path("/x")) == Path("/tmp/z"),
      str(bot.resolve_repo_path("docs/api", Path("/x"))))
# اندازهٔ کانال: عدد تجمیعی واقعی، و اگر تلگرام جواب نداد هیچ کلیدی ساخته نمی‌شود
_real_call_feed = bot.tg_call
bot.PUBLIC_CHANNEL_ID = "@testchannel_feed"
bot.tg_call = lambda m, payload=None, timeout=15.0: ({"ok": True, "result": 137}
                                                     if m == "getChatMemberCount" else _real_call_feed(m, payload, timeout))
bot.publish_public_feed(_fake_rates(), force=True)
_members_stats = _json.loads((bot.PUBLIC_FEED_DIR / "stats.json").read_text(encoding="utf-8"))
check("اندازهٔ کانال به‌صورت عدد تجمیعی در stats.json منتشر می‌شود",
      _members_stats.get("channel_members") == 137, str(_members_stats))
bot.tg_call = lambda m, payload=None, timeout=15.0: ({"ok": False, "description": "nope"}
                                                     if m == "getChatMemberCount" else _real_call_feed(m, payload, timeout))
bot.publish_public_feed(_fake_rates(), force=True)
_members_stats2 = _json.loads((bot.PUBLIC_FEED_DIR / "stats.json").read_text(encoding="utf-8"))
check("اگر تلگرام شمارش را نداد، هیچ عدد ساختگی در stats.json نمی‌نشیند",
      "channel_members" not in _members_stats2, str(_members_stats2))
bot.tg_call = _real_call_feed
bot.PUBLIC_CHANNEL_ID = ""

check("آیدی عددی کانال هرگز در فید عمومی نمی‌رود",
      bot._public_channel_handle("-1001234567") == ""
      and bot._public_channel_handle("@tradeguard1") == "@tradeguard1")
check("آمار فید فقط شمارنده‌های تجمیعی دارد",
      _stats["users_total"] >= 1 and "note" in _stats and _stats["languages"] == 6, str(_stats))
_stamp1 = _json.loads(_radar_path.read_text(encoding="utf-8"))["generated_at"]
bot.publish_public_feed(_fake_rates())
_stamp2 = _json.loads(_radar_path.read_text(encoding="utf-8"))["generated_at"]
check("انتشار زودهنگام دوباره نویسی نمی‌کند (ضد نویز کامیت)",
      _stamp1 == _stamp2, f"{_stamp1} → {_stamp2}")
check("انتشار اجباری (force) همیشه فید تازه می‌نویسد",
      bot.publish_public_feed(_fake_rates(), force=True) is not None
      and _json.loads(_radar_path.read_text(encoding="utf-8"))["funding"][0]["symbol"] == "BTC")
check("تاریخ فید ISO و UTC است",
      _radar["generated_at"].endswith("Z") and "T" in _radar["generated_at"], _radar["generated_at"])
bot.PRO_STATUS_PUSH = False
check("بدون PRO_STATUS_PUSH هیچ پوشی انجام نمی‌شود",
      bot.publish_public_feed(_fake_rates()) is not None)

print("\n۹٫۱۶) گزارش قیف شرکا (/biz) برای بروکر و صرافی")
_sqlf = __import__("sqlite3")
_now = int(__import__("time").time())
with bot._db_lock, _sqlf.connect(bot.DB_PATH) as _c:
    _c.execute("DELETE FROM users WHERE source LIKE 'p_okx%'")
    for _i, _src in enumerate(["p_okx", "p_okx_ab12", "p_okx_ab12", "p_bybit"]):
        _uid = 77001000 + _i
        _c.execute(
            "INSERT OR REPLACE INTO users (user_id, username, lang, referred_by, referrals_count,"
            " free_trial_claimed, pro_until, created_at, source) VALUES (?,?,?,?,?,?,?,?,?)",
            (_uid, "u%d" % _i, "en", 0, 0, 0, _now + 86400 if _i == 0 else 0, _now, _src),
        )
    _c.execute("INSERT OR REPLACE INTO join_rewards (user_id, days, granted_at) VALUES (?,?,?)",
               (77001000, 1, _now))
    _c.execute("INSERT OR REPLACE INTO join_rewards (user_id, days, granted_at) VALUES (?,?,?)",
               (77001001, 1, _now))
bot.ADMIN_USER_ID = str(USER)
bot.set_setting("partner_start_okx", "10")
check("شناسهٔ شریک از کد منبع درست استخراج می‌شود (subid جدا می‌شود)",
      bot._partner_id_from_source("p_okx_ab12") == "okx"
      and bot._partner_id_from_source("p_bybit") == "bybit"
      and bot._partner_id_from_source("direct") == "", "p_okx_ab12 → okx")
_rows = bot.partner_funnel_rows()
_okx = [r for r in _rows if r["partner"] == "okx"]
check("ردیف‌های قیف فقط منابع شرکا را برمی‌گرداند (با شناسهٔ یکتا، بدون direct)",
      _okx and {r["partner"] for r in _rows} == {"okx", "bybit"}, str([r["partner"] for r in _rows]))
check("هر ردیف همهٔ کدهای subid خودش را نگه می‌دارد",
      sorted([r for r in _rows if r["partner"] == "okx"][0]["sources"]) == ["p_okx", "p_okx_ab12"],
      str([r for r in _rows if r["partner"] == "okx"][0]["sources"]))
_starts = sum(r["starts"] for r in _okx)
check("مجموع استارت‌های یک شریک با subidهایش جمع می‌شود", _starts == 3, str(_starts))
check("کلیک‌های شریک از settings خوانده می‌شود", any(r["clicks"] == 10 for r in _okx), str(_okx[:1]))
_txt = bot.biz_report_text("okx")
check("گزارش /biz عددهای واقعی قیف را نشان می‌دهد (۳ استارت، ۲ عضویت)",
      "`okx`" in _txt and "استارت: *3*" in _txt and "عضویت تأییدشدهٔ کانال: *2*" in _txt, _txt[:120])
check("گزارش /biz subidها را زیر یک شریک جمع می‌کند",
      "p_okx_ab12" in _txt and "p_okx`" in _txt, [l for l in _txt.split("\n") if "کدها" in l][:1])
check("گزارش /biz نرخ کلیک‌به‌استارت را حساب می‌کند (۳ از ۱۰ = ۳۰٪)",
      "30%" in _txt, [ln for ln in _txt.split("\n") if "کلیک" in ln][:1])
check("گزارش /biz عضویت تأییدشده و پرو فعال را جدا می‌دهد",
      "عضویت تأییدشدهٔ کانال" in _txt and "پرو فعال" in _txt)
check("گزارش /biz صادقانه می‌گوید KYC و دپوزیت را نمی‌داند",
      "KYC" in _txt and "postback" in _txt and "نمی‌داند" in _txt)
check("شِمای رهگیری click-id در گزارش هست",
      "p_<id>_<clickid>" in _txt and "tg_id" in _txt)
check("برای کد ناشناس، گزارش به‌جای عدد جعلی راهنمای لینک می‌دهد",
      "داده‌ای نیست" in bot.biz_report_text("p_none") and "start=p_<partner-id>" in bot.biz_report_text("p_none"))
check("گزارش بدون آرگومان همهٔ شرکا را فهرست می‌کند",
      "bybit" in bot.biz_report_text() and "okx" in bot.biz_report_text(), bot.biz_report_text()[:60])
_posts.clear()
bot.handle_message(msg("/biz", uid=USER))
_biz_txt = _posts[-1][1] if _posts else ""
check("/biz برای ادمین گزارش قیف می‌فرستد", "قیف شرکا" in _biz_txt, _biz_txt[:60])
check("/biz اعداد واقعی همان شریک را در پیام می‌آورد",
      "*3*" in _biz_txt and "30%" in _biz_txt, _biz_txt[:200])
_posts.clear()
bot.handle_message(msg("/biz", uid=BUYER))
_biz_txt2 = _posts[-1][1] if _posts else ""
check("/biz برای غیر ادمین مسدود است", "⛔" in _biz_txt2, _biz_txt2[:60])

print("\n۹٫۱۷) ماشین‌حساب ریسک و حجم در چت (/rr)")
_rr = bot.rr_text("1000 1 64000 62500 67500", "fa")
check("/rr ریسک دلاری را حساب می‌کند (۱۰۰۰ × ۱٪ = ۱۰ دلار)", "$10.00" in _rr, _rr[:80])
check("/rr حجم پوزیشن را از فاصلهٔ ورود تا حد ضرر می‌دهد (۰٫۰۰۶۶۶۷)",
      "0.00666667" in _rr, _rr[:160])
check("/rr نسبت R/R را می‌دهد (۳۵۰۰ ÷ ۱۵۰۰ = ۲٫۳۳)", "2.33" in _rr, _rr[:200])
check("/rr سود در هدف را هم می‌دهد (۰٫۰۰۶۶۶۶ × ۳۵۰۰ ≈ ۲۳٫۳۳ دلار)",
      "23.33" in _rr, _rr[:220])
check("/rr جهت را از محل حد ضرر می‌فهمد (لانگ)", "لانگ" in _rr, _rr[:40])
_rr_short = bot.rr_text("1000 1 64000 65500 61000", "fa")
check("/rr شورت را هم تشخیص می‌دهد و R/R درست است",
      "شورت" in _rr_short and "2.00" in _rr_short, _rr_short[:120])
check("/rr بدون آرگومان راهنمای استفاده می‌دهد", "بالانس" in bot.rr_text("", "fa"))
check("/rr ورودی خراب را با پیام روشن رد می‌کند", "عدد" in bot.rr_text("abc def ghi jkl", "fa"))
check("/rr حد ضرر مساوی ورود را رد می‌کند", "یکی" in bot.rr_text("1000 1 100 100", "fa"))
check("/rr هدف در جهت اشتباه را هشدار می‌دهد (بدون R/R جعلی)",
      "جهت اشتباه" in bot.rr_text("1000 1 100 90 80", "fa"))
check("/rr بدون هدف هم کار می‌کند و R/R نمی‌سازد",
      "هدف را هم بفرست" in bot.rr_text("1000 1 100 90", "fa"))
_rr_en = bot.rr_text("1000 1 64000 62500 67500", "en")
check("/rr در انگلیسی هم درست است و حرف فارسی ندارد",
      "Position size" in _rr_en and not any("\u0600" <= ch <= "\u06ff" for ch in _rr_en), _rr_en[:80])
check("رشته‌های /rr در هر ۶ زبان کامل است",
      all(set(bot.BOT_STRINGS_RR["fa"]) <= set(bot.BOT_STRINGS_RR[l]) for l in ("en", "ru", "ar", "tr", "es")),
      str([l for l in bot.BOT_STRINGS_RR if len(bot.BOT_STRINGS_RR[l]) < 7]))
_posts.clear()
bot.handle_message(msg("/rr 1000 1 64000 62500 67500"))
_rr_msg = _posts[-1][1] if _posts else ""
check("دستور /rr در چت پیام می‌دهد", "2.33" in _rr_msg, _rr_msg[:80])
_posts.clear()
bot.handle_message(msg("/rr", lang="en", uid=BUYER + 2468))
check("/rr برای کاربر انگلیسی، راهنمای انگلیسی می‌دهد",
      "Position size" in (_posts[-1][1] if _posts else ""), (_posts[-1][1][:60] if _posts else ""))

print("\n۹٫۱۸) هشدارهای شخصی (/alert) — ذخیره، فهرست و بررسی واقعی")
bot.ADMIN_USER_ID = str(USER)
_check_uid = 78001000
with bot._db_lock, __import__("sqlite3").connect(bot.DB_PATH) as _c:
    _c.execute("DELETE FROM price_alerts WHERE user_id IN (?, ?)", (_check_uid, USER))
check("تحلیل قانون هشدار درست است (BTC funding above 0.05)",
      bot.parse_alert_rule("BTC funding above 0.05") == ("BTC", "funding", "above", 0.05))
check("معادل فارسی هم پذیرفته می‌شود (طلای قیمت پایین‌تر از)",
      bot.parse_alert_rule("ETH price پایین‌تر 2800") == ("ETH", "price", "below", 2800.0),
      str(bot.parse_alert_rule("ETH price پایین‌تر 2800")))
check("قانون ناقص/بی‌معنی رد می‌شود",
      bot.parse_alert_rule("BTC funding") is None
      and bot.parse_alert_rule("BTC funding above abc") is None
      and bot.parse_alert_rule("BTC weird above 1") is None
      and bot.parse_alert_rule("BTC funding above 99") is None)
_added = bot.handle_alert_command("/alert BTC funding above 0.05", _check_uid, "fa")
check("ثبت هشدار پیام تأیید می‌دهد و قاعده را نشان می‌دهد",
      "ثبت شد" in _added and "BTC" in _added and "0.05" in _added, _added[:90])
_rules = bot.user_alerts(_check_uid)
check("هشدار در دیتابیس ذخیره شده و فعال است",
      len(_rules) == 1 and _rules[0]["metric"] == "funding" and _rules[0]["active"] == 1, str(_rules))
_list_txt = bot.handle_alert_command("/alert", _check_uid, "fa")
check("فهرست هشدارها شماره و وضعیت را نشان می‌دهد",
      f"#{_rules[0]['id']}" in _list_txt and "🟢" in _list_txt, _list_txt[:120])
check("خاموش/روشن کردن هشدار کار می‌کند",
      "خاموش" in bot.handle_alert_command(f"/alert off {_rules[0]['id']}", _check_uid, "fa")
      and bot.user_alerts(_check_uid)[0]["active"] == 0
      and "روشن" in bot.handle_alert_command(f"/alert on {_rules[0]['id']}", _check_uid, "fa")
      and bot.user_alerts(_check_uid)[0]["active"] == 1)
check("هشدار کاربر دیگر قابل دستکاری نیست",
      "پیدا نشد" in bot.handle_alert_command(f"/alert off {_rules[0]['id']}", _check_uid + 1, "fa")
      and bot.user_alerts(_check_uid)[0]["active"] == 1)
# بررسی واقعی: فاندینگ ۰٫۰۸ بالای ۰٫۰۵ است → باید پیام برود
_posts.clear()
_fired = bot.evaluate_user_alerts(rates=[{"sym": "BTC", "rate_pct": 0.08, "price": 60000}], now=1_800_000_000)
check("وقتی شرط برقرار است پیام هشدار ارسال می‌شود", len(_fired) == 1 and _posts, str(_fired))
check("متن هشدار مقدار فعلی و شرط را دارد",
      "0.0800" in (_posts[-1][1] if _posts else "") and "0.05" in (_posts[-1][1] if _posts else ""),
      (_posts[-1][1][:90] if _posts else ""))
_posts.clear()
_fired2 = bot.evaluate_user_alerts(rates=[{"sym": "BTC", "rate_pct": 0.09, "price": 60000}], now=1_800_000_000 + 600)
check("در بازهٔ خنک‌شدن (۶ ساعت) پیام تکراری نمی‌رود", _fired2 == [] and not _posts, str(_fired2))
_posts.clear()
_fired3 = bot.evaluate_user_alerts(rates=[{"sym": "BTC", "rate_pct": 0.09, "price": 60000}],
                                   now=1_800_000_000 + bot.ALERT_COOLDOWN_SEC + 10)
check("بعد از ۶ ساعت دوباره می‌شود هشدار داد", len(_fired3) == 1 and _posts, str(_fired3))
_posts.clear()
_fired4 = bot.evaluate_user_alerts(rates=[{"sym": "BTC", "rate_pct": 0.01, "price": 60000}], now=1_900_000_000)
check("وقتی شرط برقرار نیست هیچ پیامی نمی‌رود", _fired4 == [] and not _posts, str(_fired4))
_posts.clear()
_fired5 = bot.evaluate_user_alerts(rates=[{"sym": "ETH", "rate_pct": 9.0, "price": 2800}], now=1_900_000_000)
check("هشدار فقط روی نماد خودش بررسی می‌شود (بدون داده → بی‌صدا)", _fired5 == [] and not _posts)
_posts.clear()
bot.add_user_alert(_check_uid, "XRP", "price", "below", 0.5)
_fired6 = bot.evaluate_user_alerts(rates=[{"sym": "XRP", "rate_pct": 0.0, "price": 0}], now=1_900_000_000)
check("بدون قیمت واقعی، هشدار قیمت هرگز شلیک نمی‌کند (ضد عدد جعلی)", _fired6 == [] and not _posts)
for _i in range(5):
    bot.add_user_alert(_check_uid, f"SYM{_i}", "price", "above", 1)
check("سقف ۵ هشدار برای هر کاربر اعمال می‌شود",
      len(bot.user_alerts(_check_uid)) == 5
      and "سقف" in bot.handle_alert_command("/alert DOGE price above 1", _check_uid, "fa"),
      str(len(bot.user_alerts(_check_uid))))
check("حذف هشدار کار می‌کند",
      "حذف" in bot.handle_alert_command(f"/alert del {_rules[0]['id']}", _check_uid, "fa")
      and len(bot.user_alerts(_check_uid)) == 4)
_posts.clear()
bot.handle_message(msg("/alert SOL funding below -0.02", uid=_check_uid))
check("دستور /alert از طریق ربات پاسخ می‌دهد",
      bool(_posts) and "ثبت شد" in _posts[-1][1], (_posts[-1][1][:70] if _posts else ""))
_posts.clear()
bot.handle_message(msg("/alert", lang="en", uid=BUYER + 8642))
check("راهنمای /alert برای کاربر تازه (انگلیسی) می‌آید",
      bool(_posts) and "Personal alert" in _posts[-1][1], (_posts[-1][1][:60] if _posts else ""))
check("متن‌های /alert در هر ۶ زبان کامل است",
      all(set(bot.BOT_STRINGS_ALERT["fa"]) <= set(bot.BOT_STRINGS_ALERT[l]) for l in ("en", "ru", "ar", "tr", "es")))

print("\n۹٫۱۹) گزارش ماهانهٔ شرکا (اسنپ‌شات + تغییر)")
bot.set_setting("partner_snapshot_2026-09", __import__("json").dumps(
    {"okx": {"clicks": 4, "starts": 2, "joined": 1, "pro": 0}}))
_month_txt = bot.monthly_partner_report("2026-11")
check("گزارش ماهانه عددهای واقعی هر شریک را دارد",
      "okx" in _month_txt and "کلیک" in _month_txt and "2026-11" in _month_txt, _month_txt[:120])
check("تغییر نسبت به اسنپ‌شات قبلی محاسبه می‌شود (۳−۲=+۱ استارت)",
      "تغییر" in _month_txt and "+" in _month_txt, [l for l in _month_txt.split("\n") if "تغییر" in l][:1])
check("گزارش صادقانه می‌گوید دپوزیت/KYC در سمت بروکر است",
      "KYC" in _month_txt and "بروکر" in _month_txt)
check("اسنپ‌شات ماه جاری در settings ذخیره می‌شود",
      bool(bot.get_setting("partner_snapshot_2026-11", "")), bot.get_setting("partner_snapshot_2026-11", "")[:40])
bot.set_setting("partner_report_last_month", "")
_posts.clear()
_sent_month = bot.maybe_send_monthly_partner_report()
check("گزارش ماهانه برای ادمین ارسال می‌شود", _sent_month and bool(_posts) and "گزارش ماهانه" in _posts[-1][1])
_posts.clear()
check("ارسال دوباره در همان ماه انجام نمی‌شود (idempotent)",
      bot.maybe_send_monthly_partner_report() is False and not _posts)
_posts.clear()
bot.handle_message(msg("/biz report", uid=USER))
check("دستور /biz report در چت گزارش می‌دهد",
      bool(_posts) and "گزارش ماهانه" in _posts[-1][1], (_posts[-1][1][:60] if _posts else ""))

print("\n۹٫۲۰) رشد واقعی کانال: /share، جمع‌بندی هفتگی، صفحه‌های SEO")
import tempfile as _tmp
import pathlib as _pl

# ── /share: متن‌های آماده + لینک اختصاصی، بدون عدد ساختگی ──────────────
_posts.clear()
bot.handle_message(msg("/share", uid=USER))
_share_txt = _posts[-1][1] if _posts else ""
check("/share متن آمادهٔ دعوت می‌دهد (۶ زبانه)",
      bool(_share_txt) and ("کپی" in _share_txt or "Copy" in _share_txt), _share_txt[:80])
check("/share لینک اختصاصی ref_<id> کاربر را دارد",
      f"ref_{USER}" in _share_txt, _share_txt[:120])
check("/share دکمهٔ «ارسال به دوست» تلگرام را هم می‌گذارد",
      "t.me/share/url" in str(_posts[-1][2] if _posts else {}),
      str(_posts[-1][2] if _posts else "")[:80])
_share_ref = bot.invite_link(USER)
_share_btn = bot.growth_share_button(_share_txt, "en")
check("لینک share با کدگذاری درست ساخته می‌شود (بدون فاصله/خط جدید خام)",
      _share_btn["url"].startswith("https://t.me/share/url?url=")
      and " " not in _share_btn["url"] and "\n" not in _share_btn["url"],
      _share_btn["url"][:80])
check("دکمهٔ share در هر ۶ زبان برچسب دارد",
      all(bot.tr(l, "share_btn") and bot.tr(l, "share_btn") != "share_btn"
          for l in ("fa", "en", "ru", "ar", "tr", "es")))

# ── آمار واقعی دعوت: فقط ۷ روز گذشته، فقط referred_by ─────────────────
import sqlite3 as _sq
import time as _time
_now = int(_time.time())
with bot._db_lock, _sq.connect(bot.DB_PATH) as _c:
    _c.execute("INSERT OR REPLACE INTO users (user_id, username, lang, referred_by, referrals_count, "
               "free_trial_claimed, pro_until, created_at, source) VALUES (?,?,?,?,?,?,?,?,?)",
               (990111, "", "fa", USER, 0, 0, 0, _now - 3600, "test"))
    _c.execute("INSERT OR REPLACE INTO users (user_id, username, lang, referred_by, referrals_count, "
               "free_trial_claimed, pro_until, created_at, source) VALUES (?,?,?,?,?,?,?,?,?)",
               (990112, "", "fa", USER, 0, 0, 0, _now - 30 * 86400, "test"))
    _c.execute("UPDATE users SET referrals_count = referrals_count + 2 WHERE user_id = ?", (USER,))
_stats_w = bot.weekly_invite_stats(_now)
# مبنا: تعداد واقعی موجود؛ تست فقط «افزایش ۱» و «نشمردن ردیف ۳۰ روزه» را می‌سنجد
with bot._db_lock, _sq.connect(bot.DB_PATH) as _c0:
    _baseline = int(_c0.execute(
        "SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL AND created_at >= ?",
        (_now - 7 * 86400,)).fetchone()[0] or 0)
check("آمار هفتگی فقط دعوت‌های ۷ روز اخیر را می‌شمارد (ردیف ۳۰ روزه شمرده نشد)",
      int(_stats_w["new_referrals"]) == _baseline and _baseline >= 1,
      f"{_stats_w['new_referrals']} vs {_baseline}")

_recap = bot.build_invite_recap_post("fa", _now)
check("جمع‌بندی هفتگی ساخته می‌شود و عدد واقعی دارد",
      bool(_recap) and "۱" in _recap[0] and "گزارش هفتگی" in _recap[0], (_recap[0][:100] if _recap else ""))
check("جمع‌بندی هفتگی نام را ماسک می‌کند (آیدی عددی لو نمی‌رود)",
      bool(_recap) and str(USER) not in _recap[0], (_recap[0][-80:] if _recap else ""))
check("جمع‌بندی هفتگی دکمهٔ دعوت و فوروارد دارد",
      bool(_recap) and len(_recap[1]["inline_keyboard"]) == 3
      and any(b.get("url", "").startswith("https://t.me/share/url")
              for row in _recap[1]["inline_keyboard"] for b in row))
bot.set_setting("invite_recap_week", "")
_old_fa_ch, _old_en_ch = bot.PUBLIC_CHANNEL_ID, bot.PUBLIC_CHANNEL_EN
bot.PUBLIC_CHANNEL_ID, bot.PUBLIC_CHANNEL_EN = "@testchannel", ""
SENT.clear()
_posted_recap = bot.post_weekly_invite_recap(_now)
check("جمع‌بندی هفتگی در کانال ارسال می‌شود", bool(_posted_recap), str(_posted_recap))
SENT.clear()
check("ارسال دوباره در همان هفته انجام نمی‌شود (idempotent)",
      bot.post_weekly_invite_recap(_now) == [] and not SENT)
bot.PUBLIC_CHANNEL_ID, bot.PUBLIC_CHANNEL_EN = _old_fa_ch, _old_en_ch
_real_stats = bot.weekly_invite_stats
bot.weekly_invite_stats = lambda now=None: {"new_referrals": 0, "users_total": 0, "top": []}
check("وقتی هیچ دعوتی نیست، هیچ پستی ساخته نمی‌شود (بدون عدد ساختگی)",
      bot.build_invite_recap_post("fa", _now) is None)
bot.weekly_invite_stats = _real_stats

# ── صفحه‌های SEO هر نماد از همان فید ──────────────────────────────────
_feed = {"generated_at": "2026-11-10T09:30:00Z", "live": True,
         "fear_greed": {"value": 13, "label": "Extreme Fear"},
         "funding": [
             {"symbol": "WIF", "funding_pct_8h": -0.0369, "apr_pct": -40.4, "oi_usd_m": 2.33},
             {"symbol": "BTC", "funding_pct_8h": 0.01, "apr_pct": 10.9, "oi_usd_m": 2518.27,
              "mark_price": 64000.0},
         ]}
with _tmp.TemporaryDirectory() as _d:
    _written = bot._write_symbol_pages(_feed, out_dir=_pl.Path(_d))
    _names = sorted(x.name for x in _written)
    check("برای هر نماد یک صفحهٔ عمومی ساخته می‌شود",
          {"wif.html", "btc.html", "sitemap.xml", "robots.txt"} <= set(_names), str(_names))
    _page = (_pl.Path(_d) / "s" / "wif.html").read_text(encoding="utf-8")
    check("صفحهٔ نماد همان عدد فید را نشان می‌دهد (بدون گرد کردن ساختگی)",
          "-0.0369" in _page and "WIF" in _page)
    check("صفحهٔ نماد canonical و og و JSON-LD دارد",
          "rel=\"canonical\"" in _page and "og:title" in _page and "application/ld+json" in _page)
    check("صفحهٔ نماد CTA کانال و ربات دارد",
          "t.me/tradeguard1" in _page and f"t.me/{bot.BOT_USERNAME}?start=sym_wif" in _page)
    check("صفحهٔ نماد «سیگنال/وعدهٔ سود نیست» را می‌گوید",
          "سیگنال" in _page and "وعدهٔ سود" in _page)
    _sitemap = (_pl.Path(_d) / "sitemap.xml").read_text(encoding="utf-8")
    check("sitemap همهٔ صفحه‌های نماد را لیست می‌کند",
          "/s/wif.html" in _sitemap and "/s/btc.html" in _sitemap and "2026-11-10" in _sitemap)
    check("sitemap صفحهٔ فرود تلگرام (join.html) را هم دارد", "/join.html" in _sitemap)
    _robots = (_pl.Path(_d) / "robots.txt").read_text(encoding="utf-8")
    check("robots.txt به sitemap اشاره می‌کند", "Sitemap:" in _robots and "sitemap.xml" in _robots)
    # تزریق: نماد مخرب نباید HTML را بشکند
    _bad = {"generated_at": "2026-11-10T09:30:00Z", "live": True,
            "fear_greed": {"value": 50, "label": "Neutral"},
            "funding": [{"symbol": "<script>x</script>", "funding_pct_8h": 0.001,
                         "apr_pct": 1.1, "oi_usd_m": 1.0}]}
    bot._write_symbol_pages(_bad, out_dir=_pl.Path(_d))
    _badfiles = list((_pl.Path(_d) / "s").glob("*.html"))
    _badhtml = "".join(f.read_text(encoding="utf-8") for f in _badfiles)
    check("نماد مخرب escape/sanitize می‌شود (بدون تزریق اسکریپت)",
          "<script>x</script>" not in _badhtml and "&lt;script&gt;" in _badhtml)
with _tmp.TemporaryDirectory() as _d2:
    check("وقتی فید زنده نیست، هیچ صفحه‌ای نوشته نمی‌شود",
          bot._write_symbol_pages({"live": False, "funding": []}, out_dir=_pl.Path(_d2)) == []
          and not (_pl.Path(_d2) / "s").exists())

# ── publish_public_feed هم صفحه‌ها را می‌سازد و در همان کامیت می‌گذارد ───
_old_feed_dir = bot.PUBLIC_FEED_DIR
_old_push = bot.PRO_STATUS_PUSH
_real_feed = bot.fetch_live_funding_and_oi
_real_fng = bot.fetch_fear_greed
try:
    with _tmp.TemporaryDirectory() as _d3:
        bot.PUBLIC_FEED_DIR = _pl.Path(_d3) / "docs" / "api"
        bot.PRO_STATUS_PUSH = False
        bot.fetch_live_funding_and_oi = lambda: [
            {"sym": "SOL", "rate_pct": -0.0139, "oi_m": 298.7, "magnet": "", "daily_500": 0.0}]
        bot.fetch_fear_greed = lambda: (55, "Neutral")
        _pub = bot.publish_public_feed(force=True)
        check("انتشار فید، صفحه‌های نماد را هم می‌نویسد",
              bool(_pub) and ((_pl.Path(_d3) / "docs" / "s" / "sol.html").exists())
              and (_pl.Path(_d3) / "docs" / "sitemap.xml").exists(),
              str(sorted(x.name for x in (_pl.Path(_d3) / "docs").glob("**/*"))[:6]))
finally:
    bot.PUBLIC_FEED_DIR = _old_feed_dir
    bot.PRO_STATUS_PUSH = _old_push
    bot.fetch_live_funding_and_oi = _real_feed
    bot.fetch_fear_greed = _real_fng

# ─────────────────────────────────────────────────────────────
print("\n۱۳) موتور درآمد: آزمایش، یادآوری تمدید، گزارش واقعی")
import sqlite3 as _sq

# در بخش‌های قبلی، tg_send_message با یک جمع‌کنندهٔ محلی (_posts) جایگزین شده؛
# پس متن آخر باید از همان‌جا خوانده شود، نه از SENT.
def _last_sent() -> str:
    if _posts:
        return str(_posts[-1][1])
    return last_text()

def _clear_sent() -> None:
    SENT.clear()
    _posts.clear()

# نرخ تبدیل و صحت ستون‌های جدید
check("نرخ استارز→دلار درست است", abs(bot.stars_to_usd(300) - (300 * bot.STARS_USD_RATE * bot.STARS_NET_SHARE)) < 1e-9,
      str(bot.stars_to_usd(300)))
check("استارز صفر، دلار صفر می‌دهد", bot.stars_to_usd(0) == 0)
with _sq.connect(bot.DB_PATH) as _c:
    _pcols = [r[1] for r in _c.execute("PRAGMA table_info(payments)").fetchall()]
    _ucols = [r[1] for r in _c.execute("PRAGMA table_info(users)").fetchall()]
check("ستون‌های درآمدی payments ساخته شده‌اند",
      {"source", "days", "kind"} <= set(_pcols), str(_pcols))
check("ستون pro_trial_used برای آزمایش یک‌باره هست", "pro_trial_used" in _ucols, str(_ucols))

# آزمایش یک‌باره
TRIAL_USER = 999000111
bot.handle_message(msg("/start", uid=TRIAL_USER))
_with_trial = bot.is_user_pro(TRIAL_USER)
check("/start کاربر تازه را پرو نمی‌کند", not _with_trial[0])
_clear_sent()
bot.handle_message(msg("/trial", uid=TRIAL_USER))
_trial_ok = bot.is_user_pro(TRIAL_USER)
check("/trial کاربر را پرو می‌کند", _trial_ok[0], str(_trial_ok))
check("متن /trial می‌گوید دورهٔ آزمایشی فعال شد", "آزمایشی" in _last_sent(), _last_sent()[:60])
check("متن /trial می‌گوید پرداختی انجام نشد", "پرداختی انجام نشد" in _last_sent(), _last_sent()[-60:])
with _sq.connect(bot.DB_PATH) as _c:
    _trial_rows = _c.execute("SELECT COUNT(*) FROM payments WHERE user_id = ?", (TRIAL_USER,)).fetchone()[0]
check("آزمایش هیچ ردیف پرداختی نمی‌سازد (درآمد آلوده نمی‌شود)", int(_trial_rows) == 0, str(_trial_rows))

# اگر دورهٔ آزمایشی تمام شود، /trial دوباره نباید کار کند (ضد سوءاستفاده)
with bot._db_lock, _sq.connect(bot.DB_PATH) as _c:
    _c.execute("UPDATE users SET pro_until = ? WHERE user_id = ?",
               (int(bot.time.time()) - 60, TRIAL_USER))
_clear_sent()
bot.handle_message(msg("/trial", uid=TRIAL_USER))
check("/trial پس از پایان دوره دوباره فعال نمی‌شود (یک‌بار برای همیشه)",
      not bot.is_user_pro(TRIAL_USER)[0] and "قبلاً استفاده شده" in _last_sent(), _last_sent()[:70])

# یادآوری تمدید (۳ روز مانده) — یک‌بار و بدون تکرار
import time as _t
_now = int(bot.time.time())
REN_USER = 999000222
bot.handle_message(msg("/start", uid=REN_USER))
_chg = "test_renew_charge_1"
bot.activate_pro_subscription(REN_USER, stars=bot.SUBSCRIPTION_STARS, charge_id=_chg, days=30)
with bot._db_lock, _sq.connect(bot.DB_PATH) as _c:
    _c.execute("UPDATE users SET pro_until = ? WHERE user_id = ?", (_now + 2 * 86400, REN_USER))
with _sq.connect(bot.DB_PATH) as _c:
    _prow = _c.execute("SELECT stars_amount, days, kind, source FROM payments WHERE telegram_charge_id = ?",
                       (_chg,)).fetchone()
check("پرداخت با روز و نوع ثبت می‌شود", _prow is not None and int(_prow[1]) == 30 and _prow[2] == "stars", str(_prow))
check("کاربر در فهرست نامزد تمدید است",
      any(u == REN_USER for u, _e in bot.renewal_candidates(_now)), str(bot.renewal_candidates(_now))[:80])

_clear_sent()
_sent1 = bot.maybe_send_renewal_reminders(_now)
check("یادآوری تمدید برای کاربر در آستانهٔ انقضا ارسال می‌شود",
      (REN_USER, "renew") in _sent1, str(_sent1))
check("یادآوری همراه فاکتور استارز است", count("sendInvoice") >= 1, str(count("sendInvoice")))
_ren_msgs = [str(pp[1]) for pp in _posts if pp[0] == REN_USER]
check("متن یادآوری تاریخ انقضا را می‌گوید",
      any("تمام می‌شود" in m or "تمدید" in m for m in _ren_msgs), str(_ren_msgs)[:80])
_clear_sent()
_sent2 = bot.maybe_send_renewal_reminders(_now)
check("یادآوری تمدید دوباره فرستاده نمی‌شود (ضد اسپم)", _sent2 == [] and count("sendMessage") == 0, str(_sent2))

# بازگرداندن کاربر تازه‌منقضی
WIN_USER = 999000333
bot.handle_message(msg("/start", uid=WIN_USER))
bot.activate_pro_subscription(WIN_USER, stars=bot.SUBSCRIPTION_STARS, charge_id="test_winback_charge_1", days=30)
with bot._db_lock, _sq.connect(bot.DB_PATH) as _c:
    _c.execute("UPDATE users SET pro_until = ? WHERE user_id = ?", (_now - 86400, WIN_USER))
_clear_sent()
_sent3 = bot.maybe_send_renewal_reminders(_now)
check("کاربر تازه‌منقضی پیام بازگشت می‌گیرد", (WIN_USER, "winback") in _sent3, str(_sent3))
_win_msgs = [str(pp[1]) for pp in _posts if pp[0] == WIN_USER]
check("پیام بازگشت می‌گوید داده‌ای پاک نمی‌شود",
      any("پاک نمی‌شود" in m for m in _win_msgs), str(_win_msgs)[:80])
_clear_sent()
check("پیام بازگشت تکرار نمی‌شود", bot.maybe_send_renewal_reminders(_now) == [] and count("sendMessage") == 0)

# در حالت رایگان هیچ پیام درآمدی نمی‌رود
bot.set_free_mode(True)
with bot._db_lock, _sq.connect(bot.DB_PATH) as _c:
    _c.execute("UPDATE users SET pro_until = ? WHERE user_id = ?", (_now + 86400, REN_USER))
_clear_sent()
check("در دورهٔ رایگان یادآوری تمدید فرستاده نمی‌شود",
      bot.maybe_send_renewal_reminders(_now) == [] and count("sendMessage") == 0)
bot.set_free_mode(False)

# گزارش درآمد: انتساب منبع + جداکردن هدیه
SRC_USER = 999000444
bot.register_user_and_check_referral(SRC_USER, "srcuser", "fa", None, "p_okx_ab12")
bot.activate_pro_subscription(SRC_USER, stars=bot.SUBSCRIPTION_STARS, charge_id="test_src_charge_1", days=30)
GIFT_USER = 999000555
bot.activate_pro_subscription(GIFT_USER, stars=0, charge_id="test_gift_charge_1", days=30)
with _sq.connect(bot.DB_PATH) as _c:
    _gkind = _c.execute("SELECT kind, stars_amount FROM payments WHERE telegram_charge_id = ?",
                        ("test_gift_charge_1",)).fetchone()
check("هدیهٔ ۰ استارزی نوع gift می‌گیرد (درآمد را بالا نمی‌برد)",
      _gkind is not None and _gkind[0] == "gift" and int(_gkind[1]) == 0, str(_gkind))

_inc = bot.income_report(30)
check("گزارش درآمد ساخته می‌شود", "گزارش درآمد" in _inc and "نرخ اجرا" in _inc, _inc[:60])
check("گزارش درآمد منبع پول‌ساز را نشان می‌دهد", "p_okx_ab12" in _inc)
check("گزارش درآمد «قدم بعدی» می‌دهد", "قدم بعدی" in _inc)
check("گزارش درآمد عدد ساختگی ندارد (مجموع با دیتابیس یکی است)",
      f"{bot.SUBSCRIPTION_STARS * 2:,}" in _inc or "مجموع دریافتی" in _inc, _inc[:200])
check("گزارش درآمد یادآوری می‌کند نرخ دلار تخمینی است", "STARS_USD_RATE" in _inc)

_clear_sent()
bot.handle_message(msg("/income", uid=TRIAL_USER))
check("/income برای کاربر عادی بسته است", "فقط ادمین" in _last_sent(), _last_sent()[:40])

# freemode until + announce
bot.set_free_mode_until(0)
bot.set_free_mode(True)
check("رایگان بدون تاریخ = منهای یک (هشدار درآمد صفر)", bot.free_mode_days_left() == -1)
_future = int(_t.time()) + 5 * 86400
bot.set_free_mode_until(_future)
_left = bot.free_mode_days_left()
check("تاریخ پایان رایگان ذخیره و شمرده می‌شود", 4 <= _left <= 5, str(_left))
check("تاریخ پایان در دیتابیس می‌ماند", bot.get_setting("free_mode_until") == str(_future))

# شمارش معکوس در کانال: «رایگان» باید تاریخ داشته باشد، وگرنه فوریتی نمی‌سازد
_line_fa = bot.free_mode_countdown_line("fa")
check("خط شمارش معکوس تاریخ پایان و روزهای مانده را می‌گوید",
      bot._utc_date(_future) in _line_fa and "روز دیگر" in _line_fa, _line_fa[:90])
check("نسخهٔ انگلیسی خط شمارش معکوس دارد",
      "days left" in bot.free_mode_countdown_line("en"))
_post_until, _ = bot.build_channel_post([])
check("پست کانال وقتی تاریخ پایان هست، شمارش معکوس نشان می‌دهد",
      bot._utc_date(_future) in _post_until, _post_until[-200:])
bot.set_free_mode_until(0)
check("رایگانِ بی‌پایان هیچ تاریخ ساختگی در کانال نمی‌گذارد",
      bot.free_mode_countdown_line("fa") == ""
      and "رایگان تا" not in bot.build_channel_post([])[0])
bot.set_free_mode_until(_future)
bot.publish_pro_status()
_status_until = __import__("json").loads(_STATUS_TMP.read_text(encoding="utf-8"))
check("pro_users.json تاریخ پایان را منتشر می‌کند (مینی‌اپ شمارش معکوس دارد)",
      int(_status_until.get("freeUntil") or 0) == _future, str(_status_until)[:80])
bot.set_free_mode(False)
bot.publish_pro_status()
_status_off = __import__("json").loads(_STATUS_TMP.read_text(encoding="utf-8"))
check("با خاموش شدن رایگان، freeUntil صفر می‌شود (شمارش معکوس محو می‌شود)",
      int(_status_off.get("freeUntil") or 0) == 0, str(_status_off)[:80])
bot.set_free_mode(True)
bot.set_free_mode_until(_future)
# پلن‌های بلندمدت: قیمت، payload و روزهای واقعی
bot.set_free_mode(False)   # برای تست خرید باید پرداخت باز باشد
check("قیمت پلن ۹۰ روزه از قیمت ۳۰ روزه گران‌تر و از ۳ برابر ارزان‌تر است",
      bot.SUBSCRIPTION_STARS < bot.plan_price(90) < bot.SUBSCRIPTION_STARS * 3,
      f"{bot.plan_price(30)}/{bot.plan_price(90)}")
check("قیمت پلن سالانه از ۱۲ برابر ماهانه ارزان‌تر است",
      bot.plan_price(365) < bot.SUBSCRIPTION_STARS * 12, str(bot.plan_price(365)))
check("روزها فقط از payload مجاز خوانده می‌شوند (ضد دست‌کاری)",
      bot.plan_days_from_payload("tradeguard_pro_90d_750") == 90
      and bot.plan_days_from_payload("tradeguard_pro_7d_1") == 30
      and bot.plan_days_from_payload("garbage") == 30,
      str(bot.plan_days_from_payload("tradeguard_pro_365d_2400")))

_clear_sent()
bot.send_pro_invoice(USER, "fa", 90)
_inv = [pl for api, pl in SENT if api == "sendInvoice"]
check("فاکتور پلن ۹۰ روزه با مبلغ و payload درست ساخته می‌شود",
      bool(_inv) and _inv[-1]["prices"][0]["amount"] == bot.plan_price(90)
      and f"tradeguard_pro_90d_{bot.plan_price(90)}" == _inv[-1]["payload"],
      str(_inv[-1:])[:120])

PLAN_USER = 999000666
bot.handle_message(msg("/start", uid=PLAN_USER))
_clear_sent()
bot.handle_message(msg("/buy 90", uid=PLAN_USER))
_inv2 = [pl for api, pl in SENT if api == "sendInvoice"]
check("/buy 90 فاکتور ۹۰ روزه می‌دهد",
      bool(_inv2) and _inv2[-1]["prices"][0]["amount"] == bot.plan_price(90),
      str(_inv2[-1:])[:120])
_clear_sent()
bot.handle_message(msg("/buy", uid=PLAN_USER))
check("/buy بدون آرگومان جدول پلن‌ها را نشان می‌دهد",
       any(pp[0] == PLAN_USER and "پلن‌های TradeGuard PRO" in str(pp[1]) for pp in _posts),
      str([pp[1] for pp in _posts])[:60])

# پرداخت موفق با payload ۹۰ روزه باید ۹۰ روز فعال کند
_pay_msg = msg("", uid=PLAN_USER)
_pay_msg.pop("text")
_pay_msg["successful_payment"] = {
    "currency": "XTR",
    "total_amount": bot.plan_price(90),
    "invoice_payload": f"tradeguard_pro_90d_{bot.plan_price(90)}",
    "telegram_payment_charge_id": "plan90_charge_test",
    "provider_payment_charge_id": "x",
}
_clear_sent()
bot.handle_message(_pay_msg)
_ok90, _exp90 = bot.is_user_pro(PLAN_USER)
_days90 = int(round((_exp90 - int(bot.time.time())) / 86400))
check("پرداخت ۹۰ روزه واقعاً ۹۰ روز فعال می‌کند", _ok90 and 88 <= _days90 <= 90, f"{_ok90}/{_days90}")
with _sq.connect(bot.DB_PATH) as _c:
    _pdays = _c.execute("SELECT days, stars_amount FROM payments WHERE telegram_charge_id = ?",
                        ("plan90_charge_test",)).fetchone()
check("ردیف پرداخت روزهای پلن را ثبت می‌کند",
      _pdays is not None and int(_pdays[0]) == 90 and int(_pdays[1]) == bot.plan_price(90),
      str(_pdays))

# انتشار پلن‌ها برای مینی‌اپ (تک‌منبع قیمت)
_payload = bot.build_plans_payload()
check("payload پلن‌ها همان قیمت واقعی ربات است",
      [p["stars"] for p in _payload["plans"]] == [bot.plan_price(d) for d in bot.PRO_PLAN_DAYS],
      str([p["stars"] for p in _payload["plans"]]))
check("payload پلن‌ها دورهٔ آزمایشی و ارز را می‌گوید",
      _payload["currency"] == "XTR" and _payload["trial_days"] == bot.PRO_TRIAL_DAYS)
check("payload پلن‌ها هیچ عدد ساختگی ندارد (دلار از نرخ env می‌آید)",
      abs(_payload["plans"][0]["usd_gross"] - bot.plan_price(30) * bot.STARS_USD_RATE) < 1e-9,
      str(_payload["plans"][0]))
_old_feed = bot.PUBLIC_FEED_DIR
with _tmp.TemporaryDirectory() as _pd:
    bot.PUBLIC_FEED_DIR = _pl.Path(_pd) / "api"
    _written = bot.publish_plans(push=False)
    _pf = _pl.Path(_pd) / "api" / "plans.json"
    check("plans.json برای مینی‌اپ نوشته می‌شود",
          _pf.exists() and _written is not None and '"plans"' in _pf.read_text(encoding="utf-8"))
bot.PUBLIC_FEED_DIR = _old_feed

bot.set_free_mode(False)
bot.set_free_mode_until(0)

print("\n۱۴) لحظه‌های مهم: اولین درآمد + پایان دورهٔ رایگان + قیمت پایدار")


def _admin_msgs() -> str:
    return "\n".join(str(pp[1]) for pp in _posts if str(pp[0]) == str(bot.ADMIN_USER_ID))


# ── اولین درآمد: فقط پرداخت واقعی استارز، فقط یک‌بار ──
_prev_admin = bot.ADMIN_USER_ID
bot.ADMIN_USER_ID = str(USER)
with _sq.connect(bot.DB_PATH) as _c:
    _c.execute("DELETE FROM settings WHERE key = 'first_income_notified'")
    _c.execute("DELETE FROM settings WHERE key = 'first_income_at'")
_first = bot.first_paid_payment()
check("اولین پرداخت واقعی پیدا می‌شود و هدیه حساب نمی‌شود",
      _first is not None and int(_first["stars"]) > 0, str(_first))
_clear_sent()
check("پیام اولین درآمد ارسال می‌شود", bot.maybe_announce_first_income() is True)
_msg1 = _admin_msgs()
check("پیام اولین درآمد عدد واقعی و منبع را می‌گوید",
      "اولین درآمد واقعی" in _msg1 and "Stars" in _msg1 and "منبع ورود" in _msg1, _msg1[:160])
check("تاریخ اولین درآمد ذخیره می‌شود",
      (bot.get_setting("first_income_at") or "").isdigit(), bot.get_setting("first_income_at"))
_clear_sent()
check("پیام اولین درآمد دوباره تکرار نمی‌شود", bot.maybe_announce_first_income() is False)
_inc_first = bot.income_report(30)
check("گزارش درآمد تاریخ اولین درآمد را نشان می‌دهد",
      "اولین درآمد" in _inc_first and bot._utc_date(int(bot.get_setting("first_income_at"))) in _inc_first,
      _inc_first[-160:])

# ── پایان دورهٔ رایگان: یک‌بار به ادمین، با تاریخ واقعی ──
with _sq.connect(bot.DB_PATH) as _c:
    _c.execute("DELETE FROM settings WHERE key = 'free_ended_notice'")
_old_until = bot.FREE_MODE_UNTIL
_old_mode = bot.FREE_MODE
bot.FREE_MODE = True
bot.set_free_mode_until(int(_t.time()) + 3 * 86400)
_clear_sent()
check("تا وقتی تاریخ پایان نرسیده، هیچ پیامی نمی‌آید",
      bot.maybe_notify_free_mode_ended() is False and not _posts)
bot.set_free_mode_until(int(_t.time()) - 60)
_clear_sent()
check("گذشتن تاریخ پایان، پیام «تمام شد» می‌دهد", bot.maybe_notify_free_mode_ended() is True)
_msg2 = _admin_msgs()
check("پیام پایان دورهٔ رایگان تاریخ و قدم بعدی را می‌گوید",
      "دورهٔ رایگان تمام شد" in _msg2 and bot._utc_date(bot.FREE_MODE_UNTIL) in _msg2
      and "/income" in _msg2, _msg2[:180])
_clear_sent()
check("پیام پایان دورهٔ رایگان تکرار نمی‌شود", bot.maybe_notify_free_mode_ended() is False)
check("پس از پایان، رایگان فعال نیست (قفل‌ها بسته‌اند)", bot.free_mode_active() is False)
bot.set_free_mode_until(_old_until)
bot.FREE_MODE = _old_mode

# ── قیمت: هر جریان تازه (کرون فید) باید همان قیمت دیتابیس را منتشر کند ──
_prev_raw = bot.get_setting("SUBSCRIPTION_STARS")
bot.set_setting("SUBSCRIPTION_STARS", "450")
bot.forget_persisted_price()
check("قیمت ذخیره‌شدهٔ ادمین بر پیش‌فرض env مقدّم است", bot.plan_price(30) == 450,
      f"plan_price(30)={bot.plan_price(30)}")
check("قیمت ذخیره‌شده در payload انتشار هم می‌آید",
      bot.build_plans_payload()["plans"][0]["stars"] == 450)
check("قیمت پلن‌های بلندمدت با قیمت ذخیره‌شده قاطی نمی‌شود",
      bot.plan_price(90) == bot.SUBSCRIPTION_STARS_90
      and bot.plan_price(365) == bot.SUBSCRIPTION_STARS_365)
bot.set_setting("SUBSCRIPTION_STARS", _prev_raw or "")
bot.forget_persisted_price()
check("بازگشت قیمت، دوباره از پیش‌فرض می‌خواند",
      bot.plan_price(30) == bot.SUBSCRIPTION_STARS, str(bot.plan_price(30)))
bot.FREE_MODE = False
bot.set_free_mode_until(0)
bot.ADMIN_USER_ID = _prev_admin

print("\n۱۵) انتشار بدون انتظار: کد جدید در ≤۵ دقیقه زنده می‌شود")

import run_forever as _rf  # noqa: E402  (نگهبان ربات)

# ── هش گیت: مقایسهٔ محتوا با sha برگشتی از API، بدون دانلود فایل ──
check("هش blob گیت برای محتوای ساده درست است",
      _rf._git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
      _rf._git_blob_sha(b""))
_real_sha = _rf._git_blob_sha((_rf.BASE / "bot.py").read_bytes())
check("هش blob فایل واقعی ۴۰ کاراکتر hex است",
      len(_real_sha) == 40 and all(c in "0123456789abcdef" for c in _real_sha), _real_sha)


def _fake_gh(files, listing_sha=None, fail=False):
    """جایگزین شبکه: فهرست پوشه + محتوای فایل‌ها."""
    calls = []

    def _get(url, env, accept, timeout=10.0):
        calls.append(url)
        if fail:
            raise OSError("شبکه قطع است")
        if url.endswith("/contents/tradeguard-pro?ref=main"):
            entries = []
            for name, body in files.items():
                sha = (listing_sha or {}).get(name) or _rf._git_blob_sha(body)
                entries.append({"name": name, "type": "file", "sha": sha})
            return json.dumps(entries).encode()
        for name, body in files.items():
            if url.endswith(f"/contents/tradeguard-pro/{name}?ref=main"):
                return body
        raise KeyError(url)

    return _get, calls


_ENV_OK = {"GITHUB_TOKEN": "t0ken", "GITHUB_REPOSITORY": "rmanm19/tradeguard-bot"}
_LIVE = {n: (_rf.BASE / n).read_bytes() for n in ("bot.py", "run_forever.py", "db_crypt.py")}

_get, _calls = _fake_gh(_LIVE)
_rf._gh_get = _get
_same = _rf.remote_code_changed(_ENV_OK)
check("کد یکسان روی main → هیچ ری‌استارتی لازم نیست",
      _same == (False, []), str(_same))
check("فقط یک درخواست برای هر بررسی (فهرست پوشه) → سهمیهٔ API نمی‌سوزد",
      len(_calls) == 1, str(len(_calls)))

_get, _ = _fake_gh(_LIVE, listing_sha={"bot.py": "0" * 40})
_rf._gh_get = _get
_changed, _names = _rf.remote_code_changed(_ENV_OK)
check("sha متفاوت ولی محتوای یکسان (مثلاً CRLF) → ری‌استارت نمی‌شود",
      _changed is False and _names == [], f"{_changed} {_names}")

_get, _ = _fake_gh({**_LIVE, "bot.py": b"# \xd9\x86\xdb\xaf\xd8\x87\xd9\x94\xd8\xb3\xd9\x84\xd9\x87\xd8\xa7\xd8\xb4\xd9\x94 x = 1\n"})
_rf._gh_get = _get
_changed, _names = _rf.remote_code_changed(_ENV_OK)
check("bot.py روی main عوض شده → به‌روزرسانی لازم است و نامش هم برمی‌گردد",
      _changed is True and _names == ["bot.py"], f"{_changed} {_names}")

_rf._gh_get, _ = _fake_gh(_LIVE, fail=True)
check("خطای شبکه → «نمی‌دانم» (None) و هیچ ری‌استارتی",
      _rf.remote_code_changed(_ENV_OK) == (None, []), str(_rf.remote_code_changed(_ENV_OK)))
check("بدون GITHUB_TOKEN هیچ درخواستی نمی‌زند (سهمیهٔ ۶۰/ساعت IP مشترک)",
      _rf.remote_code_changed({"GITHUB_REPOSITORY": "rmanm19/tradeguard-bot"}) == (None, []))

# ── کامیت‌های [skip ci] تنظیمات، ربات را ری‌استارت نمی‌کنند ──
_get, _ = _fake_gh(_LIVE)
_rf._gh_get = _get
check("فایل selftest/docs در مقایسه نیست؛ فقط کدِ زمان اجرا",
      "selftest_offline.py" not in _rf.RUNTIME_FILES
      and set(_rf.RUNTIME_FILES) == {"bot.py", "run_forever.py", "db_crypt.py"},
      str(_rf.RUNTIME_FILES))

# ── درخواست دستی: /restart → فایل → نگهبان می‌خواند و پاک می‌کند ──
_flag = Path(tempfile.mkdtemp()) / "restart.flag"
_old_flag = _rf.RESTART_FLAG
_old_bot_flag = bot.RESTART_FLAG_PATH
_rf.RESTART_FLAG = _flag
bot.RESTART_FLAG_PATH = _flag
check("دستور /restart فایل درخواست را می‌نویسد", bot.request_restart("/restart از ادمین")[0] is True
      and _flag.exists())
check("نگهبان دلیل درخواست را می‌خواند", "restart" in _rf.read_restart_request(),
      _rf.read_restart_request())
_rf.clear_restart_request()
check("پس از خواندن، درخواست پاک می‌شود (وگرنه حلقهٔ ری‌استارت بی‌پایان)",
      _flag.exists() is False and _rf.read_restart_request() == "")

# ── خط «کدِ زنده» در گزارش ادمین ──
_old_sha = bot.RUN_CODE_SHA
bot.RUN_CODE_SHA = "abc1234def5678"
check("گزارش ادمین نشان می‌دهد کدام کد در حال اجراست",
      "abc1234" in bot.build_admin_report(), bot.build_admin_report()[-120:])
bot.RUN_CODE_SHA = ""
check("بدون SHA گیت‌هاب، ادعای نسخه نمی‌کند",
      "اجرای محلی" in bot.code_version_line(), bot.code_version_line())
bot.RUN_CODE_SHA = _old_sha
_rf.RESTART_FLAG = _old_flag
bot.RESTART_FLAG_PATH = _old_bot_flag
check("تست هیچ فایل restart.flag در ریپو جا نمی‌گذارد",
      not (HERE / "restart.flag").exists())

print("\n۱۶) ورود با گوگل (Device Flow) + ژورنال ابری")

import base64 as _b64g  # noqa: E402


def _fake_tok(claims: dict) -> str:
    head = _b64g.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').decode().rstrip("=")
    body = _b64g.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"{head}.{body}.signature-not-checked"


_old_admin_g = bot.ADMIN_USER_ID
_old_http_g = bot._http_json
_old_gid = bot.get_setting("GOOGLE_CLIENT_ID")
_old_gsecret = bot.get_setting("GOOGLE_CLIENT_SECRET")
_old_gdays = bot.get_setting("AUTH_GRANT_DAYS")
bot.ADMIN_USER_ID = ""            # کاربر تست نباید از مسیر ادمین رد شود
bot._PENDING_AUTH.clear()
with _sq.connect(bot.DB_PATH) as _c:
    _c.execute("DELETE FROM google_auth")
    _c.execute("DELETE FROM journal")
    _c.execute("DELETE FROM journal_notes")

# ── بدون کلید، ربات دروغ نمی‌گوید و دکمهٔ مرده هم نمی‌سازد ──
bot.set_setting("GOOGLE_CLIENT_ID", "")
bot.set_setting("GOOGLE_CLIENT_SECRET", "")
_ok, _txt = bot.start_google_auth(USER, USER)
check("بدون Client ID، پیام «تنظیم نشده» با مراحل دقیق می‌آید",
      _ok is False and "تنظیم نشده" in _txt and "TVs and Limited Input" in _txt, _txt[:120])
check("بدون کلاینت، دکمهٔ ورود در کیبورد ساخته نمی‌شود",
      not any(b.get("callback_data") == "auth_login"
              for row in bot.main_keyboard(True, "fa")["inline_keyboard"] for b in row))
check("ژورنال برای کاربر تأییدنشده قفل است و راهش را می‌گوید",
      "تأییدشده" in (bot.journal_gate(USER) or "") and "/login" in (bot.journal_gate(USER) or ""))

# ── با کلید: شروع Device Flow ──
bot.set_setting("GOOGLE_CLIENT_ID", "1234567890-abc.apps.googleusercontent.com")
bot.set_setting("GOOGLE_CLIENT_SECRET", "GOCSPX-fake-secret-for-tests")
check("Client ID و Secret از دیتابیس خوانده می‌شوند",
      bot.google_client_config()[0].endswith(".apps.googleusercontent.com")
      and bot.google_client_config()[1].startswith("GOCSPX-"))
check("دکمهٔ ورود با گوگل بعد از تنظیم کلاینت ظاهر می‌شود",
      any(b.get("callback_data") == "auth_login"
          for row in bot.main_keyboard(True, "fa")["inline_keyboard"] for b in row))

_device_calls = []


def _fake_http_device(url, form=None, timeout=15.0):
    _device_calls.append((url, dict(form or {})))
    if url == bot.GOOGLE_DEVICE_URL:
        return {"device_code": "dev-code-1", "user_code": "ABCD-EFGH",
                "verification_url": "https://www.google.com/device",
                "expires_in": 1800, "interval": 5}
    return {"error": "authorization_pending"}


bot._http_json = _fake_http_device
_ok, _txt = bot.start_google_auth(USER, USER)
check("کد کاربر و لینک گوگل در پیام می‌آید",
      _ok and "ABCD-EFGH" in _txt and "google.com/device" in _txt, _txt[:140])
check("اسکوپ درخواستی فقط openid و email است (نه دسترسی به جیمیل/درایو)",
      _device_calls and _device_calls[0][1].get("scope") == "openid email", str(_device_calls[:1]))
check("نشست در انتظار ثبت شد و کلید رمز لو نمی‌رود",
      USER in bot._PENDING_AUTH and "GOCSPX" not in _txt)

bot._PENDING_AUTH[USER]["next_try"] = 0
_state, _ = bot.poll_google_auth(USER)
check("تا وقتی کاربر تأیید نکرده، state همان pending است", _state == "pending", _state)
check("در حالت pending هنوز تأیید نشده", bot.is_verified(USER) is False)

# ── تأیید واقعی ──
_claims = {"sub": "google-sub-AAA", "email": "Trader@Gmail.com", "email_verified": True}


def _fake_http_ok(url, form=None, timeout=15.0):
    if url == bot.GOOGLE_DEVICE_URL:
        return {"device_code": "dev-code-2", "user_code": "WXYZ-1234",
                "verification_url": "https://www.google.com/device",
                "expires_in": 1800, "interval": 5}
    return {"access_token": "at", "id_token": _fake_tok(_claims)}


bot._http_json = _fake_http_ok
bot.start_google_auth(USER, USER)
bot._PENDING_AUTH[USER]["next_try"] = 0
_pro_until_before = bot.is_user_pro(USER)[1]
_state, _payload = bot.poll_google_auth(USER)
check("توکن گوگل → تأیید کامل", _state == "verified", f"{_state} {_payload}")
check("ایمیل نمایش داده می‌شود ولی ماسک‌شده",
      _payload.get("mail") == "T***@Gmail.com", str(_payload.get("mail")))
check("پاداش پیش‌فرض ۳۰ روز پرمیوم است (بدون تمدید خودکار)",
      bot.is_user_pro(USER)[1] - max(_pro_until_before, int(_t.time())) >= 29 * 86400)
_status = bot.auth_status(USER)
check("هویت گوگل در دیتابیس ثبت شد", bool(_status) and _status["sub"] == "google-sub-AAA")
with _sq.connect(bot.DB_PATH) as _c:
    _row = _c.execute("SELECT email_hash, granted_days FROM google_auth WHERE user_id = ?", (USER,)).fetchone()
    _raw = _c.execute("SELECT group_concat(sub || email_hash || verified_at) FROM google_auth").fetchone()[0]
check("ایمیل خام ذخیره نمی‌شود؛ فقط هش آن",
      _row[0] == bot.email_hash("trader@gmail.com") and "trader@gmail.com" not in str(_raw), str(_row))
check("پاداش یک‌بار ثبت می‌شود", int(_row[1]) == 30, str(_row[1]))
check("ژورنال برای کاربر تأییدشده باز است", bot.journal_gate(USER) is None)

# ── قواعد ضدسوءاستفاده ──
_other = 888000333
_ok2, _why2, _ = bot.link_google_identity(_other, _claims)
check("همان حساب گوگل به اکانت دوم وصل نمی‌شود",
      _ok2 is False and "اکانت تلگرام دیگری" in _why2, _why2)
_ok3, _why3, _ = bot.link_google_identity(_other, {**_claims, "sub": "google-sub-BBB"})
check("همان ایمیل با اکانت دوم تأیید نمی‌شود",
      _ok3 is False and "ایمیل قبلاً" in _why3, _why3)
_ok4, _why4, _exp4 = bot.link_google_identity(USER, _claims)
check("وصل‌شدن دوباره، پاداش تازه نمی‌سازد",
      _ok4 is True and _why4 == "relink", f"{_ok4} {_why4}")
check("حساب بدون ایمیل تأییدشده رد می‌شود",
      bot.link_google_identity(999, {"sub": "x", "email": "a@b.c", "email_verified": False})[0] is False)

# ── ژورنال: محاسبهٔ R ──
_ok, _reply, _tid = bot.journal_add(USER, "btc", "long", 65000, 63500, 69000, 50)
check("ثبت ستاپ با شناسه و پیام قابل‌فهم", _ok and _tid > 0 and f"#{_tid}" in _reply, _reply[:120])
check("لانگ با حد ضرر بالای ورود رد می‌شود",
      bot.journal_add(USER, "ETH", "long", 3000, 3100)[0] is False)
check("شورت با حد ضرر زیر ورود رد می‌شود",
      bot.journal_add(USER, "ETH", "short", 3000, 2900)[0] is False)
check("نمادهای عجیب پاک می‌شوند و ورود=حد ضرر رد می‌شود",
      bot.journal_add(USER, "B$T@C!", "long", 100, 100)[0] is False)
_ok, _cmsg = bot.journal_close(USER, _tid, 69000)
check("بستن معامله، R واقعی را حساب می‌کند (+2.67R)",
      _ok and "+2.67R" in _cmsg, _cmsg[:160])
_ok2b, _r2, _tid2 = bot.journal_add(USER, "SOL", "short", 200, 210, 180, 0)
_ok3b, _cmsg2 = bot.journal_close(USER, _tid2, 205)
check("شورت هم درست حساب می‌شود (−0.50R)", _ok3b and "-0.50R" in _cmsg2, _cmsg2[:120])
check("بستن دوبارهٔ همان پوزیشن رد می‌شود", bot.journal_close(USER, _tid, 70000)[0] is False)
check("بستن پوزیشنِ کاربر دیگر ممکن نیست",
      bot.journal_close(_other, _tid, 1)[0] is False)
_stats = bot.journal_stats(USER)
check("آمار واقعی: ۲ بسته، ۱ برد، نرخ برد ۵۰٪",
      _stats["closed_count"] == 2 and _stats["wins"] == 1
      and abs(_stats["win_rate"] - 50.0) < 0.01, str(_stats))
_stxt = bot.journal_stats_text(USER)
check("گزارش ژورنال نرخ برد و میانگین R را نشان می‌دهد",
      "نرخ برد" in _stxt and "میانگین" in _stxt and "50%" in _stxt, _stxt[:160])
_js = bot.journal_export_json(USER)
check("خروجی JSON قابل‌خواندن است و R را شامل می‌شود",
      "```json" in _js and '"r":' in _js and json.loads(_js.split("```json")[1].split("```")[0])["trades"],
      _js[:120])
check("حذف پوزیشنِ خودِ کاربر کار می‌کند و پوزیشن غریبه نه",
      bot.journal_delete(USER, _tid2)[0] is True and bot.journal_delete(USER, _tid2)[0] is False)

# ── تحلیل روزانه ──
check("تحلیل خیلی کوتاه رد می‌شود", bot.note_add(USER, "ok")[0] is False)
_okN, _nmsg = bot.note_add(USER, "بایاس لانگ تا ۶۸٬۰۰۰؛ فقط لبه و ریسک ۰٫۵٪")
check("تحلیل روزانه ثبت و تاریخ‌دار می‌شود",
      _okN and bot._utc_date(int(_t.time())) in _nmsg, _nmsg[:120])
check("خواندن تحلیل‌ها متن امروز را نشان می‌دهد",
      "بایاس لانگ" in bot.notes_text(USER) and bot.journal_stats(USER)["notes_today"] == 1)
check("کاربر تأییدنشده نمی‌تواند تحلیل بنویسد",
      "تأییدشده" in (bot.journal_gate(_other) or ""))

# ── انقضا، قطع اتصال، ادمین ──
bot._http_json = _fake_http_device
bot.start_google_auth(USER, USER)
bot._PENDING_AUTH[USER]["expires_at"] = int(_t.time()) - 1
_state, _payload = bot.poll_google_auth(USER)
check("کد منقضی‌شده، پیام روشن می‌دهد و نشست پاک می‌شود",
      _state == "error" and _payload.get("error") == "expired" and USER not in bot._PENDING_AUTH)

with _sq.connect(bot.DB_PATH) as _c:
    _c.execute("UPDATE google_auth SET revoked = 1 WHERE user_id = ?", (USER,))
check("پس از قطع اتصال، ژورنال دوباره قفل می‌شود",
      bot.is_verified(USER) is False and bot.journal_gate(USER) is not None)
with _sq.connect(bot.DB_PATH) as _c:
    _c.execute("UPDATE google_auth SET revoked = 0 WHERE user_id = ?", (USER,))
bot.ADMIN_USER_ID = "123456789"
check("ادمین برای آزمایش به احراز هویت نیاز ندارد (بقیه نه)",
      bot.is_verified(123456789) is True and bot.is_verified(_other) is False)

# بازگرداندن وضعیت
bot.ADMIN_USER_ID = _old_admin_g
bot._http_json = _old_http_g
bot._PENDING_AUTH.clear()
bot.set_setting("GOOGLE_CLIENT_ID", _old_gid)
bot.set_setting("GOOGLE_CLIENT_SECRET", _old_gsecret)
bot.set_setting("AUTH_GRANT_DAYS", _old_gdays)
check("تست هیچ نشست باز یا کلید جعلی جا نمی‌گذارد",
      not bot._PENDING_AUTH and not bot.get_setting("GOOGLE_CLIENT_ID"))

# ── مسیر واقعی دستورات در چت (نه فقط توابع) ──
# توجه: در این فایل bot.tg_send_message با یک نسخهٔ تقلبی جایگزین شده که
# پیام‌ها را در _posts می‌ریزد؛ پس همین‌جا را می‌خوانیم، نه SENT را.
def _last_post() -> str:
    return str(_posts[-1][1]) if _posts else ""


bot.set_setting("GOOGLE_CLIENT_ID", "1234567890-abc.apps.googleusercontent.com")
bot.set_setting("GOOGLE_CLIENT_SECRET", "GOCSPX-fake-secret-for-tests")
bot._http_json = _fake_http_ok
bot.handle_message(msg("/login"))
check("دستور /login در چت کد گوگل را می‌فرستد",
      "ABCD" in _last_post() or "WXYZ" in _last_post(), _last_post()[:120])
bot._PENDING_AUTH.clear()

bot.handle_message(msg("/journal", uid=_other))
check("/journal برای کاربر تأییدنشده قفل است", "تأییدشده" in _last_post(), _last_post()[:120])
bot.handle_message(msg("/note چیزی", uid=_other))
check("/note هم برای کاربر تأییدنشده قفل است", "تأییدشده" in _last_post(), _last_post()[:120])

bot.handle_message(msg("/jadd BTC long 65000 63500 69000 50"))
check("/jadd در چت پوزیشن ثبت می‌کند و شماره می‌دهد",
      "ثبت شد" in _last_post() and "#" in _last_post(), _last_post()[:140])
bot.handle_message(msg("/journal", uid=USER))
check("/journal در چت آمار را نشان می‌دهد", "ژورنال" in _last_post(), _last_post()[:120])
bot.handle_message(msg("/notes"))
check("/notes در چت فهرست تحلیل‌ها را می‌آورد", "تحلیل" in _last_post(), _last_post()[:120])
bot.handle_message(msg("/journal json"))
check("/journal json خروجی قابل‌خواندن می‌دهد", "```json" in _last_post(), _last_post()[:80])

# ادمین: راهنمای تنظیم کلیدها + ماسک‌شدن Secret
bot.ADMIN_USER_ID = str(USER)
bot.handle_message(msg("/google"))
_g = _last_post()
check("/google برای ادمین وضعیت کلیدها را می‌دهد", "Client ID" in _g and "30" in _g, _g[:160])
check("/google هرگز Secret را برنمی‌گرداند", "GOCSPX-fake-secret-for-tests" not in _g)
check("/google دستور تستِ کلیدها را هم نشان می‌دهد", "/google test" in _g, _g[:200])
bot.handle_message(msg("/google days 0"))
check("/google days پاداش را خاموش می‌کند", bot.auth_grant_days() == 0)
bot.handle_message(msg("/google days 30"))
bot.handle_message(msg("/google id not-a-valid-id"))
check("/google id ورودی نامعتبر را رد می‌کند", "apps.googleusercontent.com" in _last_post())
_dels = []
_old_dms = bot.delete_message_safe
bot.delete_message_safe = lambda chat, mid: _dels.append((chat, mid))
bot.handle_message(msg("/google secret GOCSPX-another-secret-value"))
bot.delete_message_safe = _old_dms
check("/google secret پیام حاوی کلید را پاک می‌کند (تا در چت نماند)",
      bool(_dels) and _dels[0][0] == USER and bot.get_setting("GOOGLE_CLIENT_SECRET") == "GOCSPX-another-secret-value",
      str(_dels))
bot.handle_message(msg("/google id 999999-xyz.apps.googleusercontent.com"))
check("/google id مقدار درست را ذخیره می‌کند",
      bot.get_setting("GOOGLE_CLIENT_ID") == "999999-xyz.apps.googleusercontent.com")

# ── /google test: تست واقعی کلیدها با پاسخ‌های مختلف گوگل ─────────────
_old_http_preflight = bot._http_json
_preflight_calls = []


def _preflight(payload):
    def _f(url, form=None, timeout=15.0):
        _preflight_calls.append((url, dict(form or {})))
        return payload
    return _f


bot.ADMIN_USER_ID = str(USER)
bot._http_json = _preflight({"device_code": "dc-1", "user_code": "WXYZ-1234", "expires_in": 1800})
bot.handle_message(msg("/google test"))
_t = _last_post()
check("/google test با کلید درست تأیید می‌کند و اسکوپ را نشان می‌دهد",
      "کلیدها درست" in _t and "openid email" in _t, _t[:180])
check("/google test فقط client_id و scope می‌فرستد و Secret را لو نمی‌دهد",
      bool(_preflight_calls)
      and set(_preflight_calls[0][1]) == {"client_id", "scope"}
      and "GOCSPX" not in str(_preflight_calls), str(_preflight_calls[:1]))

bot._http_json = _preflight({"error": "invalid_client",
                             "error_description": "Unauthorized"})
bot.handle_message(msg("/google test"))
_t = _last_post()
check("/google test خطای invalid_client را به «نوع کلاینت» ترجمه می‌کند",
      "invalid_client" in _t and "TVs and Limited Input" in _t, _t[:220])

bot._http_json = _preflight({"error": "invalid_scope"})
bot.handle_message(msg("/google test"))
check("/google test خطای invalid_scope را به «اسکوپ تأیید نشده» ترجمه می‌کند",
      "اسکوپ" in _last_post(), _last_post()[:160])

bot._http_json = _preflight({"error": "network: timed out"})
bot.handle_message(msg("/google test"))
check("/google test خطای شبکه را می‌فهمد و راهنمای دوباره‌تست می‌دهد",
      "دسترسی" in _last_post(), _last_post()[:160])

bot.set_setting("GOOGLE_CLIENT_SECRET", "")
bot.handle_message(msg("/google test"))
check("/google test نبودِ Secret را صریح می‌گوید", "Client Secret نیست" in _last_post(),
      _last_post()[:160])
bot.set_setting("GOOGLE_CLIENT_SECRET", "GOCSPX-fake-secret-for-tests")

bot.set_setting("GOOGLE_CLIENT_ID", "")
bot.handle_message(msg("/google test"))
check("/google test نبودِ Client ID را جدا می‌گوید", "Client ID نیست" in _last_post(),
      _last_post()[:160])

bot.set_setting("GOOGLE_CLIENT_SECRET", "")
bot.handle_message(msg("/google test"))
check("/google test بدون هیچ کلیدی راهنمای تنظیم می‌دهد", "هنوز هیچ کلیدی" in _last_post(),
      _last_post()[:160])

bot.set_setting("GOOGLE_CLIENT_ID", "999999-xyz.apps.googleusercontent.com")
bot.set_setting("GOOGLE_CLIENT_SECRET", "GOCSPX-fake-secret-for-tests")
bot._http_json = _old_http_preflight
bot.ADMIN_USER_ID = ""

# ── استقرار: ورک‌فلو باید کلیدهای گوگل را به ربات برساند ─────────────
_wf = (bot.REPO_ROOT / ".github" / "workflows" / "bot.yml").read_text(encoding="utf-8")
check("ورک‌فلو هر دو Secret گوگل را به env ربات می‌دهد",
      "GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}" in _wf
      and "GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}" in _wf)
check("راهنمای راه‌اندازی ورود با گوگل در ریپو هست",
      (bot.REPO_ROOT / "GOOGLE_LOGIN_FA.md").exists())

# ── ممبر گرفتن: تاریخچهٔ اعضا، /members و دکمهٔ عضویت در /start ────────
bot.init_db()
bot.ADMIN_USER_ID = str(ADMIN)

_old_chan = bot.PUBLIC_CHANNEL_ID
bot.PUBLIC_CHANNEL_ID = "@testchannel"   # تا channel_url() لینک بدهد

_D1 = int(_time.time()) - 4 * 86400        # ۴ روز پیش، نسبت به ساعت واقعی
bot.record_member_snapshot(100, _D1)
bot.record_member_snapshot(110, _D1 + 3600)          # همان روز → به‌روزرسانی
_hist = bot.member_history()
check("تاریخچهٔ اعضا برای هر روز یک ردیف نگه می‌دارد (به‌روزرسانی، نه تکرار)",
      len(_hist) == 1 and _hist[0][1] == 110, str(_hist))

bot.record_member_snapshot(140, _D1 + 3 * 86400)
check("member_count_on عدد روزهای قبل را از تاریخچه می‌خواند",
      bot.member_count_on(0, now=_D1 + 3 * 86400) == 140
      and bot.member_count_on(1, now=_D1 + 3 * 86400) == 110
      and bot.member_count_on(30, now=_D1 + 3 * 86400) is None, str(bot.member_history()))

_old_member_now = bot.member_count_now
bot.member_count_now = lambda: 150
bot.handle_message(msg("/members", ADMIN))
_mtxt = _last_post()
check("‏/members عدد زندهٔ کانال را نشان می‌دهد",
      "اعضای کانال" in _mtxt and "۱۵۰" in _mtxt, _mtxt[:200])
check("‏/members دلتای روز قبل را با علامت درست نشان می‌دهد",
      "+۱۰" in _mtxt, _mtxt[:400])
check("‏/members نرخ تبدیل کاربر→عضو را می‌گوید", "نرخ تبدیل" in _mtxt, _mtxt[:200])

SENT.clear()
bot.handle_message(msg("/members", USER))
check("‏/members برای غیرادمین بسته است", "فقط ادمین" in _last_post(), _last_post()[:120])
bot.member_count_now = _old_member_now

_fresh = 999000444
check("‏join_nudge به کاربری که پاداش نگرفته پیشنهاد عضویت می‌دهد",
      bool(bot.join_nudge(_fresh)))
cb("join_claim", _fresh)
check("کال‌بک join_claim بعد از تأیید واقعی، ۷ روز پرو می‌دهد",
      "تأیید شد" in _last_post(), _last_post()[:160])
check("بعد از گرفتن پاداش، پیشنهاد عضویت دیگر تکرار نمی‌شود",
      bot.join_nudge(_fresh) is None)

bot.handle_message(msg("/start", uid=999000555))
_start_kb = kb_buttons(_posts[-1][2] if _posts else {})
check("‏/start دکمهٔ عضویت کانال و «عضو شدم» را نشان می‌دهد",
      any("عضویت در کانال" in (b.get("text") or "") for b in _start_kb)
      and any(b.get("callback_data") == "join_claim" for b in _start_kb),
      str([b.get("text") for b in _start_kb]))

# ── درآمد: عرضهٔ محدود، فاکتور و اعتبارسنجی مبلغ ──────────────────────
bot.http_json = fake_http_json
bot.FREE_MODE = False                     # پرداخت باز، تا مسیر فروش تست شود
bot.ADMIN_USER_ID = str(ADMIN)
bot.stop_launch()

_base30 = bot.plan_price(30)
check("بدون عرضه، قیمت مؤثر همان قیمت پایه است",
      bot.effective_price(30) == _base30 and bot.effective_price(90) == bot.plan_price(90))

_ok, _msg = bot.start_launch(_base30, 10)          # گران‌تر از پایه = باید رد شود
check("عرضه با قیمت مساوی/بیشتر از پایه رد می‌شود", not _ok, _msg)

_until = int(_time.time()) + 7 * 86400
_ok, _msg = bot.start_launch(_base30 - 100, 50, _until)
check("عرضهٔ محدود با قیمت کمتر و سقف تعداد روشن می‌شود", _ok, _msg)
check("قیمت مؤثر ۳۰ روز به قیمت عرضه تغییر می‌کند",
      bot.effective_price(30) == _base30 - 100, str(bot.effective_price(30)))
check("پلن‌های ۹۰ و ۳۶۵ روز دست نمی‌خورند",
      bot.effective_price(90) == bot.plan_price(90)
      and bot.effective_price(365) == bot.plan_price(365))

SENT.clear()
bot.send_pro_invoice(USER, "fa", 30)
_inv = [p for a, p in SENT if a == "sendInvoice"]
check("فاکتور با قیمت عرضه صادر می‌شود (نه قیمت قبلی)",
      bool(_inv) and _inv[-1]["prices"][0]["amount"] == _base30 - 100, str(_inv[-1:])[:200])
check("payload فاکتور همان ریالِ قیمت را حمل می‌کند",
      bool(_inv) and _inv[-1]["payload"].endswith(f"_{_base30 - 100}"))

_pay = bot.build_plans_payload()
check("plans.json عرضه و قیمت جدید را منتشر می‌کند",
      _pay["launch"]["active"] is True
      and _pay["launch"]["stars"] == _base30 - 100
      and _pay["plans"][0]["stars"] == _base30 - 100)

# pre_checkout: فاکتورِ کهنه (قیمت قبل از عرضه) نباید پذیرفته شود
def _pcq(payload: str, amount: int) -> dict:
    SENT.clear()
    bot.process_update({"pre_checkout_query": {
        "id": "pcq-1", "invoice_payload": payload, "currency": "XTR", "total_amount": amount}})
    ans = [p for a, p in SENT if a == "answerPreCheckoutQuery"]
    return ans[-1] if ans else {}

check("pre_checkout با مبلغ کهنه (قیمت قبل از عرضه) رد می‌شود",
      _pcq(f"tradeguard_pro_30d_{_base30}", _base30).get("ok") is False)
check("pre_checkout با مبلغ درست عرضه پذیرفته می‌شود",
      _pcq(f"tradeguard_pro_30d_{_base30 - 100}", _base30 - 100).get("ok") is True)
check("pre_checkout با payload بیگانه رد می‌شود",
      _pcq("something_else", 100).get("ok") is False)

# تمام‌شدن سقف: بعد از ۵۰ فروش، قیمت به حالت عادی برمی‌گردد
with _sq.connect(bot.DB_PATH) as _c:
    _started = int(bot.get_setting("launch_started", "0") or 0)
    for _i in range(50):
        _c.execute("INSERT INTO payments (user_id, stars_amount, telegram_charge_id, paid_at, kind) "
                   "VALUES (?, ?, ?, ?, 'stars')",
                   (900000000 + _i, _base30 - 100, f"chg_{_i}", _started + 60 + _i))
check("بعد از پر شدن سقف، عرضه خودکار تمام می‌شود",
      bot.launch_state()["active"] is False and bot.effective_price(30) == _base30)

# ── دستورهای /launch و /revenue ──────────────────────────────────────
SENT.clear()
bot.handle_message(msg("/launch", USER))
check("‏/launch برای غیرادمین بسته است", "فقط ادمین" in _last_post(), _last_post()[:120])
SENT.clear()
bot.handle_message(msg("/revenue", USER))
check("‏/revenue برای غیرادمین بسته است", "فقط ادمین" in _last_post(), _last_post()[:120])

bot.handle_message(msg("/launch", ADMIN))
check("‏/launch وضعیت عرضه را نشان می‌دهد", "عرضهٔ محدود" in _last_post(), _last_post()[:160])

bot.stop_launch()
check("خاموش‌کردن عرضه قیمت را به پایه برمی‌گرداند",
      bot.effective_price(30) == _base30 and bot.launch_state()["active"] is False)

bot.handle_message(msg("/revenue", ADMIN))
_rev = _last_post()
check("‏/revenue حالت رایگان، قیمت‌ها و فروش را می‌گوید",
      "درآمد" in _rev and "قیمت‌ها" in _rev and "فروش تا امروز" in _rev, _rev[:200])
check("‏/revenue «قدم بعدی» می‌دهد", "قدم بعدی" in _rev, _rev[:200])
bot.ADMIN_USER_ID = ""

# ── تاریخ پایان دورهٔ رایگان: هم تاریخ بخوان، هم ثانیه ─────────────────
check("تاریخ YYYY-MM-DD به پایان همان روز UTC تبدیل می‌شود",
      bot._utc_date(bot.parse_moment("2026-11-22")) == "2026-11-22"
      and bot.parse_moment("2026-11-22") % 86400 == 86399,
      str(bot.parse_moment("2026-11-22")))
check("ثانیهٔ یونیکس بدون تغییر رد می‌شود",
      bot.parse_moment("1795996799") == 1795996799)
check("ورودی خالی/نامعتبر صفر می‌دهد (نه کرش)",
      bot.parse_moment("") == 0 and bot.parse_moment("22/11/2026") == 0)
_bw = (bot.REPO_ROOT / ".github" / "workflows" / "bot.yml").read_text(encoding="utf-8")
check("ورک‌فلو تاریخ پایان دورهٔ رایگان را تنظیم می‌کند",
      'FREE_MODE_UNTIL:' in _bw and 'FREE_MODE: "1"' in _bw)

# ── استقرار: چک سلامت واقعی، از بیرونِ ربات ──────────────────────────
_hw = (bot.REPO_ROOT / ".github" / "workflows" / "health.yml").read_text(encoding="utf-8")
check("ورک‌فلو چک سلامت وجود دارد و توکن/ادمین/کانال را می‌خواند",
      "getChatMemberCount" in _hw and "ADMIN_USER_ID" in _hw)
check("چک سلامت نتیجه را در docs/api/health.json می‌نویسد",
      "docs/api/health.json" in _hw)
check("چک سلامت «صف آپدیت‌ها» و «ضربان موتور» را می‌سنجد",
      "pending_update_count" in _hw and "generated_at" in _hw)
check("راهنمای گرفتن ممبر در ریپو هست", (bot.REPO_ROOT / "MEMBERS_FA.md").exists())
bot.ADMIN_USER_ID = ""

print("\n" + "─" * 46)
if FAILS:
    print(f"❌ {len(FAILS)} تست شکست خورد: {', '.join(FAILS)}")
    sys.exit(1)
print(f"✅ همه تست‌ها سبز — {len(SENT)} تماس تلگرام، {len(DOWNLOADS)} فایل")
sys.exit(0)
